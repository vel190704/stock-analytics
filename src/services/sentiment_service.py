from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import anthropic
import httpx

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class ScoredHeadline:
    headline: str
    score: Decimal
    label: str
    reason: str
    source_url: str


def _normalise_label(score: float, label: str | None) -> str:
    if label and label.lower() in {"bullish", "bearish", "neutral"}:
        return label.lower()
    if score > 0.55:
        return "bullish"
    if score < 0.45:
        return "bearish"
    return "neutral"


def parse_sentiment_response(raw_text: str) -> list[dict[str, object]]:
    """Parse Claude response and coerce it into the expected JSON array."""
    payload_text = raw_text.strip()
    if payload_text.startswith("```"):
        payload_text = payload_text.strip("`")
        payload_text = payload_text.replace("json\n", "", 1).strip()

    if "[" in payload_text and "]" in payload_text:
        start = payload_text.find("[")
        end = payload_text.rfind("]") + 1
        payload_text = payload_text[start:end]

    parsed = json.loads(payload_text)
    if not isinstance(parsed, list):
        raise ValueError("Claude sentiment response was not a list")

    normalised: list[dict[str, object]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        headline = str(item.get("headline", "")).strip()
        reason = str(item.get("reason", "")).strip()
        score = float(item.get("score", 0.5))
        score = min(1.0, max(0.0, score))
        label = _normalise_label(score, str(item.get("label", "")).strip() or None)
        if headline:
            normalised.append(
                {
                    "headline": headline,
                    "score": score,
                    "label": label,
                    "reason": reason,
                }
            )
    return normalised


async def fetch_news_headlines(ticker: str) -> list[dict[str, str]]:
    """Fetch recent headlines for ticker from NewsAPI."""
    api_key = settings.newsapi_key.strip()
    if not api_key:
        logger.info("newsapi_key_missing", ticker=ticker)
        return []

    since = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    params = {
        "q": ticker,
        "from": since,
        "sortBy": "publishedAt",
        "pageSize": 10,
        "language": "en",
        "apiKey": api_key,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get("https://newsapi.org/v2/everything", params=params)
        response.raise_for_status()
        payload = response.json()

    articles = payload.get("articles", [])
    headlines: list[dict[str, str]] = []
    for article in articles:
        title = str(article.get("title", "")).strip()
        url = str(article.get("url", "")).strip()
        if not title:
            continue
        headlines.append({"headline": title, "source_url": url})

    return headlines[:10]


async def fetch_and_score_sentiment(ticker: str) -> list[ScoredHeadline]:
    """Fetch news headlines and score sentiment in one Claude API batch call."""
    headlines = await fetch_news_headlines(ticker)
    if not headlines:
        return []

    anthropic_key = settings.anthropic_api_key.strip()
    if not anthropic_key:
        logger.info("anthropic_key_missing_for_sentiment", ticker=ticker)
        return []

    headlines_text = "\n".join(
        f"- {item['headline']}" for item in headlines
    )

    client = anthropic.AsyncAnthropic(api_key=anthropic_key)
    prompt = f"""
Score the sentiment of these {ticker} news headlines.
For each headline, respond with a JSON array of objects:
{{"headline": "...", "score": 0.85, "label": "bullish|bearish|neutral", "reason": "..."}}
score is 0.0 (very bearish) to 1.0 (very bullish). 0.5 is neutral.
Respond ONLY with valid JSON. No preamble.

Headlines:
{headlines_text}
""".strip()

    message = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
    )

    blocks = getattr(message, "content", [])
    text_parts: list[str] = []
    for block in blocks:
        if getattr(block, "type", "") == "text" and getattr(block, "text", ""):
            text_parts.append(block.text)

    scored_json = parse_sentiment_response("\n".join(text_parts))
    source_by_headline = {item["headline"]: item["source_url"] for item in headlines}

    results: list[ScoredHeadline] = []
    for item in scored_json:
        headline = str(item["headline"])
        score = Decimal(str(item["score"])).quantize(Decimal("0.0001"))
        label = str(item["label"])
        reason = str(item["reason"])
        source_url = source_by_headline.get(headline, "")
        results.append(
            ScoredHeadline(
                headline=headline,
                score=score,
                label=label,
                reason=reason,
                source_url=source_url,
            )
        )

    return results

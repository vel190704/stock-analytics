from __future__ import annotations

from dataclasses import dataclass

import anthropic

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class AlertEventContext:
    close: float
    pct_change: float
    volume: int
    vwap: float | None = None


async def analyse_price_event(ticker: str, event: AlertEventContext, rule: object) -> str:
    """Call Claude to generate a natural-language explanation of a fired alert."""
    api_key = settings.anthropic_api_key.strip()
    if not api_key:
        return (
            f"Alert fired for {ticker}: close {event.close:.2f} and "
            f"change {event.pct_change:.2f}% met your configured condition."
        )

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        prompt = f"""
Stock alert triggered for {ticker}.
Rule: price {getattr(rule, 'condition', 'condition')} ${getattr(rule, 'threshold', '0')}
Current price: ${event.close:.4f}
Price change: {event.pct_change:.2f}%
Volume: {event.volume:,}
VWAP: ${event.vwap if event.vwap is not None else 'N/A'}

In 2-3 sentences, explain what this price action suggests to a retail investor.
Be specific about the magnitude and context. Do not give financial advice.
""".strip()

        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=160,
            messages=[{"role": "user", "content": prompt}],
        )

        blocks = getattr(message, "content", [])
        text_parts: list[str] = []
        for block in blocks:
            if getattr(block, "type", "") == "text" and getattr(block, "text", ""):
                text_parts.append(block.text.strip())

        response_text = " ".join(part for part in text_parts if part)
        if response_text:
            return response_text
    except Exception as exc:
        logger.warning("claude_alert_analysis_failed", ticker=ticker, error=str(exc))

    return (
        f"Alert fired for {ticker}: close {event.close:.2f} and "
        f"change {event.pct_change:.2f}% matched the configured threshold."
    )

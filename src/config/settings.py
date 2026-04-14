from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "Stock Analytics API"
    environment: str = "development"
    log_level: str = "INFO"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "stock_prices"
    kafka_dlq_topic: str = "stock_prices_dlq"
    kafka_consumer_group: str = "stock-processor-group"

    # Database
    database_url: str = "postgresql+asyncpg://stockuser:stockpass@localhost:5432/stockdb"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    analytics_cache_ttl: int = 30

    # Data Source
    polygon_api_key: str = ""
    newsapi_key: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-1"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_from: str = "alerts@stockanalytics.local"

    tickers: list[str] = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "META",
        "NVDA",
        "JPM",
        "V",
        "NFLX",
    ]
    poll_interval_seconds: float = 1.0
    allow_simulated_data: bool = False

    @field_validator("tickers", mode="before")
    @classmethod
    def parse_tickers(cls, v: object) -> object:
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [t.strip() for t in v.split(",") if t.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

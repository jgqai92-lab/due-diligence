import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Point to the project root .env file (one level up from backend/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    database_url: str = "sqlite:///./data/skeptical_analyst.db"
    cache_ttl_hours: int = 24
    cors_origins: list[str] = [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
        "http://localhost:3002", "http://127.0.0.1:3002",
        "http://localhost:3003", "http://127.0.0.1:3003",
    ]
    claude_model: str = "claude-sonnet-4-20250514"
    claude_timeout: int = 120
    sec_edgar_user_agent: str = "SkepticalAnalyst research@example.com"

    model_config = {"env_file": str(ENV_FILE), "env_file_encoding": "utf-8"}


settings = Settings()

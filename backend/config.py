from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "AutoApply Web"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'autoapply.db'}"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h

    # Scraper settings
    SCRAPE_INTERVAL_MINUTES: int = 30
    APPLY_INTERVAL_SECONDS: int = 60  # delay between applications
    MAX_DAILY_APPLICATIONS: int = 50

    # Playwright
    HEADLESS: bool = True
    SLOW_MO: int = 100  # ms between actions (anti-detection)

    # Paths
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"

    class Config:
        env_file = ".env"


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

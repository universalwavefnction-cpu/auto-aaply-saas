from pathlib import Path

from pydantic_settings import BaseSettings

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

    # AI form filling
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemini-2.0-flash-001"

    # Residential proxy (for LinkedIn/Indeed — set in .env)
    PROXY_URL: str = ""  # e.g. "http://user:pass@gate.smartproxy.com:7000"

    # Gmail IMAP (for Indeed code-based login — set in .env)
    GMAIL_EMAIL: str = ""  # e.g. "you@gmail.com"
    GMAIL_APP_PASSWORD: str = ""  # 16-char app password from Google

    # Gmail IMAP for LinkedIn (separate account)
    GMAIL_EMAIL_LI: str = ""
    GMAIL_APP_PASSWORD_LI: str = ""

    # Paths
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"

    class Config:
        env_file = ".env"


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

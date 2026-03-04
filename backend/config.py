import secrets
import sys
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "AutoApply Web"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'autoapply.db'}"
    SECRET_KEY: str = "change-me-in-production"
    CREDENTIAL_KEY: str = ""  # Key for encrypting platform credentials (Fernet)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1h (was 24h)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SSE_TOKEN_EXPIRE_SECONDS: int = 60  # Short-lived SSE stream tokens

    # CORS — override in .env for production
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 10

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

    # Discovery API keys (optional — scrapers skip gracefully if empty)
    JOOBLE_API_KEY: str = ""  # Register at https://jooble.org/api/about
    ADZUNA_APP_ID: str = ""  # Register at https://developer.adzuna.com/
    ADZUNA_APP_KEY: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID: str = ""
    FRONTEND_URL: str = "https://jobs-autoapply.com"

    # Paths
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"

    class Config:
        env_file = ".env"


settings = Settings()

# ── Startup safety checks ────────────────────────────────────────────────

if settings.SECRET_KEY == "change-me-in-production":
    print(
        "\n[SECURITY] SECRET_KEY is still the default!"
        "\n  Generate one: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        "\n  Add to .env:  SECRET_KEY=<your-key>\n",
        file=sys.stderr,
    )
    # Auto-generate for dev so the app still starts, but warn loudly
    settings.SECRET_KEY = secrets.token_urlsafe(64)

if not settings.CREDENTIAL_KEY:
    print(
        "\n[SECURITY] CREDENTIAL_KEY is not set — platform credentials won't be encrypted safely!"
        "\n  Generate one: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        "\n  Add to .env:  CREDENTIAL_KEY=<your-key>\n",
        file=sys.stderr,
    )
    # Auto-generate for dev
    settings.CREDENTIAL_KEY = secrets.token_urlsafe(32)

settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite only
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def migrate_db():
    """Add missing columns to existing tables (SQLite-safe, idempotent)."""
    from sqlalchemy import text

    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(users)"))}
        additions = [
            ("is_admin", "BOOLEAN DEFAULT 0 NOT NULL"),
            ("subscription_status", "VARCHAR DEFAULT 'free' NOT NULL"),
            ("stripe_customer_id", "VARCHAR"),
            ("stripe_subscription_id", "VARCHAR"),
            ("subscription_ends_at", "DATETIME"),
        ]
        for col, definition in additions:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {definition}"))

        # Jobs table: add user_id
        job_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(jobs)"))}
        if "user_id" not in job_cols:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN user_id INTEGER REFERENCES users(id)"))

        # Credentials table: add gmail fields for LinkedIn verification
        cred_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(credentials)"))}
        if "gmail_email" not in cred_cols:
            conn.execute(text("ALTER TABLE credentials ADD COLUMN gmail_email VARCHAR"))
        if "gmail_app_password_encrypted" not in cred_cols:
            conn.execute(text("ALTER TABLE credentials ADD COLUMN gmail_app_password_encrypted VARCHAR"))

        conn.commit()

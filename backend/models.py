from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    profile = relationship("Profile", back_populates="user", uselist=False)
    credentials = relationship("PlatformCredential", back_populates="user")
    applications = relationship("Application", back_populates="user")
    job_filter = relationship("JobFilter", back_populates="user", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String)
    city = Column(String)
    zip_code = Column(String)
    street_address = Column(String)
    salary_expectation = Column(Integer)
    years_experience = Column(Integer)
    linkedin_url = Column(String)
    cv_path = Column(String)
    summary = Column(Text)
    questions_json = Column(JSON, default=dict)  # Q&A pairs for form filling
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="profile")


class PlatformCredential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    platform = Column(String, nullable=False)  # stepstone, xing, linkedin
    email = Column(String)
    password_encrypted = Column(String)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="credentials")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, index=True)
    external_id = Column(String, index=True)
    title = Column(String, nullable=False)
    company = Column(String)
    location = Column(String)
    salary_min = Column(Float)
    salary_max = Column(Float)
    description = Column(Text)
    url = Column(String, unique=True)
    remote = Column(Boolean, default=False)
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    raw_data = Column(JSON)

    applications = relationship("Application", back_populates="job")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    platform = Column(String, index=True)
    external_job_id = Column(String)
    job_title = Column(String)
    company = Column(String)
    url = Column(String)
    status = Column(String, default="pending", index=True)  # pending, applying, success, failed, skipped
    response_status = Column(String, default="waiting")  # waiting, interview, rejected, ghosted, offer
    applied_at = Column(DateTime)
    error_log = Column(Text)
    notes = Column(Text)
    is_manual = Column(Boolean, default=False)

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")


class JobFilter(Base):
    __tablename__ = "job_filters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    job_titles = Column(JSON, default=list)  # ["Manager", "Project Manager"]
    locations = Column(JSON, default=list)  # ["Berlin", "Remote"]
    remote_only = Column(Boolean, default=False)
    min_salary = Column(Integer, default=0)
    max_salary = Column(Integer, default=0)
    blacklist_companies = Column(JSON, default=list)
    blacklist_keywords = Column(JSON, default=list)
    autopilot_enabled = Column(Boolean, default=False)

    user = relationship("User", back_populates="job_filter")


class BotLog(Base):
    __tablename__ = "bot_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    session_id = Column(String, index=True)  # Groups logs per bot run
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    level = Column(String, default="info")  # debug, info, warn, error
    category = Column(String)  # browser, form, network, apply, scrape, system
    event = Column(String)  # page_load, field_detected, field_filled, field_skipped, submit, login, error, screenshot
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    platform = Column(String)
    data = Column(JSON)  # Stores all detail: field info, match scores, URLs, timings, errors

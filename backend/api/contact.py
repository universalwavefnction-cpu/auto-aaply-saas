import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import Column, DateTime, Integer, String, Text

from ..database import Base, SessionLocal, engine

logger = logging.getLogger(__name__)

# ── Model ────────────────────────────────────────────────────────────────


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Create table
ContactMessage.__table__.create(bind=engine, checkfirst=True)

# ── Router ───────────────────────────────────────────────────────────────

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class ContactRequest(BaseModel):
    name: str
    email: str
    subject: str
    message: str


@router.post("")
@limiter.limit("5/hour")
async def submit_contact(req: ContactRequest, request: Request):
    db = SessionLocal()
    try:
        msg = ContactMessage(
            name=req.name,
            email=req.email,
            subject=req.subject,
            message=req.message,
        )
        db.add(msg)
        db.commit()
        logger.info(f"Contact form: {req.name} <{req.email}> - {req.subject}")
        return {"ok": True}
    finally:
        db.close()

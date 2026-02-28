"""Bot control API: start/stop, SSE stream, screenshots, log analytics."""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from jose import JWTError, jwt
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..auth import ALGORITHM, create_sse_token, get_current_user
from ..bot_engine import SCREENSHOT_DIR, BotEngine
from ..config import settings
from ..database import get_db
from ..models import BotLog, User

router = APIRouter()

# Active bot engines per user
active_bots: dict[int, BotEngine] = {}


@router.post("/start")
async def start_bot(
    mode: str = "scrape_and_apply",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.id in active_bots and active_bots[user.id].running:
        raise HTTPException(400, "Bot is already running")

    # Subscription gate (admins bypass)
    if not user.is_admin and user.subscription_status != "active":
        raise HTTPException(403, "Active subscription required to run the bot.")

    # Log the CV that will be used (for debugging)
    from ..models import CVFile, JobFilter

    jf = db.query(JobFilter).filter(JobFilter.user_id == user.id).first()
    cv_info = "none"
    if jf and jf.selected_cv_id:
        cv = db.query(CVFile).filter(CVFile.id == jf.selected_cv_id).first()
        cv_info = f"id={jf.selected_cv_id} label={cv.label}" if cv else f"id={jf.selected_cv_id} (missing)"
    import logging

    logging.getLogger("bot").info(f"Bot start: user={user.id} mode={mode} cv={cv_info}")

    engine = BotEngine(user.id)
    active_bots[user.id] = engine

    # Launch bot in background task
    asyncio.create_task(engine.run(mode=mode))

    return {
        "status": "started",
        "session_id": engine.session_id,
        "mode": mode,
        "cv": cv_info,
    }


@router.post("/stop")
async def stop_bot(user: User = Depends(get_current_user)):
    engine = active_bots.get(user.id)
    if not engine or not engine.running:
        raise HTTPException(400, "Bot is not running")

    await engine.stop()
    return {"status": "stopping"}


@router.get("/status")
async def bot_status(user: User = Depends(get_current_user)):
    engine = active_bots.get(user.id)
    if not engine:
        return {"running": False, "stats": None}
    return {
        "running": engine.running,
        "session_id": engine.session_id,
        "stats": engine.stats,
    }


@router.post("/stream-token")
async def get_stream_token(user: User = Depends(get_current_user)):
    """Get a short-lived token (60s) for SSE stream connection.

    This avoids passing the main JWT in URL query params where it could be logged.
    """
    return {"token": create_sse_token(user.id)}


def _get_user_from_sse_token(token: str, db: Session) -> User:
    """Decode a short-lived SSE token. Only accepts type='sse'."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "sse":
            raise HTTPException(401, "Invalid token type — use /stream-token first")
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(401, "Invalid or expired stream token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


@router.get("/stream")
async def stream_events(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Server-Sent Events stream of bot activity.

    Requires a short-lived SSE token from POST /stream-token.
    """
    user = _get_user_from_sse_token(token, db)
    engine = active_bots.get(user.id)
    if not engine:
        raise HTTPException(400, "Bot is not running")

    async def event_generator():
        try:
            while engine.running or not engine.events.empty():
                try:
                    event = await asyncio.wait_for(engine.events.get(), timeout=30)
                    event_type = event.get("type", "log")
                    data = json.dumps(event)
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield "event: ping\ndata: {}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/screenshot/latest")
async def get_screenshot(user: User = Depends(get_current_user)):
    path = SCREENSHOT_DIR / f"{user.id}_latest.png"
    if not path.exists():
        raise HTTPException(404, "No screenshot available")
    return FileResponse(str(path), media_type="image/png")


# ── Log Analytics Endpoints ──────────────────────────────────────────────


@router.get("/logs/sessions")
def list_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all bot sessions with summary stats. Admins see all users."""
    q = db.query(
        BotLog.session_id,
        BotLog.user_id,
        func.min(BotLog.timestamp).label("started_at"),
        func.max(BotLog.timestamp).label("ended_at"),
        func.count(BotLog.id).label("log_count"),
    )
    if not user.is_admin:
        q = q.filter(BotLog.user_id == user.id)
    sessions = (
        q.group_by(BotLog.session_id, BotLog.user_id)
        .order_by(desc(func.min(BotLog.timestamp)))
        .limit(100)
        .all()
    )

    # Cache user emails for admin view
    user_emails = {}
    if user.is_admin:
        user_ids = {s.user_id for s in sessions}
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_emails = {u.id: u.email for u in users}

    result = []
    for s in sessions:
        end_log = db.query(BotLog).filter(BotLog.session_id == s.session_id, BotLog.event == "session_end").first()
        stats = end_log.data.get("stats", {}) if end_log and end_log.data else {}

        # Count errors and warnings in this session
        error_count = db.query(func.count(BotLog.id)).filter(
            BotLog.session_id == s.session_id, BotLog.level.in_(["error", "warn"])
        ).scalar() or 0

        entry = {
            "session_id": s.session_id,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "log_count": s.log_count,
            "error_count": error_count,
            "applied": stats.get("applied", 0),
            "failed": stats.get("failed", 0),
            "skipped": stats.get("skipped", 0),
            "fields_filled": stats.get("fields_filled", 0),
            "fields_total": stats.get("fields_total", 0),
        }
        if user.is_admin:
            entry["user_id"] = s.user_id
            entry["user_email"] = user_emails.get(s.user_id, "unknown")
        result.append(entry)

    return {"sessions": result}


@router.get("/logs")
def get_logs(
    session_id: str = None,
    level: str = None,
    category: str = None,
    limit: int = 2000,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed logs, optionally filtered. Admins see all users."""
    q = db.query(BotLog)
    if not user.is_admin:
        q = q.filter(BotLog.user_id == user.id)
    if session_id:
        q = q.filter(BotLog.session_id == session_id)
    if level:
        q = q.filter(BotLog.level == level)
    if category:
        q = q.filter(BotLog.category == category)

    logs = q.order_by(BotLog.timestamp.asc()).limit(limit).all()

    return {
        "logs": [
            {
                "id": l.id,
                "session_id": l.session_id,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                "level": l.level,
                "category": l.category,
                "event": l.event,
                "job_id": l.job_id,
                "platform": l.platform,
                "data": l.data,
            }
            for l in logs
        ]
    }


@router.get("/logs/analytics")
def log_analytics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate analytics across all sessions. Admins see all users."""
    def _q():
        q = db.query(func.count(BotLog.id))
        if not user.is_admin:
            q = q.filter(BotLog.user_id == user.id)
        return q

    total_sessions_q = db.query(func.count(func.distinct(BotLog.session_id)))
    if not user.is_admin:
        total_sessions_q = total_sessions_q.filter(BotLog.user_id == user.id)
    total_sessions = total_sessions_q.scalar()

    total_fields_filled = _q().filter(BotLog.event == "field_filled").scalar()
    total_fields_skipped = _q().filter(BotLog.event == "field_skipped").scalar()
    total_applies = _q().filter(BotLog.event == "success").scalar()
    total_failures = _q().filter(BotLog.event.in_(["no_fields_matched", "error", "no_button"])).scalar()

    fill_rate = (total_fields_filled / max(total_fields_filled + total_fields_skipped, 1)) * 100

    return {
        "total_sessions": total_sessions,
        "total_fields_filled": total_fields_filled,
        "total_fields_skipped": total_fields_skipped,
        "field_fill_rate": round(fill_rate, 1),
        "total_successful_applies": total_applies,
        "total_failures": total_failures,
    }


@router.get("/logs/unmatched-fields")
def unmatched_fields(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List form field labels that couldn't be matched. Admins see all users."""
    q = db.query(BotLog).filter(BotLog.event == "field_skipped")
    if not user.is_admin:
        q = q.filter(BotLog.user_id == user.id)
    logs = q.all()

    # Count frequency of each unmatched label
    label_counts: dict[str, int] = {}
    for l in logs:
        label = (l.data or {}).get("label", "")
        if label:
            label_lower = label.lower().strip()
            label_counts[label_lower] = label_counts.get(label_lower, 0) + 1

    sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "unmatched_fields": [{"label": label, "count": count} for label, count in sorted_labels[:50]],
        "total_unique": len(label_counts),
    }

"""Bot control API: start/stop, SSE stream, screenshots, log analytics."""
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from jose import JWTError, jwt

from ..database import get_db
from ..models import User, BotLog
from ..auth import get_current_user
from ..config import settings
from ..bot_engine import BotEngine, SCREENSHOT_DIR

router = APIRouter()

# Active bot engines per user
active_bots: dict[int, BotEngine] = {}


@router.post("/start")
async def start_bot(
    mode: str = "scrape_and_apply",
    user: User = Depends(get_current_user),
):
    if user.id in active_bots and active_bots[user.id].running:
        raise HTTPException(400, "Bot is already running")

    engine = BotEngine(user.id)
    active_bots[user.id] = engine

    # Launch bot in background task
    asyncio.create_task(engine.run(mode=mode))

    return {
        "status": "started",
        "session_id": engine.session_id,
        "mode": mode,
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


def _get_user_from_token(token: str, db: Session) -> User:
    """Decode JWT token and return user. Used for SSE where Authorization header isn't available."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(401, "Invalid token")
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

    Uses token query param since EventSource can't send Authorization headers.
    """
    user = _get_user_from_token(token, db)
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
                    yield f"event: ping\ndata: {{}}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            yield f"event: done\ndata: {{}}\n\n"

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
    """List all bot sessions with summary stats."""
    sessions = (
        db.query(
            BotLog.session_id,
            func.min(BotLog.timestamp).label("started_at"),
            func.max(BotLog.timestamp).label("ended_at"),
            func.count(BotLog.id).label("log_count"),
        )
        .filter(BotLog.user_id == user.id)
        .group_by(BotLog.session_id)
        .order_by(desc(func.min(BotLog.timestamp)))
        .limit(50)
        .all()
    )

    result = []
    for s in sessions:
        # Get session stats from the session_end log
        end_log = (
            db.query(BotLog)
            .filter(BotLog.session_id == s.session_id, BotLog.event == "session_end")
            .first()
        )
        stats = end_log.data.get("stats", {}) if end_log and end_log.data else {}

        result.append({
            "session_id": s.session_id,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "log_count": s.log_count,
            "applied": stats.get("applied", 0),
            "failed": stats.get("failed", 0),
            "skipped": stats.get("skipped", 0),
            "fields_filled": stats.get("fields_filled", 0),
            "fields_total": stats.get("fields_total", 0),
        })

    return {"sessions": result}


@router.get("/logs")
def get_logs(
    session_id: str = None,
    level: str = None,
    category: str = None,
    limit: int = 200,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed logs, optionally filtered."""
    q = db.query(BotLog).filter(BotLog.user_id == user.id)
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
    """Aggregate analytics across all sessions."""
    total_sessions = db.query(func.count(func.distinct(BotLog.session_id))).filter(
        BotLog.user_id == user.id
    ).scalar()

    total_fields_filled = db.query(func.count(BotLog.id)).filter(
        BotLog.user_id == user.id, BotLog.event == "field_filled"
    ).scalar()

    total_fields_skipped = db.query(func.count(BotLog.id)).filter(
        BotLog.user_id == user.id, BotLog.event == "field_skipped"
    ).scalar()

    total_applies = db.query(func.count(BotLog.id)).filter(
        BotLog.user_id == user.id, BotLog.event == "success"
    ).scalar()

    total_failures = db.query(func.count(BotLog.id)).filter(
        BotLog.user_id == user.id, BotLog.event.in_(["no_fields_matched", "error", "no_button"])
    ).scalar()

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
    """List form field labels that couldn't be matched — tells you what Q&A to add."""
    logs = (
        db.query(BotLog)
        .filter(
            BotLog.user_id == user.id,
            BotLog.event == "field_skipped",
        )
        .all()
    )

    # Count frequency of each unmatched label
    label_counts: dict[str, int] = {}
    for l in logs:
        label = (l.data or {}).get("label", "")
        if label:
            label_lower = label.lower().strip()
            label_counts[label_lower] = label_counts.get(label_lower, 0) + 1

    sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "unmatched_fields": [
            {"label": label, "count": count}
            for label, count in sorted_labels[:50]
        ],
        "total_unique": len(label_counts),
    }

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Application, User

router = APIRouter()


@router.get("")
def list_applications(
    platform: str | None = None,
    status: str | None = None,
    response_status: str | None = None,
    source: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Application).filter(Application.user_id == user.id)
    if source == "external":
        q = q.filter(Application.status == "external")
    elif source == "bot":
        q = q.filter(Application.status != "external")
    if platform:
        q = q.filter(Application.platform == platform.lower())
    if status:
        q = q.filter(Application.status == status)
    if response_status:
        q = q.filter(Application.response_status == response_status)

    total = q.count()
    apps = q.order_by(desc(Application.applied_at)).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "applications": [
            {
                "id": a.id,
                "platform": a.platform,
                "job_title": a.job_title,
                "company": a.company,
                "url": a.url,
                "status": a.status,
                "response_status": a.response_status,
                "is_manual": a.is_manual,
                "applied_at": a.applied_at.isoformat() if a.applied_at else None,
                "notes": a.notes,
            }
            for a in apps
        ],
    }


@router.post("/{app_id}/response")
def update_response(
    app_id: int,
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = (
        db.query(Application)
        .filter(
            Application.id == app_id,
            Application.user_id == user.id,
        )
        .first()
    )
    if not app:
        return {"error": "Application not found"}
    if "response_status" in data:
        app.response_status = data["response_status"]
    if "notes" in data:
        app.notes = data["notes"]
    db.commit()
    return {"status": "updated"}


@router.post("/manual")
def manual_apply(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a job as manually applied (user applied themselves via the link)."""
    app = Application(
        user_id=user.id,
        job_id=data.get("job_id"),
        platform=data.get("platform", "manual"),
        job_title=data.get("job_title"),
        company=data.get("company"),
        url=data.get("url"),
        status="success",
        is_manual=True,
        applied_at=datetime.now(timezone.utc),
    )
    db.add(app)
    db.commit()
    return {"id": app.id, "status": "recorded"}

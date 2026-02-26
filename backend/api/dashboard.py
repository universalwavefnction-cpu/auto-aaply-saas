from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import User, Application, Job
from ..auth import get_current_user

router = APIRouter()


@router.get("/stats")
def get_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Application stats
    total_apps = db.query(func.count(Application.id)).filter(
        Application.user_id == user.id
    ).scalar() or 0

    by_status = dict(
        db.query(Application.status, func.count(Application.id)).filter(
            Application.user_id == user.id
        ).group_by(Application.status).all()
    )

    by_platform = dict(
        db.query(Application.platform, func.count(Application.id)).filter(
            Application.user_id == user.id
        ).group_by(Application.platform).all()
    )

    by_response = dict(
        db.query(Application.response_status, func.count(Application.id)).filter(
            Application.user_id == user.id
        ).group_by(Application.response_status).all()
    )

    # Job stats
    total_jobs = db.query(func.count(Job.id)).scalar() or 0

    # Recent applications
    recent = db.query(Application).filter(
        Application.user_id == user.id
    ).order_by(Application.applied_at.desc()).limit(10).all()

    return {
        "total_applications": total_apps,
        "total_jobs_discovered": total_jobs,
        "by_status": by_status,
        "by_platform": by_platform,
        "by_response": by_response,
        "success_rate": round(by_status.get("success", 0) / total_apps * 100, 1) if total_apps else 0,
        "recent": [
            {
                "id": a.id, "job_title": a.job_title, "company": a.company,
                "platform": a.platform, "status": a.status,
                "applied_at": a.applied_at.isoformat() if a.applied_at else None,
            }
            for a in recent
        ],
    }

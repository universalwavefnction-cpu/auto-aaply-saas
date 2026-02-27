from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Job, JobFilter, User

router = APIRouter()


@router.get("")
def list_jobs(
    platform: str | None = None,
    search: str | None = None,
    location: str | None = None,
    remote: bool | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Job)
    if platform:
        q = q.filter(Job.platform == platform.lower())
    if search:
        q = q.filter(Job.title.ilike(f"%{search}%") | Job.company.ilike(f"%{search}%"))
    if location:
        q = q.filter(Job.location.ilike(f"%{location}%"))
    if remote is not None:
        q = q.filter(Job.remote == remote)

    total = q.count()
    jobs = q.order_by(desc(Job.scraped_at)).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "jobs": [
            {
                "id": j.id,
                "platform": j.platform,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "salary_min": j.salary_min,
                "salary_max": j.salary_max,
                "url": j.url,
                "remote": j.remote,
                "scraped_at": j.scraped_at.isoformat() if j.scraped_at else None,
            }
            for j in jobs
        ],
    }


@router.get("/{job_id}")
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return {"error": "Job not found"}
    return {
        "id": job.id,
        "platform": job.platform,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "description": job.description,
        "url": job.url,
        "remote": job.remote,
        "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
    }


@router.get("/filters/current")
def get_filters(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = db.query(JobFilter).filter(JobFilter.user_id == user.id).first()
    if not f:
        return {}
    return {
        "job_titles": f.job_titles or [],
        "locations": f.locations or [],
        "remote_only": f.remote_only,
        "min_salary": f.min_salary,
        "max_salary": f.max_salary,
        "blacklist_companies": f.blacklist_companies or [],
        "blacklist_keywords": f.blacklist_keywords or [],
        "autopilot_enabled": f.autopilot_enabled,
        "platform": f.platform or "stepstone",
        "max_applications": f.max_applications or 10,
        "selected_cv_id": f.selected_cv_id,
    }


@router.put("/filters")
def update_filters(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    f = db.query(JobFilter).filter(JobFilter.user_id == user.id).first()
    if not f:
        f = JobFilter(user_id=user.id)
        db.add(f)
    for key, val in data.items():
        if hasattr(f, key):
            setattr(f, key, val)
    db.commit()
    return {"status": "updated"}

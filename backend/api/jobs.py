import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Job, JobFilter, User

router = APIRouter()
logger = logging.getLogger(__name__)

# Track running discoveries per user
_active_discoveries: dict[int, bool] = {}


class FilterUpdate(BaseModel):
    job_titles: list[str] | None = None
    locations: list[str] | None = None
    remote_only: bool | None = None
    min_salary: int | None = None
    max_salary: int | None = None
    blacklist_companies: list[str] | None = None
    blacklist_keywords: list[str] | None = None
    autopilot_enabled: bool | None = None
    platform: str | None = None
    scrape_platforms: list[str] | None = None
    max_applications: int | None = None
    selected_cv_id: int | None = None


class DiscoverRequest(BaseModel):
    platforms: list[str] | None = None
    query: str | None = None  # Override saved job_titles — search this exact term
    location: str | None = None  # Override saved locations


@router.get("")
def list_jobs(
    platform: str | None = None,
    search: str | None = None,
    location: str | None = None,
    remote: bool | None = None,
    employment_type: str | None = None,
    has_description: bool | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    posted_days: int | None = None,
    sort_by: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Job).filter(Job.user_id == user.id)
    if platform:
        q = q.filter(Job.platform == platform.lower())
    if search:
        q = q.filter(Job.title.ilike(f"%{search}%") | Job.company.ilike(f"%{search}%"))
    if location:
        q = q.filter(Job.location.ilike(f"%{location}%"))
    if remote is not None:
        q = q.filter(Job.remote == remote)
    if employment_type:
        q = q.filter(Job.employment_type.ilike(f"%{employment_type}%"))
    if has_description is True:
        q = q.filter(Job.description.isnot(None), Job.description != "")
    if salary_min is not None:
        q = q.filter(Job.salary_min >= salary_min)
    if salary_max is not None:
        q = q.filter(Job.salary_max <= salary_max)
    if posted_days is not None and posted_days > 0:
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=posted_days)
        q = q.filter(Job.posted_at >= cutoff)

    # Sorting
    if sort_by == "posted_at":
        q = q.order_by(desc(Job.posted_at))
    elif sort_by == "company":
        q = q.order_by(Job.company)
    elif sort_by == "salary":
        q = q.order_by(desc(Job.salary_min))
    else:
        q = q.order_by(desc(Job.scraped_at))

    total = q.count()
    jobs = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "jobs": [_job_to_dict(j) for j in jobs],
    }


@router.get("/facets")
def get_facets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return distinct locations, platforms, employment types for filter dropdowns."""
    from sqlalchemy import func

    locations_raw = (
        db.query(Job.location)
        .filter(Job.user_id == user.id, Job.location.isnot(None), Job.location != "")
        .group_by(Job.location)
        .order_by(func.count(Job.id).desc())
        .limit(50)
        .all()
    )
    platforms = (
        db.query(Job.platform)
        .filter(Job.user_id == user.id)
        .group_by(Job.platform)
        .order_by(func.count(Job.id).desc())
        .all()
    )
    emp_types = (
        db.query(Job.employment_type)
        .filter(Job.user_id == user.id, Job.employment_type.isnot(None), Job.employment_type != "")
        .group_by(Job.employment_type)
        .order_by(func.count(Job.id).desc())
        .limit(20)
        .all()
    )
    return {
        "locations": [r[0] for r in locations_raw],
        "platforms": [r[0] for r in platforms],
        "employment_types": [r[0] for r in emp_types],
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
        "scrape_platforms": f.scrape_platforms or ["arbeitsagentur", "linkedin_guest", "arbeitnow"],
        "max_applications": f.max_applications or 10,
        "selected_cv_id": f.selected_cv_id,
    }


@router.put("/filters")
def update_filters(
    data: FilterUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    f = db.query(JobFilter).filter(JobFilter.user_id == user.id).first()
    if not f:
        f = JobFilter(user_id=user.id)
        db.add(f)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(f, field, value)
    db.commit()
    return {"status": "updated"}


@router.get("/{job_id}")
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        return {"error": "Job not found"}
    return _job_to_dict(job, full=True)


@router.post("/discover")
async def discover_jobs(
    body: DiscoverRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger standalone job discovery across platforms."""
    # Subscription gate (same as bot start)
    is_admin = user.email == "dimitri.perepelkin@gmail.com"
    if not is_admin and user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")

    if _active_discoveries.get(user.id):
        raise HTTPException(status_code=409, detail="Discovery already running")

    platforms = body.platforms if body else None
    query = body.query if body else None
    location = body.location if body else None

    # Run discovery as background task
    _active_discoveries[user.id] = True

    async def _run():
        try:
            from ..workers.scrape_worker import run_discovery

            result = await run_discovery(
                user.id,
                platforms=platforms,
                query_override=query,
                location_override=location,
            )
            logger.info("Discovery completed for user %d: %s", user.id, result)
        finally:
            _active_discoveries.pop(user.id, None)

    asyncio.ensure_future(_run())
    return {"status": "started", "message": "Discovery started"}


@router.get("/discover/status")
def discovery_status(user: User = Depends(get_current_user)):
    """Check if discovery is currently running."""
    return {"running": bool(_active_discoveries.get(user.id))}


def _job_to_dict(j: Job, full: bool = False) -> dict:
    """Convert Job model to API response dict."""
    d = {
        "id": j.id,
        "platform": j.platform,
        "title": j.title,
        "company": j.company,
        "location": j.location,
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "salary_text": j.salary_text,
        "url": j.url,
        "remote": j.remote,
        "employment_type": j.employment_type,
        "posted_at": j.posted_at.isoformat() if j.posted_at else None,
        "scraped_at": j.scraped_at.isoformat() if j.scraped_at else None,
        "platforms_seen": j.platforms_seen or [j.platform],
        "description_preview": (j.description or "")[:200] if not full else None,
    }
    if full:
        d["description"] = j.description
        d["source_id"] = j.source_id
        d.pop("description_preview", None)
    return d

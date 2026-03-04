"""Background worker for job discovery across platforms.

Orchestrates both API scrapers (fast, no credentials) and browser scrapers (slow, credential-based).
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Job, JobFilter, PlatformCredential
from ..scrapers.adzuna import AdzunaScraper
from ..scrapers.arbeitnow import ArbeitnowScraper
from ..scrapers.arbeitsagentur import ArbeitsagenturScraper
from ..scrapers.dedup import compute_description_hash
from ..scrapers.indeed_jobspy import IndeedJobspyScraper
from ..scrapers.jooble import JoobleScraper
from ..scrapers.linkedin_guest import LinkedInGuestScraper
from ..scrapers.stepstone import StepStoneScraper
from ..scrapers.xing import XingScraper

logger = logging.getLogger(__name__)

# API scrapers: no credentials needed
API_SCRAPERS = {
    "arbeitsagentur": ArbeitsagenturScraper,
    "arbeitnow": ArbeitnowScraper,
    "linkedin_guest": LinkedInGuestScraper,
    "indeed": IndeedJobspyScraper,
    "jooble": JoobleScraper,
    "adzuna": AdzunaScraper,
}

# Browser scrapers: need credentials
BROWSER_SCRAPERS = {
    "stepstone": StepStoneScraper,
    "xing": XingScraper,
}

DEFAULT_PLATFORMS = ["arbeitsagentur", "linkedin_guest", "arbeitnow"]


async def run_discovery(
    user_id: int,
    platforms: list[str] | None = None,
    query_override: str | None = None,
    location_override: str | None = None,
) -> dict:
    """Run standalone job discovery across multiple platforms.

    Args:
        query_override: If set, search this exact term instead of saved job_titles.
        location_override: If set, search this location instead of saved locations.

    Returns summary dict with counts and errors.
    """
    db: Session = SessionLocal()
    summary = {
        "total_found": 0,
        "new_jobs": 0,
        "duplicates_merged": 0,
        "errors": [],
        "by_platform": {},
    }

    try:
        job_filter = db.query(JobFilter).filter(JobFilter.user_id == user_id).first()

        # Use overrides if provided, otherwise fall back to saved filter
        if query_override:
            titles = [query_override]
        elif job_filter and job_filter.job_titles:
            titles = job_filter.job_titles
        else:
            summary["errors"].append("No search query provided and no job titles in Settings")
            return summary

        if location_override:
            locations = [location_override]
        elif job_filter and job_filter.locations:
            locations = job_filter.locations
        else:
            locations = [""]

        # Determine which platforms to scrape — all API scrapers by default for ad-hoc queries
        if platforms is None:
            if query_override:
                # Ad-hoc search: use all available API scrapers
                platforms = list(API_SCRAPERS.keys())
            elif job_filter and job_filter.scrape_platforms:
                platforms = job_filter.scrape_platforms
            else:
                platforms = DEFAULT_PLATFORMS

        # Run API scrapers (fast, parallel per-platform)
        api_tasks = []
        for platform_name in platforms:
            if platform_name in API_SCRAPERS:
                api_tasks.append(
                    _run_api_scraper(platform_name, titles, locations, job_filter, user_id, db, summary)
                )

        if api_tasks:
            await asyncio.gather(*api_tasks, return_exceptions=True)

        # Run browser scrapers (slow, sequential, need credentials)
        creds = (
            db.query(PlatformCredential)
            .filter(
                PlatformCredential.user_id == user_id,
                PlatformCredential.is_active == True,  # noqa: E712
            )
            .all()
        )
        for platform_name in platforms:
            if platform_name in BROWSER_SCRAPERS:
                cred = next((c for c in creds if c.platform == platform_name), None)
                if not cred:
                    continue
                await _run_browser_scraper(platform_name, cred, titles, locations, job_filter, user_id, db, summary)

    except Exception as e:
        summary["errors"].append(f"Discovery error: {e}")
        logger.exception("Discovery failed for user %d", user_id)
    finally:
        db.close()

    return summary


async def _run_api_scraper(
    platform_name: str,
    titles: list[str],
    locations: list[str],
    job_filter: JobFilter,
    user_id: int,
    db: Session,
    summary: dict,
):
    """Run a single API scraper across all title/location combinations."""
    scraper_cls = API_SCRAPERS[platform_name]
    scraper = scraper_cls()
    platform_count = 0

    try:
        await scraper.start()
        for title in titles:
            for location in locations:
                try:
                    jobs = await scraper.search_jobs(title, location)
                    for job_data in jobs:
                        if _is_blacklisted(job_data, job_filter):
                            continue
                        added = _upsert_job(db, user_id, job_data)
                        if added:
                            platform_count += 1
                            summary["new_jobs"] += 1
                        else:
                            summary["duplicates_merged"] += 1
                        summary["total_found"] += 1
                except Exception as e:
                    logger.error("%s search error for '%s' in '%s': %s", platform_name, title, location, e)

        db.commit()
    except Exception as e:
        summary["errors"].append(f"{platform_name}: {e}")
        logger.error("%s scraper failed: %s", platform_name, e)
    finally:
        await scraper.stop()

    summary["by_platform"][platform_name] = platform_count


async def _run_browser_scraper(
    platform_name: str,
    cred: PlatformCredential,
    titles: list[str],
    locations: list[str],
    job_filter: JobFilter,
    user_id: int,
    db: Session,
    summary: dict,
):
    """Run a single browser scraper (requires login)."""
    scraper_cls = BROWSER_SCRAPERS[platform_name]
    scraper = scraper_cls()
    platform_count = 0

    try:
        await scraper.start()
        logged_in = await scraper.login(cred.email, cred.get_password())
        if not logged_in:
            summary["errors"].append(f"{platform_name}: login failed")
            return

        for title in titles:
            for location in locations:
                try:
                    jobs = await scraper.search_jobs(title, location)
                    for job_data in jobs:
                        if _is_blacklisted(job_data, job_filter):
                            continue
                        added = _upsert_job(db, user_id, job_data)
                        if added:
                            platform_count += 1
                            summary["new_jobs"] += 1
                        else:
                            summary["duplicates_merged"] += 1
                        summary["total_found"] += 1
                except Exception as e:
                    logger.error("%s search error: %s", platform_name, e)

                await asyncio.sleep(2)

        db.commit()
    except Exception as e:
        summary["errors"].append(f"{platform_name}: {e}")
    finally:
        await scraper.stop()

    summary["by_platform"][platform_name] = platform_count


def _is_blacklisted(job_data: dict, job_filter: JobFilter) -> bool:
    """Check if a job should be filtered out by blacklists."""
    company = (job_data.get("company") or "").lower()
    title = (job_data.get("title") or "").lower()
    if any(b.lower() in company for b in (job_filter.blacklist_companies or [])):
        return True
    return any(k.lower() in title for k in (job_filter.blacklist_keywords or []))


def _upsert_job(db: Session, user_id: int, job_data: dict) -> bool:
    """Insert or merge a job. Returns True if new job was created."""
    desc_hash = compute_description_hash(
        job_data.get("title", ""),
        job_data.get("company", ""),
        job_data.get("location", ""),
    )
    platform = job_data["platform"]

    # Check for exact URL match first
    existing = db.query(Job).filter(Job.url == job_data["url"], Job.user_id == user_id).first()
    if existing:
        # Update platforms_seen
        seen = existing.platforms_seen or []
        if platform not in seen:
            seen.append(platform)
            existing.platforms_seen = seen
        return False

    # Check for cross-platform duplicate via description_hash
    existing = db.query(Job).filter(Job.description_hash == desc_hash, Job.user_id == user_id).first()
    if existing:
        seen = existing.platforms_seen or []
        if platform not in seen:
            seen.append(platform)
            existing.platforms_seen = seen
        return False

    # New job
    db.add(
        Job(
            user_id=user_id,
            platform=platform,
            title=job_data["title"],
            company=job_data.get("company"),
            location=job_data.get("location"),
            url=job_data["url"],
            description=job_data.get("description"),
            remote=job_data.get("remote", False),
            scraped_at=datetime.now(timezone.utc),
            employment_type=job_data.get("employment_type"),
            posted_at=job_data.get("posted_at"),
            source_id=job_data.get("source_id"),
            description_hash=desc_hash,
            salary_text=job_data.get("salary_text"),
            platforms_seen=[platform],
        )
    )
    return True


# Legacy function kept for backward compatibility with existing bot_engine.py
async def run_scrape_cycle(user_id: int):
    """Run one scrape cycle (legacy — wraps run_discovery for browser scrapers only)."""
    return await run_discovery(user_id, platforms=["stepstone", "xing"])

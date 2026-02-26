"""Background worker for job discovery across platforms."""
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Job, JobFilter, PlatformCredential
from ..scrapers.stepstone import StepStoneScraper
from ..scrapers.xing import XingScraper


SCRAPERS = {
    "stepstone": StepStoneScraper,
    "xing": XingScraper,
}


async def run_scrape_cycle(user_id: int):
    """Run one scrape cycle for a user across all configured platforms."""
    db: Session = SessionLocal()
    results = {"jobs_found": 0, "errors": []}

    try:
        job_filter = db.query(JobFilter).filter(JobFilter.user_id == user_id).first()
        creds = db.query(PlatformCredential).filter(
            PlatformCredential.user_id == user_id,
            PlatformCredential.is_active == True,
        ).all()

        if not job_filter or not job_filter.job_titles:
            results["errors"].append("No job titles configured")
            return results

        for cred in creds:
            scraper_cls = SCRAPERS.get(cred.platform)
            if not scraper_cls:
                continue

            scraper = scraper_cls()
            try:
                await scraper.start()
                logged_in = await scraper.login(cred.email, cred.password_encrypted)
                if not logged_in:
                    results["errors"].append(f"{cred.platform}: login failed")
                    continue

                for title in job_filter.job_titles:
                    for location in (job_filter.locations or [""]):
                        jobs = await scraper.search_jobs(title, location)
                        for job_data in jobs:
                            # Skip blacklisted
                            company = job_data.get("company", "").lower()
                            if any(b.lower() in company for b in (job_filter.blacklist_companies or [])):
                                continue
                            title_text = job_data.get("title", "").lower()
                            if any(k.lower() in title_text for k in (job_filter.blacklist_keywords or [])):
                                continue

                            # Upsert job
                            existing = db.query(Job).filter(Job.url == job_data["url"]).first()
                            if not existing:
                                db.add(Job(
                                    platform=job_data["platform"],
                                    title=job_data["title"],
                                    company=job_data.get("company"),
                                    location=job_data.get("location"),
                                    url=job_data["url"],
                                    scraped_at=datetime.now(timezone.utc),
                                ))
                                results["jobs_found"] += 1

                        await asyncio.sleep(2)  # Rate limit between searches

                db.commit()
            except Exception as e:
                results["errors"].append(f"{cred.platform}: {e}")
            finally:
                await scraper.stop()

    finally:
        db.close()

    return results

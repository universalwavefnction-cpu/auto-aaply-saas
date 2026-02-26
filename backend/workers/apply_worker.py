"""Background worker for auto-applying to discovered jobs."""
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Job, Application, Profile, PlatformCredential, JobFilter
from ..scrapers.stepstone import StepStoneScraper
from ..scrapers.xing import XingScraper


SCRAPERS = {
    "stepstone": StepStoneScraper,
    "xing": XingScraper,
}


async def run_apply_cycle(user_id: int, max_applications: int = 10):
    """Apply to unapplied jobs for a user."""
    db: Session = SessionLocal()
    results = {"applied": 0, "failed": 0, "errors": []}

    try:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        job_filter = db.query(JobFilter).filter(JobFilter.user_id == user_id).first()
        creds = db.query(PlatformCredential).filter(
            PlatformCredential.user_id == user_id,
            PlatformCredential.is_active == True,
        ).all()

        if not profile or not job_filter or not job_filter.autopilot_enabled:
            results["errors"].append("Autopilot not enabled or profile missing")
            return results

        # Get already-applied URLs
        applied_urls = set(
            row[0] for row in
            db.query(Application.url).filter(Application.user_id == user_id).all()
            if row[0]
        )

        # Build profile dict for form filler
        profile_dict = {
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "phone": profile.phone,
            "city": profile.city,
            "zip_code": profile.zip_code,
            "street_address": profile.street_address,
            "salary_expectation": profile.salary_expectation,
            "years_experience": profile.years_experience,
            "linkedin_url": profile.linkedin_url,
            "summary": profile.summary,
            "questions_json": profile.questions_json or {},
        }

        cred_map = {c.platform: c for c in creds}
        applied_count = 0

        for platform, cred in cred_map.items():
            scraper_cls = SCRAPERS.get(platform)
            if not scraper_cls:
                continue

            # Get unapplied jobs for this platform
            unapplied = db.query(Job).filter(
                Job.platform == platform,
                ~Job.url.in_(applied_urls),
            ).limit(max_applications - applied_count).all()

            if not unapplied:
                continue

            scraper = scraper_cls()
            try:
                await scraper.start()
                logged_in = await scraper.login(cred.email, cred.password_encrypted)
                if not logged_in:
                    results["errors"].append(f"{platform}: login failed")
                    continue

                for job in unapplied:
                    if applied_count >= max_applications:
                        break

                    app = Application(
                        user_id=user_id,
                        job_id=job.id,
                        platform=platform,
                        job_title=job.title,
                        company=job.company,
                        url=job.url,
                        status="applying",
                        applied_at=datetime.now(timezone.utc),
                    )
                    db.add(app)
                    db.flush()

                    result = await scraper.apply_to_job(job.url, profile_dict)

                    if result["status"] == "success":
                        app.status = "success"
                        results["applied"] += 1
                    else:
                        app.status = "failed"
                        app.error_log = result.get("error", "")
                        results["failed"] += 1

                    db.commit()
                    applied_count += 1

                    # Delay between applications
                    await asyncio.sleep(60)

            except Exception as e:
                results["errors"].append(f"{platform}: {e}")
            finally:
                await scraper.stop()

    finally:
        db.close()

    return results

"""Indeed scraper via python-jobspy library.

Bypasses Cloudflare by using Indeed's mobile API under the hood.
"""

import asyncio
import logging
from datetime import datetime, timezone

from .base import BaseAPIScraper

logger = logging.getLogger(__name__)


class IndeedJobspyScraper(BaseAPIScraper):
    PLATFORM = "indeed"

    async def start(self):
        # No HTTP client needed — jobspy handles its own requests
        pass

    async def stop(self):
        pass

    async def search_jobs(self, query: str, location: str = "", page: int = 0) -> list[dict]:
        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("python-jobspy not installed. Run: pip install -U python-jobspy")
            return []

        loop = asyncio.get_event_loop()
        try:
            # jobspy is synchronous — run in executor
            df = await loop.run_in_executor(
                None,
                lambda: scrape_jobs(
                    site_name=["indeed"],
                    search_term=query,
                    location=location or "Germany",
                    results_wanted=50,
                    country_indeed="Germany",
                    is_remote=False,
                ),
            )
        except Exception as e:
            logger.error("Indeed/jobspy search error: %s", e)
            return []

        jobs = []
        for _, row in df.iterrows():
            try:
                job = {
                    "platform": self.PLATFORM,
                    "source_id": str(row.get("id", "")),
                    "title": row.get("title", ""),
                    "company": row.get("company", ""),
                    "location": row.get("location", ""),
                    "url": row.get("job_url", ""),
                    "description": row.get("description", ""),
                    "employment_type": row.get("job_type", None),
                    "posted_at": None,
                    "salary_text": None,
                    "remote": bool(row.get("is_remote", False)),
                }
                # Parse salary
                min_sal = row.get("min_amount")
                max_sal = row.get("max_amount")
                if min_sal and max_sal:
                    job["salary_text"] = f"{min_sal}-{max_sal} {row.get('currency', 'EUR')}"
                elif min_sal:
                    job["salary_text"] = f"{min_sal}+ {row.get('currency', 'EUR')}"

                # Parse date
                date_posted = row.get("date_posted")
                if date_posted:
                    try:
                        if hasattr(date_posted, "to_pydatetime"):
                            job["posted_at"] = date_posted.to_pydatetime().replace(tzinfo=timezone.utc)
                        else:
                            job["posted_at"] = datetime.fromisoformat(str(date_posted)).replace(tzinfo=timezone.utc)
                    except (ValueError, AttributeError):
                        pass

                if job["title"] and job["url"]:
                    jobs.append(job)
            except Exception as e:
                logger.debug("Failed to parse Indeed/jobspy row: %s", e)

        logger.info("Indeed/jobspy: found %d jobs for '%s' in '%s'", len(jobs), query, location)
        return jobs

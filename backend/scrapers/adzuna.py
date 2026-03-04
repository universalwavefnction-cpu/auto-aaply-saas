"""Adzuna API scraper.

Free tier: 250 requests/day, covers DE/AT/CH.
Register at: https://developer.adzuna.com/
"""

import contextlib
import logging
from datetime import datetime

from ..config import settings
from .base import BaseAPIScraper

logger = logging.getLogger(__name__)

API_BASE = "https://api.adzuna.com/v1/api/jobs"


class AdzunaScraper(BaseAPIScraper):
    PLATFORM = "adzuna"

    async def search_jobs(self, query: str, location: str = "", page: int = 1) -> list[dict]:
        if not self.client:
            return []

        app_id = settings.ADZUNA_APP_ID
        app_key = settings.ADZUNA_APP_KEY
        if not app_id or not app_key:
            logger.debug("Adzuna API keys not configured, skipping")
            return []

        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what": query,
            "results_per_page": 50,
            "content-type": "application/json",
        }
        if location:
            params["where"] = location

        try:
            resp = await self.client.get(
                f"{API_BASE}/de/search/{page}",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("Adzuna API error: %s", e)
            return []

        jobs = []
        for item in data.get("results", []):
            try:
                job = self._parse_job(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug("Failed to parse Adzuna job: %s", e)

        logger.info("Adzuna: found %d jobs for '%s' in '%s'", len(jobs), query, location)
        return jobs

    def _parse_job(self, item: dict) -> dict | None:
        title = item.get("title", "")
        url = item.get("redirect_url", "")
        if not title or not url:
            return None

        posted_at = None
        created = item.get("created")
        if created:
            with contextlib.suppress(ValueError, AttributeError):
                posted_at = datetime.fromisoformat(created.replace("Z", "+00:00"))

        location_parts = []
        loc = item.get("location", {})
        for area in loc.get("area", []):
            location_parts.append(area)
        location_str = ", ".join(location_parts) if location_parts else ""

        # Salary
        salary_text = None
        sal_min = item.get("salary_min")
        sal_max = item.get("salary_max")
        if sal_min and sal_max:
            salary_text = f"{int(sal_min):,}-{int(sal_max):,} EUR"
        elif sal_min:
            salary_text = f"{int(sal_min):,}+ EUR"

        company = item.get("company", {}).get("display_name", "")
        description = item.get("description", "")

        return {
            "platform": self.PLATFORM,
            "source_id": item.get("id", ""),
            "title": title,
            "company": company,
            "location": location_str,
            "url": url,
            "description": description,
            "employment_type": item.get("contract_type"),
            "posted_at": posted_at,
            "salary_text": salary_text,
            "remote": "remote" in title.lower() or "remote" in description.lower(),
        }

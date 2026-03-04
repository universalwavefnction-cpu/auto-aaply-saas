"""Arbeitnow API scraper.

Free, no API key needed. English-speaking jobs in Germany.
Endpoint: https://www.arbeitnow.com/api/job-board-api
"""

import contextlib
import logging
from datetime import datetime, timezone

from .base import BaseAPIScraper

logger = logging.getLogger(__name__)

API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowScraper(BaseAPIScraper):
    PLATFORM = "arbeitnow"

    async def search_jobs(self, query: str, location: str = "", page: int = 1) -> list[dict]:
        if not self.client:
            return []

        params: dict = {"page": page}

        try:
            resp = await self.client.get(API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("Arbeitnow API error: %s", e)
            return []

        query_lower = query.lower()
        location_lower = location.lower() if location else ""

        jobs = []
        for item in data.get("data", []):
            try:
                job = self._parse_job(item)
                if not job:
                    continue
                # Client-side keyword filtering (API doesn't support search params)
                title_lower = job["title"].lower()
                desc_lower = (job.get("description") or "").lower()
                tags_lower = " ".join(t.lower() for t in (item.get("tags") or []))
                if query_lower not in title_lower and query_lower not in desc_lower and query_lower not in tags_lower:
                    continue
                if location_lower and location_lower not in (job.get("location") or "").lower():
                    continue
                jobs.append(job)
            except Exception as e:
                logger.debug("Failed to parse Arbeitnow job: %s", e)

        logger.info("Arbeitnow: found %d jobs matching '%s' in '%s'", len(jobs), query, location)
        return jobs

    def _parse_job(self, item: dict) -> dict | None:
        title = item.get("title", "")
        if not title:
            return None

        slug = item.get("slug", "")
        url = item.get("url") or f"https://www.arbeitnow.com/view/{slug}"

        posted_at = None
        created_at = item.get("created_at")
        if created_at:
            with contextlib.suppress(ValueError, TypeError):
                posted_at = datetime.fromtimestamp(created_at, tz=timezone.utc)

        remote = item.get("remote", False)

        return {
            "platform": self.PLATFORM,
            "source_id": slug,
            "title": title,
            "company": item.get("company_name", ""),
            "location": item.get("location", ""),
            "url": url,
            "description": item.get("description", ""),
            "employment_type": None,  # Not provided by API
            "posted_at": posted_at,
            "salary_text": None,
            "remote": bool(remote),
        }

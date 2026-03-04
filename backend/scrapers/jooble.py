"""Jooble API scraper.

Free with registration. POST-based API that aggregates from many smaller job boards.
Register at: https://jooble.org/api/about
"""

import contextlib
import logging
from datetime import datetime

from ..config import settings
from .base import BaseAPIScraper

logger = logging.getLogger(__name__)

API_URL = "https://jooble.org/api"


class JoobleScraper(BaseAPIScraper):
    PLATFORM = "jooble"

    async def search_jobs(self, query: str, location: str = "", page: int = 1) -> list[dict]:
        if not self.client:
            return []

        api_key = settings.JOOBLE_API_KEY
        if not api_key:
            logger.debug("Jooble API key not configured, skipping")
            return []

        payload = {
            "keywords": query,
            "location": location or "Germany",
            "page": str(page),
        }

        try:
            resp = await self.client.post(
                f"{API_URL}/{api_key}",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("Jooble API error: %s", e)
            return []

        jobs = []
        for item in data.get("jobs", []):
            try:
                job = self._parse_job(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug("Failed to parse Jooble job: %s", e)

        logger.info("Jooble: found %d jobs for '%s' in '%s'", len(jobs), query, location)
        return jobs

    def _parse_job(self, item: dict) -> dict | None:
        title = item.get("title", "")
        link = item.get("link", "")
        if not title or not link:
            return None

        posted_at = None
        updated = item.get("updated")
        if updated:
            with contextlib.suppress(ValueError, AttributeError):
                posted_at = datetime.fromisoformat(updated.replace("Z", "+00:00"))

        snippet = item.get("snippet", "")
        company = item.get("company", "")
        location = item.get("location", "")
        salary = item.get("salary", "")

        return {
            "platform": self.PLATFORM,
            "source_id": item.get("id", ""),
            "title": title,
            "company": company,
            "location": location,
            "url": link,
            "description": snippet,
            "employment_type": item.get("type"),
            "posted_at": posted_at,
            "salary_text": salary if salary else None,
            "remote": "remote" in title.lower() or "remote" in location.lower(),
        }

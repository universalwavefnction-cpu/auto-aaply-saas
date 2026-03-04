"""Arbeitsagentur (Federal Employment Agency) API scraper.

Largest German job database. Free API with a single header key.
Endpoint: https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs
"""

import contextlib
import logging
from datetime import datetime

from .base import BaseAPIScraper

logger = logging.getLogger(__name__)

API_BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
API_KEY = "jobboerse-jobsuche"

# Map arbeitsagentur codes to our employment_type values
ARBEITSZEIT_MAP = {
    "vz": "full-time",
    "tz": "part-time",
    "ho": "remote",
    "mj": "mini-job",
    "snw": "shift-work",
}


class ArbeitsagenturScraper(BaseAPIScraper):
    PLATFORM = "arbeitsagentur"

    async def start(self):
        await super().start()
        if self.client:
            self.client.headers["X-API-Key"] = API_KEY

    async def search_jobs(self, query: str, location: str = "", page: int = 1) -> list[dict]:
        if not self.client:
            return []

        params: dict = {
            "was": query,
            "size": 50,
            "page": max(1, page),  # AA API is 1-indexed, page=0 returns 400
        }
        if location:
            params["wo"] = location
            params["umkreis"] = 50  # 50km radius

        try:
            resp = await self.client.get(API_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("Arbeitsagentur API error: %s", e)
            return []

        jobs = []
        for item in data.get("stellenangebote", []):
            try:
                job = self._parse_job(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug("Failed to parse Arbeitsagentur job: %s", e)

        logger.info("Arbeitsagentur: found %d jobs for '%s' in '%s'", len(jobs), query, location)
        return jobs

    def _parse_job(self, item: dict) -> dict | None:
        ref_nr = item.get("refnr", "")
        title = item.get("titel", "")
        if not title:
            return None

        arbeitgeber = item.get("arbeitgeber", "")
        arbeitsort = item.get("arbeitsort", {})
        ort = arbeitsort.get("ort", "")
        plz = arbeitsort.get("plz", "")
        location_str = f"{ort} {plz}".strip() if ort else ""

        # Employment type
        arbeitszeit = item.get("arbeitszeit")
        employment_type = None
        if isinstance(arbeitszeit, list):
            employment_type = ", ".join(ARBEITSZEIT_MAP.get(a, a) for a in arbeitszeit)
        elif isinstance(arbeitszeit, str):
            employment_type = ARBEITSZEIT_MAP.get(arbeitszeit, arbeitszeit)

        # Dates
        posted_at = None
        modified = item.get("modifikationsTimestamp") or item.get("aktuelleVeroeffentlichungsdatum")
        if modified:
            with contextlib.suppress(ValueError, AttributeError):
                posted_at = datetime.fromisoformat(modified.replace("Z", "+00:00"))

        # Build URL
        url = f"https://www.arbeitsagentur.de/jobsuche/suche?id={ref_nr}&was={title}"

        return {
            "platform": self.PLATFORM,
            "source_id": ref_nr,
            "title": title,
            "company": arbeitgeber,
            "location": location_str,
            "url": url,
            "description": item.get("beruf", ""),
            "employment_type": employment_type,
            "posted_at": posted_at,
            "salary_text": None,  # AA rarely exposes salary
            "remote": bool(arbeitszeit and "ho" in (arbeitszeit if isinstance(arbeitszeit, list) else [arbeitszeit])),
        }

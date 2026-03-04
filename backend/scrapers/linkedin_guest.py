"""LinkedIn Guest API scraper.

No login needed — uses LinkedIn's public guest endpoints.
Rate limited: ~100 results per IP, use 2s delays, cap at 4 pages.
"""

import asyncio
import contextlib
import html
import logging
import re
from datetime import datetime, timezone

from .base import BaseAPIScraper

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting"
MAX_PAGES = 4
RESULTS_PER_PAGE = 25


class LinkedInGuestScraper(BaseAPIScraper):
    PLATFORM = "linkedin_guest"

    async def search_jobs(self, query: str, location: str = "", page: int = 0) -> list[dict]:
        if not self.client:
            return []

        all_jobs = []
        pages_to_fetch = min(MAX_PAGES, max(1, page + 1)) if page else MAX_PAGES

        for p in range(pages_to_fetch):
            params = {
                "keywords": query,
                "location": location or "Germany",
                "start": p * RESULTS_PER_PAGE,
                "f_TPR": "r604800",  # Past week
            }

            try:
                resp = await self.client.get(SEARCH_URL, params=params)
                if resp.status_code != 200:
                    logger.warning("LinkedIn guest search returned %d", resp.status_code)
                    break
                page_jobs = self._parse_search_html(resp.text)
                if not page_jobs:
                    break
                all_jobs.extend(page_jobs)
            except Exception as e:
                logger.error("LinkedIn guest search error: %s", e)
                break

            await asyncio.sleep(2)  # Rate limiting

        logger.info("LinkedIn guest: found %d jobs for '%s' in '%s'", len(all_jobs), query, location)
        return all_jobs

    def _parse_search_html(self, html_text: str) -> list[dict]:
        """Parse the LinkedIn guest search results HTML by splitting on <li> tags."""
        jobs = []
        # Split by </li> to get individual card blocks
        cards = html_text.split("</li>")

        for card in cards:
            try:
                job = self._parse_card(card)
                if job:
                    jobs.append(job)
            except Exception:
                continue

        return jobs

    def _parse_card(self, card_html: str) -> dict | None:
        # Extract job URL — LinkedIn uses various subdomains (www, de, uk, etc.)
        url_match = re.search(
            r'href="(https://[a-z]{2,3}\.linkedin\.com/jobs/view/[^"?]+)', card_html
        )
        if not url_match:
            return None
        url = html.unescape(url_match.group(1))

        # Extract job ID from URL or entity URN
        job_id_match = re.search(r"-(\d{8,})", url) or re.search(
            r'data-entity-urn="[^"]*:(\d+)"', card_html
        )
        source_id = job_id_match.group(1) if job_id_match else ""

        # Title
        title_match = re.search(
            r'class="base-search-card__title[^"]*"[^>]*>\s*([^<]+)', card_html
        )
        if not title_match:
            # Fallback: sr-only span
            title_match = re.search(r'<span class="sr-only">\s*([^<]+)', card_html)
        title = html.unescape(title_match.group(1).strip()) if title_match else ""
        if not title:
            return None

        # Company
        company_match = re.search(
            r'class="base-search-card__subtitle[^"]*"[^>]*>\s*(?:<a[^>]*>)?\s*([^<]+)',
            card_html,
        )
        company = html.unescape(company_match.group(1).strip()) if company_match else ""

        # Location
        loc_match = re.search(
            r'class="job-search-card__location[^"]*"[^>]*>\s*([^<]+)', card_html
        )
        location = html.unescape(loc_match.group(1).strip()) if loc_match else ""

        # Date
        date_match = re.search(r'datetime="(\d{4}-\d{2}-\d{2})"', card_html)
        posted_at = None
        if date_match:
            with contextlib.suppress(ValueError):
                posted_at = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )

        return {
            "platform": self.PLATFORM,
            "source_id": source_id,
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "description": "",
            "employment_type": None,
            "posted_at": posted_at,
            "salary_text": None,
            "remote": "remote" in location.lower() or "remote" in title.lower(),
        }

    async def get_job_detail(self, job_id: str) -> dict | None:
        """Fetch full job description from LinkedIn guest detail endpoint."""
        if not self.client:
            return None
        try:
            resp = await self.client.get(f"{DETAIL_URL}/{job_id}")
            if resp.status_code != 200:
                return None
            desc_match = re.search(
                r'class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>',
                resp.text,
                re.DOTALL,
            )
            if desc_match:
                desc = re.sub(r"<[^>]+>", " ", desc_match.group(1))
                desc = re.sub(r"\s+", " ", desc).strip()
                return {"description": desc[:5000]}
        except Exception as e:
            logger.debug("LinkedIn guest detail error for %s: %s", job_id, e)
        return None

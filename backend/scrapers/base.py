import asyncio
import random
from abc import ABC, abstractmethod

import httpx
from playwright.async_api import Browser, Page, async_playwright

from ..config import settings


class BaseScraper(ABC):
    """Base class for all job platform scrapers (browser-based)."""

    PLATFORM = "unknown"

    def __init__(self):
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def start(self):
        pw = await async_playwright().start()
        self.browser = await pw.chromium.launch(
            headless=settings.HEADLESS,
            slow_mo=settings.SLOW_MO,
        )
        context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="de-DE",
        )
        self.page = await context.new_page()

    async def stop(self):
        if self.browser:
            await self.browser.close()

    async def random_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        await asyncio.sleep(random.uniform(min_s, max_s))

    @abstractmethod
    async def login(self, email: str, password: str) -> bool:
        """Login to the platform. Returns True on success."""
        ...

    @abstractmethod
    async def search_jobs(self, query: str, location: str = "") -> list[dict]:
        """Search for jobs. Returns list of job dicts."""
        ...

    @abstractmethod
    async def apply_to_job(self, job_url: str, profile: dict) -> dict:
        """Apply to a job. Returns result dict with status and error."""
        ...


class BaseAPIScraper(ABC):
    """Base class for API-based job scrapers (no browser, pure HTTP)."""

    PLATFORM = "unknown"

    def __init__(self):
        self.client: httpx.AsyncClient | None = None

    async def start(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            },
            follow_redirects=True,
        )

    async def stop(self):
        if self.client:
            await self.client.aclose()

    @abstractmethod
    async def search_jobs(self, query: str, location: str = "", page: int = 0) -> list[dict]:
        """Search for jobs. Returns list of standardized job dicts."""
        ...

    async def get_job_detail(self, job_id: str) -> dict | None:
        """Optional: fetch full job details by platform ID."""
        return None

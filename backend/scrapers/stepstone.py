import asyncio
from datetime import datetime, timezone

from .base import BaseScraper


class StepStoneScraper(BaseScraper):
    PLATFORM = "stepstone"
    BASE_URL = "https://www.stepstone.de"

    async def _accept_cookies(self):
        try:
            consent = await self.page.query_selector("#onetrust-accept-btn-handler")
            if consent:
                await consent.click()
                await asyncio.sleep(1)
        except Exception:
            pass

    async def login(self, email: str, password: str) -> bool:
        try:
            await self.page.goto(f"{self.BASE_URL}/login", timeout=20000)
            await self.random_delay(2, 4)
            await self._accept_cookies()
            await self.page.fill('input[name="email"], input[type="email"]', email)
            await self.random_delay(0.5, 1)
            await self.page.fill('input[name="password"], input[type="password"]', password)
            await self.random_delay(0.5, 1)
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await self.random_delay(2, 3)
            return "login" not in self.page.url.lower()
        except Exception as e:
            print(f"[StepStone] Login failed: {e}")
            return False

    async def search_jobs(self, query: str, location: str = "") -> list[dict]:
        jobs = []
        try:
            search_url = f"{self.BASE_URL}/jobs/{query}"
            if location:
                search_url += f"/in-{location}"
            await self.page.goto(search_url, timeout=20000)
            await self.random_delay(3, 5)
            await self._accept_cookies()

            cards = await self.page.query_selector_all('[data-testid="job-item"]')
            for card in cards:
                try:
                    title_el = await card.query_selector('a[data-testid="job-item-title"], h2 a')
                    title = (await title_el.inner_text()).strip() if title_el else ""
                    href = (await title_el.get_attribute("href")) if title_el else ""

                    # Parse company + location from card text lines
                    full_text = await card.inner_text()
                    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
                    company = lines[1] if len(lines) > 1 else ""
                    loc = lines[2] if len(lines) > 2 else ""

                    if title and href:
                        url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                        jobs.append(
                            {
                                "platform": self.PLATFORM,
                                "title": title,
                                "company": company,
                                "location": loc,
                                "url": url,
                                "scraped_at": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                except Exception:
                    continue
        except Exception as e:
            print(f"[StepStone] Search failed: {e}")
        return jobs

    async def apply_to_job(self, job_url: str, profile: dict) -> dict:
        try:
            await self.page.goto(job_url, timeout=20000)
            await self.random_delay(2, 4)
            await self._accept_cookies()

            # Click apply button
            apply_btn = await self.page.query_selector(
                'button:has-text("Jetzt bewerben"), button:has-text("Apply"), a:has-text("Jetzt bewerben")'
            )
            if not apply_btn:
                return {"status": "failed", "error": "No apply button found"}

            await apply_btn.click()
            await self.random_delay(2, 4)

            from ..automation.form_filler import fill_form

            result = await fill_form(self.page, profile)
            return result

        except Exception as e:
            return {"status": "failed", "error": str(e)}

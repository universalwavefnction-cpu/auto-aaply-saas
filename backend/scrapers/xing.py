from datetime import datetime, timezone

from .base import BaseScraper


class XingScraper(BaseScraper):
    PLATFORM = "xing"
    BASE_URL = "https://www.xing.com"

    async def login(self, email: str, password: str) -> bool:
        try:
            await self.page.goto(f"{self.BASE_URL}/login")
            await self.random_delay(2, 4)
            await self.page.fill('input[name="username"], input[name="login_form[username]"]', email)
            await self.random_delay(0.5, 1)
            await self.page.fill('input[name="password"], input[name="login_form[password]"]', password)
            await self.random_delay(0.5, 1)
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await self.random_delay(2, 3)
            return "login" not in self.page.url.lower()
        except Exception as e:
            print(f"[Xing] Login failed: {e}")
            return False

    async def search_jobs(self, query: str, location: str = "") -> list[dict]:
        jobs = []
        try:
            params = f"keywords={query}"
            if location:
                params += f"&location={location}"
            await self.page.goto(f"{self.BASE_URL}/jobs/search?{params}")
            await self.random_delay(2, 4)

            cards = await self.page.query_selector_all('[data-testid="job-posting-card"], .jobPosting-listItem')
            for card in cards:
                try:
                    title_el = await card.query_selector('a[data-testid="job-title"], h3 a, a.jobPosting-title')
                    company_el = await card.query_selector('[data-testid="company-name"], .jobPosting-company')
                    location_el = await card.query_selector('[data-testid="job-location"], .jobPosting-location')

                    title = await title_el.inner_text() if title_el else ""
                    href = await title_el.get_attribute("href") if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else ""

                    if title and href:
                        url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                        jobs.append(
                            {
                                "platform": self.PLATFORM,
                                "title": title.strip(),
                                "company": company.strip(),
                                "location": loc.strip(),
                                "url": url,
                                "scraped_at": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                except Exception:
                    continue
        except Exception as e:
            print(f"[Xing] Search failed: {e}")
        return jobs

    async def apply_to_job(self, job_url: str, profile: dict) -> dict:
        try:
            await self.page.goto(job_url)
            await self.random_delay(2, 4)

            apply_btn = await self.page.query_selector(
                'button:has-text("Jetzt bewerben"), button:has-text("Bewerben"), a:has-text("Bewerben")'
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

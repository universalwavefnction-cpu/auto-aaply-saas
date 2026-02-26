"""Bot engine: orchestrates scraping + applying with real-time event emission and detailed logging."""
import asyncio
import json
import os
import time
import uuid
import random
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright
from thefuzz import fuzz
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import BotLog, Job, Application, Profile, PlatformCredential, JobFilter

SCREENSHOT_DIR = Path("/tmp/bot_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


class BotEngine:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())[:8]
        self.events: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.stats = {"applied": 0, "failed": 0, "skipped": 0, "total": 0, "fields_filled": 0, "fields_total": 0}
        self._db: Session | None = None
        self._browser = None
        self._page = None

    def _get_db(self) -> Session:
        if not self._db:
            self._db = SessionLocal()
        return self._db

    async def log(self, level: str, category: str, event: str, data: dict = None, job_id: int = None, platform: str = None):
        """Log to DB + emit to SSE stream."""
        ts = datetime.now(timezone.utc)
        data = data or {}

        # Write to DB
        try:
            db = self._get_db()
            log_entry = BotLog(
                user_id=self.user_id,
                session_id=self.session_id,
                timestamp=ts,
                level=level,
                category=category,
                event=event,
                job_id=job_id,
                platform=platform,
                data=data,
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            print(f"[BotLog DB Error] {e}")

        # Build display message
        msg = data.get("message", f"[{category}] {event}")

        # Emit to SSE stream (info and above)
        if level in ("info", "warn", "error"):
            await self.events.put({
                "type": "log",
                "level": level,
                "category": category,
                "event": event,
                "message": msg,
                "data": data,
                "ts": ts.isoformat(),
            })

        # Print to stdout
        print(f"[{self.session_id}][{level}][{category}] {msg}")

    async def emit_progress(self):
        await self.events.put({
            "type": "progress",
            "data": self.stats.copy(),
            "ts": datetime.now(timezone.utc).isoformat(),
        })

    async def emit_status(self, status: str):
        await self.events.put({
            "type": "status",
            "data": status,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

    async def screenshot(self, label: str = "step"):
        """Capture screenshot, save, and emit event."""
        if not self._page:
            return
        try:
            filename = f"{self.user_id}_latest.png"
            path = SCREENSHOT_DIR / filename
            await self._page.screenshot(path=str(path))
            await self.events.put({
                "type": "screenshot",
                "url": f"/api/bot/screenshot/latest?t={int(time.time())}",
                "label": label,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            await self.log("debug", "browser", "screenshot", {"label": label, "path": str(path)})
        except Exception as e:
            await self.log("warn", "browser", "screenshot_failed", {"error": str(e)})

    async def _dismiss_consent(self):
        """Handle cookie/GDPR consent overlays."""
        selectors = [
            "#onetrust-accept-btn-handler",
            "button:has-text('Alle akzeptieren')",
            "button:has-text('Akzeptieren')",
            "button:has-text('Zustimmen')",
        ]
        for sel in selectors:
            try:
                btn = await self._page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await self.log("debug", "browser", "consent_dismissed", {"selector": sel})
                    await asyncio.sleep(1)
                    return True
            except:
                continue
        # Force remove overlay
        try:
            removed = await self._page.evaluate(
                "() => { const el = document.getElementById('GDPRConsentManagerContainer'); if (el) { el.remove(); return true; } return false; }"
            )
            if removed:
                await self.log("debug", "browser", "consent_force_removed")
                return True
        except:
            pass
        return False

    async def _match_and_fill_form(self, profile: dict, job_id: int = None, platform: str = None) -> dict:
        """Detect form fields, fuzzy match Q&A, fill. Returns detailed result."""
        questions = profile.get("questions_json", {})
        field_map = {
            "first name": "first_name", "vorname": "first_name",
            "last name": "last_name", "nachname": "last_name",
            "phone": "phone", "telefon": "phone", "mobile": "phone",
            "city": "city", "stadt": "city", "ort": "city",
            "zip": "zip_code", "plz": "zip_code", "postal": "zip_code",
            "street": "street_address", "strasse": "street_address",
            "salary": "salary_expectation", "gehalt": "salary_expectation",
            "experience": "years_experience", "erfahrung": "years_experience",
            "linkedin": "linkedin_url", "e-mail": "email", "email": "email",
        }

        inputs = await self._page.query_selector_all("input:visible, textarea:visible, select:visible")
        filled = 0
        skipped = 0
        unmatched = []
        field_details = []

        for inp in inputs:
            try:
                input_type = await inp.get_attribute("type") or "text"
                if input_type in ("hidden", "submit", "button", "file", "image"):
                    continue

                # Get label
                aria = await inp.get_attribute("aria-label") or ""
                placeholder = await inp.get_attribute("placeholder") or ""
                name = await inp.get_attribute("name") or ""
                inp_id = await inp.get_attribute("id") or ""
                label_text = aria or placeholder
                if not label_text and inp_id:
                    try:
                        label_el = await self._page.query_selector(f'label[for="{inp_id}"]')
                        if label_el:
                            label_text = (await label_el.inner_text()).strip()
                    except:
                        pass
                if not label_text:
                    label_text = name.replace("_", " ").replace("-", " ")

                if not label_text:
                    continue

                self.stats["fields_total"] += 1

                # Try direct profile field match
                answer = None
                matched_via = None
                match_score = 0
                label_lower = label_text.lower()

                for key, field in field_map.items():
                    if key in label_lower:
                        val = profile.get(field)
                        if val is not None:
                            answer = str(val)
                            matched_via = f"profile.{field}"
                            match_score = 100
                            break

                # Try fuzzy Q&A match
                if not answer:
                    best_score = 0
                    best_q = None
                    for q, a in questions.items():
                        score = fuzz.partial_ratio(label_lower, q.lower())
                        if score > best_score:
                            best_score = score
                            best_q = q
                            if score >= 70:
                                answer = a
                                matched_via = f"qa: {q}"
                                match_score = score

                detail = {
                    "label": label_text,
                    "type": input_type,
                    "name": name,
                    "matched_via": matched_via,
                    "answer": answer[:50] if answer else None,
                    "confidence": match_score,
                }
                field_details.append(detail)

                if answer:
                    # Fill the field
                    tag = await inp.evaluate("el => el.tagName")
                    if input_type == "checkbox":
                        if answer.lower() in ("yes", "ja", "true", "1"):
                            await inp.check()
                    elif tag == "SELECT":
                        options = await inp.query_selector_all("option")
                        best_opt_score = 0
                        best_opt_val = None
                        for opt in options:
                            opt_text = (await opt.inner_text()).strip()
                            s = fuzz.partial_ratio(answer.lower(), opt_text.lower())
                            if s > best_opt_score:
                                best_opt_score = s
                                best_opt_val = await opt.get_attribute("value")
                        if best_opt_val and best_opt_score >= 60:
                            await inp.select_option(value=best_opt_val)
                    else:
                        await inp.fill("")
                        await inp.type(answer, delay=random.randint(30, 80))

                    filled += 1
                    self.stats["fields_filled"] += 1
                    await self.log("info", "form", "field_filled", {
                        "message": f"  Field: {label_text} → {answer[:30]}",
                        **detail,
                    }, job_id=job_id, platform=platform)
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                else:
                    skipped += 1
                    unmatched.append(label_text)
                    await self.log("debug", "form", "field_skipped", {
                        "message": f"  Field skipped: {label_text} (best score: {match_score})",
                        **detail,
                    }, job_id=job_id, platform=platform)

            except Exception as e:
                await self.log("warn", "form", "field_error", {
                    "message": f"  Field error: {e}",
                    "error": str(e),
                }, job_id=job_id, platform=platform)

        # Log form summary
        await self.log("info", "form", "form_summary", {
            "message": f"Form: {filled} filled, {skipped} skipped, {len(unmatched)} unmatched",
            "total_fields": filled + skipped,
            "filled": filled,
            "skipped": skipped,
            "unmatched_labels": unmatched,
            "field_details": field_details,
        }, job_id=job_id, platform=platform)

        return {"filled": filled, "skipped": skipped, "unmatched": unmatched, "details": field_details}

    async def run(self, mode: str = "scrape_and_apply"):
        """Main bot loop. Scrapes jobs then applies."""
        self.running = True
        start_time = time.time()
        await self.emit_status("starting")
        await self.log("info", "system", "session_start", {
            "message": f"Bot session {self.session_id} starting (mode: {mode})",
            "mode": mode,
            "session_id": self.session_id,
        })

        db = self._get_db()
        profile_row = db.query(Profile).filter(Profile.user_id == self.user_id).first()
        job_filter = db.query(JobFilter).filter(JobFilter.user_id == self.user_id).first()
        creds = db.query(PlatformCredential).filter(
            PlatformCredential.user_id == self.user_id,
            PlatformCredential.is_active == True,
        ).all()

        if not profile_row:
            await self.log("error", "system", "no_profile", {"message": "No profile configured"})
            await self.emit_status("error")
            self.running = False
            return

        profile = {
            "first_name": profile_row.first_name,
            "last_name": profile_row.last_name,
            "phone": profile_row.phone,
            "city": profile_row.city,
            "zip_code": profile_row.zip_code,
            "street_address": profile_row.street_address,
            "salary_expectation": profile_row.salary_expectation,
            "years_experience": profile_row.years_experience,
            "linkedin_url": profile_row.linkedin_url,
            "email": db.query(PlatformCredential).filter(
                PlatformCredential.user_id == self.user_id
            ).first().email if creds else "",
            "questions_json": profile_row.questions_json or {},
        }

        try:
            # Phase 1: Scrape jobs
            if mode in ("scrape_and_apply", "scrape"):
                await self._scrape_phase(db, job_filter, profile)

            # Phase 2: Apply to jobs
            if mode in ("scrape_and_apply", "apply") and self.running:
                await self._apply_phase(db, profile, creds, job_filter)

        except Exception as e:
            await self.log("error", "system", "crash", {
                "message": f"Bot crashed: {e}",
                "error": str(e),
            })
        finally:
            if self._browser:
                await self._browser.close()
            if self._db:
                self._db.close()
                self._db = None

            duration = time.time() - start_time
            await self.log("info", "system", "session_end", {
                "message": f"Session complete: {self.stats['applied']} applied, {self.stats['failed']} failed in {duration:.0f}s",
                "duration_s": duration,
                "stats": self.stats,
            })
            await self.emit_status("complete")
            self.running = False

    async def _scrape_phase(self, db: Session, job_filter: JobFilter, profile: dict):
        """Scrape StepStone for new jobs."""
        await self.log("info", "scrape", "phase_start", {"message": "Starting job discovery..."})
        await self.emit_status("scraping")

        queries = job_filter.job_titles if job_filter and job_filter.job_titles else ["project-manager"]
        locations = job_filter.locations if job_filter and job_filter.locations else ["berlin"]

        pw = await async_playwright().start()
        total_new = 0

        for query in queries:
            for loc in locations:
                if not self.running:
                    break

                query_slug = query.lower().replace(" ", "-")
                url = f"https://www.stepstone.de/jobs/{query_slug}/in-{loc.lower()}"

                await self.log("info", "scrape", "search_start", {
                    "message": f"Searching: {query} in {loc}",
                    "query": query, "location": loc, "url": url,
                }, platform="stepstone")

                browser = await pw.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    viewport={"width": 1366, "height": 768},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="de-DE",
                )
                self._page = await ctx.new_page()

                try:
                    t0 = time.time()
                    await self._page.goto(url, timeout=20000)
                    load_time = time.time() - t0
                    await asyncio.sleep(random.uniform(3, 5))

                    await self.log("debug", "browser", "page_load", {
                        "url": url, "load_time_ms": int(load_time * 1000),
                        "title": await self._page.title(),
                    }, platform="stepstone")

                    await self._dismiss_consent()
                    await self.screenshot("search_results")

                    cards = await self._page.query_selector_all("[data-testid='job-item']")
                    await self.log("info", "scrape", "jobs_found", {
                        "message": f"  Found {len(cards)} jobs",
                        "count": len(cards),
                    }, platform="stepstone")

                    new_in_batch = 0
                    for card in cards:
                        try:
                            title_el = await card.query_selector("a[data-testid='job-item-title'], h2 a")
                            title = (await title_el.inner_text()).strip() if title_el else ""
                            href = (await title_el.get_attribute("href")) if title_el else ""
                            text = await card.inner_text()
                            lines = [l.strip() for l in text.split("\n") if l.strip()]
                            company = lines[1] if len(lines) > 1 else ""
                            location = lines[2] if len(lines) > 2 else ""

                            if not title or not href:
                                continue

                            full_url = href if href.startswith("http") else f"https://www.stepstone.de{href}"

                            # Check blacklist
                            if job_filter:
                                bl_companies = job_filter.blacklist_companies or []
                                bl_keywords = job_filter.blacklist_keywords or []
                                if any(bc.lower() in company.lower() for bc in bl_companies):
                                    continue
                                if any(bk.lower() in title.lower() for bk in bl_keywords):
                                    continue

                            # Upsert
                            existing = db.query(Job).filter(Job.url == full_url).first()
                            if not existing:
                                db.add(Job(
                                    platform="stepstone", title=title, company=company,
                                    location=location, url=full_url,
                                    scraped_at=datetime.now(timezone.utc),
                                ))
                                new_in_batch += 1
                        except:
                            continue

                    db.commit()
                    total_new += new_in_batch
                    await self.log("info", "scrape", "search_complete", {
                        "message": f"  {new_in_batch} new jobs stored",
                        "new_jobs": new_in_batch,
                    }, platform="stepstone")

                except Exception as e:
                    await self.log("warn", "scrape", "search_failed", {
                        "message": f"  Search failed: {str(e)[:80]}",
                        "error": str(e), "url": url,
                    }, platform="stepstone")

                await browser.close()
                self._page = None
                await asyncio.sleep(random.uniform(8, 12))

        await self.log("info", "scrape", "phase_complete", {
            "message": f"Discovery complete: {total_new} new jobs found",
            "total_new": total_new,
        })

    async def _apply_phase(self, db: Session, profile: dict, creds: list, job_filter: JobFilter):
        """Apply to unapplied jobs."""
        await self.log("info", "apply", "phase_start", {"message": "Starting application phase..."})
        await self.emit_status("applying")

        # Get already-applied URLs
        applied_urls = set(
            r[0] for r in db.query(Application.url).filter(Application.user_id == self.user_id).all() if r[0]
        )

        # Get jobs to apply to
        jobs = db.query(Job).filter(
            Job.platform == "stepstone",
            ~Job.url.in_(applied_urls) if applied_urls else True,
        ).limit(10).all()

        self.stats["total"] = len(jobs)
        await self.log("info", "apply", "jobs_queued", {
            "message": f"Queued {len(jobs)} jobs for application",
            "count": len(jobs),
        })
        await self.emit_progress()

        if not jobs:
            await self.log("info", "apply", "no_jobs", {"message": "No unapplied jobs found"})
            return

        pw = await async_playwright().start()

        for i, job in enumerate(jobs):
            if not self.running:
                break

            await self.log("info", "apply", "job_start", {
                "message": f"[{i+1}/{len(jobs)}] Opening: {job.title} at {job.company}",
                "job_title": job.title, "company": job.company, "url": job.url,
                "index": i + 1,
            }, job_id=job.id, platform=job.platform)

            # Create application record
            application = Application(
                user_id=self.user_id,
                job_id=job.id,
                platform=job.platform,
                job_title=job.title,
                company=job.company,
                url=job.url,
                status="applying",
                applied_at=datetime.now(timezone.utc),
            )
            db.add(application)
            db.commit()

            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="de-DE",
            )
            self._page = await ctx.new_page()

            try:
                t0 = time.time()
                await self._page.goto(job.url, timeout=20000)
                load_time = time.time() - t0
                await asyncio.sleep(random.uniform(2, 4))

                await self.log("debug", "browser", "page_load", {
                    "url": job.url, "load_time_ms": int(load_time * 1000),
                    "title": await self._page.title(),
                }, job_id=job.id, platform=job.platform)

                await self._dismiss_consent()
                await self.screenshot(f"job_page_{job.id}")

                # Find apply button
                apply_btn = None
                btn_text = ""
                for sel in [
                    'a:has-text("Jetzt bewerben")',
                    'button:has-text("Jetzt bewerben")',
                    'a:has-text("Schnelle Bewerbung")',
                    'button:has-text("Schnelle Bewerbung")',
                    'a:has-text("Ich bin interessiert")',
                    'button:has-text("Ich bin interessiert")',
                ]:
                    apply_btn = await self._page.query_selector(sel)
                    if apply_btn:
                        btn_text = (await apply_btn.inner_text()).strip()
                        await self.log("info", "apply", "button_found", {
                            "message": f"  Apply button: \"{btn_text}\"",
                            "selector": sel, "button_text": btn_text,
                        }, job_id=job.id, platform=job.platform)
                        break

                if not apply_btn:
                    await self.log("warn", "apply", "no_button", {
                        "message": "  No apply button found — skipping",
                    }, job_id=job.id, platform=job.platform)
                    application.status = "skipped"
                    application.error_log = "No apply button found"
                    db.commit()
                    self.stats["skipped"] += 1
                    await self.emit_progress()
                    await browser.close()
                    continue

                # Click apply
                await self.log("info", "apply", "clicking_apply", {
                    "message": f"  Clicking \"{btn_text}\"...",
                }, job_id=job.id, platform=job.platform)
                await apply_btn.click(force=True, timeout=10000)
                await asyncio.sleep(random.uniform(3, 5))
                await self._dismiss_consent()
                await self.screenshot(f"after_apply_{job.id}")

                # Check if redirected to login
                page_text = await self._page.inner_text("body")
                if "anmelden" in page_text.lower() or "einloggen" in page_text.lower():
                    await self.log("warn", "apply", "login_required", {
                        "message": "  Login required — skipping (need credentials)",
                    }, job_id=job.id, platform=job.platform)
                    application.status = "skipped"
                    application.error_log = "Login required"
                    db.commit()
                    self.stats["skipped"] += 1
                    await self.emit_progress()
                    await browser.close()
                    continue

                # Detect and fill form
                await self.log("info", "form", "detecting", {
                    "message": "  Scanning form fields...",
                }, job_id=job.id, platform=job.platform)

                form_result = await self._match_and_fill_form(profile, job_id=job.id, platform=job.platform)
                await self.screenshot(f"form_filled_{job.id}")

                if form_result["filled"] > 0:
                    # Try to submit
                    submit = await self._page.query_selector(
                        'button[type="submit"], button:has-text("Absenden"), '
                        'button:has-text("Bewerben"), button:has-text("Submit")'
                    )
                    if submit:
                        await self.log("info", "apply", "submitting", {
                            "message": "  Submitting application...",
                        }, job_id=job.id, platform=job.platform)
                        await submit.click()
                        await asyncio.sleep(3)
                        await self.screenshot(f"submitted_{job.id}")

                    application.status = "success"
                    self.stats["applied"] += 1
                    apply_duration = time.time() - t0
                    await self.log("info", "apply", "success", {
                        "message": f"  SUCCESS — {form_result['filled']} fields filled in {apply_duration:.0f}s",
                        "fields_filled": form_result["filled"],
                        "duration_s": apply_duration,
                    }, job_id=job.id, platform=job.platform)
                else:
                    application.status = "failed"
                    application.error_log = f"No fields matched. Unmatched: {form_result['unmatched'][:5]}"
                    self.stats["failed"] += 1
                    await self.log("warn", "apply", "no_fields_matched", {
                        "message": f"  FAILED — no fields could be matched",
                        "unmatched": form_result["unmatched"],
                    }, job_id=job.id, platform=job.platform)

                db.commit()
                await self.emit_progress()

            except Exception as e:
                application.status = "failed"
                application.error_log = str(e)[:500]
                db.commit()
                self.stats["failed"] += 1
                await self.log("error", "apply", "error", {
                    "message": f"  ERROR: {str(e)[:100]}",
                    "error": str(e),
                }, job_id=job.id, platform=job.platform)
                await self.emit_progress()

            await browser.close()
            self._page = None

            # Delay between applications
            if i < len(jobs) - 1 and self.running:
                delay = random.uniform(15, 30)
                await self.log("info", "system", "delay", {
                    "message": f"  Waiting {delay:.0f}s before next application...",
                    "delay_s": delay,
                })
                await asyncio.sleep(delay)

    async def stop(self):
        """Gracefully stop the bot."""
        await self.log("info", "system", "stop_requested", {"message": "Stop requested by user"})
        self.running = False

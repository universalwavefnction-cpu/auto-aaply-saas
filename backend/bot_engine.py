"""Bot engine: orchestrates scraping + applying with real-time event emission and detailed logging."""
import asyncio
import json
import os
import re
import time
import uuid
import random
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import httpx
from playwright.async_api import async_playwright
from thefuzz import fuzz
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import BotLog, Job, Application, Profile, PlatformCredential, JobFilter, CVFile
from .config import settings

SCREENSHOT_DIR = Path("/tmp/bot_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

def _normalize_german(text: str) -> str:
    """Normalize German umlauts and ß for matching. Also strips (m/w/d) suffixes."""
    import re as _re
    text = _re.sub(r'\s*\([mwfd/]+\)', '', text, flags=_re.IGNORECASE)
    text = text.lower().strip()
    text = text.replace('ä', 'a').replace('ö', 'o').replace('ü', 'u').replace('ß', 'ss')
    text = text.replace('-', ' ').replace('  ', ' ')
    return text


# Related job titles / synonyms — if user searches "kellner", accept "servicekraft" etc.
_JOB_SYNONYMS: dict[str, set[str]] = {
    "kellner": {"service", "servicekraft", "servicekrafte", "servicemitarbeiter", "bedienung", "gastronomie", "systemgastronomie", "restaurant", "barkeeper", "barista", "rezeptionist", "bankett", "catering", "buffet", "hotelfachmann", "hotelfachfrau", "empfang", "front office", "kassenkraft"},
    "barista": {"cafe", "coffee", "kellner", "service", "gastronomie"},
    "koch": {"kuche", "kuchenhilfe", "kuchenleiter", "gastronomie", "chefkoch", "beikoch", "souschef"},
    "verkaufer": {"verkauf", "fachverkaufer", "einzelhandel", "handel", "kassierer", "kassenkraft"},
    "fahrer": {"kurier", "lieferant", "zusteller", "logistik", "transport", "lkw", "chauffeur"},
    "reinigung": {"reinigungskraft", "gebaude", "hauswirtschaft", "zimmer", "housekeeping", "raumpflege"},
    "lager": {"lagerist", "lagermitarbeiter", "logistik", "kommissionierer", "versand"},
    "buro": {"burokraft", "sachbearbeiter", "verwaltung", "administration", "sekretariat", "empfang"},
    "pflege": {"pflegekraft", "altenpflege", "krankenpflege", "pflegehilfe", "pflegeassistent", "betreuer"},
}


def _is_title_relevant(job_title: str, search_queries: list[str], threshold: int = 60) -> bool:
    """Check if a job title is relevant to any of the search queries.
    Handles German plurals (Servicekraft/Servicekräfte), umlauts, hyphens.
    Also checks synonym groups so "kellner" matches "Servicekraft" etc."""
    if not search_queries:
        return True
    clean_title = _normalize_german(job_title)
    # Also create compact version (no spaces) for compound word matching
    compact_title = clean_title.replace(' ', '')
    for query in search_queries:
        q_norm = _normalize_german(query)
        q_compact = q_norm.replace(' ', '')
        # Exact substring: query appears in title or title appears in query
        if q_norm in clean_title or clean_title in q_norm:
            return True
        # Compact match: "servicekraft" in "servicekraftehotel"
        if q_compact in compact_title or compact_title in q_compact:
            return True
        # Stem match: "servicekraft" matches "servicekrafte" (German plural drops -e suffix)
        # Check if query stem is a prefix of any word in title
        for word in clean_title.split():
            if word.startswith(q_norm) or q_norm.startswith(word):
                return True
        # Check if all significant words from query appear in title
        query_words = [w for w in q_norm.split() if len(w) > 2]
        if query_words and all(w in clean_title for w in query_words):
            return True
        # Synonym matching: check if any synonym of the query appears in the title
        synonyms = _JOB_SYNONYMS.get(q_norm, set())
        for syn in synonyms:
            if syn in clean_title or syn in compact_title:
                return True
        # Also check reverse: if title words are synonyms of the query
        for syn_key, syn_set in _JOB_SYNONYMS.items():
            if q_norm in syn_set or q_norm == syn_key:
                # This query is related to syn_key — check if title has syn_key or its synonyms
                if syn_key in clean_title:
                    return True
                for s in syn_set:
                    if s in clean_title:
                        return True
        # Fuzzy token_set_ratio — high threshold to avoid false positives
        score = fuzz.token_set_ratio(q_norm, clean_title)
        if score >= threshold:
            return True
    return False


def _to_short_url(url: str) -> str:
    """Convert long stellenangebote URLs to short /job/ format. Long URLs get blocked from datacenter IPs."""
    # Already short format
    if "/job/" in url and not "stellenangebote" in url:
        return url
    # Extract job ID from long URL like: stellenangebote--Title--12345678-inline.html
    m = re.search(r'--(\d{6,})', url)
    if m:
        return f"https://www.stepstone.de/job/{m.group(1)}"
    return url


STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = {runtime: {}};
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['de-DE', 'de', 'en']});
"""


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

    async def _dismiss_consent(self, page=None):
        """Handle cookie/GDPR consent overlays. Always force-removes as fallback."""
        p = page or self._page
        if not p:
            return False
        # First try clicking "Alles akzeptieren" with force
        for sel in [
            'button:has-text("Alles akzeptieren")',
            'button:has-text("Alle akzeptieren")',
            "#onetrust-accept-btn-handler",
            'button:has-text("Akzeptieren")',
            'button:has-text("Zustimmen")',
        ]:
            try:
                btn = await p.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click(force=True, timeout=3000)
                    await self.log("debug", "browser", "consent_clicked", {"selector": sel})
                    await asyncio.sleep(1)
                    break
            except:
                continue
        # Always force-remove the overlay container
        try:
            await p.evaluate("""() => {
                const el = document.getElementById('GDPRConsentManagerContainer');
                if (el) el.remove();
                // Also remove any overlay/modal backdrops
                document.querySelectorAll('[class*="overlay"], [class*="backdrop"], [class*="consent"]').forEach(e => {
                    if (e.style && (e.style.position === 'fixed' || e.style.position === 'absolute')) e.remove();
                });
                document.body.style.overflow = 'auto';
            }""")
        except:
            pass
        return True

    async def _dismiss_popups(self, page=None):
        """Dismiss job alert and other non-consent popups that block the page."""
        p = page or self._page
        if not p:
            return
        # Dismiss "Keinen Job mehr verpassen" / "Never miss a job" / "Erhalte passende Jobs" popup
        # These have an X close button
        for sel in [
            'button:has-text("Dismiss popup")',
            'button[aria-label="close"]',
            'button[aria-label="Close"]',
            'button[aria-label="schließen"]',
            'button[aria-label="Schließen"]',
        ]:
            try:
                btn = await p.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click(force=True, timeout=3000)
                    await self.log("debug", "browser", "popup_dismissed", {"selector": sel})
                    await asyncio.sleep(1)
                    break
            except:
                continue
        # Force-remove the job-agent modal overlay (blocks clicks on "Ich bin interessiert")
        # The overlay has id="portal/job-agent-modal-dialog" and data-genesis-element="DRAWER_OVERLAY"
        try:
            removed = await p.evaluate("""() => {
                let removed = 0;
                // Remove the specific StepStone job-agent modal portal
                const portal = document.getElementById('portal/job-agent-modal-dialog');
                if (portal) { portal.remove(); removed++; }
                // Remove any DRAWER_OVERLAY elements
                document.querySelectorAll('[data-genesis-element="DRAWER_OVERLAY"]').forEach(e => { e.remove(); removed++; });
                // Remove role="dialog" modals about job alerts
                document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="popup"]').forEach(e => {
                    if (e.textContent && (
                        e.textContent.includes('verpassen') ||
                        e.textContent.includes('miss a job') ||
                        e.textContent.includes('passende Jobs') ||
                        e.textContent.includes('job matches') ||
                        e.textContent.includes('Dismiss popup')
                    )) {
                        e.remove(); removed++;
                    }
                });
                // Remove all backdrop/overlay elements that block pointer events
                document.querySelectorAll('[class*="backdrop"], [class*="Backdrop"], [class*="OVERLAY"], [class*="overlay"]').forEach(e => {
                    const style = window.getComputedStyle(e);
                    if (style.position === 'fixed' || style.position === 'absolute') {
                        e.remove(); removed++;
                    }
                });
                document.body.style.overflow = 'auto';
                return removed;
            }""")
            if removed > 0:
                await self.log("debug", "browser", "overlay_removed", {"count": removed})
        except:
            pass

    async def _extract_form_fields(self) -> list[dict]:
        """Extract all visible form fields with their metadata."""
        fields = []
        inputs = await self._page.query_selector_all("input:visible, textarea:visible, select:visible")

        for idx, inp in enumerate(inputs):
            try:
                input_type = await inp.get_attribute("type") or "text"
                if input_type in ("hidden", "submit", "button", "file", "image"):
                    continue

                aria = await inp.get_attribute("aria-label") or ""
                placeholder = await inp.get_attribute("placeholder") or ""
                name = await inp.get_attribute("name") or ""
                inp_id = await inp.get_attribute("id") or ""
                tag = await inp.evaluate("el => el.tagName")

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

                # Skip search/navigation fields — these are NOT application form fields
                search_indicators = ["search", "suche", "find job", "e.g.", "z.b.", "filter"]
                if any(si in label_text.lower() for si in search_indicators):
                    continue
                # Skip fields with search-related roles or names
                role = await inp.get_attribute("role") or ""
                if role in ("search", "searchbox", "combobox"):
                    continue
                if any(si in name.lower() for si in ["search", "query", "keyword", "q"]):
                    continue

                field_info = {
                    "index": idx,
                    "label": label_text,
                    "type": input_type,
                    "tag": tag,
                    "name": name,
                    "id": inp_id,
                    "element": inp,  # kept for filling later, stripped before sending to AI
                }

                # For selects, extract available options
                if tag == "SELECT":
                    options = await inp.query_selector_all("option")
                    opt_list = []
                    for opt in options:
                        opt_text = (await opt.inner_text()).strip()
                        opt_val = await opt.get_attribute("value") or ""
                        if opt_text and opt_val:
                            opt_list.append({"text": opt_text, "value": opt_val})
                    field_info["options"] = opt_list

                # For radio/checkbox, get current state
                if input_type in ("checkbox", "radio"):
                    field_info["checked"] = await inp.is_checked()

                fields.append(field_info)
            except:
                continue

        return fields

    async def _ask_ai_for_answers(self, fields: list[dict], profile: dict, job_title: str = "", company: str = "") -> dict:
        """Send form fields + profile to OpenRouter AI, get back field→answer mapping."""
        api_key = settings.OPENROUTER_API_KEY
        model = settings.OPENROUTER_MODEL

        if not api_key:
            await self.log("warn", "form", "no_api_key", {
                "message": "  No OpenRouter API key — falling back to basic matching",
            })
            return {}

        # Build field descriptions for the AI (strip element references)
        field_descriptions = []
        for f in fields:
            desc = {"index": f["index"], "label": f["label"], "type": f["type"], "tag": f["tag"], "name": f["name"]}
            if "options" in f:
                desc["options"] = [o["text"] for o in f["options"]]
            field_descriptions.append(desc)

        # Build profile context
        questions = profile.get("questions_json", {})
        profile_context = {
            "first_name": profile.get("first_name", ""),
            "last_name": profile.get("last_name", ""),
            "email": profile.get("email", ""),
            "phone": profile.get("phone", ""),
            "city": profile.get("city", ""),
            "zip_code": profile.get("zip_code", ""),
            "street_address": profile.get("street_address", ""),
            "salary_expectation": profile.get("salary_expectation", ""),
            "years_experience": profile.get("years_experience", ""),
            "linkedin_url": profile.get("linkedin_url", ""),
            "summary": profile.get("summary", ""),
        }

        prompt = f"""You are an expert job application form filler. Given the form fields from a job application page and the applicant's profile, determine what to fill in each field.

JOB: {job_title} at {company}

APPLICANT PROFILE:
{json.dumps(profile_context, indent=2, ensure_ascii=False)}

APPLICANT Q&A DATABASE (pre-prepared answers to common questions):
{json.dumps(questions, indent=2, ensure_ascii=False)}

FORM FIELDS DETECTED:
{json.dumps(field_descriptions, indent=2, ensure_ascii=False)}

INSTRUCTIONS:
- For each field, determine the best answer from the profile or Q&A database
- For select/dropdown fields, pick the EXACT option text that best matches
- For checkboxes, respond with "yes" or "no"
- If a field asks about availability/start date, say "sofort" (immediately) unless Q&A says otherwise
- If a field cannot be answered from the profile/Q&A, set its value to null
- For salary fields, use the number only (no currency symbol)
- Answer in the same language as the form (usually German)
- Be smart about matching — "Vorname" = first_name, "Nachname" = last_name, "Telefon" = phone, etc.
- For phone number fields: use DIGITS ONLY without spaces, dashes, or country code prefix (e.g. "15561057765" not "+49 155 610 577 65"). The country code is usually in a separate dropdown.
- Do NOT fill search/filter fields (job search, location search, etc.) — only fill application form fields.

Respond ONLY with a JSON object mapping field index (as string) to answer. Example:
{{"0": "Max", "1": "Mustermann", "2": "15512345678", "3": null}}"""

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,
                        "max_tokens": 2000,
                    },
                )
                resp.raise_for_status()
                result = resp.json()
                content = result["choices"][0]["message"]["content"]

                # Parse JSON from response (handle markdown code blocks)
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1]  # remove ```json
                    content = content.rsplit("```", 1)[0]  # remove trailing ```
                content = content.strip()

                answers = json.loads(content)
                await self.log("info", "form", "ai_response", {
                    "message": f"  AI mapped {len([v for v in answers.values() if v is not None])} fields",
                    "model": model,
                    "fields_mapped": len([v for v in answers.values() if v is not None]),
                })
                return answers

        except httpx.HTTPStatusError as e:
            await self.log("error", "form", "ai_api_error", {
                "message": f"  AI API error: {e.response.status_code} — {e.response.text[:200]}",
                "status_code": e.response.status_code,
            })
            return {}
        except json.JSONDecodeError as e:
            await self.log("error", "form", "ai_parse_error", {
                "message": f"  Could not parse AI response as JSON: {str(e)[:100]}",
                "raw_content": content[:500] if 'content' in dir() else "",
            })
            return {}
        except Exception as e:
            await self.log("error", "form", "ai_error", {
                "message": f"  AI form fill error: {str(e)[:100]}",
                "error": str(e),
            })
            return {}

    async def _match_and_fill_form(self, profile: dict, job_id: int = None, platform: str = None,
                                    job_title: str = "", company: str = "") -> dict:
        """AI-powered form filling. Extracts fields, asks AI for answers, fills them."""
        filled = 0
        skipped = 0
        unmatched = []
        field_details = []

        # Step 1: Extract all form fields
        fields = await self._extract_form_fields()
        self.stats["fields_total"] += len(fields)

        if not fields:
            await self.log("info", "form", "no_fields", {
                "message": "  No fillable form fields detected",
            }, job_id=job_id, platform=platform)
            return {"filled": 0, "skipped": 0, "unmatched": [], "details": []}

        await self.log("info", "form", "fields_detected", {
            "message": f"  Detected {len(fields)} form fields",
            "count": len(fields),
            "labels": [f["label"] for f in fields],
        }, job_id=job_id, platform=platform)

        # Step 2: Ask AI for answers
        ai_answers = await self._ask_ai_for_answers(fields, profile, job_title, company)

        # Step 3: Fill fields with AI answers (fall back to basic matching if AI fails)
        if not ai_answers:
            await self.log("warn", "form", "ai_fallback", {
                "message": "  AI unavailable — using basic profile matching",
            }, job_id=job_id, platform=platform)
            ai_answers = self._basic_field_match(fields, profile)

        for field in fields:
            idx_str = str(field["index"])
            answer = ai_answers.get(idx_str)
            inp = field["element"]
            label = field["label"]

            detail = {
                "label": label,
                "type": field["type"],
                "name": field["name"],
                "answer": str(answer)[:50] if answer else None,
                "matched_via": "ai" if ai_answers.get(idx_str) else None,
                "confidence": 95 if answer else 0,
            }
            field_details.append(detail)

            if answer is None:
                skipped += 1
                unmatched.append(label)
                await self.log("debug", "form", "field_skipped", {
                    "message": f"  Skipped: {label} (AI returned null)",
                    **detail,
                }, job_id=job_id, platform=platform)
                continue

            try:
                answer = str(answer)
                tag = field["tag"]
                input_type = field["type"]
                label_lower = label.lower()

                # Phone number cleanup — strip spaces, dashes, parens
                # If there's a separate country code field, remove +49 prefix
                if any(kw in label_lower for kw in ["phone", "telefon", "mobil", "handy", "rufnummer"]):
                    phone_clean = answer.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                    # Remove country code prefix if present (form likely has separate country code dropdown)
                    if phone_clean.startswith("+49"):
                        phone_clean = phone_clean[3:]
                    elif phone_clean.startswith("0049"):
                        phone_clean = phone_clean[4:]
                    elif phone_clean.startswith("0"):
                        phone_clean = phone_clean[1:]
                    answer = phone_clean

                if input_type == "checkbox":
                    if answer.lower() in ("yes", "ja", "true", "1"):
                        await inp.check()
                    else:
                        await inp.uncheck()
                elif tag == "SELECT":
                    # Match AI answer to closest option
                    options = field.get("options", [])
                    matched_val = None
                    # Try exact text match first
                    for opt in options:
                        if opt["text"].lower().strip() == answer.lower().strip():
                            matched_val = opt["value"]
                            break
                    # Try partial match
                    if not matched_val:
                        for opt in options:
                            if answer.lower() in opt["text"].lower() or opt["text"].lower() in answer.lower():
                                matched_val = opt["value"]
                                break
                    # Fuzzy fallback
                    if not matched_val and options:
                        best_score = 0
                        for opt in options:
                            score = fuzz.partial_ratio(answer.lower(), opt["text"].lower())
                            if score > best_score:
                                best_score = score
                                matched_val = opt["value"]
                        if best_score < 50:
                            matched_val = None

                    if matched_val:
                        await inp.select_option(value=matched_val)
                    else:
                        skipped += 1
                        unmatched.append(f"{label} (no matching option for '{answer}')")
                        continue
                else:
                    await inp.fill("")
                    await inp.type(answer, delay=random.randint(30, 80))

                filled += 1
                self.stats["fields_filled"] += 1
                await self.log("info", "form", "field_filled", {
                    "message": f"  Field: {label} → {answer[:30]}",
                    **detail,
                }, job_id=job_id, platform=platform)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            except Exception as e:
                await self.log("warn", "form", "field_error", {
                    "message": f"  Field error ({label}): {e}",
                    "error": str(e),
                }, job_id=job_id, platform=platform)

        # Upload CV to any file inputs
        cv_path = profile.get("cv_path")
        if cv_path and os.path.exists(cv_path):
            try:
                file_inputs = await self._page.query_selector_all('input[type="file"]')
                for fi in file_inputs:
                    try:
                        await fi.set_input_files(cv_path)
                        filled += 1
                        await self.log("info", "form", "cv_uploaded", {
                            "message": f"  Uploaded CV: {os.path.basename(cv_path)}",
                        }, job_id=job_id, platform=platform)
                    except Exception as e:
                        await self.log("warn", "form", "cv_upload_error", {
                            "message": f"  CV upload failed: {e}",
                        }, job_id=job_id, platform=platform)
            except:
                pass

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

    def _basic_field_match(self, fields: list[dict], profile: dict) -> dict:
        """Fallback: basic keyword matching when AI is unavailable."""
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
        questions = profile.get("questions_json", {})
        answers = {}

        for field in fields:
            label_lower = field["label"].lower()
            idx_str = str(field["index"])

            # Direct profile match
            for key, prof_field in field_map.items():
                if key in label_lower:
                    val = profile.get(prof_field)
                    if val is not None:
                        answers[idx_str] = str(val)
                        break

            # Q&A fuzzy match
            if idx_str not in answers:
                for q, a in questions.items():
                    score = fuzz.partial_ratio(label_lower, q.lower())
                    if score >= 70:
                        answers[idx_str] = a
                        break

        return answers

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

        # Load selected CV path
        cv_path = None
        if job_filter and hasattr(job_filter, 'selected_cv_id') and job_filter.selected_cv_id:
            cv_file = db.query(CVFile).filter(CVFile.id == job_filter.selected_cv_id).first()
            if cv_file and cv_file.file_path and os.path.exists(cv_file.file_path):
                cv_path = cv_file.file_path
                await self.log("info", "system", "cv_selected", {
                    "message": f"Using CV: {cv_file.label} ({os.path.basename(cv_file.file_path)})",
                })

        # Normalize phone — Xing requires +49 format, not "155 610 577 65"
        raw_phone = profile_row.phone or ""
        phone = raw_phone.strip()
        if phone and not phone.startswith("+"):
            # Remove spaces/dashes for formatting
            digits = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if digits.startswith("0"):
                phone = "+49" + digits[1:]  # 0155... → +49155...
            elif digits.startswith("49"):
                phone = "+" + digits
            else:
                phone = "+49" + digits  # bare number like 155... → +49155...

        profile = {
            "first_name": profile_row.first_name,
            "last_name": profile_row.last_name,
            "phone": phone,
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
            "cv_path": cv_path,
        }

        # Determine which platform to use
        platform = (job_filter.platform if job_filter and hasattr(job_filter, 'platform') and job_filter.platform else "stepstone").lower()
        await self.log("info", "system", "platform", {
            "message": f"Platform: {platform}",
            "platform": platform,
        })

        try:
            # Phase 1: Scrape jobs
            scraped_job_ids = []
            if mode in ("scrape_and_apply", "scrape"):
                if platform == "xing":
                    scraped_job_ids = await self._scrape_phase_xing(db, job_filter, profile)
                elif platform == "indeed":
                    scraped_job_ids = await self._scrape_phase_indeed(db, job_filter, profile)
                else:
                    scraped_job_ids = await self._scrape_phase(db, job_filter, profile)

            # Phase 2: Apply to jobs
            if mode in ("scrape_and_apply", "apply") and self.running:
                if platform == "xing":
                    await self._apply_phase_xing(db, profile, creds, job_filter, scraped_job_ids=scraped_job_ids)
                elif platform == "indeed":
                    await self._apply_phase_indeed(db, profile, creds, job_filter, scraped_job_ids=scraped_job_ids)
                else:
                    await self._apply_phase(db, profile, creds, job_filter, scraped_job_ids=scraped_job_ids)

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

    async def _scrape_phase(self, db: Session, job_filter: JobFilter, profile: dict) -> list[int]:
        """Scrape StepStone for new jobs — paginates dynamically based on max_applications. Returns list of all job IDs found."""
        await self.log("info", "scrape", "phase_start", {"message": "Starting job discovery..."})
        await self.emit_status("scraping")

        queries = job_filter.job_titles if job_filter and job_filter.job_titles else ["project-manager"]
        locations = job_filter.locations if job_filter and job_filter.locations else ["berlin"]
        # Scale pages based on requested applications (25 jobs/page, ~50% pass filter)
        requested_apps = int(job_filter.max_applications or 10) if job_filter and hasattr(job_filter, 'max_applications') else 10
        max_pages = max(5, min((requested_apps * 3) // 25 + 1, 40))  # 5-40 pages
        all_job_ids = []  # Track ALL job IDs found in this scrape (new + existing)

        pw = await async_playwright().start()
        total_new = 0

        for query in queries:
            for loc in locations:
                if not self.running:
                    break

                query_slug = query.lower().replace(" ", "-")

                await self.log("info", "scrape", "search_start", {
                    "message": f"Searching: {query} in {loc} (up to {max_pages} pages)",
                    "query": query, "location": loc,
                }, platform="stepstone")

                browser = await pw.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled', '--disable-http2'])
                ctx = await browser.new_context(
                    viewport={"width": 1366, "height": 768},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="de-DE",
                )
                self._page = await ctx.new_page()

                new_for_query = 0
                for page_num in range(1, max_pages + 1):
                    if not self.running:
                        break

                    url = f"https://www.stepstone.de/jobs/{query_slug}/in-{loc.lower()}"
                    if page_num > 1:
                        url += f"?page={page_num}"

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
                        if page_num == 1:
                            await self.screenshot("search_results")

                        cards = await self._page.query_selector_all("[data-testid='job-item']")
                        if not cards:
                            await self.log("info", "scrape", "no_more_pages", {
                                "message": f"  Page {page_num}: no jobs — end of results",
                            }, platform="stepstone")
                            break

                        await self.log("info", "scrape", "jobs_found", {
                            "message": f"  Page {page_num}: {len(cards)} jobs",
                            "count": len(cards), "page": page_num,
                        }, platform="stepstone")

                        new_in_page = 0
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

                                raw_url = href if href.startswith("http") else f"https://www.stepstone.de{href}"
                                full_url = _to_short_url(raw_url)

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
                                    new_job = Job(
                                        platform="stepstone", title=title, company=company,
                                        location=location, url=full_url,
                                        scraped_at=datetime.now(timezone.utc),
                                    )
                                    db.add(new_job)
                                    db.flush()  # Get the ID
                                    all_job_ids.append(new_job.id)
                                    new_in_page += 1
                                else:
                                    all_job_ids.append(existing.id)
                            except:
                                continue

                        db.commit()
                        new_for_query += new_in_page
                        total_new += new_in_page

                        await self.log("info", "scrape", "page_complete", {
                            "message": f"  Page {page_num}: {new_in_page} new jobs stored",
                            "new_jobs": new_in_page, "page": page_num,
                        }, platform="stepstone")

                        # Wait between pages
                        if page_num < max_pages:
                            await asyncio.sleep(random.uniform(5, 8))

                    except Exception as e:
                        await self.log("warn", "scrape", "page_failed", {
                            "message": f"  Page {page_num} failed: {str(e)[:80]}",
                            "error": str(e), "url": url, "page": page_num,
                        }, platform="stepstone")
                        break

                await self.log("info", "scrape", "query_complete", {
                    "message": f"  {query} in {loc}: {new_for_query} new jobs total",
                    "new_jobs": new_for_query,
                }, platform="stepstone")

                await browser.close()
                self._page = None
                await asyncio.sleep(random.uniform(5, 8))

        await self.log("info", "scrape", "phase_complete", {
            "message": f"Discovery complete: {total_new} new jobs found ({len(all_job_ids)} total in search results)",
            "total_new": total_new,
            "total_in_results": len(all_job_ids),
        })
        return all_job_ids

    async def _login_stepstone(self, page, cred) -> bool:
        """Log into StepStone. Goes to register page, switches to login, fills creds."""
        await self.log("info", "apply", "login_start", {
            "message": f"Logging into StepStone as {cred.email}...",
        }, platform="stepstone")

        try:
            # /login is blocked (403). Use register page which has a login toggle.
            await page.goto(
                "https://www.stepstone.de/de-DE/candidate/register?login_source=Homepage_top-register",
                timeout=20000,
            )
            await asyncio.sleep(random.uniform(3, 5))
            await self._dismiss_consent(page)

            # Take screenshot of register page
            await self.screenshot("login_01_register_page")

            # Switch to login mode — try multiple selectors
            login_toggle = None
            for sel in [
                'button:has-text("Jetzt einloggen")',
                'a:has-text("Jetzt einloggen")',
                'button:has-text("Log in")',
                'a:has-text("Log in")',
                'button:has-text("Sign in")',
                '[data-testid="login-toggle"]',
            ]:
                login_toggle = await page.query_selector(sel)
                if login_toggle and await login_toggle.is_visible():
                    break
                login_toggle = None

            if login_toggle:
                await login_toggle.click(force=True)
                await self.log("info", "apply", "login_toggle", {
                    "message": "  Switched to login mode",
                }, platform="stepstone")
                await asyncio.sleep(2)
                await self._dismiss_consent(page)
            else:
                await self.log("warn", "apply", "login_no_toggle", {
                    "message": "  No login toggle found — trying direct login URL",
                }, platform="stepstone")
                # Try alternative login endpoint
                await page.goto(
                    "https://www.stepstone.de/de-DE/candidate/login",
                    timeout=20000,
                )
                await asyncio.sleep(3)
                await self._dismiss_consent(page)

            await self.screenshot("login_02_login_form")

            # Fill email — try multiple selectors
            email_input = None
            for sel in [
                'input[type="email"]',
                'input[name="email"]',
                'input[autocomplete="email"]',
                'input[autocomplete="username"]',
                'input[id*="email"]',
                'input[id*="Email"]',
            ]:
                email_input = await page.query_selector(sel)
                if email_input and await email_input.is_visible():
                    break
                email_input = None

            if email_input:
                await email_input.click()
                await asyncio.sleep(0.3)
                await email_input.fill("")
                await email_input.type(cred.email, delay=random.randint(30, 80))
                await self.log("info", "apply", "login_email", {
                    "message": f"  Entered email: {cred.email}",
                }, platform="stepstone")
            else:
                await self.screenshot("login_err_no_email")
                await self.log("warn", "apply", "login_no_email_field", {
                    "message": "  Could not find email input",
                }, platform="stepstone")
                return False

            # Fill password — try multiple selectors
            pw_input = None
            for sel in [
                'input[type="password"]',
                'input[name="password"]',
                'input[autocomplete="current-password"]',
            ]:
                pw_input = await page.query_selector(sel)
                if pw_input and await pw_input.is_visible():
                    break
                pw_input = None

            if pw_input:
                await pw_input.click()
                await asyncio.sleep(0.3)
                await pw_input.type(cred.password_encrypted, delay=random.randint(30, 80))
                await self.log("info", "apply", "login_password", {
                    "message": "  Entered password",
                }, platform="stepstone")
            else:
                await self.screenshot("login_err_no_pw")
                await self.log("warn", "apply", "login_no_pw_field", {
                    "message": "  Password field not found",
                }, platform="stepstone")
                return False

            await asyncio.sleep(random.uniform(0.5, 1))
            await self._dismiss_consent(page)
            await self.screenshot("login_03_filled")

            # Click "Einloggen" / "Log in" / "Sign in" button
            login_btn = None
            for sel in [
                'button:has-text("Einloggen")',
                'button:has-text("Log in")',
                'button:has-text("Sign in")',
                'button[type="submit"]',
            ]:
                login_btn = await page.query_selector(sel)
                if login_btn and await login_btn.is_visible():
                    break
                login_btn = None

            if login_btn:
                await login_btn.click(force=True)
                await self.log("info", "apply", "login_submit", {
                    "message": "  Clicked login button...",
                }, platform="stepstone")
            else:
                await pw_input.press("Enter")
                await self.log("info", "apply", "login_submit", {
                    "message": "  Pressed Enter to submit...",
                }, platform="stepstone")

            # Wait for navigation — up to 15s
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except:
                pass
            await asyncio.sleep(random.uniform(3, 5))
            await self._dismiss_consent(page)
            await self.screenshot("login_04_after_submit")

            current_url = page.url
            await self.log("info", "apply", "login_check", {
                "message": f"  After login URL: {current_url[:100]}",
                "url": current_url,
            }, platform="stepstone")

            # If already on profile page, login succeeded — skip error check
            if "profile" in current_url and "login" not in current_url and "register" not in current_url:
                await self.log("info", "apply", "login_success", {
                    "message": f"  Login successful — redirected to profile",
                    "url": current_url,
                }, platform="stepstone")
                cookies = await page.context.cookies()
                ss_cookies = [c["name"] for c in cookies if "stepstone" in c.get("domain", "")]
                await self.log("debug", "apply", "login_cookies", {
                    "message": f"  Session cookies: {ss_cookies[:10]}",
                    "cookie_count": len(ss_cookies),
                }, platform="stepstone")
                return True

            # Only check for errors if still on login/register page
            if "login" in current_url or "register" in current_url:
                error_text = ""
                for err_sel in [
                    '[class*="error"]', '[class*="Error"]', '[role="alert"]',
                    '[data-testid*="error"]',
                ]:
                    error_el = await page.query_selector(err_sel)
                    if error_el:
                        try:
                            t = (await error_el.inner_text()).strip()
                            if t and len(t) > 5:
                                error_text = t
                                break
                        except:
                            pass

                if error_text:
                    await self.log("error", "apply", "login_error_message", {
                        "message": f"  Login error: {error_text[:200]}",
                        "error": error_text,
                    }, platform="stepstone")
                    await self.screenshot("login_err_message")
                    return False

            # Verify login by navigating to a protected page
            await page.goto("https://www.stepstone.de/profile", timeout=20000)
            await asyncio.sleep(random.uniform(3, 5))
            await self._dismiss_consent(page)
            await self.screenshot("login_05_profile_check")

            verify_url = page.url
            page_text = (await page.inner_text("body")).lower()

            await self.log("info", "apply", "login_verify", {
                "message": f"  Profile page URL: {verify_url[:100]}",
                "url": verify_url,
            }, platform="stepstone")

            # If we're on the profile page (not redirected to login/register) = success
            if "register" not in verify_url and "login" not in verify_url:
                # Double-check: look for logged-in indicators
                if any(kw in page_text for kw in [
                    "mein stepstone", "abmelden", "logout", "mein konto",
                    "my stepstone", "sign out", "profil", "profile",
                    "lebenslauf", "resume", "bewerbung",
                ]):
                    await self.log("info", "apply", "login_success", {
                        "message": f"  Login VERIFIED — profile page accessible",
                        "url": verify_url,
                    }, platform="stepstone")

                    # Check cookies for session tokens
                    cookies = await page.context.cookies()
                    ss_cookies = [c["name"] for c in cookies if "stepstone" in c.get("domain", "")]
                    await self.log("debug", "apply", "login_cookies", {
                        "message": f"  Session cookies: {ss_cookies[:10]}",
                        "cookie_count": len(ss_cookies),
                    }, platform="stepstone")
                    return True

                # URL is not login/register but no profile keywords — might still be OK
                await self.log("info", "apply", "login_probable_success", {
                    "message": f"  Probably logged in (not on login page), continuing...",
                    "url": verify_url,
                }, platform="stepstone")
                return True

            # Still on login/register page = login failed
            await self.log("warn", "apply", "login_failed", {
                "message": f"  Login FAILED — redirected back to login: {verify_url[:100]}",
                "url": verify_url,
            }, platform="stepstone")
            await self.screenshot("login_err_failed")
            return False

        except Exception as e:
            await self.log("error", "apply", "login_error", {
                "message": f"  Login error: {str(e)[:200]}",
                "error": str(e),
            }, platform="stepstone")
            await self.screenshot("login_err_exception")
            return False

    async def _apply_phase(self, db: Session, profile: dict, creds: list, job_filter: JobFilter, scraped_job_ids: list[int] = None):
        """Apply to unapplied jobs. If scraped_job_ids provided, only apply to those."""
        await self.log("info", "apply", "phase_start", {"message": "Starting application phase..."})
        await self.emit_status("applying")

        # Get already-applied URLs
        applied_urls = set(
            r[0] for r in db.query(Application.url).filter(Application.user_id == self.user_id).all() if r[0]
        )

        # Get jobs to apply to
        if scraped_job_ids:
            # Only apply to jobs from THIS search session
            query = db.query(Job).filter(Job.id.in_(scraped_job_ids))
        else:
            # Fallback: apply-only mode, get recent jobs
            query = db.query(Job).filter(Job.platform == "stepstone")

        if applied_urls:
            query = query.filter(~Job.url.in_(applied_urls))

        # Get search queries for title relevance filtering
        search_queries = job_filter.job_titles if job_filter and job_filter.job_titles else []
        max_apps = min(max(int(job_filter.max_applications or 10) if job_filter and hasattr(job_filter, 'max_applications') else 10, 1), 500)

        # Fetch more candidates than needed, then filter for relevance
        all_candidates = query.order_by(Job.scraped_at.desc()).limit(max_apps * 5).all()
        if search_queries:
            jobs = [j for j in all_candidates if _is_title_relevant(j.title, search_queries)][:max_apps]
            skipped_count = len(all_candidates) - len([j for j in all_candidates if _is_title_relevant(j.title, search_queries)])
            if skipped_count > 0:
                await self.log("info", "apply", "relevance_filter", {
                    "message": f"Filtered {skipped_count} irrelevant jobs, {len(jobs)} relevant remaining (max: {max_apps})",
                    "total_candidates": len(all_candidates),
                    "irrelevant_skipped": skipped_count,
                })
        else:
            jobs = all_candidates[:max_apps]

        self.stats["total"] = len(jobs)
        await self.log("info", "apply", "jobs_queued", {
            "message": f"Queued {len(jobs)} relevant jobs for application",
            "count": len(jobs),
        })
        await self.emit_progress()

        if not jobs:
            await self.log("info", "apply", "no_jobs", {"message": "No unapplied jobs found"})
            return

        # Launch ONE browser and log in first (reuse session for all jobs)
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled', '--disable-http2'])
        ctx = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="de-DE",
        )
        self._page = await ctx.new_page()
        await self._page.add_init_script(STEALTH_JS)

        # Log into StepStone if we have credentials
        ss_cred = next((c for c in creds if c.platform == "stepstone" and c.is_active), None)
        logged_in = False
        if ss_cred:
            logged_in = await self._login_stepstone(self._page, ss_cred)
            if not logged_in:
                await self.log("error", "apply", "login_required", {
                    "message": "LOGIN FAILED — Cannot apply without being logged in. Aborting apply phase.",
                }, platform="stepstone")
                await self.log("error", "apply", "login_hint", {
                    "message": "Check credentials in Profile page. Make sure email and password are correct for StepStone.",
                }, platform="stepstone")
                await browser.close()
                await pw.stop()
                return
        else:
            await self.log("error", "apply", "no_credentials", {
                "message": "No StepStone credentials found — cannot apply. Add credentials in Profile page.",
            }, platform="stepstone")
            await browser.close()
            await pw.stop()
            return

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

            try:
                t0 = time.time()

                # Navigate with retry on timeout/HTTP2 errors
                nav_ok = False
                for attempt in range(3):
                    try:
                        await self._page.goto(_to_short_url(job.url), timeout=45000, wait_until="domcontentloaded")
                        nav_ok = True
                        break
                    except Exception as nav_err:
                        err_str = str(nav_err)
                        if attempt < 2 and ("Timeout" in err_str or "ERR_HTTP2" in err_str or "ERR_CONNECTION" in err_str):
                            wait = random.uniform(10, 20) * (attempt + 1)
                            await self.log("warn", "browser", "nav_retry", {
                                "message": f"  Navigation failed ({err_str[:50]}), retrying in {wait:.0f}s ({attempt+2}/3)...",
                            }, job_id=job.id, platform=job.platform)
                            await asyncio.sleep(wait)
                            # Open fresh page in same context (keeps cookies)
                            old_page = self._page
                            self._page = await old_page.context.new_page()
                            await self._page.add_init_script(STEALTH_JS)
                            await old_page.close()
                        else:
                            raise
                if not nav_ok:
                    raise Exception("Failed to navigate after 3 attempts")

                await asyncio.sleep(random.uniform(2, 4))

                await self.log("debug", "browser", "page_load", {
                    "url": job.url,
                    "title": await self._page.title(),
                }, job_id=job.id, platform=job.platform)

                await self._dismiss_consent()
                await asyncio.sleep(2)
                await self._dismiss_consent()
                await self._dismiss_popups()  # Dismiss job alert popup
                await asyncio.sleep(1)

                # Find apply button — try full apply first, then Schnellbewerbung
                apply_btn = None
                btn_text = ""
                apply_type = "full"  # "full" or "interest"
                for sel in [
                    'a:has-text("Jetzt bewerben")',
                    'button:has-text("Jetzt bewerben")',
                    'a:has-text("Apply now")',
                    'button:has-text("Apply now")',
                    'a:has-text("Schnelle Bewerbung")',
                    'button:has-text("Schnelle Bewerbung")',
                    'a:has-text("Quick apply")',
                    'button:has-text("Quick apply")',
                    'button:has-text("Bewerbung fortsetzen")',
                    'a:has-text("Bewerbung fortsetzen")',
                    'button:has-text("Continue application")',
                    'a:has-text("Continue application")',
                ]:
                    apply_btn = await self._page.query_selector(sel)
                    if apply_btn and await apply_btn.is_visible():
                        btn_text = (await apply_btn.inner_text()).strip()
                        await self.log("info", "apply", "button_found", {
                            "message": f"  Apply button: \"{btn_text}\"",
                            "selector": sel, "button_text": btn_text,
                        }, job_id=job.id, platform=job.platform)
                        break
                    apply_btn = None

                # Fall back to "Ich bin interessiert" / "I'm interested" (Schnellbewerbung)
                if not apply_btn:
                    for sel in [
                        'button:has-text("Ich bin interessiert")',
                        'a:has-text("Ich bin interessiert")',
                        "button:has-text(\"I'm interested\")",
                        "a:has-text(\"I'm interested\")",
                    ]:
                        apply_btn = await self._page.query_selector(sel)
                        if apply_btn and await apply_btn.is_visible():
                            btn_text = (await apply_btn.inner_text()).strip()
                            apply_type = "interest"
                            await self.log("info", "apply", "interest_button", {
                                "message": f"  Schnellbewerbung: \"{btn_text}\"",
                            }, job_id=job.id, platform=job.platform)
                            break
                        apply_btn = None

                if not apply_btn:
                    # Debug: log what buttons actually exist on page
                    all_btns = await self._page.query_selector_all("button:visible")
                    btn_texts = []
                    for b in all_btns[:15]:
                        try:
                            t = (await b.inner_text()).strip()
                            if t and len(t) < 60:
                                btn_texts.append(t)
                        except: pass
                    await self.log("warn", "apply", "no_button", {
                        "message": f"  No apply button found — skipping. Buttons on page: {btn_texts[:8]}",
                        "buttons_found": btn_texts,
                    }, job_id=job.id, platform=job.platform)
                    application.status = "skipped"
                    application.error_log = "No apply button found on page"
                    db.commit()
                    self.stats["skipped"] += 1
                    await self.emit_progress()
                    continue

                # Click apply / interest button
                await self.log("info", "apply", "clicking_apply", {
                    "message": f"  Clicking \"{btn_text}\"...",
                }, job_id=job.id, platform=job.platform)
                # Aggressively remove ALL overlays before clicking
                await self._dismiss_popups()
                await self._page.evaluate("""() => {
                    // Remove all portal overlays, fixed-position blockers, backdrops
                    document.querySelectorAll('[id*="portal"]').forEach(e => e.remove());
                    document.querySelectorAll('[data-genesis-element="DRAWER_OVERLAY"]').forEach(e => e.remove());
                    document.querySelectorAll('[class*="backdrop"], [class*="Backdrop"]').forEach(e => e.remove());
                    // Remove any fixed-position elements that block clicks
                    document.querySelectorAll('div').forEach(e => {
                        const s = window.getComputedStyle(e);
                        if (s.position === 'fixed' && s.zIndex > 100 && e.id !== 'onetrust-consent-sdk') {
                            e.remove();
                        }
                    });
                    document.body.style.overflow = 'auto';
                    document.body.style.pointerEvents = 'auto';
                }""")
                await asyncio.sleep(0.5)

                # Re-find button after overlay removal (DOM changes can detach handles)
                apply_btn = None
                all_selectors = [
                    'a:has-text("Jetzt bewerben")', 'button:has-text("Jetzt bewerben")',
                    'a:has-text("Apply now")', 'button:has-text("Apply now")',
                    'button:has-text("Bewerbung fortsetzen")', 'a:has-text("Bewerbung fortsetzen")',
                    'button:has-text("Ich bin interessiert")', 'a:has-text("Ich bin interessiert")',
                    "button:has-text(\"I'm interested\")", "a:has-text(\"I'm interested\")",
                ]
                for sel in all_selectors:
                    apply_btn = await self._page.query_selector(sel)
                    if apply_btn and await apply_btn.is_visible():
                        break
                    apply_btn = None

                if not apply_btn:
                    await self.log("warn", "apply", "button_lost", {
                        "message": "  Button disappeared after overlay removal — skipping",
                    }, job_id=job.id, platform=job.platform)
                    application.status = "failed"
                    application.error_log = "Button lost after overlay removal"
                    db.commit()
                    self.stats["failed"] += 1
                    await self.emit_progress()
                    continue

                # Scroll button into view
                await apply_btn.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)

                # Use JavaScript .click() — normal Playwright clicks fail due to body overflow
                old_url = self._page.url
                await apply_btn.evaluate("el => el.click()")
                # Wait for navigation (can take a few seconds for React to process)
                for _wait in range(8):
                    await asyncio.sleep(1)
                    if self._page.url != old_url:
                        break

                await self._dismiss_consent()
                await self._dismiss_popups()

                current_url = self._page.url
                await self.screenshot("after_apply_click")

                # Check if we landed on success/confirmation page (Flow B: direct success)
                if "confirmation/success" in current_url or "success" in current_url:
                    application.status = "success"
                    self.stats["applied"] += 1
                    apply_duration = time.time() - t0
                    await self.log("info", "apply", "success", {
                        "message": f"  SUCCESS — Application auto-submitted in {apply_duration:.0f}s",
                        "duration_s": apply_duration,
                    }, job_id=job.id, platform=job.platform)
                    db.commit()
                    await self.emit_progress()

                    if i < len(jobs) - 1 and self.running:
                        delay = random.uniform(15, 25)
                        await self.log("info", "system", "delay", {
                            "message": f"  Waiting {delay:.0f}s before next...",
                            "delay_s": delay,
                        })
                        await asyncio.sleep(delay)
                    continue

                # Smart Apply flow (Flow A): form with "Bewerbung abschicken"
                if "smart-apply" in current_url or "application" in current_url:
                    await self.log("info", "apply", "smart_apply_form", {
                        "message": "  Smart Apply form loaded — submitting application...",
                        "url": current_url[:100],
                    }, job_id=job.id, platform=job.platform)

                    await asyncio.sleep(random.uniform(2, 4))
                    await self._dismiss_consent()
                    await self._dismiss_popups()

                    # Upload our selected CV to any file inputs on the Smart Apply form
                    cv_path = profile.get("cv_path")
                    if cv_path and os.path.exists(cv_path):
                        try:
                            file_inputs = await self._page.query_selector_all('input[type="file"]')
                            for fi in file_inputs:
                                try:
                                    await fi.set_input_files(cv_path)
                                    await self.log("info", "form", "cv_uploaded", {
                                        "message": f"  Uploaded CV: {os.path.basename(cv_path)}",
                                    }, job_id=job.id, platform=job.platform)
                                    await asyncio.sleep(1)
                                except Exception as e:
                                    await self.log("warn", "form", "cv_upload_error", {
                                        "message": f"  CV upload failed: {e}",
                                    }, job_id=job.id, platform=job.platform)
                        except:
                            pass

                        # Also try clicking any "Upload CV" / "Lebenslauf hochladen" button
                        for upload_sel in [
                            'button:has-text("Upload")', 'button:has-text("Hochladen")',
                            'button:has-text("Lebenslauf")', 'button:has-text("CV")',
                            'label:has-text("Upload")', 'label:has-text("Hochladen")',
                            '[data-testid*="upload"]', '[data-testid*="cv"]',
                        ]:
                            try:
                                upload_btn = await self._page.query_selector(upload_sel)
                                if upload_btn and await upload_btn.is_visible():
                                    # Check if this button has an associated file input
                                    for_id = await upload_btn.get_attribute("for")
                                    if for_id:
                                        fi = await self._page.query_selector(f'input#{for_id}')
                                        if fi:
                                            await fi.set_input_files(cv_path)
                                            await self.log("info", "form", "cv_uploaded_via_label", {
                                                "message": f"  Uploaded CV via label: {os.path.basename(cv_path)}",
                                            }, job_id=job.id, platform=job.platform)
                                            await asyncio.sleep(1)
                                            break
                            except:
                                continue

                    # Find and click "Bewerbung abschicken" / "Submit application"
                    submit_btn = None
                    for sel in [
                        'button:has-text("Bewerbung abschicken")',
                        'button:has-text("Submit application")',
                        'button:has-text("Send application")',
                        'button:has-text("Jetzt bewerben")',
                        'button:has-text("Apply now")',
                        'button:has-text("Absenden")',
                        'button:has-text("Submit")',
                        'button:has-text("Senden")',
                        'button:has-text("Send")',
                        'button[type="submit"]',
                    ]:
                        submit_btn = await self._page.query_selector(sel)
                        if submit_btn and await submit_btn.is_visible():
                            break
                        submit_btn = None

                    if submit_btn:
                        submit_text = (await submit_btn.inner_text()).strip()
                        await self.log("info", "apply", "submitting", {
                            "message": f"  Clicking \"{submit_text}\"...",
                        }, job_id=job.id, platform=job.platform)
                        await submit_btn.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        pre_submit_url = self._page.url
                        # Primary: el.click() (more reliable on StepStone React)
                        await submit_btn.evaluate("el => el.click()")
                        # Wait for navigation or page change
                        for _wait in range(8):
                            await asyncio.sleep(1)
                            if self._page.url != pre_submit_url:
                                break
                        await asyncio.sleep(random.uniform(1, 2))
                        await self.screenshot("after_submit")

                        # Check for success
                        after_url = self._page.url
                        page_text = (await self._page.inner_text("body")).lower()
                        success = any(kw in page_text for kw in [
                            "bewerbung abgeschickt", "application sent", "erfolgreich",
                            "vielen dank", "thank you", "gesendet", "submitted",
                            "bewerbung wurde", "application has been",
                        ])
                        if success or "success" in after_url or "confirmation" in after_url:
                            application.status = "success"
                            self.stats["applied"] += 1
                            apply_duration = time.time() - t0
                            await self.log("info", "apply", "success", {
                                "message": f"  SUCCESS — Application submitted in {apply_duration:.0f}s",
                                "duration_s": apply_duration,
                            }, job_id=job.id, platform=job.platform)
                        else:
                            # Might still have succeeded — check if button disappeared
                            still_has_submit = (
                                await self._page.query_selector('button:has-text("Bewerbung abschicken")') or
                                await self._page.query_selector('button:has-text("Submit application")') or
                                await self._page.query_selector('button:has-text("Send application")')
                            )
                            if not still_has_submit:
                                application.status = "success"
                                self.stats["applied"] += 1
                                apply_duration = time.time() - t0
                                await self.log("info", "apply", "probable_success", {
                                    "message": f"  Probably submitted — submit button gone ({apply_duration:.0f}s)",
                                    "duration_s": apply_duration,
                                }, job_id=job.id, platform=job.platform)
                            else:
                                application.status = "failed"
                                application.error_log = "Submit button still present — may not have submitted"
                                self.stats["failed"] += 1
                                await self.log("warn", "apply", "submit_uncertain", {
                                    "message": "  Submit button still visible — application may not have gone through",
                                }, job_id=job.id, platform=job.platform)
                    else:
                        # No submit button found — might need to fill form first
                        await self.log("warn", "apply", "no_submit_button", {
                            "message": "  Smart Apply form loaded but no submit button found",
                            "url": current_url[:100],
                        }, job_id=job.id, platform=job.platform)
                        application.status = "failed"
                        application.error_log = "No submit button on smart-apply form"
                        self.stats["failed"] += 1

                    db.commit()
                    await self.emit_progress()

                    if i < len(jobs) - 1 and self.running:
                        delay = random.uniform(15, 25)
                        await self.log("info", "system", "delay", {
                            "message": f"  Waiting {delay:.0f}s before next application...",
                            "delay_s": delay,
                        })
                        await asyncio.sleep(delay)
                    continue

                # Check if a login/register modal appeared (not logged in)
                if apply_type == "interest":
                    page_text = (await self._page.inner_text("body")).lower()
                    if any(kw in page_text for kw in ["anmelden oder registrieren", "log in or register"]):
                        await self.log("error", "apply", "not_logged_in", {
                            "message": "  NOT LOGGED IN — login modal appeared",
                        }, job_id=job.id, platform=job.platform)
                        application.status = "failed"
                        application.error_log = "Not logged in"
                        db.commit()
                        self.stats["failed"] += 1
                        await self.emit_progress()
                        continue

                    # If we're still on the same job page, retry once with page reload
                    if current_url == old_url:
                        await self.log("warn", "apply", "click_no_effect", {
                            "message": "  Click had no effect — retrying after page reload...",
                        }, job_id=job.id, platform=job.platform)

                        # Reload page and try again
                        await self._page.reload(timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(3, 5))
                        await self._dismiss_consent()
                        await self._dismiss_popups()
                        await self._page.evaluate("""() => {
                            document.querySelectorAll('[id*="portal"]').forEach(e => e.remove());
                            document.querySelectorAll('[data-genesis-element="DRAWER_OVERLAY"]').forEach(e => e.remove());
                            document.querySelectorAll('[class*="backdrop"], [class*="Backdrop"]').forEach(e => e.remove());
                            document.querySelectorAll('div').forEach(e => {
                                const s = window.getComputedStyle(e);
                                if (s.position === 'fixed' && s.zIndex > 100 && e.id !== 'onetrust-consent-sdk') e.remove();
                            });
                            document.body.style.overflow = 'auto';
                            document.body.style.pointerEvents = 'auto';
                        }""")
                        await asyncio.sleep(1)

                        # Re-find and re-click
                        retry_btn = None
                        for sel in ['button:has-text("Ich bin interessiert")', "button:has-text(\"I'm interested\")",
                                    'button:has-text("Bewerbung fortsetzen")', 'button:has-text("Continue application")']:
                            retry_btn = await self._page.query_selector(sel)
                            if retry_btn and await retry_btn.is_visible():
                                break
                            retry_btn = None

                        if retry_btn:
                            await retry_btn.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            old_url2 = self._page.url
                            await retry_btn.evaluate("el => el.click()")
                            for _wait in range(8):
                                await asyncio.sleep(1)
                                if self._page.url != old_url2:
                                    break
                            current_url = self._page.url

                            if current_url != old_url2:
                                # Retry worked! Check for success flows
                                if "confirmation/success" in current_url or "success" in current_url:
                                    application.status = "success"
                                    self.stats["applied"] += 1
                                    await self.log("info", "apply", "success", {
                                        "message": f"  SUCCESS (retry) — Application auto-submitted",
                                    }, job_id=job.id, platform=job.platform)
                                    db.commit()
                                    await self.emit_progress()
                                    if i < len(jobs) - 1 and self.running:
                                        await asyncio.sleep(random.uniform(15, 25))
                                    continue
                                elif "smart-apply" in current_url or "application" in current_url:
                                    await self.log("info", "apply", "smart_apply_retry", {
                                        "message": "  Retry navigated to smart-apply form",
                                    }, job_id=job.id, platform=job.platform)
                                    # Fall through to smart-apply handling below won't work here,
                                    # so handle inline
                                    await asyncio.sleep(random.uniform(2, 4))
                                    await self._dismiss_consent()
                                    submit_btn = None
                                    for sel in ['button:has-text("Bewerbung abschicken")', 'button:has-text("Submit application")',
                                                'button:has-text("Send application")', 'button[type="submit"]']:
                                        submit_btn = await self._page.query_selector(sel)
                                        if submit_btn and await submit_btn.is_visible():
                                            break
                                        submit_btn = None
                                    if submit_btn:
                                        try:
                                            await submit_btn.click(timeout=5000)
                                        except Exception:
                                            await submit_btn.evaluate("el => el.click()")
                                        await asyncio.sleep(random.uniform(4, 6))
                                        after_url = self._page.url
                                        if "success" in after_url or "confirmation" in after_url:
                                            application.status = "success"
                                            self.stats["applied"] += 1
                                            await self.log("info", "apply", "success", {
                                                "message": f"  SUCCESS (retry+submit)",
                                            }, job_id=job.id, platform=job.platform)
                                        else:
                                            application.status = "failed"
                                            application.error_log = "Retry: submit uncertain"
                                            self.stats["failed"] += 1
                                    else:
                                        application.status = "failed"
                                        application.error_log = "Retry: no submit button"
                                        self.stats["failed"] += 1
                                    db.commit()
                                    await self.emit_progress()
                                    if i < len(jobs) - 1 and self.running:
                                        await asyncio.sleep(random.uniform(15, 25))
                                    continue

                        # Retry also failed
                        application.status = "failed"
                        application.error_log = "Interest click had no effect (even after retry)"
                        db.commit()
                        self.stats["failed"] += 1
                        await self.emit_progress()
                        continue

                # Full application — check if redirected to login
                page_text = await self._page.inner_text("body")
                if ("anmelden" in page_text.lower() or "einloggen" in page_text.lower()) and "login" in self._page.url.lower():
                    if not logged_in:
                        await self.log("warn", "apply", "login_required", {
                            "message": "  Login required — no credentials configured",
                        }, job_id=job.id, platform=job.platform)
                    else:
                        await self.log("warn", "apply", "login_expired", {
                            "message": "  Session expired — re-logging in...",
                        }, job_id=job.id, platform=job.platform)
                        logged_in = await self._login_stepstone(self._page, ss_cred)
                        if logged_in:
                            await self._page.goto(_to_short_url(job.url), timeout=20000)
                            await asyncio.sleep(2)
                            continue

                    application.status = "skipped"
                    application.error_log = "Login required"
                    db.commit()
                    self.stats["skipped"] += 1
                    await self.emit_progress()
                    continue

                # Detect and fill form (full application only)
                await self.log("info", "form", "detecting", {
                    "message": "  Scanning form fields...",
                }, job_id=job.id, platform=job.platform)

                form_result = await self._match_and_fill_form(
                    profile, job_id=job.id, platform=job.platform,
                    job_title=job.title, company=job.company,
                )

                if form_result["filled"] > 0:
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

            # Delay between applications (longer to avoid rate limiting)
            if i < len(jobs) - 1 and self.running:
                delay = random.uniform(20, 35)
                await self.log("info", "system", "delay", {
                    "message": f"  Waiting {delay:.0f}s before next application...",
                    "delay_s": delay,
                })
                await asyncio.sleep(delay)

        await browser.close()
        self._page = None

    # ── Xing Platform Methods ─────────────────────────────────────────────

    async def _dismiss_xing_cookies(self, page=None):
        """Handle Xing cookie/consent banner."""
        p = page or self._page
        if not p:
            return
        for sel in [
            '#consent-accept-button',
            'button[data-testid="uc-accept-all-button"]',
            'button:has-text("Accept all")',
            'button:has-text("Alle akzeptieren")',
        ]:
            try:
                btn = await p.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click(force=True, timeout=3000)
                    await asyncio.sleep(1)
                    break
            except:
                continue

    async def _login_xing(self, page, cred) -> bool:
        """Log into Xing."""
        await self.log("info", "apply", "login_start", {
            "message": f"Logging into Xing as {cred.email}...",
        }, platform="xing")

        try:
            await page.goto("https://login.xing.com/", timeout=20000)
            await asyncio.sleep(random.uniform(3, 5))
            await self._dismiss_xing_cookies(page)
            await self.screenshot("xing_login_01")

            # Fill email
            email_input = None
            for sel in ['input#username', 'input[name="username"]', 'input[type="email"]']:
                email_input = await page.query_selector(sel)
                if email_input and await email_input.is_visible():
                    break
                email_input = None

            if email_input:
                await email_input.click()
                await asyncio.sleep(0.3)
                await email_input.fill("")
                await email_input.type(cred.email, delay=random.randint(30, 80))
                await self.log("info", "apply", "login_email", {
                    "message": f"  Entered email: {cred.email}",
                }, platform="xing")
            else:
                await self.log("warn", "apply", "login_no_email", {
                    "message": "  No email input found on Xing login",
                }, platform="xing")
                await self.screenshot("xing_login_err_no_email")
                return False

            # Fill password
            pw_input = None
            for sel in ['input#password', 'input[name="password"]', 'input[type="password"]']:
                pw_input = await page.query_selector(sel)
                if pw_input and await pw_input.is_visible():
                    break
                pw_input = None

            if pw_input:
                await pw_input.click()
                await asyncio.sleep(0.3)
                await pw_input.type(cred.password_encrypted, delay=random.randint(30, 80))
                await self.log("info", "apply", "login_password", {
                    "message": "  Entered password",
                }, platform="xing")
            else:
                await self.log("warn", "apply", "login_no_pw", {
                    "message": "  No password input found on Xing login",
                }, platform="xing")
                return False

            await asyncio.sleep(0.5)
            await self.screenshot("xing_login_02_filled")

            # Click login button
            login_btn = None
            for sel in ['button[type="submit"]', 'button:has-text("Log in")', 'button:has-text("Einloggen")']:
                login_btn = await page.query_selector(sel)
                if login_btn and await login_btn.is_visible():
                    break
                login_btn = None

            if login_btn:
                await login_btn.click(force=True)
            else:
                await pw_input.press("Enter")

            await self.log("info", "apply", "login_submit", {
                "message": "  Clicked login button...",
            }, platform="xing")

            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except:
                pass
            await asyncio.sleep(random.uniform(3, 5))
            await self._dismiss_xing_cookies(page)
            await self.screenshot("xing_login_03_after")

            current_url = page.url
            await self.log("info", "apply", "login_check", {
                "message": f"  After login URL: {current_url[:100]}",
            }, platform="xing")

            # Check if logged in — should NOT be on login page anymore
            if "login" not in current_url:
                # Check for avatar or feed indicators
                avatar = await page.query_selector('[data-testid="header-avatar"], [class*="avatar"], [class*="profile-image"]')
                if avatar or "/feed" in current_url or "/jobs" in current_url or "/discover" in current_url:
                    await self.log("info", "apply", "login_success", {
                        "message": "  Xing login successful!",
                    }, platform="xing")
                    return True
                # Not on login page = probably logged in
                await self.log("info", "apply", "login_probable_success", {
                    "message": f"  Probably logged in (not on login page), continuing...",
                }, platform="xing")
                return True

            # Check for error messages
            for err_sel in ['[data-testid="input-error-message"]', '.error-message', '[role="alert"]']:
                err_el = await page.query_selector(err_sel)
                if err_el:
                    try:
                        t = (await err_el.inner_text()).strip()
                        if t:
                            await self.log("error", "apply", "login_error", {
                                "message": f"  Xing login error: {t[:200]}",
                            }, platform="xing")
                            break
                    except:
                        pass

            await self.log("warn", "apply", "login_failed", {
                "message": f"  Xing login failed — still on login page",
            }, platform="xing")
            return False

        except Exception as e:
            await self.log("error", "apply", "login_error", {
                "message": f"  Xing login error: {str(e)[:200]}",
            }, platform="xing")
            return False

    async def _scrape_phase_xing(self, db: Session, job_filter: JobFilter, profile: dict) -> list[int]:
        """Scrape Xing for jobs. Returns list of all job IDs found."""
        await self.log("info", "scrape", "phase_start", {"message": "Starting Xing job discovery..."})
        await self.emit_status("scraping")

        queries = job_filter.job_titles if job_filter and job_filter.job_titles else ["Servicekraft"]
        locations = job_filter.locations if job_filter and job_filter.locations else ["Berlin"]
        requested_apps = int(job_filter.max_applications or 10) if job_filter and hasattr(job_filter, 'max_applications') else 10
        max_pages = max(5, min((requested_apps * 3) // 25 + 1, 40))  # 5-40 pages
        all_job_ids = []

        pw = await async_playwright().start()
        total_new = 0

        for query in queries:
            for loc in locations:
                if not self.running:
                    break

                import urllib.parse
                q_enc = urllib.parse.quote(query)
                l_enc = urllib.parse.quote(loc)

                await self.log("info", "scrape", "search_start", {
                    "message": f"Searching Xing: {query} in {loc}",
                    "query": query, "location": loc,
                }, platform="xing")

                browser = await pw.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled', '--disable-http2'])
                ctx = await browser.new_context(
                    viewport={"width": 1366, "height": 768},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="de-DE",
                )
                self._page = await ctx.new_page()
                await self._page.add_init_script(STEALTH_JS)

                new_for_query = 0
                for page_num in range(1, max_pages + 1):
                    if not self.running:
                        break

                    url = f"https://www.xing.com/jobs/search?keywords={q_enc}&location={l_enc}"
                    if page_num > 1:
                        url += f"&page={page_num}"

                    try:
                        t0 = time.time()
                        await self._page.goto(url, timeout=20000)
                        load_time = time.time() - t0
                        await asyncio.sleep(random.uniform(3, 5))

                        await self._dismiss_xing_cookies()
                        if page_num == 1:
                            await self.screenshot("xing_search_results")

                        # Try multiple selectors for job cards
                        cards = await self._page.query_selector_all("article[data-testid='job-card'], article[data-testid='job-search-result']")
                        if not cards:
                            cards = await self._page.query_selector_all("a[data-testid='job-item-link']")
                        if not cards:
                            # Broader fallback
                            cards = await self._page.query_selector_all("[data-testid*='job']")

                        if not cards:
                            await self.log("info", "scrape", "no_more_pages", {
                                "message": f"  Xing page {page_num}: no jobs — end of results",
                            }, platform="xing")
                            break

                        await self.log("info", "scrape", "jobs_found", {
                            "message": f"  Xing page {page_num}: {len(cards)} jobs",
                            "count": len(cards), "page": page_num,
                        }, platform="xing")

                        new_in_page = 0
                        for card in cards:
                            try:
                                # Extract title + URL
                                title = ""
                                href = ""
                                company = ""
                                location = ""

                                # Try link inside card
                                link_el = await card.query_selector("a[href*='/jobs/']")
                                if not link_el:
                                    link_el = await card.query_selector("a")
                                if link_el:
                                    href = await link_el.get_attribute("href") or ""
                                    title = (await link_el.inner_text()).strip()

                                # If card itself is the link
                                if not href:
                                    tag = await card.evaluate("el => el.tagName.toLowerCase()")
                                    if tag == "a":
                                        href = await card.get_attribute("href") or ""
                                        title = (await card.inner_text()).strip()

                                # Title from h2/h3
                                if not title or len(title) > 200:
                                    title_el = await card.query_selector("h2, h3")
                                    if title_el:
                                        title = (await title_el.inner_text()).strip()

                                # Company
                                for comp_sel in ["[data-testid='job-card-company-name']", "p[class*='Company']", "[class*='company']"]:
                                    comp_el = await card.query_selector(comp_sel)
                                    if comp_el:
                                        company = (await comp_el.inner_text()).strip()
                                        break

                                if not title or not href:
                                    continue

                                full_url = href if href.startswith("http") else f"https://www.xing.com{href}"

                                # Blacklist check
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
                                    new_job = Job(
                                        platform="xing", title=title[:200], company=company[:200],
                                        location=location[:200], url=full_url,
                                        scraped_at=datetime.now(timezone.utc),
                                    )
                                    db.add(new_job)
                                    db.flush()
                                    all_job_ids.append(new_job.id)
                                    new_in_page += 1
                                else:
                                    all_job_ids.append(existing.id)
                            except:
                                continue

                        db.commit()
                        new_for_query += new_in_page
                        total_new += new_in_page

                        await self.log("info", "scrape", "page_complete", {
                            "message": f"  Xing page {page_num}: {new_in_page} new jobs stored",
                            "new_jobs": new_in_page,
                        }, platform="xing")

                        if page_num < max_pages:
                            # Try clicking next page button
                            next_btn = await self._page.query_selector("button[data-testid='pagination-next-button']")
                            if next_btn and await next_btn.is_visible():
                                await next_btn.click()
                                await asyncio.sleep(random.uniform(3, 5))
                            else:
                                break

                    except Exception as e:
                        await self.log("warn", "scrape", "page_failed", {
                            "message": f"  Xing page {page_num} failed: {str(e)[:80]}",
                        }, platform="xing")
                        break

                await self.log("info", "scrape", "query_complete", {
                    "message": f"  Xing {query} in {loc}: {new_for_query} new jobs",
                }, platform="xing")

                await browser.close()
                self._page = None
                await asyncio.sleep(random.uniform(5, 8))

        await self.log("info", "scrape", "phase_complete", {
            "message": f"Xing discovery complete: {total_new} new jobs ({len(all_job_ids)} total)",
            "total_new": total_new, "total_in_results": len(all_job_ids),
        })
        return all_job_ids

    async def _apply_phase_xing(self, db: Session, profile: dict, creds: list, job_filter: JobFilter, scraped_job_ids: list[int] = None):
        """Apply to Xing jobs."""
        await self.log("info", "apply", "phase_start", {"message": "Starting Xing application phase..."})
        await self.emit_status("applying")

        applied_urls = set(
            r[0] for r in db.query(Application.url).filter(Application.user_id == self.user_id).all() if r[0]
        )

        if scraped_job_ids:
            query = db.query(Job).filter(Job.id.in_(scraped_job_ids))
        else:
            query = db.query(Job).filter(Job.platform == "xing")

        if applied_urls:
            query = query.filter(~Job.url.in_(applied_urls))

        # Title relevance filtering
        search_queries = job_filter.job_titles if job_filter and job_filter.job_titles else []
        max_apps = min(max(int(job_filter.max_applications or 10) if job_filter and hasattr(job_filter, 'max_applications') else 10, 1), 500)
        all_candidates = query.order_by(Job.scraped_at.desc()).limit(max_apps * 5).all()
        if search_queries:
            jobs = [j for j in all_candidates if _is_title_relevant(j.title, search_queries)][:max_apps]
        else:
            jobs = all_candidates[:max_apps]

        self.stats["total"] = len(jobs)
        await self.log("info", "apply", "jobs_queued", {
            "message": f"Queued {len(jobs)} Xing jobs for application (max: {max_apps})",
            "count": len(jobs),
        })
        await self.emit_progress()

        if not jobs:
            await self.log("info", "apply", "no_jobs", {"message": "No unapplied Xing jobs found"})
            return

        # Launch browser + login
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled', '--disable-http2'])
        ctx = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="de-DE",
        )
        self._page = await ctx.new_page()
        await self._page.add_init_script(STEALTH_JS)

        xing_cred = next((c for c in creds if c.platform == "xing" and c.is_active), None)
        if not xing_cred:
            await self.log("error", "apply", "no_credentials", {
                "message": "No Xing credentials found — add them in Profile page.",
            }, platform="xing")
            await browser.close()
            await pw.stop()
            return

        logged_in = await self._login_xing(self._page, xing_cred)
        if not logged_in:
            await self.log("error", "apply", "login_required", {
                "message": "XING LOGIN FAILED — Aborting apply phase.",
            }, platform="xing")
            await browser.close()
            await pw.stop()
            return

        for i, job in enumerate(jobs):
            if not self.running:
                break

            await self.log("info", "apply", "job_start", {
                "message": f"[{i+1}/{len(jobs)}] Opening: {job.title} at {job.company}",
                "job_title": job.title, "company": job.company, "url": job.url,
            }, job_id=job.id, platform="xing")

            application = Application(
                user_id=self.user_id, job_id=job.id, platform="xing",
                job_title=job.title, company=job.company, url=job.url,
                status="applying", applied_at=datetime.now(timezone.utc),
            )
            db.add(application)
            db.commit()

            try:
                t0 = time.time()
                await self._page.goto(job.url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(2, 4))
                await self._dismiss_xing_cookies()
                await self.screenshot("xing_job_page")

                # Find apply button — prioritize "Easy apply" (Xing's native apply)
                # First check if this is an external-only job (no Easy Apply available)
                external_only = False
                try:
                    all_link_texts = await self._page.evaluate("""() => {
                        return Array.from(document.querySelectorAll('a, button')).map(e => ({
                            text: (e.innerText || '').trim().toLowerCase(),
                            href: (e.href || '').toLowerCase()
                        }));
                    }""")
                    has_external = any(
                        "arbeitgeberseite" in l["text"] or "employer website" in l["text"] or "visit employer" in l["text"]
                        for l in all_link_texts
                    )
                    has_easy_apply = any(
                        "easy apply" in l["text"] or "schnellbewerbung" in l["text"]
                        for l in all_link_texts
                    )
                    if has_external and not has_easy_apply:
                        external_only = True
                except:
                    pass

                if external_only:
                    await self.log("info", "apply", "external_only", {
                        "message": f"  External-only job (no Easy Apply) — skipping",
                    }, job_id=job.id, platform="xing")
                    application.status = "skipped"
                    application.error_log = "External apply only — no Xing Easy Apply"
                    db.commit()
                    self.stats["skipped"] += 1
                    await self.emit_progress()
                    continue

                apply_btn = None
                btn_text = ""
                apply_selectors = [
                    'button:has-text("Easy apply")',
                    'button:has-text("Schnellbewerbung")',
                    'button:has-text("Jetzt bewerben")',
                    'button:has-text("Bewerben")',
                    'button:has-text("Apply now")',
                    'button:has-text("Apply")',
                    'a:has-text("Easy apply")',
                    'a:has-text("Schnellbewerbung")',
                    'a:has-text("Jetzt bewerben")',
                    'a:has-text("Bewerben")',
                    'a:has-text("Apply now")',
                    'a[data-testid="apply-button-inner"]',
                    'button[data-testid="apply-button-inner"]',
                    '[data-testid="apply-button"]',
                    'a[href*="/apply"]',
                    'a[href*="bewerben"]',
                ]

                # Try twice — first pass, then wait 3s for lazy-loaded buttons
                for attempt in range(2):
                    for sel in apply_selectors:
                        apply_btn = await self._page.query_selector(sel)
                        if apply_btn and await apply_btn.is_visible():
                            try:
                                btn_text = (await apply_btn.inner_text()).strip()
                            except:
                                btn_text = sel
                            break
                        apply_btn = None
                    if apply_btn:
                        break
                    if attempt == 0:
                        # Scroll down and wait for lazy content
                        await self._page.evaluate("window.scrollBy(0, 400)")
                        await asyncio.sleep(3)

                if not apply_btn:
                    all_btns = await self._page.query_selector_all("button:visible, a:visible")
                    btn_texts = []
                    for b in all_btns[:15]:
                        try:
                            t = (await b.inner_text()).strip()
                            if t and len(t) < 60:
                                btn_texts.append(t)
                        except:
                            pass
                    await self.log("warn", "apply", "no_button", {
                        "message": f"  No Xing apply button found. Buttons: {btn_texts[:8]}",
                    }, job_id=job.id, platform="xing")
                    application.status = "skipped"
                    application.error_log = "No apply button (may be external apply)"
                    db.commit()
                    self.stats["skipped"] += 1
                    await self.emit_progress()
                    continue

                await self.log("info", "apply", "clicking_apply", {
                    "message": f"  Clicking \"{btn_text}\"...",
                }, job_id=job.id, platform="xing")

                # Click apply — may open new tab or modal
                old_url = self._page.url
                old_pages = ctx.pages[:]
                await apply_btn.click()
                await asyncio.sleep(random.uniform(3, 5))

                # Check if new tab opened
                new_pages = [p for p in ctx.pages if p not in old_pages]
                target_page = new_pages[0] if new_pages else self._page
                if new_pages:
                    await self.log("info", "apply", "new_tab", {
                        "message": "  Application opened in new tab",
                    }, job_id=job.id, platform="xing")
                    try:
                        await target_page.wait_for_load_state("domcontentloaded", timeout=15000)
                    except:
                        pass
                    await asyncio.sleep(2)

                await self.screenshot("xing_after_apply_click")

                # Detect external redirect — if we left xing.com, skip this job
                target_url = target_page.url.lower()
                if "xing.com" not in target_url and "xing.com" not in self._page.url.lower():
                    await self.log("warn", "apply", "external_redirect", {
                        "message": f"  External redirect to {target_url[:80]} — skipping (not a Xing Easy Apply)",
                    }, job_id=job.id, platform="xing")
                    application.status = "skipped"
                    application.error_log = f"External apply: {target_url[:200]}"
                    db.commit()
                    self.stats["skipped"] += 1
                    await self.emit_progress()
                    if new_pages and not new_pages[0].is_closed():
                        await new_pages[0].close()
                    if i < len(jobs) - 1 and self.running:
                        await asyncio.sleep(random.uniform(10, 15))
                    continue

                # Check for success already (instant "Easy apply" — no form)
                page_text = (await target_page.inner_text("body")).lower()
                if any(kw in page_text for kw in ["bewerbung wurde gesendet", "application sent", "erfolgreich gesendet", "bewerbung abgeschickt"]):
                    application.status = "success"
                    self.stats["applied"] += 1
                    await self.log("info", "apply", "success", {
                        "message": f"  SUCCESS — Application sent! ({time.time()-t0:.0f}s)",
                    }, job_id=job.id, platform="xing")
                    db.commit()
                    await self.emit_progress()
                    if new_pages and not new_pages[0].is_closed():
                        await new_pages[0].close()
                    if i < len(jobs) - 1 and self.running:
                        await asyncio.sleep(random.uniform(15, 25))
                    continue

                # Multi-step form: loop through Next/Submit buttons
                form_success = False
                prev_page_signature = ""
                stuck_count = 0
                for step in range(10):
                    # Check if we've been redirected to an external site (not xing.com)
                    try:
                        step_url = target_page.url.lower()
                        if "xing.com" not in step_url:
                            await self.log("warn", "apply", "external_redirect", {
                                "message": f"  Left Xing (now on {step_url[:80]}) — stopping form loop",
                            }, job_id=job.id, platform="xing")
                            break
                    except:
                        pass

                    # Capture page signature to detect stuck loops
                    try:
                        cur_url = target_page.url
                        cur_inputs = await target_page.evaluate("""() => {
                            const inputs = document.querySelectorAll('input:not([type=hidden]), select, textarea');
                            return Array.from(inputs).map(e => e.name || e.id || e.type).join(',');
                        }""")
                        page_signature = f"{cur_url}|{cur_inputs}"
                    except:
                        page_signature = ""

                    if page_signature and page_signature == prev_page_signature:
                        stuck_count += 1
                        if stuck_count >= 2:
                            await self.log("warn", "apply", "form_stuck", {
                                "message": f"  Form stuck — same page after {stuck_count} attempts, giving up",
                            }, job_id=job.id, platform="xing")
                            # Check for validation errors before breaking
                            try:
                                err_els = await target_page.query_selector_all('[class*="error"], [class*="Error"], [role="alert"], .field-error, .validation-error')
                                for err_el in err_els[:3]:
                                    err_text = (await err_el.inner_text()).strip()
                                    if err_text:
                                        await self.log("warn", "apply", "validation_error", {
                                            "message": f"  Validation error: {err_text[:100]}",
                                        }, job_id=job.id, platform="xing")
                            except:
                                pass
                            break
                    else:
                        stuck_count = 0
                    prev_page_signature = page_signature

                    # Try to fill form fields if any
                    original_page = self._page
                    self._page = target_page
                    form_result = await self._match_and_fill_form(
                        profile, job_id=job.id, platform="xing",
                        job_title=job.title, company=job.company,
                    )
                    self._page = original_page

                    # Click submit/next/continue
                    clicked = False
                    for sel in [
                        'button[type="submit"]',
                        '[data-testid="submit-application-button"]',
                        '[data-testid="application-submit-button"]',
                        'button:has-text("Bewerbung absenden")',
                        'button:has-text("Send application")',
                        'button:has-text("Weiter")',
                        'button:has-text("Next")',
                        'button:has-text("Continue")',
                        'button:has-text("Fortfahren")',
                        '[data-testid="dps-button"]',
                    ]:
                        btn = await target_page.query_selector(sel)
                        if btn and await btn.is_visible():
                            try:
                                step_text = (await btn.inner_text()).strip()
                                await self.log("info", "apply", "form_step", {
                                    "message": f"  Step {step+1}: clicking \"{step_text}\"",
                                }, job_id=job.id, platform="xing")
                                await btn.click()
                                await asyncio.sleep(random.uniform(2, 4))
                                clicked = True
                                break
                            except:
                                continue

                    if not clicked:
                        await self.log("info", "apply", "form_no_button", {
                            "message": f"  No more buttons at step {step+1}",
                        }, job_id=job.id, platform="xing")
                        break

                    # Check for validation errors after clicking (form didn't advance)
                    try:
                        err_els = await target_page.query_selector_all('[class*="error"], [class*="Error"], [role="alert"], .field-error, .validation-error')
                        for err_el in err_els[:3]:
                            err_text = (await err_el.inner_text()).strip()
                            if err_text and len(err_text) < 200:
                                await self.log("warn", "apply", "validation_error", {
                                    "message": f"  Validation: {err_text[:100]}",
                                }, job_id=job.id, platform="xing")
                    except:
                        pass

                    # Check success after each step
                    try:
                        page_text = (await target_page.inner_text("body")).lower()
                    except:
                        # Page might have closed/navigated — could be success
                        form_success = True
                        break
                    success_keywords = [
                        "bewerbung wurde gesendet", "bewerbung abgeschickt",
                        "erfolgreich gesendet", "application sent", "application submitted",
                        "successfully sent", "we have received your application",
                        "wir haben ihre bewerbung erhalten",
                        "vielen dank für ihre bewerbung", "thank you for your application",
                    ]
                    if any(kw in page_text for kw in success_keywords):
                        form_success = True
                        break

                    # Also check if "Send application" button disappeared (= submitted)
                    send_btn_gone = True
                    for check_sel in ['button:has-text("Send application")', 'button:has-text("Bewerbung absenden")', 'button:has-text("Easy apply")']:
                        check_btn = await target_page.query_selector(check_sel)
                        if check_btn and await check_btn.is_visible():
                            send_btn_gone = False
                            break
                    # If we clicked "Send application" and it's gone, that's likely success
                    if send_btn_gone and "send" in step_text.lower() or "absenden" in step_text.lower():
                        form_success = True
                        break

                if form_success:
                    application.status = "success"
                    self.stats["applied"] += 1
                    await self.log("info", "apply", "success", {
                        "message": f"  SUCCESS — Xing application submitted ({time.time()-t0:.0f}s)",
                    }, job_id=job.id, platform="xing")
                else:
                    # One more check: maybe success page loaded after the loop
                    # NOTE: Only match SPECIFIC success phrases — "bewerbung" alone matches every Xing page
                    try:
                        final_text = (await target_page.inner_text("body")).lower()
                        if any(kw in final_text for kw in [
                            "bewerbung wurde gesendet", "bewerbung abgeschickt",
                            "erfolgreich gesendet", "application sent", "application submitted",
                            "we have received your application", "wir haben ihre bewerbung erhalten",
                        ]):
                            application.status = "success"
                            self.stats["applied"] += 1
                            await self.log("info", "apply", "success", {
                                "message": f"  SUCCESS (delayed detection) — Xing application submitted",
                            }, job_id=job.id, platform="xing")
                        else:
                            application.status = "failed"
                            application.error_log = "Could not complete Xing application form"
                            self.stats["failed"] += 1
                            await self.log("warn", "apply", "form_incomplete", {
                                "message": f"  Could not complete application form",
                            }, job_id=job.id, platform="xing")
                    except:
                        application.status = "failed"
                        application.error_log = "Could not complete Xing application form"
                        self.stats["failed"] += 1
                        await self.log("warn", "apply", "form_incomplete", {
                            "message": f"  Could not complete application form",
                        }, job_id=job.id, platform="xing")

                await self.screenshot("xing_after_submit")
                db.commit()
                await self.emit_progress()

                # Close popup tab if opened
                if new_pages and not new_pages[0].is_closed():
                    await new_pages[0].close()

            except Exception as e:
                application.status = "failed"
                application.error_log = str(e)[:500]
                db.commit()
                self.stats["failed"] += 1
                await self.log("error", "apply", "error", {
                    "message": f"  ERROR: {str(e)[:100]}",
                }, job_id=job.id, platform="xing")
                await self.emit_progress()

            if i < len(jobs) - 1 and self.running:
                delay = random.uniform(20, 35)
                await self.log("info", "system", "delay", {
                    "message": f"  Waiting {delay:.0f}s before next...",
                })
                await asyncio.sleep(delay)

        await browser.close()
        self._page = None

    # ── Indeed Platform Methods ─────────────────────────────────────────────

    async def _dismiss_indeed_cookies(self, page=None):
        """Handle Indeed cookie/consent banner."""
        page = page or self._page
        if not page:
            return
        try:
            for sel in [
                'button#onetrust-accept-btn-handler',
                'button[aria-label="dismiss"]',
                'button:has-text("Accept")',
                'button:has-text("Alle akzeptieren")',
                'button:has-text("Zustimmen")',
                '#onetrust-accept-btn-handler',
            ]:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(1)
                    break
        except:
            pass

    async def _login_indeed(self, page, cred) -> bool:
        """Log into Indeed."""
        await self.log("info", "apply", "login_start", {
            "message": f"Logging into Indeed as {cred.email}...",
        }, platform="indeed")

        try:
            await page.goto("https://secure.indeed.com/account/login?hl=de_DE", timeout=20000)
            await asyncio.sleep(random.uniform(3, 5))
            await self._dismiss_indeed_cookies(page)
            await self.screenshot("indeed_login_01")

            # Indeed login: email first, then password on next screen (or same page)
            email_input = (
                await page.query_selector('input[type="email"]') or
                await page.query_selector('input[name="__email"]') or
                await page.query_selector('input#ifl-InputFormField-3')
            )
            if email_input:
                await email_input.click()
                await asyncio.sleep(0.3)
                await email_input.fill("")
                await email_input.type(cred.email, delay=random.randint(30, 80))
                await self.log("info", "apply", "login_email", {
                    "message": f"  Entered email: {cred.email}",
                }, platform="indeed")
            else:
                await self.log("warn", "apply", "login_no_email", {
                    "message": "  No email input found on Indeed login",
                }, platform="indeed")
                await self.screenshot("indeed_login_err_no_email")
                return False

            # Click continue/next or press Enter
            continue_btn = (
                await page.query_selector('button[type="submit"]') or
                await page.query_selector('button:has-text("Continue")') or
                await page.query_selector('button:has-text("Weiter")')
            )
            if continue_btn and await continue_btn.is_visible():
                await continue_btn.click()
            else:
                await email_input.press("Enter")

            await asyncio.sleep(random.uniform(3, 5))
            await self.screenshot("indeed_login_02_after_email")

            # Now enter password (may be on same page or new page)
            pw_input = (
                await page.query_selector('input[type="password"]') or
                await page.query_selector('input[name="__password"]')
            )
            if pw_input:
                await pw_input.click()
                await asyncio.sleep(0.3)
                await pw_input.type(cred.password_encrypted, delay=random.randint(30, 80))
                await self.log("info", "apply", "login_password", {
                    "message": "  Entered password",
                }, platform="indeed")

                # Submit
                submit_btn = (
                    await page.query_selector('button[type="submit"]') or
                    await page.query_selector('button:has-text("Sign in")') or
                    await page.query_selector('button:has-text("Anmelden")')
                )
                if submit_btn and await submit_btn.is_visible():
                    await submit_btn.click()
                else:
                    await pw_input.press("Enter")

                await asyncio.sleep(random.uniform(4, 6))
            else:
                # Indeed sometimes uses magic link / phone verification — no password field
                await self.log("warn", "apply", "login_no_password", {
                    "message": "  No password field — Indeed may require verification",
                }, platform="indeed")
                await self.screenshot("indeed_login_no_password")
                return False

            await self._dismiss_indeed_cookies(page)
            await self.screenshot("indeed_login_03_after")

            # Check login success
            current_url = page.url
            if "login" not in current_url or "secure.indeed" not in current_url:
                await self.log("info", "apply", "login_success", {
                    "message": "  Indeed login successful!",
                }, platform="indeed")
                return True

            # Check for error messages
            try:
                page_text = await page.inner_text("body")
                if "captcha" in page_text.lower() or "verify" in page_text.lower():
                    await self.log("warn", "apply", "login_captcha", {
                        "message": "  CAPTCHA or verification required — cannot proceed",
                    }, platform="indeed")
                    return False
            except:
                pass

            await self.log("warn", "apply", "login_failed", {
                "message": "  Indeed login failed — still on login page",
            }, platform="indeed")
            return False

        except Exception as e:
            await self.log("error", "apply", "login_error", {
                "message": f"  Indeed login error: {str(e)[:200]}",
            }, platform="indeed")
            return False

    async def _scrape_phase_indeed(self, db: Session, job_filter: JobFilter, profile: dict) -> list[int]:
        """Scrape Indeed for jobs. Returns list of all job IDs found."""
        await self.log("info", "scrape", "phase_start", {"message": "Starting Indeed job discovery..."})
        await self.emit_status("scraping")

        queries = job_filter.job_titles if job_filter and job_filter.job_titles else ["kellner"]
        locations = job_filter.locations if job_filter and job_filter.locations else ["berlin"]
        requested_apps = int(job_filter.max_applications or 10) if job_filter and hasattr(job_filter, 'max_applications') else 10
        max_pages = max(3, min((requested_apps * 2) // 15 + 1, 30))
        all_job_ids = []
        total_new = 0

        pw = await async_playwright().start()

        for query in queries:
            for loc in locations:
                if not self.running:
                    break

                q_enc = urllib.parse.quote(query)
                l_enc = urllib.parse.quote(loc)

                await self.log("info", "scrape", "search_start", {
                    "message": f"Searching Indeed: {query} in {loc} (up to {max_pages} pages)",
                    "query": query, "location": loc,
                }, platform="indeed")

                browser = await pw.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled', '--disable-http2'],
                )
                ctx = await browser.new_context(
                    viewport={"width": 1366, "height": 768},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="de-DE",
                )
                self._page = await ctx.new_page()
                await self._page.add_init_script(STEALTH_JS)

                new_for_query = 0
                for page_num in range(1, max_pages + 1):
                    if not self.running:
                        break

                    # Indeed pagination: start=0, 10, 20, ...
                    url = f"https://de.indeed.com/jobs?q={q_enc}&l={l_enc}"
                    if page_num > 1:
                        url += f"&start={(page_num - 1) * 10}"

                    try:
                        await self._page.goto(url, timeout=20000, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(3, 6))
                        await self._dismiss_indeed_cookies()

                        if page_num == 1:
                            await self.screenshot("indeed_search_results")

                        # Indeed job cards — multiple possible selectors
                        cards = await self._page.query_selector_all(
                            'div.job_seen_beacon, div.slider_container .slider_item, '
                            'li[data-resultcount], div[data-jk], .resultContent, '
                            'table.jobCard_mainContent, div.cardOutline'
                        )
                        # Fallback: try generic result containers
                        if not cards:
                            cards = await self._page.query_selector_all('#mosaic-provider-jobcards a.jcs-JobTitle')
                            # If we got title links, use parent containers
                            if cards:
                                parent_cards = []
                                for c in cards:
                                    parent = await c.evaluate("el => el.closest('.job_seen_beacon, .cardOutline, [data-jk], li')")
                                    if parent:
                                        parent_el = await self._page.query_selector(f'[data-jk="{parent}"]') if isinstance(parent, str) else None
                                        if parent_el:
                                            parent_cards.append(parent_el)
                                if parent_cards:
                                    cards = parent_cards

                        if not cards:
                            await self.log("info", "scrape", "no_more_pages", {
                                "message": f"  Indeed page {page_num}: no jobs — end of results",
                            }, platform="indeed")
                            break

                        await self.log("info", "scrape", "jobs_found", {
                            "message": f"  Indeed page {page_num}: {len(cards)} jobs",
                            "count": len(cards), "page": page_num,
                        }, platform="indeed")

                        new_in_page = 0
                        for card in cards:
                            try:
                                # Extract title — Indeed uses h2.jobTitle or a.jcs-JobTitle
                                title_el = (
                                    await card.query_selector('h2.jobTitle a, h2.jobTitle span, a.jcs-JobTitle, '
                                                              'span[id^="jobTitle"], a[data-jk]')
                                )
                                title = (await title_el.inner_text()).strip() if title_el else ""

                                # Extract URL — from title link or data-jk attribute
                                href = ""
                                if title_el:
                                    href = await title_el.get_attribute("href") or ""
                                if not href:
                                    # Try data-jk on card itself
                                    jk = await card.get_attribute("data-jk") or ""
                                    if jk:
                                        href = f"/viewjob?jk={jk}"
                                    else:
                                        # Find any link with /viewjob or /rc/clk
                                        link = await card.query_selector('a[href*="viewjob"], a[href*="/rc/clk"]')
                                        if link:
                                            href = await link.get_attribute("href") or ""

                                # Extract company
                                company_el = (
                                    await card.query_selector('[data-testid="company-name"], span.companyName, '
                                                              'span.company, .companyInfo span')
                                )
                                company = (await company_el.inner_text()).strip() if company_el else ""

                                # Extract location
                                location_el = (
                                    await card.query_selector('[data-testid="text-location"], div.companyLocation, '
                                                              'div.company_location, span.companyLocation')
                                )
                                location_text = (await location_el.inner_text()).strip() if location_el else ""

                                if not title or not href:
                                    continue

                                full_url = href if href.startswith("http") else f"https://de.indeed.com{href}"
                                # Normalize URL — strip tracking params, keep jk
                                if "jk=" in full_url:
                                    import re as _re
                                    jk_match = _re.search(r'jk=([a-f0-9]+)', full_url)
                                    if jk_match:
                                        full_url = f"https://de.indeed.com/viewjob?jk={jk_match.group(1)}"

                                # Blacklist check
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
                                    new_job = Job(
                                        platform="indeed", title=title[:200], company=company[:200],
                                        location=location_text[:200], url=full_url,
                                        scraped_at=datetime.now(timezone.utc),
                                    )
                                    db.add(new_job)
                                    db.flush()
                                    all_job_ids.append(new_job.id)
                                    new_in_page += 1
                                else:
                                    all_job_ids.append(existing.id)
                            except:
                                continue

                        db.commit()
                        new_for_query += new_in_page
                        total_new += new_in_page

                        await self.log("info", "scrape", "page_complete", {
                            "message": f"  Indeed page {page_num}: {new_in_page} new jobs stored",
                            "new_jobs": new_in_page, "page": page_num,
                        }, platform="indeed")

                        if page_num < max_pages:
                            await asyncio.sleep(random.uniform(5, 10))

                    except Exception as e:
                        await self.log("warn", "scrape", "page_failed", {
                            "message": f"  Indeed page {page_num} failed: {str(e)[:80]}",
                        }, platform="indeed")
                        break

                await self.log("info", "scrape", "query_complete", {
                    "message": f"  Indeed {query} in {loc}: {new_for_query} new jobs",
                }, platform="indeed")
                await browser.close()
                self._page = None
                await asyncio.sleep(random.uniform(5, 8))

        await pw.stop()

        await self.log("info", "scrape", "phase_complete", {
            "message": f"Indeed discovery complete: {total_new} new jobs ({len(all_job_ids)} total)",
            "total_new": total_new,
            "total_in_results": len(all_job_ids),
        }, platform="indeed")

        return all_job_ids

    async def _apply_phase_indeed(self, db: Session, profile: dict, creds: list, job_filter: JobFilter, scraped_job_ids: list[int] = None):
        """Apply to Indeed jobs."""
        await self.log("info", "apply", "phase_start", {"message": "Starting Indeed application phase..."})
        await self.emit_status("applying")

        applied_urls = set(
            r[0] for r in db.query(Application.url).filter(Application.user_id == self.user_id).all() if r[0]
        )

        if scraped_job_ids:
            query = db.query(Job).filter(Job.id.in_(scraped_job_ids))
        else:
            query = db.query(Job).filter(Job.platform == "indeed")

        if applied_urls:
            query = query.filter(~Job.url.in_(applied_urls))

        search_queries = job_filter.job_titles if job_filter and job_filter.job_titles else []
        max_apps = min(max(int(job_filter.max_applications or 10) if job_filter and hasattr(job_filter, 'max_applications') else 10, 1), 500)
        all_candidates = query.order_by(Job.scraped_at.desc()).limit(max_apps * 5).all()
        if search_queries:
            jobs = [j for j in all_candidates if _is_title_relevant(j.title, search_queries)][:max_apps]
        else:
            jobs = all_candidates[:max_apps]

        self.stats["total"] = len(jobs)
        await self.log("info", "apply", "jobs_queued", {
            "message": f"Queued {len(jobs)} Indeed jobs for application (max: {max_apps})",
            "count": len(jobs),
        })
        await self.emit_progress()

        if not jobs:
            await self.log("info", "apply", "no_jobs", {"message": "No unapplied Indeed jobs found"})
            return

        # Launch browser + login
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled', '--disable-http2'])
        ctx = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="de-DE",
        )
        self._page = await ctx.new_page()
        await self._page.add_init_script(STEALTH_JS)

        indeed_cred = next((c for c in creds if c.platform == "indeed" and c.is_active), None)
        if not indeed_cred:
            await self.log("error", "apply", "no_credentials", {
                "message": "No Indeed credentials found — add them in Profile page.",
            }, platform="indeed")
            await browser.close()
            await pw.stop()
            return

        logged_in = await self._login_indeed(self._page, indeed_cred)
        if not logged_in:
            await self.log("error", "apply", "login_required", {
                "message": "INDEED LOGIN FAILED — Aborting apply phase.",
            }, platform="indeed")
            await browser.close()
            await pw.stop()
            return

        for i, job in enumerate(jobs):
            if not self.running:
                break

            await self.log("info", "apply", "job_start", {
                "message": f"[{i+1}/{len(jobs)}] Opening: {job.title} at {job.company}",
                "job_title": job.title, "company": job.company, "url": job.url,
            }, job_id=job.id, platform="indeed")

            application = Application(
                user_id=self.user_id, job_id=job.id, platform="indeed",
                job_title=job.title, company=job.company, url=job.url,
                status="applying", applied_at=datetime.now(timezone.utc),
            )
            db.add(application)
            db.commit()

            try:
                t0 = time.time()
                await self._page.goto(job.url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(2, 4))
                await self._dismiss_indeed_cookies()
                await self.screenshot("indeed_job_page")

                # Find apply button — Indeed uses "Jetzt bewerben" / "Apply now" / "Schnellbewerbung"
                apply_btn = None
                btn_text = ""
                is_easy_apply = False

                for sel in [
                    'button#indeedApplyButton',
                    'button[data-testid="indeedApplyButton"]',
                    'button:has-text("Jetzt bewerben")',
                    'button:has-text("Apply now")',
                    'button:has-text("Schnellbewerbung")',
                    'a:has-text("Jetzt bewerben")',
                    'a:has-text("Apply now")',
                    'a[data-testid="apply-button"]',
                    '#applyButtonLinkContainer a',
                ]:
                    apply_btn = await self._page.query_selector(sel)
                    if apply_btn and await apply_btn.is_visible():
                        try:
                            btn_text = (await apply_btn.inner_text()).strip()
                        except:
                            btn_text = sel
                        # Check if it's Indeed Easy Apply (not external)
                        btn_id = await apply_btn.get_attribute("id") or ""
                        btn_class = await apply_btn.get_attribute("class") or ""
                        if "indeedApply" in btn_id or "indeedApply" in btn_class:
                            is_easy_apply = True
                        break
                    apply_btn = None

                if not apply_btn:
                    # Scroll down and retry
                    await self._page.evaluate("window.scrollBy(0, 400)")
                    await asyncio.sleep(2)
                    for sel in ['button#indeedApplyButton', 'button:has-text("Jetzt bewerben")', 'button:has-text("Apply now")']:
                        apply_btn = await self._page.query_selector(sel)
                        if apply_btn and await apply_btn.is_visible():
                            btn_text = (await apply_btn.inner_text()).strip()
                            break
                        apply_btn = None

                if not apply_btn:
                    all_btns = await self._page.query_selector_all("button:visible, a:visible")
                    btn_texts = []
                    for b in all_btns[:15]:
                        try:
                            t = (await b.inner_text()).strip()
                            if t and len(t) < 60:
                                btn_texts.append(t)
                        except:
                            pass
                    await self.log("warn", "apply", "no_button", {
                        "message": f"  No Indeed apply button found. Buttons: {btn_texts[:8]}",
                    }, job_id=job.id, platform="indeed")
                    application.status = "skipped"
                    application.error_log = "No apply button found"
                    db.commit()
                    self.stats["skipped"] += 1
                    await self.emit_progress()
                    continue

                await self.log("info", "apply", "clicking_apply", {
                    "message": f"  Clicking \"{btn_text}\"... {'(Easy Apply)' if is_easy_apply else '(may redirect)'}",
                }, job_id=job.id, platform="indeed")

                # Click apply — may open new tab, modal, or redirect externally
                old_url = self._page.url
                old_pages = ctx.pages[:]
                await apply_btn.click()
                await asyncio.sleep(random.uniform(3, 5))

                # Check if new tab opened
                new_pages = [p for p in ctx.pages if p not in old_pages]
                target_page = new_pages[0] if new_pages else self._page
                if new_pages:
                    await self.log("info", "apply", "new_tab", {
                        "message": "  Application opened in new tab",
                    }, job_id=job.id, platform="indeed")
                    try:
                        await target_page.wait_for_load_state("domcontentloaded", timeout=15000)
                    except:
                        pass
                    await asyncio.sleep(2)

                await self.screenshot("indeed_after_apply_click")

                # Detect external redirect — if we left indeed.com, skip
                target_url = target_page.url.lower()
                if "indeed.com" not in target_url and "indeed.com" not in self._page.url.lower():
                    await self.log("warn", "apply", "external_redirect", {
                        "message": f"  External redirect to {target_url[:80]} — skipping",
                    }, job_id=job.id, platform="indeed")
                    application.status = "skipped"
                    application.error_log = f"External apply: {target_url[:200]}"
                    db.commit()
                    self.stats["skipped"] += 1
                    await self.emit_progress()
                    if new_pages and not new_pages[0].is_closed():
                        await new_pages[0].close()
                    continue

                # Check for instant success
                page_text = (await target_page.inner_text("body")).lower()
                if any(kw in page_text for kw in [
                    "your application has been submitted", "ihre bewerbung wurde gesendet",
                    "bewerbung abgeschickt", "application sent", "erfolgreich beworben",
                ]):
                    application.status = "success"
                    self.stats["applied"] += 1
                    await self.log("info", "apply", "success", {
                        "message": f"  SUCCESS — Indeed application sent! ({time.time()-t0:.0f}s)",
                    }, job_id=job.id, platform="indeed")
                    db.commit()
                    await self.emit_progress()
                    if new_pages and not new_pages[0].is_closed():
                        await new_pages[0].close()
                    if i < len(jobs) - 1 and self.running:
                        await asyncio.sleep(random.uniform(15, 25))
                    continue

                # Multi-step Indeed Easy Apply form
                form_success = False
                prev_page_signature = ""
                stuck_count = 0

                for step in range(15):
                    # Check external redirect mid-form
                    try:
                        step_url = target_page.url.lower()
                        if "indeed.com" not in step_url:
                            await self.log("warn", "apply", "external_redirect", {
                                "message": f"  Left Indeed (now on {step_url[:80]}) — stopping",
                            }, job_id=job.id, platform="indeed")
                            break
                    except:
                        pass

                    # Stuck detection
                    try:
                        cur_url = target_page.url
                        cur_inputs = await target_page.evaluate("""() => {
                            const inputs = document.querySelectorAll('input:not([type=hidden]), select, textarea');
                            return Array.from(inputs).map(e => e.name || e.id || e.type).join(',');
                        }""")
                        page_signature = f"{cur_url}|{cur_inputs}"
                    except:
                        page_signature = ""

                    if page_signature and page_signature == prev_page_signature:
                        stuck_count += 1
                        if stuck_count >= 2:
                            await self.log("warn", "apply", "form_stuck", {
                                "message": f"  Form stuck — same page after {stuck_count} attempts",
                            }, job_id=job.id, platform="indeed")
                            # Log validation errors
                            try:
                                err_els = await target_page.query_selector_all('[class*="error"], [class*="Error"], [role="alert"]')
                                for err_el in err_els[:3]:
                                    err_text = (await err_el.inner_text()).strip()
                                    if err_text:
                                        await self.log("warn", "apply", "validation_error", {
                                            "message": f"  Validation: {err_text[:100]}",
                                        }, job_id=job.id, platform="indeed")
                            except:
                                pass
                            break
                    else:
                        stuck_count = 0
                    prev_page_signature = page_signature

                    # Fill form fields
                    original_page = self._page
                    self._page = target_page
                    form_result = await self._match_and_fill_form(
                        profile, job_id=job.id, platform="indeed",
                        job_title=job.title, company=job.company,
                    )
                    self._page = original_page

                    # Click continue/submit/next
                    clicked = False
                    for sel in [
                        'button[data-testid="submit-button"]',
                        'button:has-text("Bewerbung abschicken")',
                        'button:has-text("Submit your application")',
                        'button:has-text("Submit")',
                        'button:has-text("Apply")',
                        'button:has-text("Absenden")',
                        'button:has-text("Continue")',
                        'button:has-text("Weiter")',
                        'button:has-text("Next")',
                        'button[type="submit"]',
                        'a:has-text("Continue")',
                    ]:
                        btn = await target_page.query_selector(sel)
                        if btn and await btn.is_visible():
                            try:
                                step_text = (await btn.inner_text()).strip()
                                await self.log("info", "apply", "form_step", {
                                    "message": f"  Step {step+1}: clicking \"{step_text}\"",
                                }, job_id=job.id, platform="indeed")
                                await btn.click()
                                await asyncio.sleep(random.uniform(2, 4))
                                clicked = True
                                break
                            except:
                                continue

                    if not clicked:
                        await self.log("info", "apply", "form_no_button", {
                            "message": f"  No more buttons at step {step+1}",
                        }, job_id=job.id, platform="indeed")
                        break

                    # Check validation errors
                    try:
                        err_els = await target_page.query_selector_all('[class*="error"], [class*="Error"], [role="alert"]')
                        for err_el in err_els[:3]:
                            err_text = (await err_el.inner_text()).strip()
                            if err_text and len(err_text) < 200:
                                await self.log("warn", "apply", "validation_error", {
                                    "message": f"  Validation: {err_text[:100]}",
                                }, job_id=job.id, platform="indeed")
                    except:
                        pass

                    # Check success
                    try:
                        page_text = (await target_page.inner_text("body")).lower()
                    except:
                        form_success = True
                        break

                    if any(kw in page_text for kw in [
                        "your application has been submitted", "ihre bewerbung wurde gesendet",
                        "bewerbung abgeschickt", "application sent", "erfolgreich beworben",
                        "we have received your application", "vielen dank für ihre bewerbung",
                        "thank you for your application",
                    ]):
                        form_success = True
                        break

                if form_success:
                    application.status = "success"
                    self.stats["applied"] += 1
                    await self.log("info", "apply", "success", {
                        "message": f"  SUCCESS — Indeed application submitted ({time.time()-t0:.0f}s)",
                    }, job_id=job.id, platform="indeed")
                else:
                    # Final check
                    try:
                        final_text = (await target_page.inner_text("body")).lower()
                        if any(kw in final_text for kw in [
                            "your application has been submitted", "bewerbung abgeschickt",
                            "erfolgreich beworben", "application sent",
                        ]):
                            application.status = "success"
                            self.stats["applied"] += 1
                            await self.log("info", "apply", "success", {
                                "message": f"  SUCCESS (delayed) — Indeed application submitted",
                            }, job_id=job.id, platform="indeed")
                        else:
                            application.status = "failed"
                            application.error_log = "Could not complete Indeed application form"
                            self.stats["failed"] += 1
                            await self.log("warn", "apply", "form_incomplete", {
                                "message": f"  Could not complete application form",
                            }, job_id=job.id, platform="indeed")
                    except:
                        application.status = "failed"
                        application.error_log = "Could not complete Indeed application form"
                        self.stats["failed"] += 1

                await self.screenshot("indeed_after_submit")
                db.commit()
                await self.emit_progress()

                if new_pages and not new_pages[0].is_closed():
                    await new_pages[0].close()

            except Exception as e:
                application.status = "failed"
                application.error_log = str(e)[:500]
                db.commit()
                self.stats["failed"] += 1
                await self.log("error", "apply", "error", {
                    "message": f"  ERROR: {str(e)[:100]}",
                }, job_id=job.id, platform="indeed")
                await self.emit_progress()

            if i < len(jobs) - 1 and self.running:
                delay = random.uniform(20, 35)
                await self.log("info", "system", "delay", {
                    "message": f"  Waiting {delay:.0f}s before next...",
                })
                await asyncio.sleep(delay)

        await browser.close()
        self._page = None

    async def stop(self):
        """Gracefully stop the bot."""
        await self.log("info", "system", "stop_requested", {"message": "Stop requested by user"})
        self.running = False

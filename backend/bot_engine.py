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

# Enhanced stealth script for LinkedIn (comprehensive anti-detection)
_STEALTH_SCRIPT_FULL = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined, configurable: true});
delete navigator.__proto__.webdriver;
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const p = [{name:'Chrome PDF Plugin',filename:'internal-pdf-viewer',description:'Portable Document Format'},
                    {name:'Chrome PDF Viewer',filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai',description:''},
                    {name:'Native Client',filename:'internal-nacl-plugin',description:''}];
        p.length = 3; p.item = i => p[i]; p.namedItem = n => p.find(x => x.name === n) || null; p.refresh = () => {};
        return p;
    }, configurable: true
});
Object.defineProperty(navigator, 'languages', {get: () => ['de-DE','de','en-US','en'], configurable: true});
if (!window.chrome) window.chrome = {};
window.chrome.runtime = {connect:()=>{},sendMessage:()=>{},onMessage:{addListener:()=>{},removeListener:()=>{}},id:undefined};
window.chrome.app = {isInstalled:false,InstallState:{DISABLED:'disabled',INSTALLED:'installed',NOT_INSTALLED:'not_installed'},RunningState:{CANNOT_RUN:'cannot_run',READY_TO_RUN:'ready_to_run',RUNNING:'running'}};
window.chrome.csi = () => ({}); window.chrome.loadTimes = () => ({});
const origQ = window.navigator.permissions?.query;
if (origQ) { window.navigator.permissions.query = p => p.name==='notifications' ? Promise.resolve({state:Notification.permission,onchange:null}) : origQ.call(navigator.permissions,p); }
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8, configurable: true});
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8, configurable: true});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32', configurable: true});
Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.', configurable: true});
Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0, configurable: true});
const gpH = {apply:(t,a,args) => {if(args[0]===37445) return 'Intel Inc.'; if(args[0]===37446) return 'Intel Iris OpenGL Engine'; return Reflect.apply(t,a,args);}};
try { const gc = HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext = function(t,a) { const c = gc.call(this,t,a); if(c&&(t==='webgl'||t==='webgl2'||t==='experimental-webgl')) { c.getParameter = new Proxy(c.getParameter.bind(c), gpH); } return c; }; } catch(e) {}
if (window.outerWidth === 0) Object.defineProperty(window, 'outerWidth', {get: () => window.innerWidth});
if (window.outerHeight === 0) Object.defineProperty(window, 'outerHeight', {get: () => window.innerHeight + 100});
window.Notification = window.Notification || {permission:'default'};
window.speechSynthesis = window.speechSynthesis || {getVoices:()=>[]};
"""

# User agent pool for LinkedIn (rotate per session)
_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

# LinkedIn question-answer patterns (bilingual DE/EN)
_LINKEDIN_QA: dict[str, str] = {
    "authorized to work": "Yes", "legally authorized": "Yes", "work authorization": "Yes",
    "work permit": "Yes", "right to work": "Yes", "eligible to work": "Yes",
    "arbeitsgenehmigung": "Yes", "arbeitserlaubnis": "Yes", "arbeitsberechtigung": "Yes",
    "sponsorship": "No", "visa sponsorship": "No", "require sponsorship": "No",
    "visum": "No", "visumsponsoring": "No",
    "relocation": "Yes", "willing to relocate": "Yes", "umzug": "Yes", "umziehen": "Yes",
    "commute": "Yes", "work on-site": "Yes", "hybrid": "Yes", "remote": "Yes",
    "pendeln": "Yes", "vor ort": "Yes", "homeoffice": "Yes",
    "background check": "Yes", "drug test": "Yes", "führungszeugnis": "Yes",
    "start immediately": "Yes", "notice period": "2 weeks", "earliest start": "Immediately",
    "availability": "Immediately", "kündigungsfrist": "2 Wochen",
    "verfügbarkeit": "Sofort", "eintrittsdatum": "Sofort", "ab wann": "Sofort",
    "degree": "Yes", "bachelor": "Yes", "education": "Yes",
    "abschluss": "Yes", "ausbildung": "Yes",
}


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
            # Save both latest (for live view) and labeled (for debugging)
            filename = f"{self.user_id}_latest.png"
            path = SCREENSHOT_DIR / filename
            await self._page.screenshot(path=str(path))
            labeled_path = SCREENSHOT_DIR / f"{self.user_id}_{label}_{int(time.time())}.png"
            await self._page.screenshot(path=str(labeled_path))
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
                    scraped_job_ids = await self._scrape_phase_xing(db, job_filter, profile, creds)
                elif platform == "indeed":
                    scraped_job_ids = await self._scrape_phase_indeed(db, job_filter, profile)
                elif platform == "linkedin":
                    scraped_job_ids = await self._scrape_phase_linkedin(db, job_filter, profile)
                else:
                    scraped_job_ids = await self._scrape_phase(db, job_filter, profile)

            # Phase 2: Apply to jobs
            if mode in ("scrape_and_apply", "apply") and self.running:
                if platform == "xing":
                    await self._apply_phase_xing(db, profile, creds, job_filter, scraped_job_ids=scraped_job_ids)
                elif platform == "indeed":
                    await self._apply_phase_indeed(db, profile, creds, job_filter, scraped_job_ids=scraped_job_ids)
                elif platform == "linkedin":
                    await self._apply_phase_linkedin(db, profile, creds, job_filter, scraped_job_ids=scraped_job_ids)
                else:
                    await self._apply_phase(db, profile, creds, job_filter, scraped_job_ids=scraped_job_ids)

        except Exception as e:
            await self.log("error", "system", "crash", {
                "message": f"Bot crashed: {e}",
                "error": str(e),
            })
        finally:
            try:
                if self._browser:
                    await self._browser.close()
            except Exception:
                pass
            self._browser = None
            self._page = None
            if self._db:
                self._db.close()
                self._db = None

            duration = time.time() - start_time
            ext_count = self.stats.get("external", 0)
            summary = f"Session complete: {self.stats['applied']} applied, {self.stats['failed']} failed"
            if ext_count:
                summary += f", {ext_count} external"
            summary += f" in {duration:.0f}s"
            await self.log("info", "system", "session_end", {
                "message": summary,
                "duration_s": duration,
                "stats": self.stats,
            })
            # Log external jobs summary if any were found
            if ext_count and self._db:
                try:
                    ext_apps = self._db.query(Application).filter(
                        Application.user_id == self.user_id,
                        Application.status == "external",
                        Application.applied_at >= datetime.fromtimestamp(start_time, tz=timezone.utc),
                    ).all()
                    if ext_apps:
                        lines = [f"  {a.job_title} at {a.company}" + (f" — {a.notes}" if a.notes else "") for a in ext_apps]
                        await self.log("info", "system", "external_summary", {
                            "message": f"External jobs ({len(ext_apps)}) — apply manually:\n" + "\n".join(lines),
                            "external_jobs": [{"title": a.job_title, "company": a.company, "url": a.url, "employer_url": a.notes} for a in ext_apps],
                        })
                except:
                    pass
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
                                        user_id=self.user_id,
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

    async def _update_stepstone_profile_cv(self, page, cv_path: str):
        """Upload the selected CV to the StepStone profile so Schnellbewerbung uses it."""
        if not cv_path or not os.path.exists(cv_path):
            return
        try:
            await self.log("info", "system", "profile_cv_start", {
                "message": f"  Updating StepStone profile CV to: {os.path.basename(cv_path)}",
            }, platform="stepstone")

            # Navigate to profile documents page
            await page.goto("https://www.stepstone.de/profile/documents", timeout=20000)
            await asyncio.sleep(random.uniform(2, 4))
            await self._dismiss_consent(page)
            await self._dismiss_popups(page)
            await self.screenshot("profile_cv_page")

            current_url = page.url
            # If redirected away from documents, try alternative URLs
            if "documents" not in current_url and "dokument" not in current_url.lower():
                for alt_url in [
                    "https://www.stepstone.de/profile/cv",
                    "https://www.stepstone.de/profile/lebenslauf",
                ]:
                    await page.goto(alt_url, timeout=15000)
                    await asyncio.sleep(2)
                    await self._dismiss_consent(page)
                    if "profile" in page.url:
                        break

            # Look for file input and upload CV
            file_inputs = await page.query_selector_all('input[type="file"]')
            if file_inputs:
                for fi in file_inputs:
                    try:
                        await fi.set_input_files(cv_path)
                        await self.log("info", "system", "profile_cv_uploaded", {
                            "message": f"  Profile CV updated: {os.path.basename(cv_path)}",
                        }, platform="stepstone")
                        await asyncio.sleep(2)
                        # Click save if there's a save button
                        for save_sel in [
                            'button:has-text("Speichern")', 'button:has-text("Save")',
                            'button:has-text("Hochladen")', 'button:has-text("Upload")',
                            'button[type="submit"]',
                        ]:
                            save_btn = await page.query_selector(save_sel)
                            if save_btn and await save_btn.is_visible():
                                await save_btn.click()
                                await asyncio.sleep(2)
                                break
                        await self.screenshot("profile_cv_uploaded")
                        return
                    except Exception as e:
                        await self.log("warn", "system", "profile_cv_upload_err", {
                            "message": f"  File input upload failed: {e}",
                        }, platform="stepstone")

            # Try clicking an upload button/area first to reveal file input
            for upload_sel in [
                'button:has-text("Lebenslauf hochladen")',
                'button:has-text("Upload CV")',
                'button:has-text("Hochladen")',
                'button:has-text("Upload")',
                '[data-testid*="upload"]',
                'a:has-text("Lebenslauf")',
                'button:has-text("Dokument")',
                'button:has-text("hinzufügen")',
                'button:has-text("Add")',
            ]:
                try:
                    btn = await page.query_selector(upload_sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(2)
                        # Check for file input again
                        file_inputs = await page.query_selector_all('input[type="file"]')
                        if file_inputs:
                            await file_inputs[0].set_input_files(cv_path)
                            await self.log("info", "system", "profile_cv_uploaded", {
                                "message": f"  Profile CV updated via button: {os.path.basename(cv_path)}",
                            }, platform="stepstone")
                            await asyncio.sleep(2)
                            await self.screenshot("profile_cv_uploaded")
                            return
                except:
                    continue

            await self.log("warn", "system", "profile_cv_no_input", {
                "message": "  Could not find CV upload on profile page — Schnellbewerbung will use existing profile CV",
                "url": page.url[:100],
            }, platform="stepstone")

        except Exception as e:
            await self.log("warn", "system", "profile_cv_error", {
                "message": f"  Profile CV update failed: {str(e)[:200]} — continuing with existing profile CV",
            }, platform="stepstone")

    async def _apply_phase(self, db: Session, profile: dict, creds: list, job_filter: JobFilter, scraped_job_ids: list[int] = None):
        """Apply to unapplied jobs. If scraped_job_ids provided, only apply to those."""
        await self.log("info", "apply", "phase_start", {"message": "Starting application phase..."})
        await self.emit_status("applying")

        # Only skip jobs that were successfully applied to (or currently applying)
        applied_urls = set(
            r[0] for r in db.query(Application.url).filter(
                Application.user_id == self.user_id,
                Application.status.in_(["success", "applying", "external"]),
            ).all() if r[0]
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

            # CV will be uploaded per-application via "Bewerbung bearbeiten" flow
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

                # Log current URL to detect redirects
                cur_url = self._page.url
                await self.log("info", "browser", "current_url", {
                    "message": f"  URL: {cur_url}",
                    "url": cur_url,
                }, job_id=job.id, platform=job.platform)

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
                    # Dump page HTML around apply area + iframe URLs for diagnosis
                    iframe_info = []
                    for f in self._page.frames:
                        if f == self._page.main_frame:
                            continue
                        try:
                            f_content = await f.evaluate("() => document.body ? document.body.innerText.substring(0, 200) : 'empty'")
                            iframe_info.append(f"{f.url[:60]} | {f_content[:80]}")
                        except:
                            iframe_info.append(f"{f.url[:60]} | [inaccessible]")
                    # Get main page HTML snippet around apply area
                    page_snippet = await self._page.evaluate("""() => {
                        // Look for the job actions area
                        const areas = document.querySelectorAll('[class*="actions"], [class*="apply"], [class*="Action"], [class*="Apply"], [class*="sidebar"], [class*="Sidebar"]');
                        let snippet = '';
                        areas.forEach(a => { snippet += a.outerHTML.substring(0, 300) + '\\n'; });
                        if (!snippet) {
                            // Fallback: get all elements with data-at attributes
                            const dataAts = document.querySelectorAll('[data-at]');
                            dataAts.forEach(e => { snippet += `<${e.tagName} data-at="${e.getAttribute('data-at')}">${e.textContent.substring(0, 50)}\\n`; });
                        }
                        return snippet.substring(0, 800);
                    }""")
                    await self.log("warn", "apply", "no_button", {
                        "message": f"  No apply btn. Iframes: {iframe_info[:4]}",
                    }, job_id=job.id, platform=job.platform)
                    if page_snippet.strip():
                        await self.log("info", "apply", "page_snippet", {
                            "message": f"  Page snippet: {page_snippet[:400]}",
                        }, job_id=job.id, platform=job.platform)
                    application.status = "external"
                    application.error_log = "No apply button found on page or iframes"
                    db.commit()
                    self.stats["external"] = self.stats.get("external", 0) + 1
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
                refind_selectors = [
                    'a:has-text("Jetzt bewerben")', 'button:has-text("Jetzt bewerben")',
                    'a:has-text("Apply now")', 'button:has-text("Apply now")',
                    'button:has-text("Bewerbung fortsetzen")', 'a:has-text("Bewerbung fortsetzen")',
                    'button:has-text("Ich bin interessiert")', 'a:has-text("Ich bin interessiert")',
                    "button:has-text(\"I'm interested\")", "a:has-text(\"I'm interested\")",
                ]
                for sel in refind_selectors:
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

                current_url = self._page.url

                # ── Interest / Schnellbewerbung: wait for summary overlay ──
                if apply_type == "interest":
                    # Don't dismiss popups yet — the summary IS an overlay/dialog
                    await self._dismiss_consent()

                    # Wait for summary overlay to appear (up to 12s)
                    has_summary = False
                    for _sw in range(12):
                        await asyncio.sleep(1)
                        try:
                            page_text = (await self._page.inner_text("body")).lower()
                            if any(kw in page_text for kw in [
                                "zusammenfassung", "bewerbung fortsetzen",
                                "bewerbung bearbeiten", "continue application",
                                "application summary", "edit application",
                                "haupt-lebenslauf", "kontaktdaten",
                            ]):
                                has_summary = True
                                break
                        except:
                            break

                    await self.screenshot("after_apply_click")

                    if has_summary:
                        cv_path = profile.get("cv_path")
                        await self.log("debug", "apply", "schnell_cv_check", {
                            "message": f"  CV path: {cv_path}, exists: {os.path.exists(cv_path) if cv_path else 'N/A'}",
                        }, job_id=job.id, platform=job.platform)

                        # Click "Bewerbung bearbeiten" to edit and upload correct CV
                        if cv_path:
                            edit_btn = None
                            for sel in [
                                'button:has-text("Bewerbung bearbeiten")',
                                'a:has-text("Bewerbung bearbeiten")',
                                'button:has-text("Edit application")',
                                'a:has-text("Edit application")',
                                # Try broader selectors — might be a div or span
                                '[data-testid*="edit"]',
                                'text=Bewerbung bearbeiten',
                            ]:
                                try:
                                    edit_btn = await self._page.query_selector(sel)
                                    if edit_btn and await edit_btn.is_visible():
                                        await self.log("debug", "apply", "edit_btn_found", {
                                            "message": f"  Found edit button with: {sel}",
                                        }, job_id=job.id, platform=job.platform)
                                        break
                                except:
                                    pass
                                edit_btn = None

                            if not edit_btn:
                                # Log what buttons ARE on the page
                                try:
                                    all_btns = await self._page.evaluate("""() => {
                                        return Array.from(document.querySelectorAll('button, a[role="button"], [role="button"]'))
                                            .filter(e => e.offsetParent !== null)
                                            .map(e => e.innerText.trim().substring(0, 60))
                                            .filter(t => t.length > 0);
                                    }""")
                                    await self.log("debug", "apply", "visible_buttons", {
                                        "message": f"  Visible buttons: {all_btns[:10]}",
                                    }, job_id=job.id, platform=job.platform)
                                except:
                                    pass

                            if edit_btn:
                                await self.log("info", "apply", "schnell_edit", {
                                    "message": "  Clicking 'Bewerbung bearbeiten' to upload correct CV...",
                                }, job_id=job.id, platform=job.platform)
                                await edit_btn.scroll_into_view_if_needed()
                                await asyncio.sleep(0.5)
                                await edit_btn.evaluate("el => el.click()")
                                await asyncio.sleep(random.uniform(2, 4))
                                await self.screenshot("schnell_step1")

                                # Step 1/2: Contact details — click "Weiter" (Next)
                                weiter_btn = None
                                for sel in [
                                    'button:has-text("Weiter")',
                                    'button:has-text("Next")',
                                    'button:has-text("Continue")',
                                    'button[type="submit"]',
                                ]:
                                    weiter_btn = await self._page.query_selector(sel)
                                    if weiter_btn and await weiter_btn.is_visible():
                                        break
                                    weiter_btn = None

                                if weiter_btn:
                                    weiter_label = (await weiter_btn.inner_text()).strip()
                                    await self.log("info", "apply", "schnell_step1_next", {
                                        "message": f"  Step 1: Contact details pre-filled — clicking \"{weiter_label}\"",
                                    }, job_id=job.id, platform=job.platform)
                                    await weiter_btn.scroll_into_view_if_needed()
                                    await asyncio.sleep(0.5)
                                    await weiter_btn.evaluate("el => el.click()")
                                    await asyncio.sleep(random.uniform(2, 4))
                                    await self.screenshot("schnell_step2")

                                # Step 2/2: CV upload — upload our CV via file input
                                step2_text = (await self._page.inner_text("body")).lower()
                                if "lebenslauf" in step2_text or "cv" in step2_text or "upload" in step2_text:
                                    # Try to find and use file input
                                    uploaded = False
                                    try:
                                        file_inputs = await self._page.query_selector_all('input[type="file"]')
                                        for fi in file_inputs:
                                            try:
                                                await fi.set_input_files(cv_path)
                                                await self.log("info", "form", "cv_uploaded", {
                                                    "message": f"  Step 2: Uploaded CV: {os.path.basename(cv_path)}",
                                                }, job_id=job.id, platform=job.platform)
                                                uploaded = True
                                                await asyncio.sleep(2)
                                                break
                                            except:
                                                pass
                                    except:
                                        pass

                                    # If no file input visible, try clicking upload area / "..." menu
                                    if not uploaded:
                                        for upload_sel in [
                                            '[aria-label*="upload"]', '[aria-label*="hochladen"]',
                                            'button:has-text("Hochladen")', 'button:has-text("Upload")',
                                            'button:has-text("Ändern")', 'button:has-text("Change")',
                                        ]:
                                            try:
                                                upload_el = await self._page.query_selector(upload_sel)
                                                if upload_el and await upload_el.is_visible():
                                                    await upload_el.click()
                                                    await asyncio.sleep(1)
                                                    file_inputs = await self._page.query_selector_all('input[type="file"]')
                                                    if file_inputs:
                                                        await file_inputs[0].set_input_files(cv_path)
                                                        await self.log("info", "form", "cv_uploaded", {
                                                            "message": f"  Step 2: Uploaded CV via button: {os.path.basename(cv_path)}",
                                                        }, job_id=job.id, platform=job.platform)
                                                        uploaded = True
                                                        await asyncio.sleep(2)
                                                        break
                                            except:
                                                continue

                                    await self.screenshot("schnell_cv_uploaded")

                                # Click "Bewerbung fortsetzen" to submit
                                fortsetzen_btn = None
                                for sel in [
                                    'button:has-text("Bewerbung fortsetzen")',
                                    'a:has-text("Bewerbung fortsetzen")',
                                    'button:has-text("Continue application")',
                                    'button:has-text("Bewerbung abschicken")',
                                    'button:has-text("Submit application")',
                                    'button:has-text("Absenden")',
                                ]:
                                    fortsetzen_btn = await self._page.query_selector(sel)
                                    if fortsetzen_btn and await fortsetzen_btn.is_visible():
                                        break
                                    fortsetzen_btn = None

                                if fortsetzen_btn:
                                    fortsetzen_label = (await fortsetzen_btn.inner_text()).strip()
                                    await self.log("info", "apply", "submitting", {
                                        "message": f"  Clicking \"{fortsetzen_label}\"...",
                                    }, job_id=job.id, platform=job.platform)
                                    await fortsetzen_btn.scroll_into_view_if_needed()
                                    await asyncio.sleep(0.5)
                                    pre_url = self._page.url
                                    await fortsetzen_btn.evaluate("el => el.click()")

                                    for _wait in range(10):
                                        await asyncio.sleep(1)
                                        if self._page.url != pre_url:
                                            break
                                    await asyncio.sleep(random.uniform(1, 2))
                                    await self.screenshot("after_schnell_submit")

                                    # Check success
                                    final_text = ""
                                    try:
                                        final_text = (await self._page.inner_text("body")).lower()
                                    except:
                                        pass
                                    final_url = self._page.url
                                    success = any(kw in final_text for kw in [
                                        "bewerbung abgeschickt", "application sent", "erfolgreich",
                                        "vielen dank", "thank you", "gesendet", "submitted",
                                        "bewerbung wurde", "application has been",
                                    ]) or "success" in final_url or "confirmation" in final_url

                                    # Check for external redirect (company's own form)
                                    is_external = (
                                        "zur verfügung gestellt von stepstone" in final_text
                                        or "brought to you by stepstone" in final_text
                                        or "no listing title" in final_text
                                        or "sie bewerben sich" in final_text and "stepstone" in final_text
                                    )

                                    if not success and not is_external:
                                        # Check if submit button is gone (probable success)
                                        still_has = await self._page.query_selector('button:has-text("Bewerbung fortsetzen")')
                                        if not still_has:
                                            success = True

                                    if is_external:
                                        application.status = "external"
                                        application.error_log = "Redirected to company external form after CV upload"
                                        self.stats["external"] = self.stats.get("external", 0) + 1
                                        apply_duration = time.time() - t0
                                        await self.log("warn", "apply", "external_redirect", {
                                            "message": f"  EXTERNAL — Redirected to company form after CV upload ({apply_duration:.0f}s)",
                                            "url": final_url,
                                            "duration_s": apply_duration,
                                        }, job_id=job.id, platform=job.platform)
                                    elif success:
                                        application.status = "success"
                                        self.stats["applied"] += 1
                                        apply_duration = time.time() - t0
                                        await self.log("info", "apply", "success", {
                                            "message": f"  SUCCESS — Schnellbewerbung with CV in {apply_duration:.0f}s",
                                            "duration_s": apply_duration,
                                        }, job_id=job.id, platform=job.platform)
                                    else:
                                        self.stats["failed"] += 1
                                        application.error_log = "Submit may not have completed"
                                        await self.log("warn", "apply", "submit_uncertain", {
                                            "message": "  Schnellbewerbung submit uncertain",
                                        }, job_id=job.id, platform=job.platform)

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

                        else:
                            # No CV to upload — just click "Bewerbung fortsetzen" directly
                            await self.log("info", "apply", "schnell_summary", {
                                "message": "  Summary shown — clicking 'Bewerbung fortsetzen'...",
                            }, job_id=job.id, platform=job.platform)

                        # Fallback: click "Bewerbung fortsetzen" on summary page directly
                        fortsetzen_btn = None
                        for sel in [
                            'button:has-text("Bewerbung fortsetzen")',
                            'a:has-text("Bewerbung fortsetzen")',
                            'button:has-text("Continue application")',
                            'button:has-text("Bewerbung abschicken")',
                        ]:
                            fortsetzen_btn = await self._page.query_selector(sel)
                            if fortsetzen_btn and await fortsetzen_btn.is_visible():
                                break
                            fortsetzen_btn = None

                        if fortsetzen_btn:
                            btn_label = (await fortsetzen_btn.inner_text()).strip()
                            await self.log("info", "apply", "submitting", {
                                "message": f"  Clicking \"{btn_label}\" (summary page)...",
                            }, job_id=job.id, platform=job.platform)
                            await fortsetzen_btn.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            pre_url = self._page.url
                            await fortsetzen_btn.evaluate("el => el.click()")
                            for _wait in range(10):
                                await asyncio.sleep(1)
                                if self._page.url != pre_url:
                                    break
                            await asyncio.sleep(2)
                            await self.screenshot("after_fortsetzen_direct")

                            # Check if actually submitted vs redirected to external form
                            final_text = ""
                            try:
                                final_text = (await self._page.inner_text("body")).lower()
                            except:
                                pass
                            final_url = self._page.url

                            success = any(kw in final_text for kw in [
                                "bewerbung abgeschickt", "application sent", "erfolgreich",
                                "vielen dank", "thank you", "gesendet", "submitted",
                                "bewerbung wurde", "application has been",
                            ]) or "success" in final_url or "confirmation" in final_url

                            # Check for external redirect (company's own form)
                            is_external = (
                                "brought to you by stepstone" in final_text
                                or "no listing title" in final_text
                                or "apply" in final_url and "external" in final_url
                            )

                            if not success and not is_external:
                                # Check if the continue button is gone (probable success)
                                still_has = await self._page.query_selector('button:has-text("Bewerbung fortsetzen")')
                                summary_still = await self._page.query_selector('button:has-text("Continue application")')
                                if not still_has and not summary_still:
                                    success = True

                            if is_external:
                                application.status = "external"
                                application.error_log = "Redirected to company external form"
                                self.stats["external"] = self.stats.get("external", 0) + 1
                                apply_duration = time.time() - t0
                                await self.log("warn", "apply", "external_redirect", {
                                    "message": f"  EXTERNAL — Redirected to company form, needs manual apply ({apply_duration:.0f}s)",
                                    "url": final_url,
                                    "duration_s": apply_duration,
                                }, job_id=job.id, platform=job.platform)
                            elif success:
                                application.status = "success"
                                self.stats["applied"] += 1
                                apply_duration = time.time() - t0
                                await self.log("info", "apply", "success", {
                                    "message": f"  SUCCESS — Submitted via \"{btn_label}\" ({apply_duration:.0f}s)",
                                    "duration_s": apply_duration,
                                }, job_id=job.id, platform=job.platform)
                            else:
                                application.status = "failed"
                                self.stats["failed"] += 1
                                apply_duration = time.time() - t0
                                application.error_log = "Submit not confirmed after clicking continue"
                                await self.log("warn", "apply", "submit_uncertain", {
                                    "message": f"  UNCERTAIN — Clicked \"{btn_label}\" but no confirmation ({apply_duration:.0f}s)",
                                    "url": final_url,
                                    "duration_s": apply_duration,
                                }, job_id=job.id, platform=job.platform)

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

                    # No summary — check if interest was registered directly
                    interest_confirmed = any(kw in page_text for kw in [
                        "interesse wurde", "interesse bekundet", "interest has been",
                        "interest expressed", "already applied", "bereits beworben",
                    ])
                    if not interest_confirmed:
                        btn_still = None
                        for sel in [
                            'button:has-text("Ich bin interessiert")',
                            "button:has-text(\"I'm interested\")",
                        ]:
                            btn_still = await self._page.query_selector(sel)
                            if btn_still:
                                is_disabled = await btn_still.get_attribute("disabled")
                                aria_disabled = await btn_still.get_attribute("aria-disabled")
                                if is_disabled is not None or aria_disabled == "true":
                                    interest_confirmed = True
                                break
                        if not btn_still:
                            interest_confirmed = True

                    if interest_confirmed:
                        application.status = "success"
                        self.stats["applied"] += 1
                        apply_duration = time.time() - t0
                        await self.log("info", "apply", "success", {
                            "message": f"  SUCCESS — Interest registered (Schnellbewerbung) in {apply_duration:.0f}s",
                            "duration_s": apply_duration,
                        }, job_id=job.id, platform=job.platform)
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

                # ── Non-interest (full apply) path ──
                if apply_type != "interest":
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

                # Recover browser if page/context was closed
                if "has been closed" in str(e) or "Target page" in str(e):
                    await self.log("warn", "system", "browser_recovery", {
                        "message": "  Browser crashed — recreating browser and re-logging in...",
                    }, platform="stepstone")
                    try:
                        try:
                            await browser.close()
                        except:
                            pass
                        try:
                            await pw.stop()
                        except:
                            pass
                        pw = await async_playwright().start()
                        browser = await pw.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled', '--disable-http2'])
                        ctx = await browser.new_context(
                            viewport={"width": 1366, "height": 768},
                            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            locale="de-DE",
                        )
                        self._page = await ctx.new_page()
                        await self._page.add_init_script(STEALTH_JS)
                        if ss_cred:
                            logged_in = await self._login_stepstone(self._page, ss_cred)
                        await self.log("info", "system", "browser_recovered", {
                            "message": "  Browser recovered — continuing applications",
                        }, platform="stepstone")
                    except Exception as recovery_err:
                        await self.log("error", "system", "browser_recovery_failed", {
                            "message": f"  Browser recovery failed: {str(recovery_err)[:200]} — aborting",
                        }, platform="stepstone")
                        break

            # Delay between applications (longer to avoid rate limiting)
            if i < len(jobs) - 1 and self.running:
                delay = random.uniform(20, 35)
                await self.log("info", "system", "delay", {
                    "message": f"  Waiting {delay:.0f}s before next application...",
                    "delay_s": delay,
                })
                await asyncio.sleep(delay)

        try:
            await browser.close()
        except:
            pass
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

    async def _scrape_phase_xing(self, db: Session, job_filter: JobFilter, profile: dict, creds: list = None) -> list[int]:
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

        # Log in once — Xing shows far more results when authenticated
        xing_cred = next((c for c in (creds or []) if c.platform == "xing" and c.is_active), None)
        logged_in = False

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

                # Login for first query (reuses browser session for subsequent queries)
                if xing_cred and not logged_in:
                    logged_in = await self._login_xing(self._page, xing_cred)
                    if logged_in:
                        await self.log("info", "scrape", "login_ok", {
                            "message": f"Logged into Xing for scraping",
                        }, platform="xing")
                    await asyncio.sleep(random.uniform(2, 4))

                new_for_query = 0
                for page_num in range(1, max_pages + 1):
                    if not self.running:
                        break

                    url = f"https://www.xing.com/jobs/search?keywords={q_enc}&location={l_enc}&radius=30"
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
                                        user_id=self.user_id,
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

                        if new_in_page == 0:
                            # No new jobs on this page — stop paginating
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

    async def _xing_easy_apply(self, page, profile: dict, job, creds: list) -> tuple[bool, str]:
        """Handle Xing Easy Apply 4-step wizard. Returns (success, error_msg)."""
        # Get email from Xing credentials
        xing_cred = next((c for c in (creds or []) if c.platform == "xing" and c.is_active), None)
        email = xing_cred.email if xing_cred else profile.get("email", "")
        first_name = profile.get("first_name", "")
        last_name = profile.get("last_name", "")
        phone = profile.get("phone", "")
        cv_path = profile.get("cv_path", "")

        # Strip country code from phone — Xing has a separate country code dropdown
        if phone.startswith("+49"):
            phone = phone[3:]
        elif phone.startswith("0049"):
            phone = phone[4:]
        if phone.startswith("0"):
            phone = phone[1:]

        for step in range(8):
            await asyncio.sleep(random.uniform(1.5, 3))
            try:
                page_text = (await page.inner_text("body")).lower()
            except:
                return (False, "Page closed unexpectedly")

            await self.screenshot(f"xing_ea_step{step}")

            # ── Check for success ──
            success_kw = ["bewerbung wurde gesendet", "bewerbung abgeschickt",
                          "erfolgreich gesendet", "application sent", "application submitted",
                          "vielen dank", "thank you for your application",
                          "wir haben ihre bewerbung erhalten", "we have received"]
            if any(kw in page_text for kw in success_kw):
                return (True, "")

            # ── 1-click apply: "Send application" / "Apply with CV" ──
            # When logged in, Xing pre-fills profile data — just click Send
            for sel in ['button:has-text("Send application")', 'button:has-text("Bewerbung senden")',
                        'button:has-text("Bewerbung abschicken")', 'button:has-text("Apply")',
                        'button:has-text("Bewerben")']:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    btn_text = (await btn.inner_text()).strip()
                    # Only click actual submit buttons, not "Easy apply" or "Edit" links
                    if any(kw in btn_text.lower() for kw in ["send", "senden", "abschicken", "apply", "bewerben"]) \
                       and "edit" not in btn_text.lower() and "easy" not in btn_text.lower():
                        await self.log("info", "apply", "xing_ea_1click", {
                            "message": f"  Step {step+1}: Clicking \"{btn_text}\" (1-click apply)",
                        }, job_id=job.id, platform="xing")
                        await btn.click()
                        await asyncio.sleep(3)
                        # Check confirmation
                        try:
                            confirm = (await page.inner_text("body")).lower()
                            if any(kw in confirm for kw in success_kw):
                                await self.screenshot("xing_ea_success")
                                return (True, "")
                            # Button might have submitted and page changed
                            still_has_send = await page.query_selector(sel)
                            if not still_has_send or not await still_has_send.is_visible():
                                await self.screenshot("xing_ea_success")
                                return (True, "")
                        except:
                            return (True, "")
                    break

            # ── Detect which step we're on and fill fields ──

            # Step: Email
            if "e-mail" in page_text and ("contact" in page_text or "add an" in page_text or "e-mail-adresse" in page_text or "kontakt" in page_text):
                filled = await page.evaluate(f"""(email) => {{
                    let filled = 0;
                    const inputs = document.querySelectorAll('input');
                    for (const inp of inputs) {{
                        const ph = (inp.placeholder || '').toLowerCase();
                        const t = (inp.type || '').toLowerCase();
                        const label = (inp.getAttribute('aria-label') || '').toLowerCase();
                        if (t === 'email' || ph.includes('mail') || label.includes('mail')) {{
                            inp.focus();
                            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                            nativeInputValueSetter.call(inp, email);
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            filled++;
                        }}
                    }}
                    return filled;
                }}""", email)
                await self.log("info", "apply", "xing_ea_email", {
                    "message": f"  Step {step+1}: Filled email ({filled} fields)",
                }, job_id=job.id, platform="xing")

            # Step: Name + Phone
            elif "name" in page_text and ("phone" in page_text or "telefon" in page_text or "first" in page_text or "vorname" in page_text):
                filled = await page.evaluate(f"""(data) => {{
                    let filled = 0;
                    const inputs = document.querySelectorAll('input');
                    for (const inp of inputs) {{
                        const ph = (inp.placeholder || '').toLowerCase();
                        const label = (inp.getAttribute('aria-label') || '').toLowerCase();
                        const name = (inp.name || '').toLowerCase();
                        const hint = ph + ' ' + label + ' ' + name;
                        let value = '';
                        if (hint.includes('first') || hint.includes('vorname')) value = data.first_name;
                        else if (hint.includes('last') || hint.includes('nachname') || hint.includes('family')) value = data.last_name;
                        else if (hint.includes('phone') || hint.includes('telefon') || hint.includes('mobil')) value = data.phone;
                        if (value) {{
                            inp.focus();
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                            setter.call(inp, value);
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            filled++;
                        }}
                    }}
                    return filled;
                }}""", {"first_name": first_name, "last_name": last_name, "phone": phone})
                await self.log("info", "apply", "xing_ea_name", {
                    "message": f"  Step {step+1}: Filled name+phone ({filled} fields)",
                }, job_id=job.id, platform="xing")

            # Step: Document upload
            elif "document" in page_text or "dokument" in page_text or "upload" in page_text or "lebenslauf" in page_text or "cv" in page_text:
                uploaded = False
                if cv_path and os.path.exists(cv_path):
                    # Try direct file input first
                    file_inputs = await page.query_selector_all('input[type="file"]')
                    if file_inputs:
                        try:
                            await file_inputs[0].set_input_files(cv_path)
                            uploaded = True
                        except:
                            pass

                    # If no file input, click "Upload CV" button to reveal it
                    if not uploaded:
                        for sel in ['button:has-text("Upload CV")', 'button:has-text("Upload")',
                                    'button:has-text("Hochladen")', 'button:has-text("Lebenslauf hochladen")',
                                    'a:has-text("Upload CV")', '[data-testid*="upload"]']:
                            btn = await page.query_selector(sel)
                            if btn and await btn.is_visible():
                                await btn.click()
                                await asyncio.sleep(2)
                                file_inputs = await page.query_selector_all('input[type="file"]')
                                if file_inputs:
                                    try:
                                        await file_inputs[0].set_input_files(cv_path)
                                        uploaded = True
                                    except:
                                        pass
                                break

                    if not uploaded:
                        # Last resort: find ANY file input (even hidden)
                        try:
                            await page.evaluate("""() => {
                                document.querySelectorAll('input[type="file"]').forEach(i => {
                                    i.style.display = 'block';
                                    i.style.opacity = '1';
                                });
                            }""")
                            await asyncio.sleep(0.5)
                            file_inputs = await page.query_selector_all('input[type="file"]')
                            if file_inputs:
                                await file_inputs[0].set_input_files(cv_path)
                                uploaded = True
                        except:
                            pass

                await self.log("info", "apply", "xing_ea_cv", {
                    "message": f"  Step {step+1}: CV upload {'OK' if uploaded else 'FAILED'} ({os.path.basename(cv_path) if cv_path else 'no CV'})",
                }, job_id=job.id, platform="xing")

            # Step: Review — fill optional message, then click Apply
            elif "review" in page_text or "überprüf" in page_text or "prüfen" in page_text:
                # Optional: fill message textarea
                try:
                    ta = await page.query_selector('textarea')
                    if ta and await ta.is_visible():
                        # Leave empty — user can configure a message template later
                        pass
                except:
                    pass

                await self.log("info", "apply", "xing_ea_review", {
                    "message": f"  Step {step+1}: Review page — clicking Apply",
                }, job_id=job.id, platform="xing")

                # Click the final Apply button
                for sel in ['button:has-text("Apply")', 'button:has-text("Bewerben")',
                            'button:has-text("Bewerbung absenden")', 'button:has-text("Jetzt bewerben")',
                            'button:has-text("Send application")', 'button:has-text("Bewerbung abschicken")']:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(3)
                        # Check for confirmation
                        try:
                            confirm_text = (await page.inner_text("body")).lower()
                            if any(kw in confirm_text for kw in success_kw):
                                await self.screenshot("xing_ea_success")
                                return (True, "")
                        except:
                            # Page might have navigated — could be success
                            return (True, "")
                        break

                # If we got here, Apply button might not have been found
                await self.screenshot("xing_ea_review_stuck")

            # ── Click Continue/Next/Review button to advance ──
            clicked_next = False
            for sel in ['button:has-text("Continue")', 'button:has-text("Weiter")',
                        'button:has-text("Next")', 'button:has-text("Review your application")',
                        'button:has-text("Bewerbung überprüfen")', 'button:has-text("Fortfahren")']:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    try:
                        btn_text = (await btn.inner_text()).strip()
                        await btn.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await btn.click()
                        clicked_next = True
                        await self.log("info", "apply", "xing_ea_next", {
                            "message": f"  Step {step+1}: Clicking \"{btn_text}\"",
                        }, job_id=job.id, platform="xing")
                    except:
                        pass
                    break

            if not clicked_next:
                # No button found — might be stuck or done
                await self.log("warn", "apply", "xing_ea_stuck", {
                    "message": f"  Step {step+1}: No next/continue button found",
                }, job_id=job.id, platform="xing")
                # One final success check
                try:
                    final_text = (await page.inner_text("body")).lower()
                    if any(kw in final_text for kw in success_kw):
                        return (True, "")
                except:
                    pass
                return (False, f"Stuck at step {step+1} — no button to advance")

        return (False, "Exceeded maximum steps (8)")

    async def _apply_phase_xing(self, db: Session, profile: dict, creds: list, job_filter: JobFilter, scraped_job_ids: list[int] = None):
        """Apply to Xing jobs."""
        await self.log("info", "apply", "phase_start", {"message": "Starting Xing application phase..."})
        await self.emit_status("applying")

        # Only skip jobs that were successfully applied to (or currently applying)
        # External/failed/skipped jobs can be retried
        applied_urls = set(
            r[0] for r in db.query(Application.url).filter(
                Application.user_id == self.user_id,
                Application.status.in_(["success", "applying", "external"]),
            ).all() if r[0]
        )

        if scraped_job_ids:
            query = db.query(Job).filter(Job.id.in_(scraped_job_ids))
        else:
            query = db.query(Job).filter(Job.platform == "xing")

        if applied_urls:
            query = query.filter(~Job.url.in_(applied_urls))

        # Title relevance filtering — skip if jobs came from this session's scrape
        # (Xing search already filtered by keyword, double-filtering is too aggressive)
        search_queries = job_filter.job_titles if job_filter and job_filter.job_titles else []
        max_apps = min(max(int(job_filter.max_applications or 10) if job_filter and hasattr(job_filter, 'max_applications') else 10, 1), 500)
        all_candidates = query.order_by(Job.scraped_at.desc()).limit(max_apps * 5).all()
        if search_queries and not scraped_job_ids:
            # Only filter by title when re-processing old jobs (no fresh scrape)
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
                    # Try to extract the employer apply URL
                    ext_url = ""
                    try:
                        for l in all_link_texts:
                            if any(kw in l["text"] for kw in ["arbeitgeberseite", "employer website", "visit employer"]):
                                if l.get("href") and l["href"] != "":
                                    ext_url = l["href"]
                                    break
                    except:
                        pass
                    await self.log("info", "apply", "external_only", {
                        "message": f"  External-only job — saved to external list" + (f" ({ext_url[:60]})" if ext_url else ""),
                    }, job_id=job.id, platform="xing")
                    application.status = "external"
                    application.error_log = f"External apply only — no Xing Easy Apply" + (f"\nEmployer URL: {ext_url}" if ext_url else "")
                    if ext_url:
                        application.notes = ext_url
                    db.commit()
                    self.stats["external"] = self.stats.get("external", 0) + 1
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
                    await self.log("info", "apply", "external_only", {
                        "message": f"  No Xing apply button — saved to external list",
                    }, job_id=job.id, platform="xing")
                    application.status = "external"
                    application.error_log = "No apply button (may be external apply)"
                    db.commit()
                    self.stats["external"] = self.stats.get("external", 0) + 1
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
                    await self.log("info", "apply", "external_only", {
                        "message": f"  External redirect — saved to external list ({target_url[:80]})",
                    }, job_id=job.id, platform="xing")
                    application.status = "external"
                    application.error_log = f"External apply: {target_url[:200]}"
                    application.notes = target_page.url
                    db.commit()
                    self.stats["external"] = self.stats.get("external", 0) + 1
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

                # Xing Easy Apply wizard — dedicated step-by-step handler
                ea_success, ea_error = await self._xing_easy_apply(target_page, profile, job, creds)
                if ea_success:
                    application.status = "success"
                    self.stats["applied"] += 1
                    await self.log("info", "apply", "success", {
                        "message": f"  SUCCESS — Xing application submitted ({time.time()-t0:.0f}s)",
                    }, job_id=job.id, platform="xing")
                else:
                    application.status = "failed"
                    application.error_log = ea_error or "Could not complete Xing Easy Apply"
                    self.stats["failed"] += 1
                    await self.log("warn", "apply", "form_incomplete", {
                        "message": f"  FAILED — {ea_error}",
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

    @staticmethod
    def _fetch_indeed_code_from_gmail(email: str, app_password: str, timeout_s: int = 90, sender: str = "indeed") -> str | None:
        """Poll Gmail via IMAP for the latest verification code from a sender."""
        import imaplib
        import email as email_lib
        from email.header import decode_header

        deadline = time.time() + timeout_s
        seen_ids: set[str] = set()

        while time.time() < deadline and self.running:
            try:
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(email, app_password)
                mail.select("INBOX")

                # Search for recent emails from sender
                _, msg_ids = mail.search(None, f'(FROM "{sender}" UNSEEN)')
                if not msg_ids or not msg_ids[0]:
                    _, msg_ids = mail.search(None, f'(FROM "{sender}")')

                ids = msg_ids[0].split() if msg_ids[0] else []
                # Check newest first
                for mid in reversed(ids[-10:]):
                    mid_str = mid.decode()
                    if mid_str in seen_ids:
                        continue
                    seen_ids.add(mid_str)

                    _, data = mail.fetch(mid, "(RFC822)")
                    raw = data[0][1]
                    msg = email_lib.message_from_bytes(raw)

                    # Get body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ct = part.get_content_type()
                            if ct == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="replace")
                                break
                            elif ct == "text/html":
                                body = part.get_payload(decode=True).decode(errors="replace")
                    else:
                        body = msg.get_payload(decode=True).decode(errors="replace")

                    # Extract code — Indeed sends 6-8 digit codes
                    import re as _re
                    # Look for standalone 6-8 digit number (the code)
                    code_match = _re.search(r'\b(\d{6,8})\b', body)
                    if code_match:
                        mail.logout()
                        return code_match.group(1)

                mail.logout()
            except Exception:
                pass

            time.sleep(5)

        return None

    async def _login_indeed(self, page, cred) -> bool:
        """Log into Indeed — handles password, Google OAuth, and code-based login."""
        await self.log("info", "apply", "login_start", {
            "message": f"Logging into Indeed as {cred.email}...",
        }, platform="indeed")

        try:
            await page.goto("https://secure.indeed.com/account/login?hl=de_DE", timeout=45000)
            await asyncio.sleep(random.uniform(3, 5))

            # Wait for Cloudflare / Turnstile challenge
            for _cf in range(20):  # up to ~60s
                title = await page.title()
                body_text = (await page.inner_text("body")).lower()
                has_cf = (
                    "just a moment" in title.lower()
                    or "verifizierung" in body_text
                    or "checking" in body_text
                    or "verify you are human" in body_text
                    or "bestätigen sie" in body_text
                )
                if not has_cf:
                    break
                # Try clicking Turnstile widget — click the iframe element itself
                clicked = False
                for sel in [
                    'iframe[src*="challenges.cloudflare.com"]',
                    '.cf-turnstile iframe',
                    'iframe[title*="Cloudflare"]',
                    'iframe[title*="Widget"]',
                ]:
                    cf_el = await page.query_selector(sel)
                    if cf_el:
                        try:
                            bbox = await cf_el.bounding_box()
                            if bbox:
                                # Click center of the checkbox area (left side of iframe)
                                await page.mouse.click(
                                    bbox["x"] + 28,
                                    bbox["y"] + bbox["height"] / 2,
                                )
                                clicked = True
                                await self.log("info", "apply", "cf_click", {
                                    "message": "  Clicked Cloudflare Turnstile widget",
                                }, platform="indeed")
                        except Exception:
                            pass
                        break
                if not clicked:
                    # Also try frame-internal click
                    for sel in ['iframe[src*="challenges"]', 'iframe[src*="turnstile"]']:
                        cf_el = await page.query_selector(sel)
                        if cf_el:
                            try:
                                frame = await cf_el.content_frame()
                                if frame:
                                    cb = await frame.query_selector('#challenge-stage input, label, .cb-i, .ctp-checkbox-container')
                                    if cb:
                                        await cb.click()
                                        clicked = True
                            except Exception:
                                pass
                            break
                await asyncio.sleep(3)

            await self._dismiss_indeed_cookies(page)
            await self.screenshot("indeed_login_01")

            # Indeed login: email first
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

            # Check what login method Indeed offers
            page_text = (await page.inner_text("body")).lower()

            # Path A: Password field available
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

            # Path B: Code-based login ("Stattdessen mit Code anmelden")
            elif "code" in page_text or "mit code" in page_text or "stattdessen" in page_text:
                await self.log("info", "apply", "login_code_flow", {
                    "message": "  Indeed requires code-based login — initiating...",
                }, platform="indeed")

                # Check if Gmail IMAP is configured
                gmail_email = settings.GMAIL_EMAIL
                gmail_app_pw = settings.GMAIL_APP_PASSWORD
                if not gmail_email or not gmail_app_pw:
                    await self.log("error", "apply", "login_no_gmail", {
                        "message": "  Code login requires GMAIL_EMAIL + GMAIL_APP_PASSWORD in .env",
                    }, platform="indeed")
                    return False

                # Click "Stattdessen mit Code anmelden" / "Sign in with code"
                code_link = (
                    await page.query_selector('a:has-text("Code")') or
                    await page.query_selector('a:has-text("code")') or
                    await page.query_selector('a:has-text("Stattdessen")')
                )
                if code_link:
                    await code_link.click()
                    await asyncio.sleep(random.uniform(2, 4))
                    await self.screenshot("indeed_login_code_page")

                # Enter email again if needed
                code_email_input = await page.query_selector('input[type="email"]')
                if code_email_input:
                    await code_email_input.fill("")
                    await code_email_input.type(cred.email, delay=random.randint(30, 70))
                    await asyncio.sleep(0.5)

                # Click send code / continue
                send_btn = (
                    await page.query_selector('button[type="submit"]') or
                    await page.query_selector('button:has-text("Send")') or
                    await page.query_selector('button:has-text("Senden")') or
                    await page.query_selector('button:has-text("Continue")') or
                    await page.query_selector('button:has-text("Weiter")')
                )
                if send_btn and await send_btn.is_visible():
                    await send_btn.click()
                    await self.log("info", "apply", "login_code_sent", {
                        "message": "  Code requested — checking Gmail...",
                    }, platform="indeed")
                    await asyncio.sleep(5)
                else:
                    await self.log("warn", "apply", "login_no_send_btn", {
                        "message": "  No send button found for code flow",
                    }, platform="indeed")
                    return False

                await self.screenshot("indeed_login_waiting_code")

                # Poll Gmail for the verification code
                code = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._fetch_indeed_code_from_gmail,
                    gmail_email, gmail_app_pw, 90
                )

                if not code:
                    await self.log("error", "apply", "login_no_code", {
                        "message": "  No verification code found in Gmail after 90s",
                    }, platform="indeed")
                    return False

                await self.log("info", "apply", "login_code_found", {
                    "message": f"  Got verification code: {code}",
                }, platform="indeed")

                # Enter the code
                code_input = (
                    await page.query_selector('input[type="text"]') or
                    await page.query_selector('input[type="number"]') or
                    await page.query_selector('input[name="otp"]') or
                    await page.query_selector('input[inputmode="numeric"]')
                )
                if code_input:
                    await code_input.click()
                    await asyncio.sleep(0.3)
                    await code_input.type(code, delay=random.randint(50, 100))
                    await asyncio.sleep(0.5)

                    # Submit code
                    submit_btn = (
                        await page.query_selector('button[type="submit"]') or
                        await page.query_selector('button:has-text("Verify")') or
                        await page.query_selector('button:has-text("Bestätigen")') or
                        await page.query_selector('button:has-text("Continue")') or
                        await page.query_selector('button:has-text("Weiter")')
                    )
                    if submit_btn and await submit_btn.is_visible():
                        await submit_btn.click()
                    else:
                        await code_input.press("Enter")

                    await asyncio.sleep(random.uniform(4, 6))
                else:
                    await self.log("error", "apply", "login_no_code_input", {
                        "message": "  No code input field found",
                    }, platform="indeed")
                    return False

            # Path C: Google OAuth only — cannot automate
            elif "google" in page_text and "weiter mit google" in page_text:
                # Try clicking code link first (might be below Google button)
                code_link = (
                    await page.query_selector('a:has-text("Code")') or
                    await page.query_selector('a:has-text("code")') or
                    await page.query_selector('a:has-text("Stattdessen")')
                )
                if code_link:
                    await self.log("info", "apply", "login_switch_to_code", {
                        "message": "  Google OAuth page — switching to code login...",
                    }, platform="indeed")
                    await code_link.click()
                    await asyncio.sleep(random.uniform(2, 4))
                    # Recurse with the new page state
                    return await self._login_indeed(page, cred)
                else:
                    await self.log("error", "apply", "login_google_only", {
                        "message": "  Indeed only offers Google OAuth — cannot automate",
                    }, platform="indeed")
                    return False

            else:
                await self.log("warn", "apply", "login_unknown_flow", {
                    "message": "  Unknown login flow — no password or code option found",
                }, platform="indeed")
                await self.screenshot("indeed_login_unknown")
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

                # Retry with fresh IP if Cloudflare blocks page 1
                _cf_retries = 0
                _max_cf_retries = 3
                browser = ctx = None

                while _cf_retries <= _max_cf_retries and self.running:
                    browser, ctx, self._page = await self._launch_stealth_browser(pw, "indeed")
                    # Quick test: load page 1 and check for Cloudflare block
                    _test_url = f"https://de.indeed.com/jobs?q={q_enc}&l={l_enc}"
                    try:
                        await self._page.goto(_test_url, timeout=45000, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(5, 8))
                        _test_body = (await self._page.inner_text("body"))[:500].lower()
                        if any(kw in _test_body for kw in ["verifizierung", "bestätigen sie", "verify"]):
                            _cf_retries += 1
                            await self.log("warn", "scrape", "cf_blocked", {
                                "message": f"  Cloudflare blocked — rotating IP (attempt {_cf_retries}/{_max_cf_retries})",
                            }, platform="indeed")
                            await browser.close()
                            browser = ctx = None
                            if _cf_retries > _max_cf_retries:
                                break
                            await asyncio.sleep(2)
                            continue
                        else:
                            break  # Good IP, proceed
                    except Exception:
                        _cf_retries += 1
                        try:
                            await browser.close()
                        except:
                            pass
                        browser = ctx = None
                        if _cf_retries > _max_cf_retries:
                            break
                        continue

                if not browser:
                    await self.log("error", "scrape", "cf_all_blocked", {
                        "message": f"  All {_max_cf_retries} proxy IPs blocked by Cloudflare — skipping Indeed scrape",
                    }, platform="indeed")
                    continue

                new_for_query = 0
                for page_num in range(1, max_pages + 1):
                    if not self.running:
                        break

                    # Indeed pagination: start=0, 10, 20, ...
                    url = f"https://de.indeed.com/jobs?q={q_enc}&l={l_enc}"
                    if page_num > 1:
                        url += f"&start={(page_num - 1) * 10}"

                    try:
                        if page_num > 1:  # Page 1 already loaded during CF retry loop
                            await self._page.goto(url, timeout=45000, wait_until="domcontentloaded")
                            await asyncio.sleep(random.uniform(5, 8))
                        # Wait for Cloudflare / Turnstile challenge
                        for _cf_wait in range(20):
                            title = await self._page.title()
                            body_text = (await self._page.inner_text("body")).lower()
                            has_cf = (
                                "just a moment" in title.lower()
                                or "verifizierung" in body_text
                                or "checking" in body_text
                                or "verify you are human" in body_text
                                or "bestätigen sie" in body_text
                            )
                            if not has_cf:
                                break
                            for sel in [
                                'iframe[src*="challenges.cloudflare.com"]',
                                '.cf-turnstile iframe',
                                'iframe[title*="Cloudflare"]',
                                'iframe[title*="Widget"]',
                            ]:
                                cf_el = await self._page.query_selector(sel)
                                if cf_el:
                                    try:
                                        bbox = await cf_el.bounding_box()
                                        if bbox:
                                            await self._page.mouse.click(
                                                bbox["x"] + 28,
                                                bbox["y"] + bbox["height"] / 2,
                                            )
                                    except Exception:
                                        pass
                                    break
                            await asyncio.sleep(3)
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
                                        user_id=self.user_id,
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
            r[0] for r in db.query(Application.url).filter(
                Application.user_id == self.user_id,
                Application.status.in_(["success", "applying", "external"]),
            ).all() if r[0]
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

        # Launch browser + login (retry with fresh IP if Cloudflare blocks)
        pw = await async_playwright().start()

        indeed_cred = next((c for c in creds if c.platform == "indeed" and c.is_active), None)
        if not indeed_cred:
            await self.log("error", "apply", "no_credentials", {
                "message": "No Indeed credentials found — add them in Profile page.",
            }, platform="indeed")
            await pw.stop()
            return

        logged_in = False
        browser = ctx = None
        for _login_try in range(3):
            browser, ctx, self._page = await self._launch_stealth_browser(pw, "indeed")
            logged_in = await self._login_indeed(self._page, indeed_cred)
            if logged_in:
                break
            await self.log("warn", "apply", "login_retry", {
                "message": f"  Login failed — rotating IP (attempt {_login_try + 1}/3)",
            }, platform="indeed")
            try:
                await browser.close()
            except:
                pass
            browser = ctx = None
            await asyncio.sleep(2)
        if not logged_in:
            await self.log("error", "apply", "login_required", {
                "message": "INDEED LOGIN FAILED after 3 IP rotations — Aborting apply phase.",
            }, platform="indeed")
            if browser:
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
                await self._page.goto(job.url, timeout=45000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(3, 5))

                # Wait for Cloudflare / Turnstile on job page
                for _cf_job in range(12):
                    title = await self._page.title()
                    body_snip = (await self._page.inner_text("body"))[:500].lower()
                    if not any(kw in body_snip for kw in ["verifizierung", "checking", "verify", "bestätigen sie"]) \
                       and "just a moment" not in title.lower():
                        break
                    for sel in [
                        'iframe[src*="challenges.cloudflare.com"]',
                        '.cf-turnstile iframe',
                        'iframe[title*="Cloudflare"]',
                        'iframe[title*="Widget"]',
                    ]:
                        cf_el = await self._page.query_selector(sel)
                        if cf_el:
                            try:
                                bbox = await cf_el.bounding_box()
                                if bbox:
                                    await self._page.mouse.click(bbox["x"] + 28, bbox["y"] + bbox["height"] / 2)
                            except Exception:
                                pass
                            break
                    await asyncio.sleep(3)

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
                    await self.log("info", "apply", "external_only", {
                        "message": f"  No Indeed apply button — saved to external list",
                    }, job_id=job.id, platform="indeed")
                    application.status = "external"
                    application.error_log = "No apply button found"
                    db.commit()
                    self.stats["external"] = self.stats.get("external", 0) + 1
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
                    await self.log("info", "apply", "external_only", {
                        "message": f"  External redirect — saved to external list ({target_url[:80]})",
                    }, job_id=job.id, platform="indeed")
                    application.status = "external"
                    application.error_log = f"External apply: {target_url[:200]}"
                    application.notes = target_page.url
                    db.commit()
                    self.stats["external"] = self.stats.get("external", 0) + 1
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

                    # Upload CV if file input present
                    cv_path = profile.get("cv_path", "")
                    if cv_path and os.path.exists(cv_path):
                        try:
                            file_inputs = await target_page.query_selector_all('input[type="file"]')
                            for fi in file_inputs:
                                await fi.set_input_files(cv_path)
                                await self.log("info", "form", "cv_uploaded", {
                                    "message": f"  Uploaded CV: {os.path.basename(cv_path)}",
                                }, job_id=job.id, platform="indeed")
                                await asyncio.sleep(1)
                        except Exception as e:
                            await self.log("debug", "form", "cv_upload_err", {
                                "message": f"  CV upload error: {e}",
                            }, job_id=job.id, platform="indeed")

                    # Wait for Turnstile on form page (Indeed embeds it in apply forms)
                    for _cf_form in range(10):
                        try:
                            cf_el = await target_page.query_selector('iframe[src*="challenges.cloudflare.com"], .cf-turnstile iframe, iframe[title*="Cloudflare"], iframe[title*="Widget"]')
                            if not cf_el:
                                break
                            # Check if turnstile resolved (checkbox checked or widget hidden)
                            bbox = await cf_el.bounding_box()
                            if not bbox or bbox["height"] < 5:
                                break  # Hidden/resolved
                            # Try clicking the turnstile checkbox
                            try:
                                await target_page.mouse.click(bbox["x"] + 28, bbox["y"] + bbox["height"] / 2)
                            except:
                                pass
                            await asyncio.sleep(3)
                        except:
                            break

                    # Log page state for debugging
                    try:
                        _dbg_url = target_page.url
                        _dbg_buttons = await target_page.evaluate("""() => {
                            const btns = document.querySelectorAll('button, a[role="button"], input[type="submit"]');
                            return Array.from(btns).filter(b => b.offsetParent !== null).map(b => b.innerText.trim()).filter(t => t.length > 0 && t.length < 60);
                        }""")
                        _dbg_inputs = await target_page.evaluate("""() => {
                            const els = document.querySelectorAll('input:not([type=hidden]), select, textarea');
                            return Array.from(els).filter(e => e.offsetParent !== null).map(e => {
                                const label = e.labels?.[0]?.innerText || e.placeholder || e.name || e.type;
                                return `${e.tagName.toLowerCase()}[${e.type||''}]: ${label}`;
                            });
                        }""")
                        await self.log("info", "apply", "page_state", {
                            "message": f"  Page: {_dbg_url[:80]} | Inputs: {_dbg_inputs[:5]} | Buttons: {_dbg_buttons[:8]}",
                        }, job_id=job.id, platform="indeed")
                    except:
                        pass

                    # Take screenshot at each form step
                    orig_page = self._page
                    self._page = target_page
                    await self.screenshot(f"indeed_form_step_{step+1}")
                    self._page = orig_page

                    # Click continue/submit/next (skip Google/OAuth buttons)
                    clicked = False
                    _skip_keywords = {"google", "facebook", "apple", "oauth", "mit google", "mit facebook", "mit apple"}
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
                        'a:has-text("Weiter")',
                    ]:
                        btn = await target_page.query_selector(sel)
                        if btn and await btn.is_visible():
                            try:
                                step_text = (await btn.inner_text()).strip()
                                # Skip OAuth / social login buttons
                                if any(kw in step_text.lower() for kw in _skip_keywords):
                                    continue
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

    # ── LinkedIn helpers ──────────────────────────────────────────────

    async def _launch_stealth_browser(self, pw, platform: str = "linkedin"):
        """Launch browser with anti-detection + optional residential proxy."""
        import re as _re
        proxy_url = settings.PROXY_URL
        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-http2',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-infobars',
            '--disable-dev-shm-usage',
        ]

        launch_kwargs: dict = {"headless": True, "args": launch_args}
        # Only use proxy for Indeed (LinkedIn doesn't need it)
        if proxy_url and platform in ("indeed",):
            # Auto-rotate: replace sessionid-XXX with a fresh random value for a new IP
            new_sid = ''.join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=16))
            proxy_url = _re.sub(r'sessionid-[^-]+', f'sessionid-{new_sid}', proxy_url)

            # Parse http://user:pass@host:port into separate fields for Playwright
            from urllib.parse import urlparse
            parsed = urlparse(proxy_url)
            proxy_cfg: dict = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
            if parsed.username:
                proxy_cfg["username"] = parsed.username
            if parsed.password:
                proxy_cfg["password"] = parsed.password
            launch_kwargs["proxy"] = proxy_cfg
            await self.log("info", "system", "proxy", {
                "message": f"Using residential proxy: {parsed.hostname}:{parsed.port} (session: {new_sid[:6]}...)",
            }, platform=platform)

        browser = await pw.chromium.launch(**launch_kwargs)

        ua = random.choice(_UA_POOL)
        ctx = await browser.new_context(
            viewport={"width": random.choice([1366, 1440, 1920]), "height": random.choice([768, 900, 1080])},
            user_agent=ua,
            locale=random.choice(["de-DE", "de-AT", "en-US"]),
            timezone_id=random.choice(["Europe/Berlin", "Europe/Vienna", "Europe/Zurich"]),
            extra_http_headers={
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
                "sec-ch-ua-platform": '"Windows"' if "Windows" in ua else '"macOS"' if "Macintosh" in ua else '"Linux"',
            },
        )
        page = await ctx.new_page()
        # Inject stealth JS before any navigation
        await page.add_init_script(_STEALTH_SCRIPT_FULL)
        return browser, ctx, page

    async def _login_linkedin(self, page, cred) -> bool:
        """Log into LinkedIn."""
        await self.log("info", "apply", "login_start", {
            "message": f"Logging into LinkedIn as {cred.email}...",
        }, platform="linkedin")

        for attempt in range(3):
            try:
                await page.goto("https://www.linkedin.com/login", timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(2, 4))

                # Already logged in?
                if any(x in page.url for x in ["/feed", "/jobs", "/mynetwork", "/messaging"]):
                    await self.log("info", "apply", "already_logged_in", {"message": "  Already logged in!"}, platform="linkedin")
                    return True

                # Fill email
                email_input = await page.query_selector("#username")
                if email_input:
                    await email_input.click()
                    await asyncio.sleep(0.3)
                    await email_input.fill("")
                    await email_input.type(cred.email, delay=random.randint(40, 90))

                await asyncio.sleep(random.uniform(0.5, 1.5))

                # Fill password
                pass_input = await page.query_selector("#password")
                if pass_input:
                    await pass_input.click()
                    await asyncio.sleep(0.3)
                    await pass_input.fill("")
                    await pass_input.type(cred.password_encrypted, delay=random.randint(40, 90))

                await asyncio.sleep(random.uniform(0.5, 1))

                # Submit
                old_url = page.url
                submit = await page.query_selector("button[type='submit']")
                if submit:
                    await submit.click()

                # Wait for navigation
                for _ in range(15):
                    await asyncio.sleep(1)
                    if page.url != old_url:
                        break

                await asyncio.sleep(2)
                await self.screenshot("linkedin_after_login")

                # Check login success
                if any(x in page.url for x in ["/feed", "/jobs", "/mynetwork", "/messaging"]):
                    await self.log("info", "apply", "login_success", {"message": "  Login successful!"}, platform="linkedin")
                    return True

                # Check for security challenge (email verification code)
                if "checkpoint" in page.url or "challenge" in page.url:
                    page_text = (await page.inner_text("body")).lower()
                    # LinkedIn sends verification code to email
                    if "code" in page_text or "verifizierung" in page_text or "sicherheitsprüfung" in page_text:
                        await self.log("info", "apply", "security_code", {
                            "message": "  LinkedIn requires email verification code — checking Gmail...",
                        }, platform="linkedin")

                        # Use LinkedIn-specific Gmail or fall back to default
                        gmail_email = settings.GMAIL_EMAIL_LI or settings.GMAIL_EMAIL
                        gmail_app_pw = settings.GMAIL_APP_PASSWORD_LI or settings.GMAIL_APP_PASSWORD
                        if not gmail_email or not gmail_app_pw:
                            await self.log("error", "apply", "no_gmail", {
                                "message": "  Code verification requires GMAIL_EMAIL + GMAIL_APP_PASSWORD in .env",
                            }, platform="linkedin")
                            return False

                        # Enter the code input field if visible, then fetch code
                        code_input = await page.query_selector('input#input__email_verification_pin, input[name="pin"], input[type="text"]')
                        if code_input:
                            # Fetch code from Gmail (LinkedIn sends from "linkedin")
                            code = self._fetch_indeed_code_from_gmail(gmail_email, gmail_app_pw, timeout_s=90, sender="linkedin")
                            if code:
                                await self.log("info", "apply", "got_code", {
                                    "message": f"  Got LinkedIn verification code: {code}",
                                }, platform="linkedin")
                                await code_input.fill("")
                                await code_input.type(code, delay=random.randint(30, 70))
                                await asyncio.sleep(1)

                                submit_btn = (
                                    await page.query_selector('button[type="submit"]') or
                                    await page.query_selector('button:has-text("Senden")') or
                                    await page.query_selector('button:has-text("Submit")')
                                )
                                if submit_btn:
                                    await submit_btn.click()
                                    await asyncio.sleep(5)

                                await self.screenshot("linkedin_after_code")

                                # Check if we're logged in now
                                if any(x in page.url for x in ["/feed", "/jobs", "/mynetwork", "/messaging"]):
                                    await self.log("info", "apply", "login_success", {
                                        "message": "  Login successful after code verification!",
                                    }, platform="linkedin")
                                    return True
                            else:
                                await self.log("error", "apply", "no_code", {
                                    "message": "  Could not retrieve verification code from Gmail",
                                }, platform="linkedin")
                                return False

                    await self.log("warn", "apply", "security_challenge", {
                        "message": "  Security challenge not handled — cannot proceed",
                        "url": page.url[:100],
                    }, platform="linkedin")
                    return False

            except Exception as e:
                await self.log("warn", "apply", "login_error", {
                    "message": f"  Login attempt {attempt+1} failed: {str(e)[:100]}",
                }, platform="linkedin")
                await asyncio.sleep(3)

        await self.log("error", "apply", "login_failed", {"message": "  All login attempts failed"}, platform="linkedin")
        return False

    async def _scrape_phase_linkedin(self, db: Session, job_filter: JobFilter, profile: dict) -> list[int]:
        """Scrape LinkedIn for Easy Apply jobs."""
        await self.log("info", "scrape", "phase_start", {"message": "Starting LinkedIn job discovery..."})
        await self.emit_status("scraping")

        queries = job_filter.job_titles if job_filter and job_filter.job_titles else ["kellner"]
        locations = job_filter.locations if job_filter and job_filter.locations else ["deutschland"]
        requested_apps = int(job_filter.max_applications or 10) if job_filter and hasattr(job_filter, 'max_applications') else 10
        max_pages = max(3, min((requested_apps * 2) // 25 + 1, 10))
        all_job_ids: list[int] = []
        total_new = 0

        pw = await async_playwright().start()
        browser, ctx, page = await self._launch_stealth_browser(pw, "linkedin")
        self._page = page
        self._browser = browser

        # Login first
        li_cred = None
        creds = db.query(PlatformCredential).filter(
            PlatformCredential.user_id == self.user_id,
            PlatformCredential.platform == "linkedin",
        ).all()
        if creds:
            li_cred = creds[0]
            logged_in = await self._login_linkedin(page, li_cred)
            if not logged_in:
                await self.log("error", "scrape", "login_required", {
                    "message": "Cannot scrape LinkedIn without login"
                }, platform="linkedin")
                await browser.close()
                return []
        else:
            await self.log("warn", "scrape", "no_credentials", {
                "message": "No LinkedIn credentials — scraping public listings only"
            }, platform="linkedin")

        for query in queries:
            for loc in locations:
                if not self.running:
                    break

                await self.log("info", "scrape", "search_start", {
                    "message": f"Searching LinkedIn: {query} in {loc} (up to {max_pages} pages)",
                    "query": query, "location": loc,
                }, platform="linkedin")

                for page_num in range(max_pages):
                    if not self.running:
                        break

                    params = urllib.parse.urlencode({
                        "keywords": query,
                        "location": loc,
                        "f_AL": "true",  # Easy Apply filter
                        "sortBy": "DD",  # Date posted
                        "start": page_num * 25,
                    })
                    url = f"https://www.linkedin.com/jobs/search/?{params}"

                    try:
                        await page.goto(url, timeout=25000, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(3, 6))

                        # Check for login wall / rate limit
                        if "authwall" in page.url or "login" in page.url:
                            await self.log("warn", "scrape", "auth_wall", {
                                "message": "  Hit auth wall — stopping scrape"
                            }, platform="linkedin")
                            break

                        await self.screenshot("linkedin_search")

                        # Extract job cards
                        card_selectors = [
                            ".scaffold-layout__list-item",
                            ".jobs-search-results__list-item",
                            "[data-job-id]",
                            ".job-card-container",
                        ]
                        cards = []
                        for sel in card_selectors:
                            cards = await page.query_selector_all(sel)
                            if cards:
                                break

                        if not cards:
                            await self.log("info", "scrape", "no_more", {
                                "message": f"  No jobs on page {page_num + 1}"
                            }, platform="linkedin")
                            break

                        await self.log("info", "scrape", "cards_found", {
                            "message": f"  Page {page_num + 1}: {len(cards)} job cards",
                        }, platform="linkedin")

                        # Fast extract: pull all job data from cards without clicking each one
                        new_on_page = 0
                        _skipped_no_title = 0
                        _skipped_no_url = 0
                        _skipped_dedup = 0
                        _errors = 0

                        card_data = await page.evaluate("""() => {
                            const cards = document.querySelectorAll('.scaffold-layout__list-item, .jobs-search-results__list-item, [data-job-id], .job-card-container');
                            return Array.from(cards).slice(0, 25).map(card => {
                                const titleEl = card.querySelector('a.job-card-list__title, .job-card-list__title, a[class*="job-card-list__title"], strong, a.job-card-container__link');
                                const companyEl = card.querySelector('.job-card-container__primary-description, .artdeco-entity-lockup__subtitle, span.job-card-container__primary-description');
                                const linkEl = card.querySelector('a[href*="/jobs/view/"], a.job-card-list__title, a.job-card-container__link');
                                const href = linkEl ? linkEl.href : '';
                                const jobIdMatch = href.match(/\\/jobs\\/view\\/(\\d+)/);
                                return {
                                    title: titleEl ? titleEl.innerText.trim() : '',
                                    company: companyEl ? companyEl.innerText.trim() : '',
                                    jobId: jobIdMatch ? jobIdMatch[1] : '',
                                    href: href,
                                };
                            }).filter(c => c.title && c.jobId);
                        }""")

                        for ci, cd in enumerate(card_data):
                            try:
                                title = cd["title"]
                                company = cd.get("company", "")
                                job_ext_id = cd["jobId"]
                                job_url = f"https://www.linkedin.com/jobs/view/{job_ext_id}/"

                                # LinkedIn already filters by keyword — skip strict relevance check
                                # (Unlike StepStone/Indeed, LinkedIn search is accurate enough)

                                # f_AL=true already filters to Easy Apply only — no extra check needed

                                # Dedup
                                existing = db.query(Job).filter(Job.url == job_url).first()
                                if existing:
                                    all_job_ids.append(existing.id)
                                    _skipped_dedup += 1
                                    continue

                                job = Job(
                                    platform="linkedin",
                                    title=title,
                                    company=company or "Unknown",
                                    url=job_url,
                                    location=loc,
                                    user_id=self.user_id,
                                    scraped_at=datetime.now(timezone.utc),
                                )
                                db.add(job)
                                db.flush()
                                all_job_ids.append(job.id)
                                new_on_page += 1

                            except Exception as e:
                                _errors += 1
                                if _errors <= 3:  # Log first 3 errors
                                    await self.log("warn", "scrape", "card_error", {
                                        "message": f"    Card {ci+1} error: {str(e)[:150]}",
                                    }, platform="linkedin")
                                continue

                        db.commit()
                        total_new += new_on_page
                        await self.log("info", "scrape", "page_summary", {
                            "message": f"  Page {page_num + 1} breakdown: {new_on_page} new, {_skipped_dedup} dedup, {_skipped_no_title} no-title, {_errors} errors",
                        }, platform="linkedin")

                        await self.log("info", "scrape", "page_done", {
                            "message": f"  Page {page_num + 1}: {new_on_page} new Easy Apply jobs stored",
                        }, platform="linkedin")

                        # Random delay between pages
                        await asyncio.sleep(random.uniform(3, 7))

                    except Exception as e:
                        err_msg = str(e)[:100]
                        await self.log("warn", "scrape", "page_error", {
                            "message": f"  Error on page {page_num + 1}: {err_msg}",
                        }, platform="linkedin")
                        # If browser/page closed, stop scraping
                        if "closed" in err_msg.lower() or "crashed" in err_msg.lower():
                            break

        await self.log("info", "scrape", "phase_done", {
            "message": f"LinkedIn scrape complete: {total_new} new jobs stored, {len(all_job_ids)} total",
            "new_jobs": total_new, "total": len(all_job_ids),
        }, platform="linkedin")
        await self.emit_progress()

        # Don't close browser — reuse for apply phase
        return all_job_ids

    async def _apply_phase_linkedin(self, db: Session, profile: dict, creds: list, job_filter: JobFilter, scraped_job_ids: list[int] = None):
        """Apply to LinkedIn jobs using Easy Apply."""
        await self.log("info", "apply", "phase_start", {"message": "Starting LinkedIn Easy Apply phase..."})
        await self.emit_status("applying")

        applied_urls = set(
            r[0] for r in db.query(Application.url).filter(
                Application.user_id == self.user_id,
                Application.status.in_(["success", "applying", "external"]),
            ).all() if r[0]
        )

        if scraped_job_ids:
            query = db.query(Job).filter(Job.id.in_(scraped_job_ids))
        else:
            query = db.query(Job).filter(Job.platform == "linkedin")

        if applied_urls:
            query = query.filter(~Job.url.in_(applied_urls))

        max_apps = min(max(int(job_filter.max_applications or 10) if job_filter and hasattr(job_filter, 'max_applications') else 10, 1), 500)
        jobs = query.order_by(Job.scraped_at.desc()).limit(max_apps).all()

        self.stats["total"] = len(jobs)
        await self.log("info", "apply", "jobs_count", {
            "message": f"Found {len(jobs)} LinkedIn Easy Apply jobs for application",
            "count": len(jobs),
        }, platform="linkedin")

        if not jobs:
            return

        # Browser setup (reuse from scrape or create new)
        pw = None
        browser = self._browser
        page = self._page
        if not browser or not page:
            pw = await async_playwright().start()
            browser, ctx, page = await self._launch_stealth_browser(pw, "linkedin")
            self._page = page
            self._browser = browser

        # Login
        li_cred = None
        li_creds = db.query(PlatformCredential).filter(
            PlatformCredential.user_id == self.user_id,
            PlatformCredential.platform == "linkedin",
        ).all()
        if li_creds:
            li_cred = li_creds[0]
        else:
            await self.log("error", "apply", "no_credentials", {
                "message": "No LinkedIn credentials configured — cannot apply"
            }, platform="linkedin")
            return

        # Check if still logged in, if not re-login
        try:
            if not any(x in page.url for x in ["/feed", "/jobs", "/mynetwork"]):
                logged_in = await self._login_linkedin(page, li_cred)
                if not logged_in:
                    await self.log("error", "apply", "login_failed", {
                        "message": "Cannot apply — login failed"
                    }, platform="linkedin")
                    return
        except:
            logged_in = await self._login_linkedin(page, li_cred)
            if not logged_in:
                return

        cv_path = profile.get("cv_path")

        for i, job in enumerate(jobs):
            if not self.running:
                break

            t0 = time.time()
            application = Application(
                user_id=self.user_id,
                job_id=job.id,
                url=job.url,
                job_title=job.title,
                company=job.company,
                platform="linkedin",
                status="pending",
                applied_at=datetime.now(timezone.utc),
            )
            db.add(application)
            db.flush()

            await self.log("info", "apply", "start", {
                "message": f"[{i+1}/{len(jobs)}] Applying: {job.title} at {job.company or 'Unknown'}",
            }, job_id=job.id, platform="linkedin")

            try:
                await page.goto(job.url, timeout=25000, wait_until="domcontentloaded")
                # Wait for job content to render (LinkedIn is SPA — content loads via JS)
                # Use JS wait instead of CSS selectors (LinkedIn changes class names frequently)
                try:
                    await page.wait_for_function("""() => {
                        const buttons = document.querySelectorAll('button, a[role="button"]');
                        for (const b of buttons) {
                            const txt = (b.innerText || '').toLowerCase();
                            if (txt.includes('easy apply') || txt.includes('einfach bewerben')) return true;
                        }
                        // Also check if any job title element rendered
                        if (document.querySelector('h1, h2.t-24, .t-24')) return true;
                        return false;
                    }""", timeout=15000)
                except:
                    pass
                await asyncio.sleep(random.uniform(1.5, 2.5))

                # Check for auth wall
                if "authwall" in page.url or "login" in page.url:
                    logged_in = await self._login_linkedin(page, li_cred)
                    if logged_in:
                        await page.goto(job.url, timeout=25000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                    else:
                        application.status = "failed"
                        application.error_log = "Login required"
                        db.commit()
                        self.stats["failed"] += 1
                        await self.emit_progress()
                        continue

                # Check if already applied
                page_text = await page.inner_text("body")
                page_text_lower = page_text.lower()
                if any(x in page_text_lower for x in ["applied", "beworben", "submitted"]):
                    btn_area = ""
                    for sel in [".jobs-apply-button", ".jobs-unified-top-card"]:
                        el = await page.query_selector(sel)
                        if el:
                            btn_area = (await el.inner_text()).lower()
                            break
                    if any(x in btn_area for x in ["applied", "beworben"]):
                        application.status = "skipped"
                        application.error_log = "Already applied"
                        db.commit()
                        self.stats["skipped"] += 1
                        await self.emit_progress()
                        continue

                # Find Easy Apply button using Playwright locators (robust against class changes)
                apply_btn = None
                # Method 1: Playwright text locator (matches any element type)
                for txt_pattern in ["Easy Apply", "Einfach bewerben"]:
                    loc = page.get_by_text(txt_pattern, exact=False)
                    if await loc.count() > 0:
                        # Find the clickable parent (button/link)
                        first_el = loc.first
                        try:
                            tag = await first_el.evaluate("el => el.tagName.toLowerCase()")
                            if tag in ("button", "a"):
                                apply_btn = first_el
                            else:
                                # Text is inside a span/svg — walk up to find clickable parent
                                parent_btn = page.locator(f"button:has-text('{txt_pattern}'), a:has-text('{txt_pattern}')")
                                if await parent_btn.count() > 0:
                                    apply_btn = parent_btn.first
                                else:
                                    apply_btn = first_el  # Click the element itself
                            break
                        except:
                            pass

                # Method 2: aria-label fallback
                if not apply_btn:
                    for aria_text in ["Easy Apply", "Einfach bewerben"]:
                        loc = page.locator(f'[aria-label*="{aria_text}"]')
                        if await loc.count() > 0:
                            apply_btn = loc.first
                            break

                if not apply_btn:
                    # Deep diagnostic: find ANY element containing "easy apply" text
                    try:
                        diag = await page.evaluate("""() => {
                            const all = document.querySelectorAll('*');
                            const matches = [];
                            for (const el of all) {
                                const txt = (el.innerText || '').trim().toLowerCase();
                                if (txt.includes('easy apply') || txt.includes('einfach bewerben')) {
                                    matches.push({
                                        tag: el.tagName,
                                        cls: el.className?.toString?.()?.slice(0, 80) || '',
                                        role: el.getAttribute('role') || '',
                                        vis: el.offsetParent !== null,
                                        rect: el.getBoundingClientRect ? {
                                            x: Math.round(el.getBoundingClientRect().x),
                                            y: Math.round(el.getBoundingClientRect().y),
                                            w: Math.round(el.getBoundingClientRect().width),
                                            h: Math.round(el.getBoundingClientRect().height)
                                        } : null,
                                        txt: (el.innerText || '').trim().slice(0, 50)
                                    });
                                    if (matches.length >= 5) break;
                                }
                            }
                            return matches;
                        }""")
                        await self.log("info", "apply", "no_easy_apply", {
                            "message": f"  No Easy Apply locator — DOM matches: {diag}",
                        }, job_id=job.id, platform="linkedin")
                    except Exception as diag_err:
                        await self.log("info", "apply", "no_easy_apply", {
                            "message": f"  No Easy Apply — diag error: {diag_err}",
                        }, job_id=job.id, platform="linkedin")
                    await self.screenshot("linkedin_no_easy_apply")
                    await self.log("info", "apply", "external_only", {
                        "message": f"  External-only job — saved to external list",
                    }, job_id=job.id, platform="linkedin")
                    application.status = "external"
                    application.error_log = "No Easy Apply button"
                    db.commit()
                    self.stats["external"] = self.stats.get("external", 0) + 1
                    await self.emit_progress()
                    continue

                # Click Easy Apply
                await apply_btn.scroll_into_view_if_needed()
                await asyncio.sleep(random.uniform(0.3, 0.8))
                await apply_btn.click(force=True)
                await asyncio.sleep(random.uniform(1, 2))

                # Check if external redirect
                if "linkedin.com" not in page.url.lower():
                    ext_redirect = page.url[:100]
                    await self.log("info", "apply", "external_only", {
                        "message": f"  External redirect — saved to external list ({ext_redirect})",
                    }, job_id=job.id, platform="linkedin")
                    application.status = "external"
                    application.error_log = f"External redirect: {ext_redirect}"
                    application.notes = page.url
                    db.commit()
                    self.stats["external"] = self.stats.get("external", 0) + 1
                    await self.emit_progress()
                    continue

                await self.screenshot("linkedin_modal")

                # Check modal opened
                modal = None
                for sel in [".jobs-easy-apply-modal", ".artdeco-modal", "[role='dialog']"]:
                    modal = await page.query_selector(sel)
                    if modal and await modal.is_visible():
                        break
                    modal = None

                if not modal:
                    application.status = "failed"
                    application.error_log = "Easy Apply modal didn't open"
                    db.commit()
                    self.stats["failed"] += 1
                    await self.emit_progress()
                    continue

                # Complete multi-step form
                success = await self._complete_linkedin_form(page, profile, cv_path, job)
                apply_duration = time.time() - t0

                if success:
                    application.status = "success"
                    self.stats["applied"] += 1
                    await self.log("info", "apply", "success", {
                        "message": f"  SUCCESS — LinkedIn Easy Apply submitted in {apply_duration:.0f}s",
                        "duration_s": apply_duration,
                    }, job_id=job.id, platform="linkedin")
                else:
                    application.status = "failed"
                    application.error_log = "Could not complete Easy Apply form"
                    self.stats["failed"] += 1
                    await self.log("warn", "apply", "form_failed", {
                        "message": f"  FAILED — Could not complete form ({apply_duration:.0f}s)",
                    }, job_id=job.id, platform="linkedin")

                # Dismiss any modal left open
                await self._dismiss_linkedin_modal(page)

            except Exception as e:
                application.status = "failed"
                application.error_log = str(e)[:500]
                self.stats["failed"] += 1
                await self.log("error", "apply", "error", {
                    "message": f"  ERROR: {str(e)[:100]}",
                }, job_id=job.id, platform="linkedin")
                await self._dismiss_linkedin_modal(page)

            db.commit()
            await self.emit_progress()

            if i < len(jobs) - 1 and self.running:
                delay = random.uniform(25, 45)
                await self.log("info", "system", "delay", {
                    "message": f"  Waiting {delay:.0f}s before next...",
                })
                await asyncio.sleep(delay)

        await browser.close()
        self._page = None
        self._browser = None

    async def _complete_linkedin_form(self, page, profile: dict, cv_path: str | None, job) -> bool:
        """Complete LinkedIn Easy Apply multi-step form. Returns True on success."""
        form_start = time.time()
        TIMEOUT = 60  # seconds
        step = 0
        just_clicked_submit = False

        questions_json = profile.get("questions_json", {})

        prev_step_url = ""
        stuck_count = 0
        submitted_once = False

        while step < 30 and self.running:
            step += 1

            # Timeout
            if time.time() - form_start > TIMEOUT:
                await self.screenshot("linkedin_form_timeout")
                await self.log("warn", "form", "timeout", {
                    "message": f"  Form timeout after {TIMEOUT}s at step {step}",
                }, platform="linkedin")
                return False

            # Check if modal is still open
            modal_visible = False
            for sel in [".jobs-easy-apply-modal", ".artdeco-modal", "[role='dialog']"]:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    modal_visible = True
                    break

            if not modal_visible:
                await asyncio.sleep(1)
                if just_clicked_submit or submitted_once:
                    error_el = await page.query_selector(".artdeco-inline-feedback--error")
                    if error_el and await error_el.is_visible():
                        return False
                    await self.log("info", "form", "modal_closed_success", {
                        "message": "  Modal closed after submit — application sent",
                    }, platform="linkedin")
                    return True
                try:
                    body = (await page.inner_text("body")).lower()
                    if any(kw in body for kw in ["application sent", "bewerbung gesendet", "successfully submitted"]):
                        return True
                except:
                    pass
                return False

            just_clicked_submit = False

            # Get modal content for step identification
            try:
                modal_text = ""
                for sel in [".jobs-easy-apply-modal", ".artdeco-modal", "[role='dialog']"]:
                    el = await page.query_selector(sel)
                    if el:
                        modal_text = (await el.inner_text()).lower()
                        break
                if any(kw in modal_text for kw in [
                    "application sent", "bewerbung gesendet", "submitted",
                    "application was sent", "bewerbung wurde gesendet",
                    "thank you", "danke", "your application", "done",
                ]):
                    await self.log("info", "form", "success_text", {
                        "message": "  Success text detected in modal",
                    }, platform="linkedin")
                    return True
            except:
                modal_text = ""

            # Detect if stuck (same content for 3+ iterations)
            step_sig = modal_text[:200]
            if step_sig == prev_step_url:
                stuck_count += 1
                if stuck_count >= 4:
                    await self.screenshot("linkedin_form_stuck")
                    # Log what's visible in the modal
                    try:
                        form_diag = await page.evaluate("""() => {
                            const modal = document.querySelector('[role="dialog"]') || document.querySelector('.artdeco-modal');
                            if (!modal) return {error: 'no modal'};
                            const inputs = modal.querySelectorAll('input:not([type="hidden"]), textarea, select');
                            const fields = Array.from(inputs).map(el => ({
                                tag: el.tagName, type: el.type || '', name: el.name || '',
                                label: (el.getAttribute('aria-label') || el.placeholder || '').slice(0, 50),
                                value: (el.value || '').slice(0, 30),
                                visible: el.offsetParent !== null
                            }));
                            const btns = Array.from(modal.querySelectorAll('button')).map(b => ({
                                text: b.innerText.trim().slice(0, 40),
                                enabled: !b.disabled, visible: b.offsetParent !== null
                            }));
                            const errors = Array.from(modal.querySelectorAll('[class*="error"], [class*="feedback"]'))
                                .map(e => e.innerText.trim().slice(0, 80)).filter(t => t);
                            return {fields, btns, errors};
                        }""")
                        await self.log("warn", "form", "stuck", {
                            "message": f"  STUCK at step {step}: {form_diag}",
                        }, platform="linkedin")
                    except Exception as diag_err:
                        await self.log("warn", "form", "stuck", {
                            "message": f"  STUCK at step {step}, diag error: {diag_err}",
                        }, platform="linkedin")
                    return False
            else:
                stuck_count = 0
                prev_step_url = step_sig

            # Check for validation errors
            has_errors = False
            error_texts = []
            for sel in [".artdeco-inline-feedback--error", "[data-test-form-element-error]"]:
                els = await page.query_selector_all(sel)
                for el in els:
                    try:
                        if await el.is_visible():
                            has_errors = True
                            txt = (await el.inner_text()).strip()
                            if txt:
                                error_texts.append(txt[:60])
                    except:
                        pass

            if error_texts:
                await self.log("info", "form", "errors_visible", {
                    "message": f"  Form errors: {error_texts}",
                }, platform="linkedin")

            # Fill fields FIRST, then click buttons
            filled = await self._fill_linkedin_fields(page, profile, questions_json, cv_path)
            if filled > 0:
                await self.log("info", "form", "fields_filled", {
                    "message": f"  Step {step}: filled {filled} fields",
                }, platform="linkedin")
                await asyncio.sleep(0.5)

            # Try Submit
            for sel in [
                "button[aria-label='Submit application']",
                "button:has-text('Submit application')",
                "button:has-text('Bewerbung absenden')",
                "button:has-text('Bewerbung senden')",
            ]:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click(force=True)
                    just_clicked_submit = True
                    submitted_once = True
                    await self.log("info", "form", "submit_clicked", {
                        "message": "  Clicked Submit",
                    }, platform="linkedin")
                    await asyncio.sleep(random.uniform(1, 2))
                    break

            if just_clicked_submit:
                continue

            # Try Next / Review
            clicked_next = False
            for sel in [
                "button[aria-label='Continue to next step']",
                "button[aria-label='Review your application']",
                "button:has-text('Next')", "button:has-text('Weiter')",
                "button:has-text('Review')", "button:has-text('Überprüfen')",
                ".artdeco-modal footer button.artdeco-button--primary",
            ]:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    try:
                        if await btn.is_enabled():
                            btn_text = (await btn.inner_text()).strip()
                            await btn.click(force=True)
                            clicked_next = True
                            await self.log("info", "form", "next_clicked", {
                                "message": f"  Clicked {btn_text}",
                            }, platform="linkedin")
                            await asyncio.sleep(random.uniform(0.8, 1.5))
                            break
                    except:
                        continue

            if not clicked_next and not has_errors and not just_clicked_submit:
                # No button found and nothing was submitted — check if post-submit confirmation
                # If modal has no form inputs and no action buttons, likely a success screen
                try:
                    has_form_content = await page.evaluate("""() => {
                        const modal = document.querySelector('[role="dialog"]') || document.querySelector('.artdeco-modal');
                        if (!modal) return false;
                        const inputs = modal.querySelectorAll('input:not([type="hidden"]), textarea, select');
                        const actionBtns = modal.querySelectorAll('button');
                        const actionTexts = Array.from(actionBtns).map(b => b.innerText.trim().toLowerCase());
                        const hasFormBtns = actionTexts.some(t =>
                            t.includes('next') || t.includes('weiter') || t.includes('submit') ||
                            t.includes('review') || t.includes('absenden') || t.includes('senden'));
                        return inputs.length > 0 || hasFormBtns;
                    }""")
                    if not has_form_content:
                        await self.log("info", "form", "post_submit_success", {
                            "message": "  No form content remaining — treating as success",
                        }, platform="linkedin")
                        return True
                except:
                    pass

                await self.log("info", "form", "no_button", {
                    "message": f"  Step {step}: no clickable button found, waiting...",
                }, platform="linkedin")

            await asyncio.sleep(random.uniform(0.5, 1.0))

        return False

    async def _fill_linkedin_fields(self, page, profile: dict, questions_json: dict, cv_path: str | None) -> int:
        """Fill visible form fields in LinkedIn Easy Apply modal."""
        filled = 0

        # Text inputs
        try:
            inputs = await page.query_selector_all("input[type='text']:visible:not([readonly]), input[type='number']:visible:not([readonly])")
            for inp in inputs:
                try:
                    current = await inp.input_value()
                    if current and current.strip():
                        continue  # Already filled

                    label = await self._get_linkedin_field_label(page, inp)
                    if not label:
                        continue
                    label_lower = label.lower()

                    answer = self._get_linkedin_answer(label_lower, profile, questions_json)
                    if answer:
                        await inp.click()
                        await asyncio.sleep(0.2)
                        await inp.fill("")
                        await inp.type(str(answer), delay=random.randint(30, 70))
                        filled += 1
                except:
                    continue
        except:
            pass

        # Textareas
        try:
            textareas = await page.query_selector_all("textarea:visible")
            for ta in textareas:
                try:
                    current = await ta.input_value()
                    if current and current.strip():
                        continue
                    label = await self._get_linkedin_field_label(page, ta)
                    label_lower = (label or "").lower()
                    answer = self._get_linkedin_answer(label_lower, profile, questions_json, field_type="textarea")
                    if answer:
                        await ta.click()
                        await asyncio.sleep(0.2)
                        await ta.fill(str(answer))
                        filled += 1
                except:
                    continue
        except:
            pass

        # Native selects
        try:
            selects = await page.query_selector_all("select:visible")
            for sel in selects:
                try:
                    current = await sel.input_value()
                    if current and current not in ["", "-1"]:
                        continue
                    options = await sel.query_selector_all("option")
                    # Prefer "Yes" / "Ja"
                    picked = False
                    for opt in options:
                        text = (await opt.inner_text()).strip().lower()
                        if text in ["yes", "ja"]:
                            val = await opt.get_attribute("value")
                            if val:
                                await sel.select_option(value=val)
                                filled += 1
                                picked = True
                                break
                    if not picked:
                        # Pick first non-empty option
                        for opt in options:
                            text = (await opt.inner_text()).strip()
                            val = await opt.get_attribute("value") or ""
                            if text and val not in ["", "-1"] and "select" not in text.lower():
                                await sel.select_option(value=val)
                                filled += 1
                                break
                except:
                    continue
        except:
            pass

        # Custom dropdowns (LinkedIn style)
        try:
            triggers = await page.query_selector_all(
                "button:has-text('Select an option'):visible, "
                "div[role='button']:has-text('Select an option'):visible, "
                "button:has-text('Option auswählen'):visible, "
                "div[role='button']:has-text('Option auswählen'):visible"
            )
            for trigger in triggers:
                try:
                    await trigger.click(force=True)
                    await asyncio.sleep(0.3)
                    options = await page.query_selector_all("[role='option'], .artdeco-dropdown__item")
                    picked = False
                    for opt in options:
                        text = (await opt.inner_text()).strip().lower()
                        if text in ["yes", "ja"]:
                            await opt.click()
                            filled += 1
                            picked = True
                            break
                    if not picked:
                        for opt in options:
                            text = (await opt.inner_text()).strip()
                            if text and "select" not in text.lower():
                                await opt.click()
                                filled += 1
                                break
                    await asyncio.sleep(0.2)
                except:
                    continue
        except:
            pass

        # Radio buttons — prefer Yes
        try:
            fieldsets = await page.query_selector_all("fieldset:visible")
            for fs in fieldsets:
                try:
                    radios = await fs.query_selector_all("input[type='radio']")
                    any_checked = False
                    for r in radios:
                        if await r.is_checked():
                            any_checked = True
                            break
                    if any_checked:
                        continue
                    # Pick "Yes" / first option
                    for r in radios:
                        label_el = await r.evaluate_handle("el => el.closest('label') || el.parentElement")
                        label_text = (await label_el.inner_text()).strip().lower() if label_el else ""
                        if label_text in ["yes", "ja"]:
                            await r.click(force=True)
                            filled += 1
                            break
                    else:
                        # Default to first radio
                        if radios:
                            await radios[0].click(force=True)
                            filled += 1
                except:
                    continue
        except:
            pass

        # File upload (CV)
        if cv_path and os.path.exists(cv_path):
            try:
                file_inputs = await page.query_selector_all("input[type='file']")
                for fi in file_inputs:
                    try:
                        # Check if resume already uploaded
                        resume_present = False
                        for sel in [".jobs-document-upload-redesign-card__file-name", "[class*='jobs-resume']"]:
                            el = await page.query_selector(sel)
                            if el and await el.is_visible():
                                resume_present = True
                                break
                        if resume_present:
                            continue
                        await fi.set_input_files(cv_path)
                        filled += 1
                        await self.log("info", "form", "cv_uploaded", {
                            "message": f"  Uploaded CV: {os.path.basename(cv_path)}",
                        }, platform="linkedin")
                        await asyncio.sleep(1)
                    except:
                        continue
            except:
                pass

        # Checkboxes — check unchecked ones
        try:
            checkboxes = await page.query_selector_all("input[type='checkbox']:visible")
            for cb in checkboxes:
                try:
                    if not await cb.is_checked():
                        await cb.click(force=True)
                        filled += 1
                except:
                    continue
        except:
            pass

        return filled

    async def _get_linkedin_field_label(self, page, element) -> str:
        """Get label text for a LinkedIn form element."""
        try:
            el_id = await element.get_attribute("id")
            if el_id:
                label = await page.query_selector(f"label[for='{el_id}']")
                if label and await label.is_visible():
                    return (await label.inner_text()).strip()
            aria = await element.get_attribute("aria-label")
            if aria:
                return aria
            placeholder = await element.get_attribute("placeholder")
            if placeholder:
                return placeholder
            # Try parent container label
            try:
                container_label = await element.evaluate("""el => {
                    const container = el.closest('.jobs-easy-apply-form-section__grouping, .fb-dash-form-element');
                    if (container) {
                        const lbl = container.querySelector('label, .fb-dash-form-element__label');
                        return lbl ? lbl.innerText.trim() : '';
                    }
                    return '';
                }""")
                if container_label:
                    return container_label
            except:
                pass
        except:
            pass
        return ""

    def _get_linkedin_answer(self, label_lower: str, profile: dict, questions_json: dict, field_type: str = "text") -> str | None:
        """Get answer for a LinkedIn form field using Q&A vault + patterns + profile."""
        if not label_lower:
            return None

        # 1. Profile fields
        profile_map = {
            "first name": profile.get("first_name", ""),
            "vorname": profile.get("first_name", ""),
            "last name": profile.get("last_name", ""),
            "nachname": profile.get("last_name", ""),
            "phone": profile.get("phone", ""),
            "telefon": profile.get("phone", ""),
            "mobil": profile.get("phone", ""),
            "city": profile.get("city", ""),
            "stadt": profile.get("city", ""),
            "zip": profile.get("zip_code", ""),
            "plz": profile.get("zip_code", ""),
            "street": profile.get("street_address", ""),
            "straße": profile.get("street_address", ""),
            "email": profile.get("email", ""),
            "e-mail": profile.get("email", ""),
        }
        for key, val in profile_map.items():
            if key in label_lower and val:
                return val

        # 2. Salary / Experience (numbers)
        if any(kw in label_lower for kw in ["salary", "gehalt", "gehaltsvorstellung", "gehaltserwartung"]):
            return str(profile.get("salary_expectation", 40000))
        if any(kw in label_lower for kw in ["years", "jahre", "experience", "erfahrung", "berufserfahrung"]):
            return str(profile.get("years_experience", 5))

        # 3. Q&A vault (fuzzy match)
        for q, a in questions_json.items():
            if q.lower() in label_lower or label_lower in q.lower():
                return str(a)
            if fuzz.partial_ratio(q.lower(), label_lower) > 80:
                return str(a)

        # 4. LinkedIn pattern answers
        for pattern, answer in _LINKEDIN_QA.items():
            if re.search(pattern, label_lower):
                return answer

        # 5. Default for textarea
        if field_type == "textarea":
            return "I am very interested in this position and believe my experience is a great fit."

        return None

    async def _dismiss_linkedin_modal(self, page):
        """Close any open LinkedIn Easy Apply modal."""
        try:
            # Try Dismiss button first
            for sel in ["button[aria-label='Dismiss']", "button:has-text('Discard')", "button:has-text('Done')", "button:has-text('Fertig')"]:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.5)
                    break
            # Confirm discard if prompted
            for sel in ["button:has-text('Discard')", "button:has-text('Verwerfen')"]:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.3)
                    break
        except:
            pass

    async def stop(self):
        """Gracefully stop the bot by killing the browser immediately."""
        self.running = False
        try:
            await self.log("info", "system", "stop_requested", {"message": "Stop requested by user"})
        except Exception:
            pass
        # Force-close browser to interrupt any blocking page operations
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
                self._page = None
        except Exception:
            pass

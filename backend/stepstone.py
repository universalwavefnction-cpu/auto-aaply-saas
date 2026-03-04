"""StepStone platform constants and pure helper functions.

Extracted from bot_engine.py for testability and single-source-of-truth.
All Playwright-dependent logic stays in bot_engine.py as async methods.
"""

import re

# ── Confirmation Keywords ───────────────────────────────────────────────
# Text on page after a successful StepStone application.
# Keep in ONE place — these were previously duplicated 8 times in bot_engine.py.

SS_CONFIRM_KEYWORDS = [
    # German
    "hat alles geklappt",
    "eckdaten zur bewerbung",
    "so kommst du schneller zum richtigen job",
    "bewerbung abgeschickt",
    "erfolgreich beworben",
    "vielen dank",
    "gesendet",
    "bewerbung wurde",
    "hast dich kürzlich",
    # English
    "did all go well",
    "application sent",
    "thank you",
    "submitted",
    "application has been",
    "you recently clicked apply",
    "recently clicked apply",
]

# Additional keywords specific to the interest/Schnellbewerbung flow.
SS_INTEREST_KEYWORDS = [
    "interesse wurde",
    "interesse bekundet",
    "interest has been",
    "interest expressed",
    "already applied",
    "bereits beworben",
]

# Summary overlay detection — the page between clicking interest and confirming.
SS_SUMMARY_KEYWORDS = [
    "zusammenfassung",
    "bewerbung fortsetzen",
    "bewerbung bearbeiten",
    "continue application",
    "application summary",
    "edit application",
    "haupt-lebenslauf",
    "kontaktdaten",
    "your default cv",
]

# External redirect detection — the job requires applying on the company's site.
SS_EXTERNAL_KEYWORDS = [
    "brought to you by stepstone",
    "zur verfügung gestellt von stepstone",
    "no listing title",
]

# ── Button Selectors ────────────────────────────────────────────────────

# Apply button selectors (on job page) — tried in priority order.
SS_APPLY_SELECTORS = [
    ('a:has-text("Jetzt bewerben")', "full"),
    ('button:has-text("Jetzt bewerben")', "full"),
    ('a:has-text("Apply now")', "full"),
    ('button:has-text("Apply now")', "full"),
    ('a:has-text("Schnelle Bewerbung")', "full"),
    ('button:has-text("Schnelle Bewerbung")', "full"),
    ('a:has-text("Quick apply")', "full"),
    ('button:has-text("Quick apply")', "full"),
    ('button:has-text("Bewerbung fortsetzen")', "full"),
    ('a:has-text("Bewerbung fortsetzen")', "full"),
    ('button:has-text("Continue application")', "full"),
    ('a:has-text("Continue application")', "full"),
]

# Interest / Schnellbewerbung button selectors (fallback).
SS_INTEREST_SELECTORS = [
    'button:has-text("Ich bin interessiert")',
    'a:has-text("Ich bin interessiert")',
    "button:has-text(\"I'm interested\")",
    "a:has-text(\"I'm interested\")",
]

# "Continue application" / "Bewerbung fortsetzen" on summary page.
SS_FORTSETZEN_SELECTORS = [
    'button:has-text("Bewerbung fortsetzen")',
    'a:has-text("Bewerbung fortsetzen")',
    'button:has-text("Continue application")',
    'a:has-text("Continue application")',
    'button:has-text("Bewerbung abschicken")',
]

# Final submit button on multi-step forms.
SS_SUBMIT_SELECTORS = [
    'button:has-text("Bewerbung abschicken")',
    'button:has-text("Submit application")',
    'button:has-text("Send application")',
    'button:has-text("Absenden")',
    'button:has-text("Jetzt bewerben")',
    'button:has-text("Apply now")',
]

# Next/Continue button selectors for advancing form steps.
SS_NEXT_SELECTORS = [
    'button:has-text("Bewerbung fortsetzen")',
    'button:has-text("Continue application")',
    'button:has-text("Weiter")',
    'button:has-text("Next")',
    'button:has-text("Continue")',
    'button[type="submit"]',
]

# Keywords that indicate a "Next" button is actually a submit button.
SS_SUBMIT_BUTTON_KEYWORDS = [
    "abschicken", "submit", "absenden",
    "send application", "jetzt bewerben", "apply now",
]

# Login page selectors.
SS_LOGIN_TOGGLE_SELECTORS = [
    'button:has-text("Jetzt einloggen")',
    'a:has-text("Jetzt einloggen")',
    'button:has-text("Log in")',
    'a:has-text("Log in")',
    'button:has-text("Sign in")',
    '[data-testid="login-toggle"]',
]

SS_EMAIL_INPUT_SELECTORS = [
    'input[type="email"]',
    'input[name="email"]',
    'input[autocomplete="email"]',
    'input[autocomplete="username"]',
    'input[id*="email"]',
    'input[id*="Email"]',
]

SS_PASSWORD_INPUT_SELECTORS = [
    'input[type="password"]',
    'input[name="password"]',
    'input[autocomplete="current-password"]',
]

SS_LOGIN_BUTTON_SELECTORS = [
    'button:has-text("Einloggen")',
    'button:has-text("Log in")',
    'button:has-text("Sign in")',
    'button[type="submit"]',
]

SS_LOGGED_IN_KEYWORDS = [
    "mein stepstone", "abmelden", "logout", "mein konto",
    "my stepstone", "sign out", "profil", "profile",
    "lebenslauf", "resume", "bewerbung",
]


# ── Pure Helper Functions ───────────────────────────────────────────────

def ss_check_confirmation(page_text: str, url: str = "") -> tuple[bool, str]:
    """Check if page text or URL indicates a successful StepStone application.

    Returns (is_confirmed, matched_keyword).
    """
    text = page_text.lower()
    for kw in SS_CONFIRM_KEYWORDS:
        if kw in text:
            return True, kw
    url_lower = url.lower()
    if "success" in url_lower or "confirmation" in url_lower:
        return True, f"url:{url}"
    return False, ""


def ss_check_interest_confirmed(page_text: str, url: str = "") -> tuple[bool, str]:
    """Check if interest/Schnellbewerbung was confirmed.

    Uses both general confirmation keywords and interest-specific ones.
    Returns (is_confirmed, matched_keyword).
    """
    # Check general confirmation first
    confirmed, kw = ss_check_confirmation(page_text, url)
    if confirmed:
        return True, kw
    # Check interest-specific keywords
    text = page_text.lower()
    for kw in SS_INTEREST_KEYWORDS:
        if kw in text:
            return True, kw
    return False, ""


def ss_check_summary(page_text: str) -> bool:
    """Check if page shows the application summary overlay."""
    text = page_text.lower()
    return any(kw in text for kw in SS_SUMMARY_KEYWORDS)


def ss_check_external(page_text: str, url: str = "") -> bool:
    """Check if page indicates an external application redirect."""
    text = page_text.lower()
    if any(kw in text for kw in SS_EXTERNAL_KEYWORDS):
        return True
    if "sie bewerben sich" in text and "stepstone" in text:
        return True
    url_lower = url.lower()
    return "apply" in url_lower and "external" in url_lower


def ss_check_on_form(page_text: str, url: str) -> bool:
    """Check if we're on a multi-step application form (not the job page)."""
    text = page_text.lower()
    url_lower = url.lower()
    return (
        "application" in url_lower
        or "dynamic-apply" in url_lower
        or any(kw in text for kw in [
            "step 1 of", "step 2 of",
            "schritt 1 von", "schritt 2 von",
        ])
    )


def ss_to_short_url(url: str) -> str:
    """Convert long stellenangebote URLs to short /job/ format.

    Long URLs get blocked from datacenter IPs.
    """
    if "/job/" in url and "stellenangebote" not in url:
        return url
    m = re.search(r'--(\d{6,})', url)
    if m:
        return f"https://www.stepstone.de/job/{m.group(1)}"
    return url


def ss_is_submit_button(button_text: str) -> bool:
    """Check if a button's text indicates it's a final submit (not just 'Next')."""
    text = button_text.lower()
    return any(kw in text for kw in SS_SUBMIT_BUTTON_KEYWORDS)


# ── Overlay Removal JS ─────────────────────────────────────────────────

SS_REMOVE_OVERLAYS_JS = """() => {
    const applyKeywords = ['bewerben', 'interessiert', 'interested', 'apply now', 'continue', 'fortsetzen'];
    function containsApplyBtn(el) {
        const text = (el.textContent || '').toLowerCase();
        return applyKeywords.some(kw => text.includes(kw));
    }
    document.querySelectorAll('[id*="portal"]').forEach(e => {
        if (!containsApplyBtn(e)) e.remove();
    });
    document.querySelectorAll('[data-genesis-element="DRAWER_OVERLAY"]').forEach(e => {
        if (!containsApplyBtn(e)) e.remove();
    });
    document.querySelectorAll('[class*="backdrop"], [class*="Backdrop"]').forEach(e => {
        if (!containsApplyBtn(e)) e.remove();
    });
    document.querySelectorAll('div').forEach(e => {
        const s = window.getComputedStyle(e);
        if (s.position === 'fixed' && s.zIndex > 100 && e.id !== 'onetrust-consent-sdk') {
            if (!containsApplyBtn(e)) e.remove();
        }
    });
    document.body.style.overflow = 'auto';
    document.body.style.pointerEvents = 'auto';
}"""

# ── Diagnostic JS ──────────────────────────────────────────────────────

SS_VISIBLE_BUTTONS_JS = """() => {
    return Array.from(document.querySelectorAll('button, a[role="button"], [role="button"]'))
        .filter(e => e.offsetParent !== null)
        .map(e => e.innerText.trim().substring(0, 60))
        .filter(t => t.length > 0);
}"""

SS_SMART_APPLY_BUTTONS_JS = """() => {
    return Array.from(document.querySelectorAll('button:not([style*="display: none"]), a[role="button"], [type="submit"]'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({ tag: b.tagName, text: b.textContent.trim().substring(0, 60), type: b.type || '' }))
        .slice(0, 10);
}"""

SS_PAGE_SNIPPET_JS = """() => {
    const areas = document.querySelectorAll('[class*="actions"], [class*="apply"], [class*="Action"], [class*="Apply"], [class*="sidebar"], [class*="Sidebar"]');
    let snippet = '';
    areas.forEach(a => { snippet += a.outerHTML.substring(0, 300) + '\\n'; });
    if (!snippet) {
        const dataAts = document.querySelectorAll('[data-at]');
        dataAts.forEach(e => { snippet += `<${e.tagName} data-at="${e.getAttribute('data-at')}">${e.textContent.substring(0, 50)}\\n`; });
    }
    return snippet.substring(0, 800);
}"""

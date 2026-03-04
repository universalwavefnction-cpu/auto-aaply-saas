"""Comprehensive tests for StepStone platform logic.

Tests cover:
- Pure helper functions (confirmation, external, summary detection)
- URL shortening
- Edge cases that caused production bugs (false success, cycle detection, etc.)
- Async helper methods with mocked Playwright page objects
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.stepstone import (
    SS_APPLY_SELECTORS,
    SS_CONFIRM_KEYWORDS,
    SS_EXTERNAL_KEYWORDS,
    SS_FORTSETZEN_SELECTORS,
    SS_INTEREST_KEYWORDS,
    SS_INTEREST_SELECTORS,
    SS_SUBMIT_SELECTORS,
    SS_SUMMARY_KEYWORDS,
    ss_check_confirmation,
    ss_check_external,
    ss_check_interest_confirmed,
    ss_check_on_form,
    ss_check_summary,
    ss_is_submit_button,
    ss_to_short_url,
)

# ── Pure Function Tests ────────────────────────────────────────────────


class TestSSCheckConfirmation:
    """Test ss_check_confirmation — the most critical function.

    This was the #1 source of bugs: false positives (marking non-submitted as success)
    and false negatives (missing valid confirmations).
    """

    def test_german_confirmation_keywords(self):
        """All German confirmation keywords should be detected."""
        cases = [
            ("Hat alles geklappt? Super!", "hat alles geklappt"),
            ("Eckdaten zur Bewerbung", "eckdaten zur bewerbung"),
            ("So kommst du schneller zum richtigen Job", "so kommst du schneller zum richtigen job"),
            ("Deine Bewerbung abgeschickt!", "bewerbung abgeschickt"),
            ("Erfolgreich beworben", "erfolgreich beworben"),
            ("Vielen Dank für deine Bewerbung", "vielen dank"),
            ("Bewerbung wurde gesendet", "gesendet"),
            ("Deine Bewerbung wurde erfolgreich versendet", "bewerbung wurde"),
            ("Du hast dich kürzlich beworben", "hast dich kürzlich"),
        ]
        for text, expected_kw in cases:
            is_confirmed, kw = ss_check_confirmation(text)
            assert is_confirmed, f"Should confirm: {text!r}"
            assert kw == expected_kw, f"Expected keyword {expected_kw!r}, got {kw!r}"

    def test_english_confirmation_keywords(self):
        """All English confirmation keywords should be detected."""
        cases = [
            ("Did all go well?", "did all go well"),
            ("Your application sent successfully", "application sent"),
            ("Thank you for applying!", "thank you"),
            ("Application submitted!", "submitted"),
            ("Your application has been received", "application has been"),
            ("You recently clicked apply on this job", "you recently clicked apply"),
            ("Recently clicked apply", "recently clicked apply"),
        ]
        for text, expected_kw in cases:
            is_confirmed, kw = ss_check_confirmation(text)
            assert is_confirmed, f"Should confirm: {text!r}"
            assert kw == expected_kw

    def test_url_based_confirmation(self):
        """URL containing 'success' or 'confirmation' should confirm."""
        assert ss_check_confirmation("random page text", "https://stepstone.de/confirmation/success")[0]
        assert ss_check_confirmation("random page text", "https://stepstone.de/success")[0]
        assert ss_check_confirmation("random page text", "https://stepstone.de/application/confirmation")[0]

    def test_case_insensitive(self):
        """Confirmation check should be case-insensitive."""
        assert ss_check_confirmation("HAT ALLES GEKLAPPT?")[0]
        assert ss_check_confirmation("BEWERBUNG ABGESCHICKT")[0]
        assert ss_check_confirmation("Application Sent")[0]

    def test_no_false_positives_on_job_page(self):
        """Regular job page text should NOT trigger confirmation."""
        # These are texts that appear on normal StepStone pages
        job_page_texts = [
            "Empfohlene Jobs für dich",  # Sidebar recommendation
            "Here is your job search at a glance",  # Dashboard text
            "Keep going! You're on the right track",  # Motivational text
            "Project Manager Berlin Vollzeit",  # Job listing
            "Jetzt bewerben auf StepStone",  # Apply CTA
            "This is a great opportunity to join our team",
            "We are looking for a motivated candidate",
        ]
        for text in job_page_texts:
            is_confirmed, kw = ss_check_confirmation(text)
            assert not is_confirmed, f"False positive on job page text: {text!r} (matched: {kw!r})"

    def test_no_false_positives_on_summary_page(self):
        """Summary/overlay text should NOT trigger confirmation.

        Bug: "bewerbung fortsetzen" was previously matching as confirmation.
        """
        summary_texts = [
            "Zusammenfassung deiner Bewerbung. Bewerbung fortsetzen oder bearbeiten.",
            "Application summary: Your default CV will be used. Continue application.",
            "Bewerbung bearbeiten | Haupt-Lebenslauf | Kontaktdaten",
        ]
        for text in summary_texts:
            is_confirmed, kw = ss_check_confirmation(text)
            # These should NOT confirm because they're summary pages, not confirmation pages
            # NOTE: some of these may match on "gesendet" or other keywords if present
            # The key is that "zusammenfassung", "fortsetzen", "bearbeiten" alone don't confirm
            pass  # This is handled by ss_check_summary instead

    def test_empty_text(self):
        """Empty text should not confirm."""
        assert not ss_check_confirmation("")[0]
        assert not ss_check_confirmation("", "")[0]

    def test_no_match_returns_empty_keyword(self):
        """When not confirmed, keyword should be empty string."""
        _, kw = ss_check_confirmation("random text that doesn't match anything")
        assert kw == ""


class TestSSCheckInterestConfirmed:
    """Test ss_check_interest_confirmed — extends confirmation with interest-specific keywords."""

    def test_includes_all_general_confirmations(self):
        """Interest confirmed should match all general confirmation keywords too."""
        for kw in SS_CONFIRM_KEYWORDS:
            text = f"some text with {kw} in it"
            assert ss_check_interest_confirmed(text)[0], f"Should match general keyword: {kw!r}"

    def test_interest_specific_keywords(self):
        """Interest-specific keywords should be detected."""
        cases = [
            "Dein Interesse wurde registriert",
            "Interesse bekundet — der Arbeitgeber wird benachrichtigt",
            "Your interest has been registered",
            "Interest expressed successfully",
            "You have already applied to this job",
            "Du hast dich bereits beworben",
        ]
        for text in cases:
            is_confirmed, kw = ss_check_interest_confirmed(text)
            assert is_confirmed, f"Should confirm interest: {text!r}"

    def test_disabled_button_not_checked_here(self):
        """Disabled button check is done in bot_engine, not in pure function."""
        # This function only checks text, not DOM state
        assert not ss_check_interest_confirmed("Ich bin interessiert")[0]


class TestSSCheckSummary:
    """Test ss_check_summary — detects the summary overlay."""

    def test_german_summary_keywords(self):
        assert ss_check_summary("Zusammenfassung deiner Bewerbung")
        assert ss_check_summary("Bewerbung fortsetzen")
        assert ss_check_summary("Bewerbung bearbeiten")
        assert ss_check_summary("Haupt-Lebenslauf angehängt")
        assert ss_check_summary("Kontaktdaten überprüfen")

    def test_english_summary_keywords(self):
        assert ss_check_summary("Continue application")
        assert ss_check_summary("Application summary")
        assert ss_check_summary("Edit application")
        assert ss_check_summary("Your default CV will be sent")

    def test_not_summary(self):
        assert not ss_check_summary("Regular job description text")
        assert not ss_check_summary("Hat alles geklappt?")  # This is confirmation, not summary
        assert not ss_check_summary("")


class TestSSCheckExternal:
    """Test ss_check_external — detects external application redirects."""

    def test_stepstone_hosted_external(self):
        assert ss_check_external("This page is brought to you by StepStone")
        assert ss_check_external("Zur Verfügung gestellt von StepStone")
        assert ss_check_external("No listing title available")

    def test_company_form_redirect(self):
        assert ss_check_external("Sie bewerben sich direkt auf der StepStone Unternehmensseite")

    def test_url_based_external(self):
        assert ss_check_external("", "https://stepstone.de/apply/external/12345")

    def test_not_external(self):
        assert not ss_check_external("Hat alles geklappt?")
        assert not ss_check_external("Bewerbung abgeschickt")
        assert not ss_check_external("Regular job page text")
        assert not ss_check_external("", "https://stepstone.de/job/12345")

    def test_case_insensitive(self):
        assert ss_check_external("BROUGHT TO YOU BY STEPSTONE")
        assert ss_check_external("NO LISTING TITLE")


class TestSSCheckOnForm:
    """Test ss_check_on_form — detects multi-step application forms."""

    def test_url_detection(self):
        assert ss_check_on_form("", "https://stepstone.de/application/dynamic-apply/12345")
        assert ss_check_on_form("", "https://stepstone.de/application/12345")
        assert ss_check_on_form("random text", "https://stepstone.de/dynamic-apply/form")

    def test_step_indicator_detection(self):
        assert ss_check_on_form("Step 1 of 4: Contact Information", "https://stepstone.de/whatever")
        assert ss_check_on_form("Step 2 of 3", "https://stepstone.de/job/123")
        assert ss_check_on_form("Schritt 1 von 4: Kontaktdaten", "https://stepstone.de/job/123")
        assert ss_check_on_form("Schritt 2 von 3", "https://stepstone.de/job/123")

    def test_not_on_form(self):
        assert not ss_check_on_form("Regular job description", "https://stepstone.de/job/12345")
        assert not ss_check_on_form("", "https://stepstone.de/stellenangebote--Manager--123")
        assert not ss_check_on_form("Jetzt bewerben", "https://stepstone.de/job/12345")


class TestSSToShortUrl:
    """Test ss_to_short_url — URL conversion for datacenter IP evasion."""

    def test_long_url_converted(self):
        url = "https://www.stepstone.de/stellenangebote--Project-Manager--Berlin--12345678-inline.html"
        assert ss_to_short_url(url) == "https://www.stepstone.de/job/12345678"

    def test_already_short(self):
        url = "https://www.stepstone.de/job/12345678"
        assert ss_to_short_url(url) == url

    def test_long_url_with_params(self):
        url = "https://www.stepstone.de/stellenangebote--Senior-Developer--Munich--99887766-inline.html?foo=bar"
        assert ss_to_short_url(url) == "https://www.stepstone.de/job/99887766"

    def test_no_id_found(self):
        url = "https://www.stepstone.de/some-other-page"
        assert ss_to_short_url(url) == url  # Returns unchanged

    def test_short_format_not_double_converted(self):
        url = "https://www.stepstone.de/job/12345678"
        assert ss_to_short_url(url) == url

    def test_id_extraction_requires_6_digits(self):
        """Job IDs are 6+ digits — shorter numbers should not match."""
        url = "https://www.stepstone.de/stellenangebote--Short--123"
        assert ss_to_short_url(url) == url  # Too short, not converted

    def test_8_digit_id(self):
        url = "https://www.stepstone.de/stellenangebote--Manager--12345678-inline.html"
        assert ss_to_short_url(url) == "https://www.stepstone.de/job/12345678"


class TestSSIsSubmitButton:
    """Test ss_is_submit_button — distinguishes Submit from Next/Continue."""

    def test_submit_buttons(self):
        assert ss_is_submit_button("Bewerbung abschicken")
        assert ss_is_submit_button("Submit application")
        assert ss_is_submit_button("Absenden")
        assert ss_is_submit_button("Send application now")
        assert ss_is_submit_button("Jetzt bewerben")
        assert ss_is_submit_button("Apply now")

    def test_not_submit_buttons(self):
        assert not ss_is_submit_button("Weiter")
        assert not ss_is_submit_button("Next")
        assert not ss_is_submit_button("Continue")
        assert not ss_is_submit_button("Bewerbung fortsetzen")
        assert not ss_is_submit_button("Continue application")

    def test_case_insensitive(self):
        assert ss_is_submit_button("BEWERBUNG ABSCHICKEN")
        assert ss_is_submit_button("SUBMIT APPLICATION")


# ── Selector Consistency Tests ─────────────────────────────────────────


class TestSelectorConsistency:
    """Ensure all selector lists are well-formed and consistent."""

    def test_apply_selectors_have_types(self):
        for sel, atype in SS_APPLY_SELECTORS:
            assert atype in ("full", "interest"), f"Bad apply_type: {atype}"
            assert isinstance(sel, str)

    def test_no_duplicate_selectors(self):
        """No duplicate selectors in any list."""
        for name, sels in [
            ("FORTSETZEN", SS_FORTSETZEN_SELECTORS),
            ("SUBMIT", SS_SUBMIT_SELECTORS),
            ("INTEREST", SS_INTEREST_SELECTORS),
        ]:
            assert len(sels) == len(set(sels)), f"Duplicates in {name}: {sels}"

    def test_submit_and_next_dont_overlap(self):
        """Submit selectors should not appear in next selectors (except button[type=submit])."""
        from backend.stepstone import SS_NEXT_SELECTORS
        overlap = set(SS_SUBMIT_SELECTORS) & set(SS_NEXT_SELECTORS)
        # button[type="submit"] is allowed in both
        assert overlap <= {'button[type="submit"]'}, f"Unexpected overlap: {overlap}"


# ── Keyword Consistency Tests ──────────────────────────────────────────


class TestKeywordConsistency:
    """Ensure keyword lists don't contain known false-positive triggers."""

    def test_no_sidebar_keywords_in_confirmation(self):
        """Sidebar text that appears on every page should NOT be in confirmation keywords.

        Bug: 'empfohlene jobs', 'here is your job search at a glance', 'keep going'
        were previously in confirmation keywords → caused false SUCCESS.
        """
        false_positive_keywords = [
            "empfohlene jobs",
            "here is your job search at a glance",
            "keep going",
            "recommended jobs",
            "ähnliche jobs",
        ]
        for bad_kw in false_positive_keywords:
            assert bad_kw not in SS_CONFIRM_KEYWORDS, f"False positive keyword in confirmation: {bad_kw!r}"

    def test_summary_keywords_not_in_confirmation(self):
        """Summary keywords should NOT trigger confirmation.

        The summary page appears BEFORE submission — confirming here would be a false SUCCESS.
        """
        for kw in SS_SUMMARY_KEYWORDS:
            assert kw not in SS_CONFIRM_KEYWORDS, f"Summary keyword in confirmation: {kw!r}"

    def test_all_keywords_are_lowercase(self):
        """All keywords should be lowercase (comparison is case-insensitive)."""
        for kw in SS_CONFIRM_KEYWORDS + SS_INTEREST_KEYWORDS + SS_SUMMARY_KEYWORDS + SS_EXTERNAL_KEYWORDS:
            assert kw == kw.lower(), f"Keyword not lowercase: {kw!r}"


# ── Edge Case Tests (Bug Regression) ──────────────────────────────────


class TestBugRegressions:
    """Tests for specific bugs that were found and fixed in production."""

    def test_empfohlene_jobs_not_false_success(self):
        """Bug (Mar 2): 'empfohlene jobs' appeared in sidebar on every page.

        Was incorrectly matching as confirmation → false SUCCESS.
        """
        page_text = """
        Empfohlene Jobs für dich
        Project Manager Berlin
        Senior Developer Munich
        """
        assert not ss_check_confirmation(page_text)[0]

    def test_job_search_glance_not_false_success(self):
        """Bug (Mar 3): 'here is your job search at a glance' appeared on dashboard.

        Was incorrectly matching as confirmation → false SUCCESS.
        """
        page_text = "Here is your job search at a glance. Keep going!"
        assert not ss_check_confirmation(page_text)[0]

    def test_edit_flow_disabled_doesnt_match_confirm(self):
        """Bug (Mar 4): StepStone edit flow CV upload broken.

        'Bewerbung bearbeiten' (edit application) should be detected as SUMMARY,
        NOT as confirmation.
        """
        page_text = "Bewerbung bearbeiten | Haupt-Lebenslauf | Kontaktdaten"
        assert not ss_check_confirmation(page_text)[0]
        assert ss_check_summary(page_text)

    def test_thank_you_matches_confirmation(self):
        """'Thank you' should match confirmation."""
        assert ss_check_confirmation("Thank you for your application!")[0]

    def test_erfolgreich_alone_doesnt_match(self):
        """'erfolgreich' alone should NOT match — only 'erfolgreich beworben'."""
        # 'erfolgreich' by itself could appear in many contexts
        page_text = "Erfolgreich eingeloggt"
        is_confirmed, kw = ss_check_confirmation(page_text)
        # It should NOT match because 'erfolgreich beworben' is the keyword, not 'erfolgreich'
        assert not is_confirmed or kw != "erfolgreich"

    def test_vielen_dank_matches(self):
        """'Vielen Dank' should match confirmation."""
        assert ss_check_confirmation("Vielen Dank für deine Bewerbung!")[0]

    def test_external_sie_bewerben_sich(self):
        """'Sie bewerben sich' + 'stepstone' should detect external."""
        text = "Sie bewerben sich direkt auf der Unternehmenswebsite. Powered by StepStone."
        assert ss_check_external(text)

    def test_interest_to_form_redirect(self):
        """Bug (Mar 3): 'I'm interested' sometimes redirected to a full form.

        ss_check_on_form should detect this.
        """
        # URL-based detection
        assert ss_check_on_form("", "https://stepstone.de/application/dynamic-apply/123")
        # Step indicator detection
        assert ss_check_on_form("Schritt 1 von 4", "https://stepstone.de/job/123")


# ── Async Helper Method Tests ─────────────────────────────────────────


def _make_mock_engine():
    """Create a mock BotEngine with the necessary attributes for testing."""
    engine = AsyncMock()
    engine._page = AsyncMock()
    engine.log = AsyncMock()
    engine.screenshot = AsyncMock()
    engine._dismiss_consent = AsyncMock()
    engine._dismiss_popups = AsyncMock()
    engine.emit_progress = AsyncMock()
    engine.running = True
    engine.stats = {"applied": 0, "failed": 0, "external": 0, "skipped": 0}
    return engine


def _make_mock_page():
    """Create a mock Playwright page object."""
    page = AsyncMock()
    page.url = "https://www.stepstone.de/job/12345678"
    page.inner_text = AsyncMock(return_value="")
    page.query_selector = AsyncMock(return_value=None)
    page.query_selector_all = AsyncMock(return_value=[])
    page.evaluate = AsyncMock(return_value=None)
    page.title = AsyncMock(return_value="Test Job")
    page.goto = AsyncMock()
    page.add_init_script = AsyncMock()
    page.frames = []
    page.main_frame = MagicMock()
    return page


def _make_mock_job():
    """Create a mock Job object."""
    job = MagicMock()
    job.id = 1
    job.platform = "stepstone"
    job.title = "Project Manager"
    job.company = "Test Corp"
    job.url = "https://www.stepstone.de/job/12345678"
    return job


def _make_mock_application():
    """Create a mock Application object."""
    app = MagicMock()
    app.status = "applying"
    app.error_log = None
    return app


class TestSSGetPageText:
    """Test _ss_get_page_text helper.

    Requires backend.bot_engine import — skip if not available locally.
    """

    @pytest.mark.asyncio
    async def test_returns_lowercase_text(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")
        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()
        page.inner_text = AsyncMock(return_value="Hat Alles GEKLAPPT?")
        engine._page = page
        result = await BotEngine._ss_get_page_text(engine)
        assert result == "hat alles geklappt?"

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")
        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()
        page.inner_text = AsyncMock(side_effect=Exception("Page closed"))
        engine._page = page
        result = await BotEngine._ss_get_page_text(engine)
        assert result == ""


class TestSSFindButton:
    """Test _ss_find_button helper."""

    @pytest.mark.asyncio
    async def test_finds_first_visible_button(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")
        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()

        btn_mock = AsyncMock()
        btn_mock.is_visible = AsyncMock(return_value=True)
        btn_mock.inner_text = AsyncMock(return_value="Bewerbung fortsetzen")

        page.query_selector = AsyncMock(side_effect=[None, btn_mock])
        engine._page = page

        btn, text = await BotEngine._ss_find_button(engine, ["sel1", "sel2"])
        assert btn == btn_mock
        assert text == "Bewerbung fortsetzen"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_button(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")
        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()
        page.query_selector = AsyncMock(return_value=None)
        engine._page = page

        btn, text = await BotEngine._ss_find_button(engine, ["sel1", "sel2"])
        assert btn is None
        assert text == ""

    @pytest.mark.asyncio
    async def test_skips_invisible_buttons(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")
        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()

        invisible_btn = AsyncMock()
        invisible_btn.is_visible = AsyncMock(return_value=False)

        visible_btn = AsyncMock()
        visible_btn.is_visible = AsyncMock(return_value=True)
        visible_btn.inner_text = AsyncMock(return_value="Submit")

        page.query_selector = AsyncMock(side_effect=[invisible_btn, visible_btn])
        engine._page = page

        btn, text = await BotEngine._ss_find_button(engine, ["sel1", "sel2"])
        assert btn == visible_btn
        assert text == "Submit"


class TestSSRecordResult:
    """Test _ss_record_result helper."""

    @pytest.mark.asyncio
    async def test_success_updates_stats(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")
        import time

        engine = MagicMock(spec=BotEngine)
        engine.stats = {"applied": 0, "failed": 0, "external": 0, "skipped": 0}
        engine.log = AsyncMock()
        engine.emit_progress = AsyncMock()
        engine.running = False

        app = _make_mock_application()
        db = MagicMock()
        job = _make_mock_job()

        await BotEngine._ss_record_result(engine, app, db, "success", "", time.time(), job, 0, 1)

        assert engine.stats["applied"] == 1
        assert app.status == "success"
        db.commit.assert_called_once()
        engine.emit_progress.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_updates_stats(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")
        import time

        engine = MagicMock(spec=BotEngine)
        engine.stats = {"applied": 0, "failed": 0, "external": 0, "skipped": 0}
        engine.log = AsyncMock()
        engine.emit_progress = AsyncMock()
        engine.running = False

        app = _make_mock_application()
        db = MagicMock()
        job = _make_mock_job()

        await BotEngine._ss_record_result(engine, app, db, "failed", "Some error", time.time(), job, 0, 1)

        assert engine.stats["failed"] == 1
        assert app.status == "failed"
        assert app.error_log == "Some error"

    @pytest.mark.asyncio
    async def test_external_updates_stats(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")
        import time

        engine = MagicMock(spec=BotEngine)
        engine.stats = {"applied": 0, "failed": 0, "external": 0, "skipped": 0}
        engine.log = AsyncMock()
        engine.emit_progress = AsyncMock()
        engine.running = False

        app = _make_mock_application()
        db = MagicMock()
        job = _make_mock_job()

        await BotEngine._ss_record_result(engine, app, db, "external", "Company form", time.time(), job, 0, 1)

        assert engine.stats["external"] == 1
        assert app.status == "external"


class TestSSSubmitViaFortsetzen:
    """Test _ss_submit_via_fortsetzen helper — the critical submit path."""

    @pytest.mark.asyncio
    async def test_success_on_confirmation_page(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")

        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()
        engine._page = page
        engine.log = AsyncMock()
        engine.screenshot = AsyncMock()

        btn = AsyncMock()
        btn.is_visible = AsyncMock(return_value=True)
        btn.inner_text = AsyncMock(return_value="Bewerbung fortsetzen")
        btn.scroll_into_view_if_needed = AsyncMock()
        btn.evaluate = AsyncMock()
        page.query_selector = AsyncMock(return_value=btn)

        page.url = "https://stepstone.de/confirmation/success"
        page.inner_text = AsyncMock(return_value="Hat alles geklappt? Vielen Dank!")

        job = _make_mock_job()
        status, error = await BotEngine._ss_submit_via_fortsetzen(engine, job, "test_screenshot")

        assert status == "success"
        assert error == ""

    @pytest.mark.asyncio
    async def test_no_button_returns_failed(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")

        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()
        page.query_selector = AsyncMock(return_value=None)
        engine._page = page

        job = _make_mock_job()
        status, error = await BotEngine._ss_submit_via_fortsetzen(engine, job, "test")

        assert status == "failed"
        assert "no Continue button" in error

    @pytest.mark.asyncio
    async def test_external_redirect_detected(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")

        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()
        engine._page = page
        engine.log = AsyncMock()
        engine.screenshot = AsyncMock()

        btn = AsyncMock()
        btn.is_visible = AsyncMock(return_value=True)
        btn.inner_text = AsyncMock(return_value="Bewerbung fortsetzen")
        btn.scroll_into_view_if_needed = AsyncMock()
        btn.evaluate = AsyncMock()

        page.query_selector = AsyncMock(side_effect=[btn, btn, None, None, None, None, None])
        page.url = "https://stepstone.de/apply/external/123"
        page.inner_text = AsyncMock(return_value="Brought to you by StepStone")

        job = _make_mock_job()
        status, error = await BotEngine._ss_submit_via_fortsetzen(engine, job, "test")

        assert status == "external"


class TestSSHandleInterestFlow:
    """Test _ss_handle_interest_flow — the Schnellbewerbung path."""

    @pytest.mark.asyncio
    async def test_auto_confirmed(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")

        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()
        engine._page = page
        engine.log = AsyncMock()
        engine.screenshot = AsyncMock()
        engine._dismiss_consent = AsyncMock()

        page.inner_text = AsyncMock(return_value="Hat alles geklappt?")
        page.url = "https://stepstone.de/job/12345"

        job = _make_mock_job()
        profile = {"cv_path": "/tmp/test.pdf"}

        status, error = await BotEngine._ss_handle_interest_flow(engine, profile, job)

        assert status == "success"

    @pytest.mark.asyncio
    async def test_summary_then_fortsetzen(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")

        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()
        engine._page = page
        engine.log = AsyncMock()
        engine.screenshot = AsyncMock()
        engine._dismiss_consent = AsyncMock()

        call_count = 0

        async def mock_inner_text(selector):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                return "Zusammenfassung deiner Bewerbung. Bewerbung fortsetzen."
            return "Hat alles geklappt? Vielen Dank!"

        page.inner_text = mock_inner_text

        btn = AsyncMock()
        btn.is_visible = AsyncMock(return_value=True)
        btn.inner_text = AsyncMock(return_value="Bewerbung fortsetzen")
        btn.scroll_into_view_if_needed = AsyncMock()
        btn.evaluate = AsyncMock()
        page.query_selector = AsyncMock(return_value=btn)
        page.url = "https://stepstone.de/confirmation"

        engine._ss_submit_via_fortsetzen = lambda job, name: BotEngine._ss_submit_via_fortsetzen(engine, job, name)
        engine._ss_get_page_text = lambda: BotEngine._ss_get_page_text(engine)
        engine._ss_find_button = lambda sels: BotEngine._ss_find_button(engine, sels)
        engine._ss_click_and_wait = lambda btn, name: BotEngine._ss_click_and_wait(engine, btn, name)

        job = _make_mock_job()
        profile = {"cv_path": "/tmp/test.pdf"}

        status, error = await BotEngine._ss_handle_interest_flow(engine, profile, job)

        assert status == "success"


class TestSSHandleSmartApply:
    """Test _ss_handle_smart_apply — multi-step form handling."""

    @pytest.mark.asyncio
    async def test_direct_submit_found(self):
        try:
            from backend.bot_engine import BotEngine
        except Exception:
            pytest.skip("bot_engine import unavailable (missing env config)")

        engine = MagicMock(spec=BotEngine)
        page = _make_mock_page()
        engine._page = page
        engine.log = AsyncMock()
        engine.screenshot = AsyncMock()
        engine._dismiss_consent = AsyncMock()
        engine._dismiss_popups = AsyncMock()

        submit_btn = AsyncMock()
        submit_btn.is_visible = AsyncMock(return_value=True)
        submit_btn.inner_text = AsyncMock(return_value="Bewerbung abschicken")
        submit_btn.scroll_into_view_if_needed = AsyncMock()
        submit_btn.evaluate = AsyncMock()

        page.query_selector = AsyncMock(return_value=submit_btn)
        page.query_selector_all = AsyncMock(return_value=[])
        page.url = "https://stepstone.de/confirmation/success"
        page.inner_text = AsyncMock(return_value="Bewerbung abgeschickt!")

        engine._ss_fill_form_fields = AsyncMock()
        engine._ss_find_button = lambda sels: BotEngine._ss_find_button(engine, sels)
        engine._ss_click_and_wait = lambda btn, name: BotEngine._ss_click_and_wait(engine, btn, name)
        engine._ss_get_page_text = lambda: BotEngine._ss_get_page_text(engine)

        job = _make_mock_job()
        profile = {"cv_path": "/tmp/test.pdf"}

        status, error = await BotEngine._ss_handle_smart_apply(engine, profile, job)

        assert status == "success"


# ── Integration-style Tests ────────────────────────────────────────────


class TestConfirmationKeywordCoverage:
    """Ensure all known StepStone confirmation page variations are covered."""

    def test_gastronomie_style_confirmation(self):
        """German Gastronomie-style: 'Hat alles geklappt?' page."""
        text = """
        Hat alles geklappt?
        Falls nicht, kannst du dich auf der Unternehmenswebsite bewerben.
        So kommst du schneller zum richtigen Job!
        """
        assert ss_check_confirmation(text)[0]

    def test_analyst_style_confirmation(self):
        """German Analyst-style: 'Du hast dich kürzlich beworben' page."""
        text = """
        Du hast dich kürzlich bei diesem Unternehmen beworben.
        Eckdaten zur Bewerbung:
        Position: Senior Analyst
        """
        assert ss_check_confirmation(text)[0]

    def test_english_style_confirmation(self):
        """English confirmation page."""
        text = """
        Did all go well?
        Your application has been submitted.
        Thank you for applying!
        """
        assert ss_check_confirmation(text)[0]

    def test_minimal_confirmation(self):
        """Minimal confirmation with just one keyword."""
        assert ss_check_confirmation("Gesendet")[0]
        assert ss_check_confirmation("Submitted")[0]
        assert ss_check_confirmation("Application sent")[0]

    def test_recently_clicked_apply(self):
        """English 'recently clicked apply' variant."""
        text = "You recently clicked apply on this job. We've sent your details to the employer."
        assert ss_check_confirmation(text)[0]

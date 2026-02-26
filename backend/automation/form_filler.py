"""Smart form detection and filling using fuzzy string matching."""
from thefuzz import fuzz
from playwright.async_api import Page
import asyncio
import random


async def fill_form(page: Page, profile: dict) -> dict:
    """
    Detect form fields on the current page and fill them using the profile's Q&A pairs.

    profile should contain:
        - questions_json: dict of {question_text: answer}
        - first_name, last_name, phone, city, etc. (direct fields)
    """
    questions = profile.get("questions_json", {})
    filled = 0
    errors = []

    try:
        # Get all visible input fields
        inputs = await page.query_selector_all(
            'input:visible, textarea:visible, select:visible'
        )

        for inp in inputs:
            try:
                input_type = await inp.get_attribute("type") or "text"
                if input_type in ("hidden", "submit", "button", "file"):
                    continue

                # Get label text for this input
                label_text = await _get_label(page, inp)
                if not label_text:
                    continue

                # Find best matching answer
                answer = _match_answer(label_text, questions, profile)
                if not answer:
                    continue

                # Fill the field
                if input_type == "checkbox":
                    if answer.lower() in ("yes", "ja", "true"):
                        await inp.check()
                elif await inp.evaluate("el => el.tagName") == "SELECT":
                    await _select_option(inp, answer)
                else:
                    await inp.fill("")
                    await inp.type(answer, delay=random.randint(30, 80))

                filled += 1
                await asyncio.sleep(random.uniform(0.3, 0.8))

            except Exception as e:
                errors.append(str(e))
                continue

        # Try to submit
        submit = await page.query_selector(
            'button[type="submit"], button:has-text("Absenden"), '
            'button:has-text("Bewerben"), button:has-text("Submit"), '
            'button:has-text("Apply")'
        )
        if submit:
            await submit.click()
            await page.wait_for_load_state("networkidle", timeout=10000)

        return {
            "status": "success" if filled > 0 else "failed",
            "fields_filled": filled,
            "errors": errors,
        }

    except Exception as e:
        return {"status": "failed", "error": str(e), "fields_filled": filled}


async def _get_label(page: Page, inp) -> str:
    """Get the label text for an input field."""
    # Try aria-label
    label = await inp.get_attribute("aria-label")
    if label:
        return label.strip().lower()

    # Try placeholder
    label = await inp.get_attribute("placeholder")
    if label:
        return label.strip().lower()

    # Try associated <label>
    inp_id = await inp.get_attribute("id")
    if inp_id:
        label_el = await page.query_selector(f'label[for="{inp_id}"]')
        if label_el:
            return (await label_el.inner_text()).strip().lower()

    # Try name attribute
    name = await inp.get_attribute("name")
    if name:
        return name.replace("_", " ").replace("-", " ").strip().lower()

    return ""


def _match_answer(label: str, questions: dict, profile: dict) -> str | None:
    """Fuzzy match a label to the best answer from questions or profile fields."""
    label_lower = label.lower()

    # Direct profile field mapping
    field_map = {
        "first name": "first_name", "vorname": "first_name",
        "last name": "last_name", "nachname": "last_name",
        "phone": "phone", "telefon": "phone", "mobile": "phone",
        "city": "city", "stadt": "city", "ort": "city",
        "zip": "zip_code", "plz": "zip_code", "postal": "zip_code",
        "street": "street_address", "strasse": "street_address", "address": "street_address",
        "salary": "salary_expectation", "gehalt": "salary_expectation",
        "experience": "years_experience", "erfahrung": "years_experience",
        "linkedin": "linkedin_url",
    }

    for key, field in field_map.items():
        if key in label_lower:
            val = profile.get(field)
            if val is not None:
                return str(val)

    # Fuzzy match against questions database
    best_score = 0
    best_answer = None
    for question, answer in questions.items():
        score = fuzz.partial_ratio(label_lower, question.lower())
        if score > best_score and score >= 70:
            best_score = score
            best_answer = answer

    return best_answer


async def _select_option(select_el, answer: str):
    """Select the best matching option in a <select> element."""
    options = await select_el.query_selector_all("option")
    best_score = 0
    best_value = None
    for opt in options:
        text = (await opt.inner_text()).strip()
        value = await opt.get_attribute("value")
        score = fuzz.partial_ratio(answer.lower(), text.lower())
        if score > best_score:
            best_score = score
            best_value = value
    if best_value and best_score >= 60:
        await select_el.select_option(value=best_value)

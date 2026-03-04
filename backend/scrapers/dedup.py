"""Cross-platform job deduplication via normalized hashing."""

import hashlib
import re
import unicodedata


def _normalize(text: str) -> str:
    """Normalize text for dedup: lowercase, strip gender markers, normalize umlauts."""
    if not text:
        return ""
    # Normalize unicode (ä → ae style via NFKD decomposition)
    text = unicodedata.normalize("NFKD", text.lower())
    # Remove common German gender markers: (m/w/d), (m/f/d), (m/w/x), (all/genders)
    text = re.sub(r"\s*\(m/[wf]/[dx]\)\s*", " ", text)
    text = re.sub(r"\s*\(all genders?\)\s*", " ", text, flags=re.IGNORECASE)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_description_hash(title: str, company: str, location: str) -> str:
    """SHA256 hash of normalized title+company+location for cross-platform dedup."""
    normalized = f"{_normalize(title)}|{_normalize(company)}|{_normalize(location)}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]

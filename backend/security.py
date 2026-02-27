"""Credential encryption and security utilities."""

import base64
import hashlib
import re
import time
from collections import defaultdict

from cryptography.fernet import Fernet

from .config import settings

# Derive a Fernet key from CREDENTIAL_KEY (must be 32 url-safe base64 bytes)
_fernet_key = base64.urlsafe_b64encode(
    hashlib.sha256(settings.CREDENTIAL_KEY.encode()).digest()
)
_fernet = Fernet(_fernet_key)


def encrypt_credential(plaintext: str) -> str:
    """Encrypt a platform credential for storage."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_credential(ciphertext: str) -> str:
    """Decrypt a stored platform credential."""
    return _fernet.decrypt(ciphertext.encode()).decode()


# ── Password complexity ──────────────────────────────────────────────────


def validate_password_strength(password: str) -> str | None:
    """Return an error message if password is too weak, else None."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one digit"
    return None


# ── Login rate limiting / lockout ────────────────────────────────────────

_login_attempts: dict[str, list[float]] = defaultdict(list)
LOCKOUT_WINDOW = 300  # 5 minutes
MAX_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes


def check_login_lockout(email: str) -> str | None:
    """Return error message if account is locked out, else None."""
    now = time.time()
    attempts = _login_attempts[email]
    # Prune old attempts
    _login_attempts[email] = [t for t in attempts if now - t < LOCKOUT_DURATION]
    attempts = _login_attempts[email]

    if len(attempts) >= MAX_ATTEMPTS:
        oldest_relevant = attempts[-MAX_ATTEMPTS]
        if now - oldest_relevant < LOCKOUT_DURATION:
            remaining = int(LOCKOUT_DURATION - (now - oldest_relevant))
            return f"Account temporarily locked. Try again in {remaining // 60} minutes."
    return None


def record_login_attempt(email: str) -> None:
    """Record a failed login attempt."""
    _login_attempts[email].append(time.time())


def clear_login_attempts(email: str) -> None:
    """Clear failed attempts after successful login."""
    _login_attempts.pop(email, None)

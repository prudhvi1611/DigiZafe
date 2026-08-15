"""Argon2id password hashing (OWASP / RFC 9106 aligned defaults)."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.profiles import RFC_9106_LOW_MEMORY  # good balance for most servers

from app.core.config import get_settings

# Use a sensible profile; can switch to HIGH_MEMORY later if hardware allows
_ph = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)
# Alternative explicit: PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID)


def hash_password(plain: str) -> str:
    settings = get_settings()
    if len(plain) < settings.password_min_length:
        raise ValueError(f"Password must be at least {settings.password_min_length} characters")
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """Call after successful verify; re-hash if parameters changed."""
    return _ph.check_needs_rehash(hashed)

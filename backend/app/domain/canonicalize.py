"""Identifier canonicalization (pure functions)."""
from __future__ import annotations

import re
import unicodedata
from enum import Enum

import idna


class IdentifierType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    USERNAME = "username"
    DOMAIN = "domain"
    GITHUB_USERNAME = "github_username"
    # Future: url, ip, etc. — not in Sprint 2 verification set


_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)
_PHONE_RE = re.compile(r"^\+[1-9]\d{6,14}$")  # E.164-ish
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]{0,38}[a-zA-Z0-9])?$")
_DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", re.I)


class CanonicalizationError(ValueError):
    pass


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()


def canonicalize_email(raw: str) -> str:
    v = normalize_unicode(raw).lower()
    if not _EMAIL_RE.match(v) or len(v) > 320:
        raise CanonicalizationError("Invalid email format")
    local, _, domain = v.partition("@")
    # Gmail-style optional normalization (dots + plus) for common providers
    if domain in {"gmail.com", "googlemail.com"}:
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    else:
        local = local.split("+", 1)[0]  # strip plus-tags generically
    # IDNA domain
    try:
        domain_idna = idna.encode(domain).decode("ascii")
    except idna.IDNAError as e:
        raise CanonicalizationError(f"Invalid email domain: {e}") from e
    return f"{local}@{domain_idna}"


def canonicalize_phone(raw: str) -> str:
    v = normalize_unicode(raw)
    # Strip spaces, dashes, parens
    digits = re.sub(r"[\s\-().]", "", v)
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if not digits.startswith("+"):
        # Assume needs country code — refuse bare local numbers for self-only safety
        raise CanonicalizationError("Phone must be E.164 with leading +country code")
    if not _PHONE_RE.match(digits):
        raise CanonicalizationError("Invalid phone (E.164 expected)")
    return digits


def canonicalize_username(raw: str) -> str:
    v = normalize_unicode(raw).lstrip("@").lower()
    if not _USERNAME_RE.match(v) or len(v) > 40:
        raise CanonicalizationError("Invalid username")
    return v


def canonicalize_domain(raw: str) -> str:
    v = normalize_unicode(raw).lower().rstrip(".")
    # Strip scheme/path if user pasted URL
    v = re.sub(r"^https?://", "", v)
    v = v.split("/")[0].split("?")[0].split("#")[0]
    if ":" in v:  # strip port
        host, _, port = v.rpartition(":")
        if port.isdigit():
            v = host
    if not v or len(v) > 253:
        raise CanonicalizationError("Invalid domain")
    labels = v.split(".")
    if len(labels) < 2:
        raise CanonicalizationError("Domain must include a public suffix (e.g. example.com)")
    for label in labels:
        if not _DOMAIN_LABEL_RE.match(label) and not label.startswith("xn--"):
            # allow punycode labels after idna
            pass
    try:
        return idna.encode(v).decode("ascii")
    except idna.IDNAError as e:
        raise CanonicalizationError(f"Invalid domain: {e}") from e


def canonicalize_github_username(raw: str) -> str:
    v = canonicalize_username(raw)
    # GitHub rules: max 39, alphanumeric/hyphen, no leading/trailing hyphen
    if v.startswith("-") or v.endswith("-") or "--" in v or len(v) > 39:
        raise CanonicalizationError("Invalid GitHub username")
    return v


def canonicalize(identifier_type: IdentifierType | str, raw: str) -> str:
    t = IdentifierType(identifier_type) if isinstance(identifier_type, str) else identifier_type
    if t == IdentifierType.EMAIL:
        return canonicalize_email(raw)
    if t == IdentifierType.PHONE:
        return canonicalize_phone(raw)
    if t == IdentifierType.USERNAME:
        return canonicalize_username(raw)
    if t == IdentifierType.DOMAIN:
        return canonicalize_domain(raw)
    if t == IdentifierType.GITHUB_USERNAME:
        return canonicalize_github_username(raw)
    raise CanonicalizationError(f"Unsupported type: {t}")


def display_redacted(identifier_type: IdentifierType | str, canonical: str) -> str:
    """Safe display form (partial redact) for UI/logs."""
    t = IdentifierType(identifier_type) if isinstance(identifier_type, str) else identifier_type
    if t == IdentifierType.EMAIL:
        local, _, domain = canonical.partition("@")
        if len(local) <= 2:
            return f"{local[0]}***@{domain}"
        return f"{local[:2]}***@{domain}"
    if t == IdentifierType.PHONE:
        return canonical[:4] + "****" + canonical[-2:]
    if t in (IdentifierType.USERNAME, IdentifierType.GITHUB_USERNAME):
        if len(canonical) <= 3:
            return canonical[0] + "***"
        return canonical[:2] + "***" + canonical[-1:]
    if t == IdentifierType.DOMAIN:
        return canonical
    return "***"

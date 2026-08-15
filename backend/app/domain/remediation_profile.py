"""Build redacted remediation profile from verified identifiers (pure)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RemediationProfile:
    """Fields used to fill Green opt-out forms — never store plaintext long-term beyond job."""
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    phone: str | None = None
    state: str | None = None
    city: str | None = None
    zip: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, Any]:
        """For audit/logs — redacted."""
        def red_email(e: str | None) -> str | None:
            if not e or "@" not in e:
                return None
            local, _, dom = e.partition("@")
            return f"{local[:2]}***@{dom}"
        return {
            "email": red_email(self.email),
            "has_name": bool(self.full_name or self.first_name),
            "has_phone": bool(self.phone),
            "state": self.state,
            "city": self.city,
        }


def split_name(full: str) -> tuple[str, str]:
    parts = full.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def build_profile_from_identifiers(
    identifiers: list[dict[str, Any]],
    *,
    display_name: str | None = None,
    state: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
) -> RemediationProfile:
    """
    identifiers: list of {type, value_canonical, is_verified}
    Only verified identifiers contribute (G1).
    """
    email = phone = None
    for i in identifiers:
        if not i.get("is_verified"):
            continue
        t = i.get("type")
        v = i.get("value_canonical") or ""
        if t == "email" and not email:
            email = v
        elif t == "phone" and not phone:
            phone = v
    first, last = ("", "")
    if display_name:
        first, last = split_name(display_name)
    return RemediationProfile(
        email=email,
        first_name=first or None,
        last_name=last or None,
        full_name=display_name,
        phone=phone,
        state=state,
        city=city,
        zip=zip_code,
    )

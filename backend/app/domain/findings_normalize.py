"""Normalize connector observations into durable finding shapes (pure)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class NormalizedFinding:
    """Ready to persist as Finding row."""

    kind: str  # breach | password_exposure | certificate | dns_rdap | profile | username_presence | serp | other
    source: str  # connector id e.g. xposedornot
    title: str
    summary: str
    severity_hint: str  # low | medium | high | critical | info
    confidence: float
    layer: str  # surface | deep | constrained_dark
    fingerprint: str  # stable dedupe key within (user, identifier, source)
    raw_ref: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    attribution: str | None = None
    observed_at: datetime | None = None
    track: str = "confirmed"  # confirmed | possible — for two-track PDSS later


def _severity_for_breach(attrs: dict[str, Any], confidence: float) -> str:
    risk = str(attrs.get("risk_label") or attrs.get("password_risk") or "").lower()
    if risk in {"high", "critical", "plaintext", "easytocrack"}:
        return "high"
    if risk in {"medium", "moderate"}:
        return "medium"
    if "password" in str(attrs.get("xposed_data") or "").lower():
        return "high"
    if confidence >= 0.9:
        return "medium"
    return "low"


def _fingerprint(source: str, kind: str, raw_ref: str | None, title: str) -> str:
    import hashlib

    base = f"{source}|{kind}|{(raw_ref or title).strip().lower()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]


def normalize_observation(obs: dict[str, Any]) -> NormalizedFinding:
    """
    Accepts RawObservation.to_dict() or equivalent.
    XposedOrNot drivers: breach_name, risk_label, xposed_data, xposed_date, etc.
    """
    kind = str(obs.get("kind") or "other")
    source = str(obs.get("source") or "unknown")
    title = str(obs.get("title") or "Finding")
    summary = str(obs.get("summary") or "")
    confidence = float(obs.get("confidence") or 0.5)
    layer = str(obs.get("layer") or "surface")
    raw_ref = obs.get("raw_ref")
    attrs = dict(obs.get("attributes") or {})
    attribution = obs.get("attribution")

    observed_at = None
    if obs.get("observed_at"):
        try:
            raw = obs["observed_at"]
            if isinstance(raw, datetime):
                observed_at = raw
            else:
                observed_at = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            observed_at = datetime.now(UTC)
    else:
        observed_at = datetime.now(UTC)

    if kind == "breach":
        severity = _severity_for_breach(attrs, confidence)
        # Prefer structured breach name
        if attrs.get("breach_name") and not raw_ref:
            raw_ref = str(attrs["breach_name"])
        track = "confirmed" if confidence >= 0.8 else "possible"
    elif kind == "password_exposure":
        severity = "critical" if int(attrs.get("count") or 0) > 10 else "high"
        track = "confirmed"
    elif kind in {"certificate", "dns_rdap"}:
        severity = "info"
        track = "confirmed" if confidence >= 0.7 else "possible"
    elif kind in {"profile", "username_presence"}:
        severity = "low"
        track = "possible" if confidence < 0.85 else "confirmed"
    elif kind == "serp":
        severity = "info"
        track = "possible"
    elif kind == "archived_metadata":
        severity = "info"
        track = "possible"
        attrs.setdefault("historical_or_indexed", True)
        attrs.setdefault("current_exposure_unproven", True)
    elif kind == "public_index_signal":
        severity = "medium" if confidence >= 0.6 else "low"
        track = "possible"
        attrs.setdefault("metadata_only", True)
        attrs.setdefault("raw_content_retrieved", False)
        attrs.setdefault("current_exposure_unproven", True)
    else:
        severity = "info"
        track = "possible"

    fp = _fingerprint(source, kind, str(raw_ref) if raw_ref else None, title)

    return NormalizedFinding(
        kind=kind,
        source=source,
        title=title[:512],
        summary=summary[:4000],
        severity_hint=severity,
        confidence=max(0.0, min(1.0, confidence)),
        layer=layer,
        fingerprint=fp,
        raw_ref=str(raw_ref)[:512] if raw_ref else None,
        attributes=attrs,
        attribution=str(attribution)[:512] if attribution else None,
        observed_at=observed_at,
        track=track,
    )


def normalize_connector_result_observations(
    observations: list[dict[str, Any]],
) -> list[NormalizedFinding]:
    out: list[NormalizedFinding] = []
    seen: set[str] = set()
    for o in observations:
        if not isinstance(o, dict):
            continue
        nf = normalize_observation(o)
        if nf.fingerprint in seen:
            continue
        seen.add(nf.fingerprint)
        out.append(nf)
    return out

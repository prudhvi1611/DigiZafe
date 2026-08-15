"""Load Green broker registry from shared/config."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _candidates(path: str) -> list[Path]:
    p = Path(path)
    return [
        p,
        Path("/app") / p,
        Path("/app/shared/config/broker_registry") / p.name,
        Path("shared/config/broker_registry") / p.name,
        Path("shared/config/broker_registry/brokers_green.json"),
    ]


@lru_cache
def load_broker_registry() -> dict[str, Any]:
    settings = get_settings()
    for c in _candidates(settings.broker_registry_path):
        if c.exists():
            with c.open("r", encoding="utf-8") as f:
                return json.load(f)
    return {
        "registry_version": "empty",
        "brokers": [],
        "freeze_targets": [],
        "generic_strategies": [],
    }


def list_green_brokers(*, enabled_only: bool = True) -> list[dict[str, Any]]:
    reg = load_broker_registry()
    out = []
    for b in reg.get("brokers") or []:
        if b.get("legality", "green") != "green":
            continue
        if enabled_only and not b.get("enabled", True):
            continue
        out.append(b)
    return out


def get_broker(broker_id: str) -> dict[str, Any] | None:
    for b in list_green_brokers(enabled_only=False):
        if b.get("id") == broker_id:
            return b
    return None


def freeze_targets() -> list[dict[str, Any]]:
    return list(load_broker_registry().get("freeze_targets") or [])


def clear_registry_cache() -> None:
    load_broker_registry.cache_clear()

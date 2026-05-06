"""Deterministic JSON canonicalization and SHA-256 event hashing."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any, Mapping

from jep_runtime.core.event import JEPEvent


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        return {unicodedata.normalize("NFC", str(k)): _normalize(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize(v) for v in value]
    return value


def canonicalize_event(event: JEPEvent | Mapping[str, Any], *, include_hash: bool = False) -> bytes:
    """Canonicalize an event as UTF-8 JSON with stable ordering and no whitespace."""

    if isinstance(event, JEPEvent):
        data = event.to_dict(include_hash=include_hash)
    else:
        data = dict(event)
        if not include_hash:
            data.pop("event_hash", None)
    normalized = _normalize(data)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_event_hash(event: JEPEvent | Mapping[str, Any]) -> str:
    """Compute a platform-stable SHA-256 hash over canonical event JSON."""

    return hashlib.sha256(canonicalize_event(event, include_hash=False)).hexdigest()

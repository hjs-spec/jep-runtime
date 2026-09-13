"""Append-only JSONL archive runtime."""

from __future__ import annotations

import json
from pathlib import Path
from filelock import FileLock
from jep_runtime.canonicalization.json import compute_event_hash
from typing import Iterable

from jep_runtime.core.event import JEPEvent
from jep_runtime.replay.engine import replay_events
from jep_runtime.verification.runtime import VerificationResult, verify_chain


class JSONLArchive:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self.path) + ".lock", timeout=10)

    def append_event(self, event: JEPEvent) -> None:
        with self._lock:
            existing = self.import_archive()
            previous = None
            ids = set()
            for candidate in [*existing, event]:
                if candidate.event_hash != compute_event_hash(candidate) or candidate.previous_event_hash != previous:
                    raise ValueError("archive hash mismatch or stale previous_event_hash")
                if candidate.event_id in ids:
                    raise ValueError("duplicate event identifier")
                ids.add(candidate.event_id)
                previous = candidate.event_hash
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n")

    def import_archive(self) -> list[JEPEvent]:
        with self._lock:
            return self._read_archive()

    def _read_archive(self) -> list[JEPEvent]:
        if not self.path.exists():
            return []
        events: list[JEPEvent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    events.append(JEPEvent.from_dict(json.loads(line)))
        return events

    def export_archive(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.path.exists() else ""

    def verify_archive(self) -> VerificationResult:
        return verify_chain(self.import_archive())

    def replay_archive(self) -> dict:
        return replay_events(self.import_archive())


def append_event(path: str | Path, event: JEPEvent) -> None:
    JSONLArchive(path).append_event(event)


def import_archive(path: str | Path) -> list[JEPEvent]:
    return JSONLArchive(path).import_archive()


def export_archive(path: str | Path) -> str:
    return JSONLArchive(path).export_archive()


def verify_archive(path: str | Path) -> VerificationResult:
    return JSONLArchive(path).verify_archive()


def replay_archive(path: str | Path) -> dict:
    return JSONLArchive(path).replay_archive()

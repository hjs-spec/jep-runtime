"""Append-only JSONL archive runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from jep_runtime.core.event import JEPEvent
from jep_runtime.replay.engine import replay_events
from jep_runtime.verification.runtime import VerificationResult, verify_chain


class JSONLArchive:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append_event(self, event: JEPEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")

    def import_archive(self) -> list[JEPEvent]:
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

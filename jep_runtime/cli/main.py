"""Command line interface for the JEP Reference Runtime."""

from __future__ import annotations

import argparse
import json
import sys

from jep_runtime.archive.jsonl import JSONLArchive
from jep_runtime.conformance.runtime import run_conformance
from jep_runtime.core.event import JEPEvent
from jep_runtime.events.factory import create_event
from jep_runtime.replay.engine import replay_events
from jep_runtime.verification.runtime import verify_event


def _load_event(path: str) -> JEPEvent:
    with open(path, "r", encoding="utf-8") as handle:
        return JEPEvent.from_dict(json.load(handle))


def _print(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jep", description="JEP Reference Runtime CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-event", help="Create and hash a J/D/T/V event")
    create.add_argument("--type", required=True, choices=["J", "D", "T", "V"])
    create.add_argument("--actor", required=True)
    create.add_argument("--subject", required=True)
    create.add_argument("--agent-id")
    create.add_argument("--session-id")
    create.add_argument("--scope-json", default="{}")
    create.add_argument("--intent-json", default="{}")
    create.add_argument("--justification", default="")
    create.add_argument("--previous-event-hash")
    create.add_argument("--profile", default="mock")
    create.add_argument("--credential-reference")
    create.add_argument("--archive", help="Append created event to JSONL archive")

    verify = sub.add_parser("verify", help="Verify one event JSON file")
    verify.add_argument("event")

    replay = sub.add_parser("replay", help="Replay a JSONL archive")
    replay.add_argument("archive")

    archive_verify = sub.add_parser("archive-verify", help="Verify an append-only JSONL archive")
    archive_verify.add_argument("archive")

    sub.add_parser("conformance-test", help="Run conformance suite and emit vectors/report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "create-event":
        event = create_event(
            args.type,
            actor=args.actor,
            subject=args.subject,
            agent_id=args.agent_id,
            session_id=args.session_id,
            authority_scope=json.loads(args.scope_json),
            intent=json.loads(args.intent_json),
            justification=args.justification,
            previous_event_hash=args.previous_event_hash,
            profile=args.profile,
            credential_reference=args.credential_reference,
        )
        if args.archive:
            JSONLArchive(args.archive).append_event(event)
        _print(event.to_dict())
        return 0
    if args.command == "verify":
        result = verify_event(_load_event(args.event))
        _print({"valid": result.valid, "errors": list(result.errors)})
        return 0 if result.valid else 1
    if args.command == "replay":
        archive = JSONLArchive(args.archive)
        _print(archive.replay_archive())
        return 0 if archive.verify_archive().valid else 1
    if args.command == "archive-verify":
        result = JSONLArchive(args.archive).verify_archive()
        _print({"valid": result.valid, "errors": list(result.errors)})
        return 0 if result.valid else 1
    if args.command == "conformance-test":
        report = run_conformance()
        _print(report)
        return 0 if report["passed"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

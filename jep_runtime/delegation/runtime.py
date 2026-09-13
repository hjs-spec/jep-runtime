"""Delegation authority propagation runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from jep_runtime.core.event import EventType, JEPEvent
from jep_runtime.events.factory import create_event


def _scope_items(scope: Mapping[str, Any]) -> dict[str, Any]:
    return dict(scope or {})


def validate_scope(
    parent_scope: Mapping[str, Any],
    child_scope: Mapping[str, Any],
    *,
    now: int | None = None,
) -> bool:
    """Return true when child_scope is bounded by parent_scope."""

    if not isinstance(parent_scope, Mapping) or not isinstance(child_scope, Mapping):
        return False
    parent, child = dict(parent_scope), dict(child_scope)
    # This local runtime profile grants only explicitly listed capabilities.
    for dimension in ("actions", "resources"):
        parent_items, child_items = parent.get(dimension, []), child.get(dimension, [])
        if not isinstance(parent_items, (list, tuple)) or not isinstance(
            child_items, (list, tuple)
        ):
            return False
        if not all(isinstance(item, str) for item in [*parent_items, *child_items]):
            return False
        if not set(child_items).issubset(parent_items):
            return False
    # Unknown constraints may be preserved but never added, changed, or dropped.
    for key in (parent.keys() | child.keys()) - {"actions", "resources", "valid_until"}:
        if key not in parent or key not in child or child[key] != parent[key]:
            return False
    parent_until, child_until = parent.get("valid_until"), child.get("valid_until")
    if any(
        value is not None and type(value) is not int
        for value in (parent_until, child_until)
    ):
        return False
    if parent_until is not None and (child_until is None or child_until > parent_until):
        return False
    effective_now = int(datetime.now(timezone.utc).timestamp()) if now is None else now
    if type(effective_now) is not int:
        return False
    return all(
        value is None or effective_now < value for value in (parent_until, child_until)
    )


def delegate_authority(
    parent_event: JEPEvent,
    *,
    delegatee: str,
    agent_id: str | None,
    scope: Mapping[str, Any],
    justification: str = "",
) -> JEPEvent:
    """Create a scoped delegation event from parent authority to a delegatee."""

    if not validate_scope(
        parent_event.authority_scope, scope, now=parent_event.timestamp + 1
    ):
        raise ValueError("delegation scope exceeds or outlives parent authority")
    chain = [*parent_event.delegation_chain, parent_event.event_hash or ""]
    return create_event(
        EventType.DELEGATION,
        actor=parent_event.subject,
        subject=delegatee,
        agent_id=agent_id,
        session_id=parent_event.session_id,
        delegation_chain=chain,
        authority_scope=scope,
        intent={"delegatee": delegatee, "parent_event_hash": parent_event.event_hash},
        justification=justification,
        previous_event_hash=parent_event.event_hash,
        profile=parent_event.profile,
        credential_reference=parent_event.credential_reference,
        timestamp=parent_event.timestamp + 1,
    )


def verify_delegation_chain(events: Iterable[JEPEvent]) -> tuple[bool, list[str]]:
    """Verify hash lineage and bounded delegation scopes for a sequence."""

    problems: list[str] = []
    previous: JEPEvent | None = None
    seen_hashes: set[str] = set()
    by_hash: dict[str, JEPEvent] = {}
    seen_ids: set[str] = set()
    for event in events:
        if event.event_id in seen_ids:
            problems.append(f"duplicate event id: {event.event_id}")
        seen_ids.add(event.event_id)
        if event.event_hash in seen_hashes:
            problems.append(f"duplicate event hash: {event.event_hash}")
        if event.event_hash:
            seen_hashes.add(event.event_hash)
        if previous:
            if event.previous_event_hash != previous.event_hash:
                problems.append(f"hash continuity break at {event.event_id}")

        if event.event_type == EventType.DELEGATION:
            parent_hash = event.intent.get("parent_event_hash")
            parent = by_hash.get(parent_hash) if isinstance(parent_hash, str) else None
            if parent is None:
                problems.append(f"unresolved delegation parent at {event.event_id}")
            else:
                if (
                    event.actor != parent.subject
                    or event.session_id != parent.session_id
                ):
                    problems.append(
                        f"delegation actor/session mismatch at {event.event_id}"
                    )
                if event.timestamp < parent.timestamp:
                    problems.append(f"delegation precedes parent at {event.event_id}")
                if event.delegation_chain != (
                    *parent.delegation_chain,
                    parent.event_hash,
                ):
                    problems.append(f"delegation ancestry mismatch at {event.event_id}")
                if not validate_scope(
                    parent.authority_scope, event.authority_scope, now=event.timestamp
                ):
                    problems.append(f"scope violation at {event.event_id}")
        if event.event_hash:
            by_hash[event.event_hash] = event
        previous = event
    return not problems, problems

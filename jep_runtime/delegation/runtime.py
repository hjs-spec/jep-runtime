"""Delegation authority propagation runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from jep_runtime.core.event import EventType, JEPEvent
from jep_runtime.events.factory import create_event


def _scope_items(scope: Mapping[str, Any]) -> dict[str, Any]:
    return dict(scope or {})


def validate_scope(parent_scope: Mapping[str, Any], child_scope: Mapping[str, Any], *, now: int | None = None) -> bool:
    """Return true when child_scope is bounded by parent_scope."""

    parent = _scope_items(parent_scope)
    child = _scope_items(child_scope)
    if not child:
        return True
    parent_actions = set(parent.get("actions", child.get("actions", [])))
    child_actions = set(child.get("actions", []))
    if child_actions and not child_actions.issubset(parent_actions):
        return False
    parent_resources = set(parent.get("resources", child.get("resources", [])))
    child_resources = set(child.get("resources", []))
    if child_resources and not child_resources.issubset(parent_resources):
        return False
    parent_until = parent.get("valid_until")
    child_until = child.get("valid_until")
    if parent_until is not None and child_until is not None and int(child_until) > int(parent_until):
        return False
    effective_now = int(datetime.now(timezone.utc).timestamp()) if now is None else now
    if parent_until is not None and int(parent_until) < effective_now:
        return False
    return True


def delegate_authority(parent_event: JEPEvent, *, delegatee: str, agent_id: str | None, scope: Mapping[str, Any], justification: str = "") -> JEPEvent:
    """Create a scoped delegation event from parent authority to a delegatee."""

    if not validate_scope(parent_event.authority_scope, scope, now=parent_event.timestamp):
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
    for event in events:
        if event.event_hash in seen_hashes:
            problems.append(f"duplicate event hash: {event.event_hash}")
        if event.event_hash:
            seen_hashes.add(event.event_hash)
        if previous:
            if event.previous_event_hash != previous.event_hash:
                problems.append(f"hash continuity break at {event.event_id}")
            if event.event_type == EventType.DELEGATION and not validate_scope(previous.authority_scope, event.authority_scope, now=event.timestamp):
                problems.append(f"scope violation at {event.event_id}")
        previous = event
    return not problems, problems

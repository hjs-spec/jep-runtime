"""Factory helpers for creating hashed JEP events."""

from __future__ import annotations

from typing import Any, Mapping
import uuid

from jep_runtime.canonicalization.json import compute_event_hash
from jep_runtime.core.event import EventType, JEPEvent


def create_event(
    event_type: EventType | str,
    *,
    actor: str,
    subject: str,
    agent_id: str | None = None,
    session_id: str | None = None,
    delegation_chain: list[str] | tuple[str, ...] | None = None,
    authority_scope: Mapping[str, Any] | None = None,
    intent: Mapping[str, Any] | None = None,
    justification: str = "",
    previous_event_hash: str | None = None,
    nonce: str | None = None,
    timestamp: int | None = None,
    profile: str = "mock",
    credential_reference: str | None = None,
    verification_state: Mapping[str, Any] | None = None,
) -> JEPEvent:
    event = JEPEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        actor=actor,
        subject=subject,
        agent_id=agent_id,
        session_id=session_id or str(uuid.uuid4()),
        delegation_chain=tuple(delegation_chain or ()),
        authority_scope=dict(authority_scope or {}),
        intent=dict(intent or {}),
        justification=justification,
        previous_event_hash=previous_event_hash,
        nonce=nonce or str(uuid.uuid4()),
        timestamp=timestamp or 0,
        profile=profile,
        credential_reference=credential_reference,
        verification_state=dict(verification_state or {}),
    )
    return event.with_hash(compute_event_hash(event))

"""Replay engine that reconstructs lineage, authority, and termination state."""

from __future__ import annotations

from jep_runtime.core.event import EventType, JEPEvent
from jep_runtime.verification.runtime import verify_chain
from jep_runtime.delegation.termination import TerminationState


def replay_events(events: list[JEPEvent]) -> dict:
    verification = verify_chain(events)
    nodes = []
    edges = []
    authority_lineage: dict[str, dict] = {}
    termination = TerminationState()
    for event in events:
        nodes.append({
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "event_type": event.event_type.value,
            "actor": event.actor,
            "subject": event.subject,
            "scope": dict(event.authority_scope),
        })
        if event.previous_event_hash:
            edges.append({"from": event.previous_event_hash, "to": event.event_hash, "type": "hash_chain"})
        for parent in event.delegation_chain:
            edges.append({"from": parent, "to": event.event_hash, "type": "delegation"})
        if event.event_type in (EventType.JUDGMENT, EventType.DELEGATION) and not termination.rejects(event):
            authority_lineage[event.subject] = {
                "event_hash": event.event_hash,
                "scope": dict(event.authority_scope),
                "delegation_chain": list(event.delegation_chain),
            }
        termination.observe(event)
        authority_lineage = {
            subject: grant for subject, grant in authority_lineage.items()
            if grant["event_hash"] not in termination.revoked_hashes
        }
    return {
        "valid": verification.valid,
        "errors": list(verification.errors),
        "lineage_graph": {"nodes": nodes, "edges": edges},
        "authority_lineage": authority_lineage,
        "termination_state": sorted({subject for _, subject in termination.terminated}),
    }

"""Conformance vectors and checks for interoperable JEP runtimes."""

from __future__ import annotations

from jep_runtime.canonicalization.json import canonicalize_event, compute_event_hash
from jep_runtime.core.event import EventType
from jep_runtime.delegation.runtime import delegate_authority, verify_delegation_chain
from jep_runtime.events.factory import create_event
from jep_runtime.profiles.adapter import MockProfileAdapter
from jep_runtime.replay.engine import replay_events
from jep_runtime.verification.runtime import verify_chain, verify_event


def generate_test_vectors() -> dict:
    adapter = MockProfileAdapter()
    ref = adapter.issue_reference("human:alice", "mock")
    root = create_event(
        EventType.JUDGMENT,
        actor="human:alice",
        subject="agent:planner",
        agent_id="agent:planner",
        session_id="session:conformance",
        authority_scope={"actions": ["read", "summarize"], "resources": ["repo:jep"], "valid_until": 4102444800},
        intent={"task": "summarize current JEP draft"},
        justification="human delegated bounded judgment authority",
        timestamp=1700000000,
        nonce="00000000-0000-4000-8000-000000000001",
        profile="mock",
        credential_reference=ref,
    )
    child = delegate_authority(root, delegatee="agent:worker", agent_id="agent:worker", scope={"actions": ["read"], "resources": ["repo:jep"], "valid_until": 4102444700})
    verify = create_event(
        EventType.VERIFICATION,
        actor="verifier:local",
        subject=child.subject,
        agent_id=child.agent_id,
        session_id=root.session_id,
        delegation_chain=child.delegation_chain,
        authority_scope=child.authority_scope,
        intent={"target_event_hash": child.event_hash, "result": "VALID"},
        previous_event_hash=child.event_hash,
        timestamp=child.timestamp + 1,
        nonce="00000000-0000-4000-8000-000000000003",
        profile="mock",
        credential_reference=ref,
    )
    return {
        "events": [root.to_dict(), child.to_dict(), verify.to_dict()],
        "canonical_root": canonicalize_event(root).decode("utf-8"),
        "root_hash": root.event_hash,
    }


def run_conformance() -> dict:
    vectors = generate_test_vectors()
    reconstructed = [__import__("jep_runtime.core.event", fromlist=["JEPEvent"]).JEPEvent.from_dict(e) for e in vectors["events"]]
    matrix = {
        "canonicalization": canonicalize_event(reconstructed[0]).decode("utf-8") == vectors["canonical_root"],
        "deterministic_hashing": compute_event_hash(reconstructed[0]) == vectors["root_hash"],
        "delegation_semantics": verify_delegation_chain(reconstructed[:2])[0],
        "verification_semantics": verify_event(reconstructed[2]).valid,
        "profile_compatibility": verify_chain(reconstructed).valid,
        "replay_correctness": replay_events(reconstructed)["valid"],
    }
    return {
        "passed": all(matrix.values()),
        "matrix": matrix,
        "test_vectors": vectors,
        "signed_vectors": {"mode": "mock", "signature": "mock-signature-over-canonical-vectors"},
        "compatibility_report": "reference runtime uses stable UTF-8 sorted JSON, SHA-256, JSONL archives, and neutral mock profiles",
    }

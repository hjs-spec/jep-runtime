import json

from jep_runtime.archive.jsonl import JSONLArchive
from jep_runtime.canonicalization.json import canonicalize_event, compute_event_hash
from jep_runtime.conformance.runtime import run_conformance
from jep_runtime.core.event import EventType, JEPEvent
from jep_runtime.delegation.runtime import delegate_authority, validate_scope
from jep_runtime.events.factory import create_event
from jep_runtime.verification.runtime import detect_tampering, verify_chain, verify_event


def test_canonical_hash_is_whitespace_independent():
    event = create_event(
        EventType.JUDGMENT,
        actor="human:alice",
        subject="agent:planner",
        session_id="s",
        authority_scope={"b": ["β"], "a": "é"},
        intent={"task": "judge"},
        timestamp=1,
        nonce="n1",
    )
    shuffled = event.to_dict()
    assert json.loads(json.dumps(shuffled, indent=4)) == shuffled
    assert compute_event_hash(shuffled) == event.event_hash
    assert b" " not in canonicalize_event(event)


def test_delegation_scope_and_chain_verification():
    root = create_event(
        "J",
        actor="human:alice",
        subject="agent:planner",
        session_id="s",
        authority_scope={"actions": ["read", "write"], "resources": ["repo"], "valid_until": 99},
        timestamp=10,
        nonce="n1",
    )
    child = delegate_authority(root, delegatee="agent:worker", agent_id="agent:worker", scope={"actions": ["read"], "resources": ["repo"], "valid_until": 90})
    assert validate_scope(root.authority_scope, child.authority_scope, now=10)
    assert verify_chain([root, child]).valid


def test_tamper_detection_recomputes_hash():
    event = create_event("J", actor="a", subject="b", timestamp=1, nonce="n1")
    data = event.to_dict()
    data["subject"] = "attacker"
    tampered = JEPEvent.from_dict(data)
    assert not verify_event(tampered).valid
    assert detect_tampering([tampered])


def test_archive_replay_verifies_full_chain(tmp_path):
    archive = JSONLArchive(tmp_path / "archive.jsonl")
    root = create_event("J", actor="human", subject="agent", session_id="s", timestamp=1, nonce="n1")
    verification = create_event("V", actor="verifier", subject="agent", session_id="s", previous_event_hash=root.event_hash, timestamp=2, nonce="n2")
    archive.append_event(root)
    archive.append_event(verification)
    assert archive.verify_archive().valid
    replay = archive.replay_archive()
    assert replay["valid"]
    assert len(replay["lineage_graph"]["nodes"]) == 2


def test_conformance_suite_passes():
    report = run_conformance()
    assert report["passed"]
    assert all(report["matrix"].values())

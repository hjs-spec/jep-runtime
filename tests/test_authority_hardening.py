from dataclasses import replace
from jep_runtime.events.factory import create_event
from jep_runtime.delegation.runtime import validate_scope, delegate_authority, verify_delegation_chain
from jep_runtime.verification.runtime import verify_profile


def test_scope_cannot_gain_capability_or_drop_expiry():
    assert not validate_scope({}, {"actions": ["admin"]}, now=1)
    assert not validate_scope({"valid_until": 10}, {}, now=1)
    assert not validate_scope({"valid_until": 10}, {"valid_until": 10}, now=10)
    assert not validate_scope({}, {"valid_until": 0}, now=1)
    assert not validate_scope({"actions": "read"}, {"actions": ["read"]}, now=1)
    assert not validate_scope({"tenant": "a"}, {}, now=1)


def test_parent_is_resolved_by_hash_and_actor_checked():
    root = create_event("J", actor="owner", subject="planner", session_id="s", timestamp=1,
                        authority_scope={"actions": ["read"]})
    child = delegate_authority(root, delegatee="worker", agent_id="worker", scope={"actions": ["read"]})
    unrelated = create_event("V", actor="auditor", subject="planner", session_id="s", timestamp=2,
                             previous_event_hash=root.event_hash)
    child = replace(child, previous_event_hash=unrelated.event_hash)
    assert verify_delegation_chain([root, unrelated, child])[0]
    assert not verify_delegation_chain([root, unrelated, replace(child, actor="attacker")])[0]
    assert not verify_delegation_chain([root, replace(child, delegation_chain=[])])[0]


def test_non_mock_profiles_require_real_adapter_and_credential():
    event = create_event("J", actor="owner", subject="agent", profile="oauth-oidc")
    assert not verify_profile(event).valid
    mock = create_event("J", actor="owner", subject="agent")
    assert verify_profile(mock).valid
    assert not verify_profile(mock).profile_checked


def test_archive_rejects_stale_tail_without_writing(tmp_path):
    import pytest
    from jep_runtime.archive.jsonl import JSONLArchive
    archive = JSONLArchive(tmp_path / "events.jsonl")
    root = create_event("J", actor="a", subject="b")
    archive.append_event(root)
    before = archive.export_archive()
    stale = create_event("J", actor="a", subject="b")
    with pytest.raises(ValueError): archive.append_event(stale)
    assert archive.export_archive() == before

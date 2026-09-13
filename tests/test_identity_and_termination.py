from dataclasses import replace

import pytest

from jep_runtime.delegation.runtime import delegate_authority
from jep_runtime.events.factory import create_event
from jep_runtime.replay.engine import replay_events
from jep_runtime.verification.runtime import verify_chain, verify_event


class AliceAdapter:
    def verify_reference(self, reference, profile):
        return reference == "credential:alice" and profile == "local-iam"

    def resolve_identity(self, reference):
        return "alice"

    def validate_authority(self, reference, scope):
        return tuple(scope.get("actions", ())) == ("read",)


def test_credential_must_resolve_to_event_actor():
    event = create_event(
        "J",
        actor="alice",
        subject="file",
        profile="local-iam",
        credential_reference="credential:alice",
        authority_scope={"actions": ["read"]},
    )
    assert verify_event(event, adapter=AliceAdapter()).profile_checked
    assert verify_chain([event], adapter=AliceAdapter()).profile_checked
    forged = replace(event, actor="bob", event_hash=None)
    from jep_runtime.canonicalization.json import compute_event_hash

    forged = forged.with_hash(compute_event_hash(forged))
    result = verify_event(forged, adapter=AliceAdapter())
    assert not result.valid and not result.profile_checked
    assert "identity" in result.errors[0]


def test_adapter_failure_is_unverified():
    class Unavailable(AliceAdapter):
        def resolve_identity(self, reference):
            raise RuntimeError("identity provider unavailable")

    event = create_event(
        "J",
        actor="alice",
        subject="file",
        profile="local-iam",
        credential_reference="credential:alice",
    )
    assert not verify_event(event, adapter=Unavailable()).valid


def test_delegation_does_not_reuse_parent_actors_credential():
    root = create_event(
        "J",
        actor="human",
        subject="alice",
        profile="local-iam",
        credential_reference="credential:human",
        authority_scope={"actions": ["read"]},
    )
    child = delegate_authority(
        root, delegatee="worker", agent_id="worker", scope=root.authority_scope
    )
    assert child.credential_reference is None
    assert not verify_event(child, adapter=AliceAdapter()).valid
    child = delegate_authority(
        root,
        delegatee="worker",
        agent_id="worker",
        scope=root.authority_scope,
        credential_reference="credential:alice",
    )
    assert verify_event(child, adapter=AliceAdapter()).valid


@pytest.fixture
def terminated_chain():
    scope = {"actions": ["read"], "resources": ["file"], "valid_until": 2000}
    root = create_event(
        "J",
        actor="human",
        subject="owner",
        session_id="s",
        timestamp=1000,
        authority_scope=scope,
    )
    worker = delegate_authority(
        root, delegatee="worker", agent_id="worker", scope=scope
    )
    descendant = delegate_authority(
        worker, delegatee="child", agent_id="child", scope=scope
    )
    terminated = create_event(
        "T",
        actor="owner",
        subject="worker",
        session_id="s",
        timestamp=1003,
        previous_event_hash=descendant.event_hash,
    )
    return [root, worker, descendant, terminated]


@pytest.mark.parametrize("actor", ["worker", "child"])
@pytest.mark.parametrize("verb", ["J", "D"])
def test_terminated_actors_and_descendants_cannot_continue(
    terminated_chain, actor, verb
):
    events = terminated_chain
    assert verify_chain(events).valid
    use = create_event(
        verb,
        actor=actor,
        subject="file",
        session_id="s",
        timestamp=1004,
        previous_event_hash=events[-1].event_hash,
    )
    result = verify_chain([*events, use])
    assert not result.valid
    assert any("terminated authority" in error for error in result.errors)
    replay = replay_events([*events, use])
    assert not replay["valid"]
    assert replay["termination_state"] == ["child", "worker"]
    assert set(replay["authority_lineage"]) == {"owner"}


def test_termination_is_session_local_and_audit_evidence_remains_valid(
    terminated_chain,
):
    events = terminated_chain
    for verb, session in [("J", "other-session"), ("V", "s")]:
        event = create_event(
            verb,
            actor="worker",
            subject="file",
            session_id=session,
            timestamp=1004,
            previous_event_hash=events[-1].event_hash,
        )
        assert verify_chain([*events, event]).valid


def test_terminated_grant_cannot_be_restored_in_same_session(terminated_chain):
    events = terminated_chain
    event = create_event(
        "J",
        actor="owner",
        subject="worker",
        session_id="s",
        timestamp=1004,
        previous_event_hash=events[-1].event_hash,
    )
    assert not verify_chain([*events, event]).valid
    assert "worker" not in replay_events([*events, event])["authority_lineage"]

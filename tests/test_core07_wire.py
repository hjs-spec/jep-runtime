from jep_runtime.core.wire07 import Core07ShapeError, event_identity, validate_core07_shape


def _base(verb="J", what=None):
    return {
        "jep": "1",
        "id": "urn:uuid:018f4f8d-7c63-7c2e-9b43-4ef657eec1c0",
        "verb": verb,
        "who": "did:example:alice",
        "when": 1700000000,
        "what": {"claim": "approve"} if what is None else what,
        "sig": "detached-jws",
    }


def test_event_identity_is_who_and_id():
    event = _base()
    assert event_identity(event) == (event["who"], event["id"])


def test_core_does_not_require_nonce():
    event = _base()
    validate_core07_shape(event)
    assert "nonce" not in event


def test_delegation_minimum():
    event = _base("D", {"delegatee": "did:example:bob", "scope": ["read"]})
    validate_core07_shape(event)


def test_termination_requires_ref_and_scope():
    event = _base("T", {"termination_scope": "future_reliance"})
    try:
        validate_core07_shape(event)
    except Core07ShapeError as exc:
        assert "T requires ref" in str(exc)
    else:
        raise AssertionError("expected Core07ShapeError")


def test_verification_requires_scope_result_and_ref():
    event = _base("V", {"verification_scope": ["cryptographic"], "result": "PASS"})
    event["ref"] = {
        "type": "jep:event",
        "value": {"who": "did:example:a", "id": "urn:uuid:x"},
    }
    validate_core07_shape(event)

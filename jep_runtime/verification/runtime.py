"""Replayable verification runtime for JEP event chains."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from jep_runtime.canonicalization.json import compute_event_hash
from jep_runtime.core.event import JEPEvent
from jep_runtime.delegation.runtime import verify_delegation_chain
from jep_runtime.profiles.adapter import MockProfileAdapter, ProfileAdapter


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    errors: tuple[str, ...] = ()
    profile_checked: bool = False


def verify_profile(event: JEPEvent, adapter: ProfileAdapter | None = None) -> VerificationResult:
    if (adapter is None or isinstance(adapter, MockProfileAdapter)) and event.profile != "mock":
        return VerificationResult(False, (f"no verifier configured for profile {event.profile}",))
    profile_adapter = adapter or MockProfileAdapter()
    if event.credential_reference is None:
        if event.profile == "mock":
            return VerificationResult(True)
        return VerificationResult(False, ("credential reference is required",))
    try:
        if not profile_adapter.verify_reference(event.credential_reference, event.profile):
            return VerificationResult(False, (f"invalid credential reference for profile {event.profile}",))
        identity = profile_adapter.resolve_identity(event.credential_reference)
        if not isinstance(identity, str) or not identity or identity != event.actor:
            return VerificationResult(False, ("credential identity does not match event actor",))
        if not profile_adapter.validate_authority(event.credential_reference, event.authority_scope):
            return VerificationResult(False, ("profile adapter rejected authority scope",))
    except Exception:
        return VerificationResult(False, ("profile adapter could not verify credential",))
    return VerificationResult(True, profile_checked=not isinstance(profile_adapter, MockProfileAdapter))


def verify_event(event: JEPEvent, *, adapter: ProfileAdapter | None = None) -> VerificationResult:
    errors: list[str] = []
    if compute_event_hash(event) != event.event_hash:
        errors.append("event_hash mismatch")
    if not event.nonce:
        errors.append("missing nonce")
    if type(event.timestamp) is not int:
        errors.append("timestamp must be an integer")
    profile_result = verify_profile(event, adapter)
    errors.extend(profile_result.errors)
    return VerificationResult(not errors, tuple(errors), profile_result.profile_checked)


def verify_chain(events: Iterable[JEPEvent], *, adapter: ProfileAdapter | None = None) -> VerificationResult:
    errors: list[str] = []
    materialized = list(events)
    nonces: set[str] = set()
    previous_hash: str | None = None
    profile_checked = bool(materialized)
    for index, event in enumerate(materialized):
        result = verify_event(event, adapter=adapter)
        profile_checked = profile_checked and result.profile_checked
        errors.extend(f"{event.event_id}: {error}" for error in result.errors)
        if event.nonce in nonces:
            errors.append(f"{event.event_id}: duplicate nonce")
        nonces.add(event.nonce)
        if index == 0:
            if event.previous_event_hash is not None:
                errors.append(f"{event.event_id}: first event must not reference previous_event_hash")
        elif event.previous_event_hash != previous_hash:
            errors.append(f"{event.event_id}: previous_event_hash does not match prior event_hash")
        previous_hash = event.event_hash
    ok, delegation_errors = verify_delegation_chain(materialized)
    if not ok:
        errors.extend(delegation_errors)
    return VerificationResult(not errors, tuple(errors), profile_checked)


def detect_tampering(events: Iterable[JEPEvent]) -> list[str]:
    return list(verify_chain(events).errors)


def verify_replay(events: Iterable[JEPEvent]) -> VerificationResult:
    return verify_chain(events)

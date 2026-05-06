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


def verify_profile(event: JEPEvent, adapter: ProfileAdapter | None = None) -> VerificationResult:
    profile_adapter = adapter or MockProfileAdapter()
    if event.credential_reference is None:
        return VerificationResult(True)
    if not profile_adapter.verify_reference(event.credential_reference, event.profile):
        return VerificationResult(False, (f"invalid credential reference for profile {event.profile}",))
    if not profile_adapter.validate_authority(event.credential_reference, event.authority_scope):
        return VerificationResult(False, ("profile adapter rejected authority scope",))
    return VerificationResult(True)


def verify_event(event: JEPEvent, *, adapter: ProfileAdapter | None = None) -> VerificationResult:
    errors: list[str] = []
    if compute_event_hash(event) != event.event_hash:
        errors.append("event_hash mismatch")
    if not event.nonce:
        errors.append("missing nonce")
    if not isinstance(event.timestamp, int):
        errors.append("timestamp must be an integer")
    profile_result = verify_profile(event, adapter)
    errors.extend(profile_result.errors)
    return VerificationResult(not errors, tuple(errors))


def verify_chain(events: Iterable[JEPEvent], *, adapter: ProfileAdapter | None = None) -> VerificationResult:
    errors: list[str] = []
    materialized = list(events)
    nonces: set[str] = set()
    previous_hash: str | None = None
    for index, event in enumerate(materialized):
        result = verify_event(event, adapter=adapter)
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
    return VerificationResult(not errors, tuple(errors))


def detect_tampering(events: Iterable[JEPEvent]) -> list[str]:
    return list(verify_chain(events).errors)


def verify_replay(events: Iterable[JEPEvent]) -> VerificationResult:
    return verify_chain(events)

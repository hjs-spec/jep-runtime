"""Core immutable event model for the JEP Reference Runtime."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
import copy
import time
import uuid


class EventType(str, Enum):
    """JEP judgment event primitives."""

    JUDGMENT = "J"
    DELEGATION = "D"
    TERMINATION = "T"
    VERIFICATION = "V"


_REQUIRED_SCHEMA_FIELDS = [
    "event_id",
    "event_type",
    "actor",
    "subject",
    "agent_id",
    "session_id",
    "delegation_chain",
    "authority_scope",
    "intent",
    "justification",
    "previous_event_hash",
    "event_hash",
    "nonce",
    "timestamp",
    "profile",
    "credential_reference",
    "verification_state",
]


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return copy.deepcopy(value)


@dataclass(frozen=True, slots=True)
class JEPEvent:
    """Immutable JEP event after hash assignment.

    The runtime keeps J/D/T/V semantics minimal: events are typed evidence
    records, linked by previous_event_hash, scoped by authority_scope, and
    replayable through nonce, timestamp, profile, and delegation_chain.
    """

    event_id: str
    event_type: EventType | str
    actor: str
    subject: str
    agent_id: str | None
    session_id: str
    delegation_chain: tuple[str, ...] = field(default_factory=tuple)
    authority_scope: Mapping[str, Any] = field(default_factory=dict)
    intent: Mapping[str, Any] = field(default_factory=dict)
    justification: str = ""
    previous_event_hash: str | None = None
    event_hash: str | None = None
    nonce: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: int = field(default_factory=lambda: int(time.time()))
    profile: str = "mock"
    credential_reference: str | None = None
    verification_state: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType(self.event_type))
        object.__setattr__(self, "delegation_chain", tuple(self.delegation_chain))
        object.__setattr__(self, "authority_scope", _freeze(self.authority_scope))
        object.__setattr__(self, "intent", _freeze(self.intent))
        object.__setattr__(self, "verification_state", _freeze(self.verification_state))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        """Return a deterministic dictionary representation."""

        data = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "actor": self.actor,
            "subject": self.subject,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "delegation_chain": list(self.delegation_chain),
            "authority_scope": _thaw(self.authority_scope),
            "intent": _thaw(self.intent),
            "justification": self.justification,
            "previous_event_hash": self.previous_event_hash,
            "event_hash": self.event_hash if include_hash else None,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "profile": self.profile,
            "credential_reference": self.credential_reference,
            "verification_state": _thaw(self.verification_state),
        }
        if not include_hash:
            data.pop("event_hash")
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "JEPEvent":
        return cls(**{field_name: data.get(field_name) for field_name in _REQUIRED_SCHEMA_FIELDS})

    def with_hash(self, event_hash: str) -> "JEPEvent":
        """Return a hashed immutable event.

        Existing event_hash values cannot be replaced, making post-hash objects
        append-only evidence records rather than mutable workflow state.
        """

        if self.event_hash and self.event_hash != event_hash:
            raise ValueError("event_hash is immutable once assigned")
        return replace(self, event_hash=event_hash)

    @staticmethod
    def json_schema() -> dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://example.org/jep-runtime/schemas/jep-event.schema.json",
            "title": "JEP Reference Runtime Event",
            "type": "object",
            "required": _REQUIRED_SCHEMA_FIELDS,
            "additionalProperties": False,
            "properties": {
                "event_id": {"type": "string"},
                "event_type": {"enum": ["J", "D", "T", "V"]},
                "actor": {"type": "string"},
                "subject": {"type": "string"},
                "agent_id": {"type": ["string", "null"]},
                "session_id": {"type": "string"},
                "delegation_chain": {"type": "array", "items": {"type": "string"}},
                "authority_scope": {"type": "object"},
                "intent": {"type": "object"},
                "justification": {"type": "string"},
                "previous_event_hash": {"type": ["string", "null"]},
                "event_hash": {"type": ["string", "null"]},
                "nonce": {"type": "string"},
                "timestamp": {"type": "integer"},
                "profile": {"type": "string"},
                "credential_reference": {"type": ["string", "null"]},
                "verification_state": {"type": "object"},
            },
        }

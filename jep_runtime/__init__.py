"""JEP Reference Runtime.

Executable, portable accountability runtime for Judgment, Delegation,
Termination, and Verification events.
"""

from jep_runtime.core.event import EventType, JEPEvent
from jep_runtime.core.version import JEP_DRAFT_REFERENCE, JEP_DRAFT_REPOSITORY, JEP_DRAFT_VERSION, RUNTIME_VERSION
from jep_runtime.events.factory import create_event
from jep_runtime.canonicalization.json import canonicalize_event, compute_event_hash
from jep_runtime.verification.runtime import verify_event, verify_chain, verify_replay

__all__ = [
    "EventType",
    "JEPEvent",
    "create_event",
    "canonicalize_event",
    "compute_event_hash",
    "verify_event",
    "verify_chain",
    "verify_replay",
    "JEP_DRAFT_VERSION",
    "JEP_DRAFT_REFERENCE",
    "JEP_DRAFT_REPOSITORY",
    "RUNTIME_VERSION",
]

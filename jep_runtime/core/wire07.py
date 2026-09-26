"""JEP Core 0.7 wire-shape helpers.

This module is deliberately separate from the runtime's historical internal
archive envelope. JEP Core 0.7 does not require runtime fields such as nonce,
previous_event_hash, delegation_chain, authority_scope, or verification_state.
"""

from __future__ import annotations

from typing import Any, Mapping

CORE07_REQUIRED = ("jep", "id", "verb", "who", "when", "what")
CORE07_VERBS = frozenset({"J", "D", "T", "V"})


class Core07ShapeError(ValueError):
    """Raised when a mapping does not satisfy the JEP Core 0.7 minimum shape."""


def event_identity(event: Mapping[str, Any]) -> tuple[str, str]:
    """Return stable JEP Event Identity (who,id) after minimum validation."""
    validate_core07_shape(event)
    return str(event["who"]), str(event["id"])


def unsigned_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Return the signed payload object with sig omitted."""
    validate_core07_shape(event, require_signature=False)
    return {str(k): v for k, v in event.items() if k != "sig"}


def validate_core07_shape(
    event: Mapping[str, Any], *, require_signature: bool = True
) -> None:
    """Validate the Core 0.7 structural minimum.

    This is not cryptographic, trust-profile, chain, or policy validation.
    """
    if not isinstance(event, Mapping):
        raise Core07ShapeError("event must be an object")

    missing = [name for name in CORE07_REQUIRED if name not in event]
    if require_signature and "sig" not in event:
        missing.append("sig")
    if missing:
        raise Core07ShapeError("missing required field(s): " + ", ".join(missing))

    if event["jep"] != "1":
        raise Core07ShapeError('jep must be "1"')
    if event["verb"] not in CORE07_VERBS:
        raise Core07ShapeError("verb must be J, D, T, or V")
    if not isinstance(event["id"], str) or not event["id"]:
        raise Core07ShapeError("id must be a non-empty string")
    if not isinstance(event["who"], str) or not event["who"]:
        raise Core07ShapeError("who must be a non-empty string")
    if type(event["when"]) is not int:
        raise Core07ShapeError("when must be an integer Unix time")

    what = event["what"]
    verb = event["verb"]
    if verb == "D":
        if not isinstance(what, Mapping) or "delegatee" not in what or "scope" not in what:
            raise Core07ShapeError("D requires what.delegatee and what.scope")
    elif verb == "T":
        if "ref" not in event:
            raise Core07ShapeError("T requires ref")
        if not isinstance(what, Mapping) or "termination_scope" not in what:
            raise Core07ShapeError("T requires what.termination_scope")
    elif verb == "V":
        if "ref" not in event:
            raise Core07ShapeError("V requires ref")
        if (
            not isinstance(what, Mapping)
            or "verification_scope" not in what
            or "result" not in what
        ):
            raise Core07ShapeError(
                "V requires what.verification_scope and what.result"
            )

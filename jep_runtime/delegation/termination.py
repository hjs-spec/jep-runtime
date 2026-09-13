"""Session-local termination state for the reference runtime profile."""

from jep_runtime.core.event import EventType, JEPEvent


class TerminationState:
    """A T ends the subject's authority and its observed descendants in a session."""

    def __init__(self) -> None:
        self.terminated: set[tuple[str, str]] = set()
        self.revoked_hashes: set[str] = set()
        self.grants: dict[str, JEPEvent] = {}

    def rejects(self, event: JEPEvent) -> bool:
        if event.event_type not in (EventType.JUDGMENT, EventType.DELEGATION):
            return False
        parent = event.intent.get("parent_event_hash")
        return (
            (event.session_id, event.actor) in self.terminated
            or (event.session_id, event.subject) in self.terminated
            or bool(self.revoked_hashes.intersection(event.delegation_chain))
            or (isinstance(parent, str) and parent in self.revoked_hashes)
        )

    def observe(self, event: JEPEvent) -> None:
        if event.event_type == EventType.TERMINATION:
            self.terminated.add((event.session_id, event.subject))
            # Ancestors precede descendants in a verified chain.
            for event_hash, grant in self.grants.items():
                if grant.session_id == event.session_id and (
                    (grant.session_id, grant.subject) in self.terminated
                    or self.revoked_hashes.intersection(grant.delegation_chain)
                ):
                    self.revoked_hashes.add(event_hash)
                    self.terminated.add((grant.session_id, grant.subject))
        elif (
            event.event_type in (EventType.JUDGMENT, EventType.DELEGATION)
            and event.event_hash
            and not self.rejects(event)
        ):
            self.grants[event.event_hash] = event

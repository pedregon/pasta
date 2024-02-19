"""The `session` module contains shell sessions."""
import dataclasses
import uuid
import collections
import hashlib
# from . import actions


@dataclasses.dataclass
class Session:
    """Session is a subshell session."""

    id: uuid.UUID
    # action: actions.Action

    def fingerprint(self) -> bytes:
        """Return the Session subshell fingerprint."""
        return hashlib.sha1().digest()

class State:
    """State is a sessions stack."""

    def __init__(self) -> None:
        self._sessions: list[Session] = []
        return

    def push(self, session: Session) -> None:
        self._sessions.append(session)

    def pop(self) -> Session:
        return self.pop()

    def get(self, index: str) -> list[Session]:
        return self._sessions
"""In-memory conversation sessions (one photo + a short text history per session)."""
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.imaging import PreparedImage
from app.providers import ChatTurn


@dataclass
class Session:
    id: str
    created_at: float
    last_used: float
    image: PreparedImage | None = None
    history: list[ChatTurn] = field(default_factory=list)


class SessionStore:
    """Sessions live in memory only: they disappear when the server restarts."""

    def __init__(
        self,
        ttl_seconds: float = 1800.0,
        max_sessions: int = 50,
        max_turns: int = 6,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self.max_turns = max_turns
        self._clock = clock
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)

    def _purge(self) -> None:
        now = self._clock()
        expired = [sid for sid, s in self._sessions.items() if now - s.last_used > self.ttl_seconds]
        for sid in expired:
            del self._sessions[sid]

    def create(self) -> Session:
        with self._lock:
            self._purge()
            while len(self._sessions) >= self.max_sessions:
                oldest = min(self._sessions.values(), key=lambda s: s.last_used)
                del self._sessions[oldest.id]
            now = self._clock()
            session = Session(id=secrets.token_urlsafe(16), created_at=now, last_used=now)
            self._sessions[session.id] = session
            return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            self._purge()
            session = self._sessions.get(session_id)
            if session is not None:
                session.last_used = self._clock()
            return session

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def set_image(self, session: Session, image: PreparedImage) -> None:
        """A new photo starts a new topic: the old conversation is dropped."""
        with self._lock:
            session.image = image
            session.history.clear()
            session.last_used = self._clock()

    def add_turn(self, session: Session, user_text: str, assistant_text: str) -> None:
        with self._lock:
            session.history.append(ChatTurn(role="user", text=user_text))
            session.history.append(ChatTurn(role="assistant", text=assistant_text))
            del session.history[: -self.max_turns * 2]
            session.last_used = self._clock()

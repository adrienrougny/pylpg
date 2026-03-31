import threading
import typing

if typing.TYPE_CHECKING:
    import pylpg.session

_thread_local: threading.local = threading.local()


def get_active_session_or_none() -> "pylpg.session.Session | None":
    """Return the active session or None if none is set."""
    return getattr(_thread_local, "session", None)


def get_active_session() -> "pylpg.session.Session":
    """Return the active session or raise if none is set."""
    session = getattr(_thread_local, "session", None)
    if session is None:
        raise RuntimeError("No active session. Use 'with Session(backend):' first.")
    return session


def set_active_session(
    session: "pylpg.session.Session | None",
) -> None:
    """Set the active session for the current thread."""
    _thread_local.session = session

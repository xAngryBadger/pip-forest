import os
import threading

_APP_PASSWORD = os.environ.get("ORCA_PASSWORD", "orca2024")

_authenticated_sessions: set[str] = set()
_auth_lock = threading.Lock()


def check_password(provided: str) -> bool:
    return provided == _APP_PASSWORD


def mark_authenticated(session_token: str):
    with _auth_lock:
        _authenticated_sessions.add(session_token)


def is_authenticated(session_token: str) -> bool:
    with _auth_lock:
        return session_token in _authenticated_sessions


def revoke_authentication(session_token: str):
    with _auth_lock:
        _authenticated_sessions.discard(session_token)

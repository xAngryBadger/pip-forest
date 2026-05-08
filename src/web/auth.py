import os

_APP_PASSWORD = os.environ.get("SRF_PASSWORD", "gazella2024")

_authenticated_sessions: set[str] = set()


def check_password(provided: str) -> bool:
    return provided == _APP_PASSWORD


def mark_authenticated(session_token: str):
    _authenticated_sessions.add(session_token)


def is_authenticated(session_token: str) -> bool:
    return session_token in _authenticated_sessions


def revoke_authentication(session_token: str):
    _authenticated_sessions.discard(session_token)


def get_password() -> str:
    return _APP_PASSWORD

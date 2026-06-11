import hashlib
import os

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Load from .htpasswd file if present, else env var, else default
_htpasswd_path = os.path.join(os.path.dirname(__file__), "..", "..", ".htpasswd")
_APP_PASSWORD_HASH: str | None = None

if os.path.exists(_htpasswd_path):
    with open(_htpasswd_path, "r") as f:
        stored = f.read().strip()
        if ":" in stored:
            _APP_PASSWORD_HASH = stored.split(":", 1)[1]
        else:
            _APP_PASSWORD_HASH = stored
else:
    default = os.environ.get("SRF_PASSWORD", "gazella2024")
    _APP_PASSWORD_HASH = _hash_password(default)

_authenticated_sessions: set[str] = set()


def check_password(provided: str) -> bool:
    return _hash_password(provided) == _APP_PASSWORD_HASH


def swap_password(new_password: str) -> bool:
    global _APP_PASSWORD_HASH
    _APP_PASSWORD_HASH = _hash_password(new_password)
    try:
        with open(_htpasswd_path, "w") as f:
            f.write(f"orca:{_APP_PASSWORD_HASH}")
        return True
    except OSError:
        return False


def mark_authenticated(session_token: str):
    _authenticated_sessions.add(session_token)


def is_authenticated(session_token: str) -> bool:
    return session_token in _authenticated_sessions


def revoke_authentication(session_token: str):
    _authenticated_sessions.discard(session_token)

import hashlib
import hmac
import os
import time
import json
import base64
from typing import Dict, Optional


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64url(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode())


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_users() -> Dict[str, str]:
    """
    SRF_USERS format:
    - "user:plainpass,user2:plainpass2"
    """
    raw = os.environ.get("SRF_USERS", "").strip()
    if not raw:
        return {"admin": _sha256_text("admin123")}
    out = {}
    for part in raw.split(","):
        p = part.strip()
        if not p or ":" not in p:
            continue
        u, pw = p.split(":", 1)
        u = u.strip()
        pw = pw.strip()
        if not u or not pw:
            continue
        out[u] = _sha256_text(pw)
    return out


def verify_password(username: str, password: str, users: Dict[str, str]) -> bool:
    ref = users.get(username)
    if not ref:
        return False
    return hmac.compare_digest(_sha256_text(password), ref)


def _secret() -> bytes:
    s = os.environ.get("SRF_JWT_SECRET", "dev-secret-change-me")
    return s.encode("utf-8")


def create_token(username: str, ttl_seconds: int = 60 * 60 * 8) -> str:
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + int(ttl_seconds)}
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    body = _b64url(raw)
    sig = hmac.new(_secret(), body.encode("utf-8"), hashlib.sha256).digest()
    return f"{body}.{_b64url(sig)}"


def decode_token(token: str) -> Optional[dict]:
    try:
        body, sig = token.split(".", 1)
        sig_calc = hmac.new(_secret(), body.encode("utf-8"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url(sig_calc), sig):
            return None
        payload = json.loads(_unb64url(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


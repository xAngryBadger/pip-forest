import os
import socket
import sys
import threading
import time
import traceback
import json
import urllib.request
from pathlib import Path

import uvicorn
import webview


# region agent log
def _dbg_log(hypothesis_id: str, location: str, message: str, data: dict):
    try:
        payload = {
            "sessionId": "09cd54",
            "runId": "run1",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open("debug-09cd54.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# endregion


def _repo_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _sessions_dir_default() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return (base / "SRF_Desktop" / "sessions").resolve()
    return (Path.home() / ".srf_desktop" / "sessions").resolve()


def _pick_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _wait_server(url: str, timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if int(resp.status) == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def main() -> None:
    repo = _repo_dir()
    sessions_dir = _sessions_dir_default()
    sessions_dir.mkdir(parents=True, exist_ok=True)
    _dbg_log(
        "H2_repo_resolution",
        "desktop_app.py:main",
        "Desktop bootstrap paths",
        {
            "repo": str(repo),
            "sessions_dir": str(sessions_dir),
            "frozen": bool(getattr(sys, "frozen", False)),
            "meipass": str(getattr(sys, "_MEIPASS", "")),
            "executable": str(getattr(sys, "executable", "")),
        },
    )

    os.environ["SRF_BASE_DIR"] = str(repo)
    os.environ.setdefault("SRF_SESSIONS_DIR", str(sessions_dir))
    os.environ.setdefault("SRF_DEFAULT_MODE", "standard")
    _dbg_log(
        "H3_env_propagation",
        "desktop_app.py:env",
        "Environment set before importing app",
        {
            "SRF_BASE_DIR": os.environ.get("SRF_BASE_DIR", ""),
            "SRF_SESSIONS_DIR": os.environ.get("SRF_SESSIONS_DIR", ""),
            "SRF_DEFAULT_MODE": os.environ.get("SRF_DEFAULT_MODE", ""),
        },
    )

    host = "127.0.0.1"
    port = _pick_free_port(host)
    try:
        from app.main import app as fastapi_app
        _dbg_log(
            "H4_import_main",
            "desktop_app.py:import_app",
            "Imported app.main successfully",
            {"ok": True},
        )
    except Exception as ex:
        _dbg_log(
            "H4_import_main",
            "desktop_app.py:import_app",
            "Failed importing app.main",
            {"error": str(ex), "trace": traceback.format_exc()},
        )
        raise
    home_url = f"http://{host}:{port}/ui"
    health_url = f"http://{host}:{port}/api/health"

    config = uvicorn.Config(
        fastapi_app,
        host=host,
        port=port,
        reload=False,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    server_err: dict[str, str] = {"trace": ""}

    def _run_server():
        try:
            server.run()
        except Exception:
            server_err["trace"] = traceback.format_exc()

    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()

    if not _wait_server(health_url, timeout_s=30.0):
        detail = server_err["trace"].strip()
        msg = "Nao foi possivel iniciar o servidor local do SRF."
        if detail:
            msg += f"\n\nDetalhe tecnico:\n{detail}"
        raise RuntimeError(msg)

    window = webview.create_window(
        title="SRF - App Desktop",
        url=home_url,
        width=1400,
        height=900,
        min_size=(1100, 700),
    )

    try:
        webview.start()
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)
        if window:
            try:
                window.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    main()

import queue
import threading
import uuid
import copy
import shutil
import datetime
import os
from pathlib import Path

from src.atm.srf import config as cfg_module
from src.atm.srf import ui as cli_ui

_BASE_DATA_DIR = Path(os.environ.get("SRF_DATA_DIR", "data"))
_SESSIONS_DIR = _BASE_DATA_DIR / "sessions"
_STEP_TIMEOUT = int(os.environ.get("SRF_STEP_TIMEOUT", "3600"))

_sessions: dict[str, "Session"] = {}
_sessions_lock = threading.Lock()


class Session:
    def __init__(self, base_config_path: str | None = None):
        self.session_id = str(uuid.uuid4())[:8]
        self.q_in: queue.Queue = queue.Queue()
        self.created_at = datetime.datetime.now()
        self.thread: threading.Thread | None = None
        self.alive = True
        self.finished = False
        self.error: str | None = None
        self.result_files: list[str] = []
        self.dashboard: dict = {}
        self._current_step: dict | None = None
        self._step_lock = threading.Lock()
        self._step_ready = threading.Event()
        self._step_answered = threading.Event()

        self.data_dir = _SESSIONS_DIR / self.session_id
        self.data_dir.mkdir(parents=True, exist_ok=True)

        cfg_src = base_config_path or str(_BASE_DATA_DIR / "config.json")
        if not os.path.exists(cfg_src):
            cfg_src = cfg_module.CFGP
        if os.path.exists(cfg_src):
            shutil.copy2(cfg_src, self.data_dir / "config.json")
        _old_cfgp = cfg_module.CFGP
        cfg_module.CFGP = str(self.data_dir / "config.json")
        try:
            self.cfg = cfg_module.carregar_config()
        finally:
            cfg_module.CFGP = _old_cfgp

        planilhas_src = _BASE_DATA_DIR / "planilhas"
        planilhas_dst = self.data_dir / "planilhas"
        if planilhas_src.exists() and not planilhas_dst.exists():
            shutil.copytree(planilhas_src, planilhas_dst)

    def step(self, step_type: str, prompt_text, default, options=None):
        if not self.alive:
            raise RuntimeError(f"Session {self.session_id} is dead")
        import time
        payload = {
            "step_id": f"step_{int(time.monotonic()*1000) % 100000}",
            "session_id": self.session_id,
            "type": step_type,
            "prompt": str(prompt_text) if prompt_text is not None else None,
            "default": default,
            "options": options,
            "dashboard": self.dashboard.copy(),
            "timestamp": datetime.datetime.now().isoformat(),
        }
        with self._step_lock:
            self._current_step = payload
            self._step_ready.set()
            self._step_answered.clear()
        self._step_answered.wait(timeout=_STEP_TIMEOUT)
        with self._step_lock:
            self._current_step = None
            self._step_ready.clear()
        if not self.alive:
            raise RuntimeError(f"Session {self.session_id} is dead")
        try:
            answer = self.q_in.get_nowait()
        except queue.Empty:
            answer = None
        return answer

    def answer(self, value):
        self.q_in.put(value)
        self._step_answered.set()

    def get_pending_step(self):
        with self._step_lock:
            if self._current_step is not None and not self._step_answered.is_set():
                return self._current_step.copy()
        return None

    def put_display(self, title, body, level="info"):
        self.step("display", title, None, {"body": body, "level": level})

    def put_table(self, title, headers, rows):
        self.step("table", title, None, {"headers": headers, "rows": rows})

    def mark_finished(self, error=None):
        self.finished = True
        self.alive = False
        self.error = error
        with self._step_lock:
            self._current_step = {
                "step_id": "result",
                "session_id": self.session_id,
                "type": "result" if not error else "error",
                "prompt": "Concluído" if not error else f"Erro: {error}",
                "default": None,
                "options": {"files": self.result_files, "error": error},
                "dashboard": self.dashboard.copy(),
                "timestamp": datetime.datetime.now().isoformat(),
            }
            self._step_ready.set()
            self._step_answered.set()


_current = threading.local()


def get_current_session() -> Session | None:
    return getattr(_current, "session", None)


def set_current_session(session: Session):
    _current.session = session


def get_session(session_id: str) -> Session | None:
    with _sessions_lock:
        return _sessions.get(session_id)


def register_session(session: Session):
    with _sessions_lock:
        _sessions[session.session_id] = session


def remove_session(session_id: str):
    with _sessions_lock:
        _sessions.pop(session_id, None)


def list_sessions():
    with _sessions_lock:
        return [
            {
                "session_id": s.session_id,
                "created_at": s.created_at.isoformat(),
                "finished": s.finished,
                "error": s.error,
            }
            for s in _sessions.values()
        ]


def cleanup_old_sessions(max_age_hours=24):
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=max_age_hours)
    with _sessions_lock:
        to_remove = [
            sid for sid, s in _sessions.items()
            if s.created_at < cutoff and s.finished
        ]
    for sid in to_remove:
        remove_session(sid)

import asyncio
import fcntl
import os
import pty
import select
import signal
import struct
import sys
import termios
import threading
import datetime
import shutil
import uuid
import base64
from pathlib import Path
from collections import deque

_sessions: dict[str, "TermSession"] = {}
_sessions_lock = threading.Lock()

_BASE_DATA_DIR = Path(os.environ.get("SRF_DATA_DIR", "data"))


class TermSession:
    _POLL_BUF_MAX = 262144

    def __init__(self, session_id: str, token: str):
        self.session_id = session_id
        self.token = token
        self.created_at = datetime.datetime.now()
        self.alive = True
        self.finished = False
        self.error: str | None = None
        self.pid: int | None = None
        self.fd: int | None = None
        self.result_files: list[str] = []
        self.data_dir = _BASE_DATA_DIR / "sessions" / session_id
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ws_clients: list = []
        self._read_task: asyncio.Task | None = None
        self._poll_buf: deque = deque()
        self._poll_seq: int = 0
        self._poll_lock = threading.Lock()

    def add_ws(self, ws):
        self._ws_clients.append(ws)

    def remove_ws(self, ws):
        if ws in self._ws_clients:
            self._ws_clients.remove(ws)

    async def broadcast(self, data: bytes):
        self._append_poll(data)
        dead = []
        for ws in self._ws_clients:
            try:
                await ws.send_bytes(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.remove_ws(ws)

    def _append_poll(self, data: bytes):
        with self._poll_lock:
            self._poll_buf.append(data)
            self._poll_seq += 1
            total = sum(len(d) for d in self._poll_buf)
            while total > self._POLL_BUF_MAX and len(self._poll_buf) > 1:
                total -= len(self._poll_buf.popleft())

    def poll_output(self, since_seq: int = 0) -> dict:
        with self._poll_lock:
            chunks = []
            seq = 0
            items = list(self._poll_buf)
            for chunk in items:
                seq += 1
                if seq > since_seq:
                    chunks.append(base64.b64encode(chunk).decode())
            return {
                "seq": self._poll_seq,
                "chunks": chunks,
                "finished": self.finished,
            }

    def set_pty_size(self, rows: int, cols: int):
        if self.fd is not None:
            try:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
            except Exception:
                pass

    def kill(self):
        if self.pid is not None:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except Exception:
                pass
        self.alive = False
        self.finished = True


def create_session(token: str) -> "TermSession":
    sid = str(uuid.uuid4())[:8]
    s = TermSession(sid, token)
    with _sessions_lock:
        _sessions[sid] = s
    return s


def get_session(sid: str) -> "TermSession | None":
    with _sessions_lock:
        return _sessions.get(sid)


def list_sessions() -> list[dict]:
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


def remove_session(sid: str):
    with _sessions_lock:
        s = _sessions.pop(sid, None)
    if s:
        s.kill()


def _setup_data_dir(session: TermSession):
    cfg_src = str(_BASE_DATA_DIR / "config.json")
    if not os.path.exists(cfg_src):
        alt = str(Path(__file__).parent.parent / "atm" / "config.json")
        if os.path.exists(alt):
            cfg_src = alt
    if os.path.exists(cfg_src):
        shutil.copy2(cfg_src, session.data_dir / "config.json")
    planilhas_src = _BASE_DATA_DIR / "planilhas"
    planilhas_dst = session.data_dir / "planilhas"
    if planilhas_src.exists() and not planilhas_dst.exists():
        shutil.copytree(planilhas_src, planilhas_dst)


def spawn_process(session: TermSession):
    _setup_data_dir(session)
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    python = sys.executable
    env = os.environ.copy()
    env["SRF_DATA_DIR"] = str(session.data_dir)
    env["SRF_WEB_MODE"] = "0"
    env.pop("SRF_PASSWORD", None)
    env["TERM"] = "xterm-256color"
    env["COLUMNS"] = "80"
    env["LINES"] = "24"
    output_dir = session.data_dir / "dossiês"
    output_dir.mkdir(parents=True, exist_ok=True)
    env["SRF_OUTPUT_DIR"] = str(output_dir)

    master_fd, slave_fd = pty.openpty()

    winsize = struct.pack("HHHH", 24, 80, 0, 0)
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

    pid = os.fork()
    if pid == 0:
        os.close(master_fd)
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        if slave_fd > 2:
            os.close(slave_fd)
        os.chdir(project_root)
        os.execve(python, [python, "-m", "src.atm.atm_v6_3"], env)
        os._exit(1)

    os.close(slave_fd)
    session.pid = pid
    session.fd = master_fd

    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


async def start_process(session: TermSession):
    try:
        spawn_process(session)
    except Exception as e:
        session.error = str(e)
        session.finished = True
        return


async def read_loop(session: TermSession):
    if session.fd is None:
        return
    loop = asyncio.get_event_loop()
    while session.alive:
        try:
            ready = await loop.run_in_executor(None, _wait_fd, session.fd, 0.5)
            if not ready:
                continue
            chunk = await loop.run_in_executor(None, os.read, session.fd, 65536)
            if not chunk:
                break
            await session.broadcast(chunk)
        except OSError:
            break
        except Exception:
            break

    try:
        pid, status = os.waitpid(session.pid, os.WNOHANG)
        if pid == 0:
            os.kill(session.pid, signal.SIGTERM)
            os.waitpid(session.pid, 0)
            status = 0
        rc = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
    except Exception:
        rc = -1
    session.finished = True
    msg = f"\r\n\x1b[90m--- Processo finalizado (codigo {rc}) ---\x1b[0m\r\n"
    await session.broadcast(msg.encode("utf-8", errors="replace"))
    _collect_result_files(session)


def _wait_fd(fd: int, timeout: float) -> bool:
    try:
        r, _, _ = select.select([fd], [], [], timeout)
        return bool(r)
    except Exception:
        return False


async def write_to_process(session: TermSession, data: bytes):
    if session.fd is not None and session.alive:
        try:
            os.write(session.fd, data)
        except Exception:
            pass


async def resize_pty(session: TermSession, rows: int, cols: int):
    session.set_pty_size(rows, cols)


def _collect_result_files(session: TermSession):
    dossier_dir = session.data_dir / "dossiês"
    if not dossier_dir.exists():
        return
    for f in sorted(dossier_dir.glob("*.xlsx")):
        if f.name not in session.result_files:
            session.result_files.append(f.name)

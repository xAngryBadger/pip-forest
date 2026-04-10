import os
import select
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from queue import Queue, Empty
from typing import Dict, List, Optional


REPO_FILES_TO_COPY = [
    "atm_v5.py",
    "srf_excel_format.py",
    "config.json",
]

REPO_DIRS_TO_COPY = [
    "testes",
    "tutorial",
]


@dataclass
class CliSession:
    session_id: str
    username: str
    workspace_dir: str
    mode: str
    proc: Optional[subprocess.Popen] = None
    master_fd: Optional[int] = None
    output_queue: Queue = field(default_factory=Queue)
    running: bool = False
    created_at: float = field(default_factory=time.time)
    execution_config: dict = field(default_factory=dict)
    execution_notes: List[dict] = field(default_factory=list)
    semantic_events: List[dict] = field(default_factory=list)

    def add_event(self, stage: str, detail: str = "", progress: int = 0, level: str = "info"):
        self.semantic_events.append(
            {
                "ts": time.time(),
                "stage": str(stage or "").strip(),
                "detail": str(detail or "").strip(),
                "progress": int(max(0, min(100, progress or 0))),
                "level": str(level or "info"),
            }
        )
        if len(self.semantic_events) > 200:
            self.semantic_events = self.semantic_events[-200:]

    def start(self):
        if self.running:
            return
        os.makedirs(self.workspace_dir, exist_ok=True)
        cmd = ["python", "atm_v5.py"]
        if self.mode == "legacy":
            cmd.append("--legacy")

        is_posix = os.name == "posix"
        if is_posix:
            import pty  # lazy import: unavailable on Windows
            master_fd, slave_fd = pty.openpty()
            self.master_fd = master_fd
            self.proc = subprocess.Popen(
                cmd,
                cwd=self.workspace_dir,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            os.close(slave_fd)
        else:
            self.proc = subprocess.Popen(
                cmd,
                cwd=self.workspace_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            self.master_fd = None
        self.running = True
        self.add_event("session_started", "Sessao CLI iniciada", progress=5)

        def _reader():
            try:
                if is_posix:
                    while self.running and self.master_fd is not None:
                        r, _, _ = select.select([self.master_fd], [], [], 0.2)
                        if not r:
                            if self.proc and self.proc.poll() is not None:
                                break
                            continue
                        data = os.read(self.master_fd, 4096)
                        if not data:
                            break
                        self.output_queue.put(data.decode("utf-8", errors="replace"))
                else:
                    while self.running and self.proc and self.proc.stdout:
                        chunk = self.proc.stdout.read(1)
                        if not chunk:
                            if self.proc.poll() is not None:
                                break
                            time.sleep(0.05)
                            continue
                        self.output_queue.put(chunk)
            except Exception as ex:
                self.output_queue.put(f"\n[erro de sessão] {ex}\n")
            finally:
                self.running = False
                self.output_queue.put("\n[processo encerrado]\n")

        t = threading.Thread(target=_reader, daemon=True)
        t.start()

    def send_input(self, text: str):
        if not self.running:
            return
        if self.master_fd is not None:
            os.write(self.master_fd, text.encode("utf-8", errors="ignore"))
            return
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(text)
                self.proc.stdin.flush()
            except Exception:
                pass

    def read_output_non_block(self) -> List[str]:
        out = []
        while True:
            try:
                out.append(self.output_queue.get_nowait())
            except Empty:
                break
        return out

    def stop(self):
        self.running = False
        self.add_event("session_stopped", "Sessao interrompida", progress=100, level="warn")
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None


class SessionManager:
    def __init__(self, base_repo_dir: str, sessions_root: str):
        self.base_repo_dir = base_repo_dir
        self.sessions_root = sessions_root
        os.makedirs(self.sessions_root, exist_ok=True)
        self.sessions: Dict[str, CliSession] = {}

    def _bootstrap_workspace(self, workspace_dir: str):
        os.makedirs(workspace_dir, exist_ok=True)
        for f in REPO_FILES_TO_COPY:
            src = os.path.join(self.base_repo_dir, f)
            dst = os.path.join(workspace_dir, f)
            if os.path.exists(src):
                shutil.copy2(src, dst)
        for d in REPO_DIRS_TO_COPY:
            srcd = os.path.join(self.base_repo_dir, d)
            dstd = os.path.join(workspace_dir, d)
            if os.path.isdir(srcd):
                if os.path.exists(dstd):
                    shutil.rmtree(dstd, ignore_errors=True)
                shutil.copytree(srcd, dstd)
        os.makedirs(os.path.join(workspace_dir, "dossiês"), exist_ok=True)

    def create_session(self, username: str, mode: str) -> CliSession:
        sid = uuid.uuid4().hex[:12]
        wdir = os.path.join(self.sessions_root, f"{username}_{sid}")
        self._bootstrap_workspace(wdir)
        s = CliSession(session_id=sid, username=username, workspace_dir=wdir, mode=mode)
        s.add_event("workspace_ready", "Workspace bootstrap concluido", progress=2)
        self.sessions[sid] = s
        return s

    def get(self, sid: str) -> Optional[CliSession]:
        return self.sessions.get(sid)

    def stop(self, sid: str):
        s = self.sessions.get(sid)
        if s:
            s.stop()


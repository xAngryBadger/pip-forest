import threading
import time
import unittest
import os
import sys

os.environ.setdefault("SRF_WEB_MODE", "1")
os.environ.setdefault("SRF_PASSWORD", "test")
os.environ.setdefault("SRF_DATA_DIR", "data")

from src.web.session import Session, get_session, remove_session, register_session, _sessions, _sessions_lock
from src.web.bridge import start_session, abort_session, install_bridge, uninstall_bridge
from src.atm.orca import ui as cli_ui


def _auto_answer(session, answers=None, defaults=True, max_steps=500):
    consumed = 0
    while consumed < max_steps:
        step = session.get_pending_step()
        if step is None:
            if session.finished:
                break
            time.sleep(0.05)
            continue
        step_type = step.get("type", "")
        if step_type in ("result", "error"):
            break

        if answers and consumed < len(answers):
            val = answers[consumed]
        elif defaults:
            val = _default_answer(step)
        else:
            val = _default_answer(step)

        session.answer(val)
        consumed += 1
    return consumed


def _default_answer(step):
    step_type = step.get("type", "")
    default = step.get("default")

    if step_type == "display":
        return "continuar"
    if step_type == "table":
        return "continuar"
    if step_type == "confirmar":
        if isinstance(default, bool):
            return default
        return True
    if step_type in ("pedir_float", "pedir_jornada"):
        return float(default) if default is not None else 1.0
    if step_type == "pedir_int":
        return int(float(default)) if default is not None else 1
    if step_type in ("selecionar", "selecionar_paginado"):
        opts = step.get("options", {})
        items = opts.get("items", [])
        if items:
            for i, it in enumerate(items):
                it_lower = str(it).strip().lower()
                if any(kw in it_lower for kw in ("continuar", "simulacao", "proximo", "avancar", "ok", "concluir", "finalizar")):
                    return i + 1
            return 1
        return 1
    if step_type == "prompt":
        return str(default) if default is not None else ""
    return str(default) if default is not None else ""


class TestE2EWeb(unittest.TestCase):

    def setUp(self):
        with _sessions_lock:
            _sessions.clear()

    def tearDown(self):
        with _sessions_lock:
            for sid in list(_sessions.keys()):
                s = _sessions.get(sid)
                if s:
                    s.alive = False
                remove_session(sid)

    def test_single_mode_completes(self):
        session = start_session("single", {"fazenda": "FORMOSA"})
        consumed = _auto_answer(session, max_steps=600)
        for _ in range(120):
            if session.finished:
                break
            time.sleep(0.5)
        self.assertTrue(session.finished, f"Session not finished after {consumed} steps. Error: {session.error}")
        self.assertIsNone(session.error, f"Session finished with error: {session.error}")

    def test_batch_mode_completes(self):
        session = start_session("batch")
        consumed = _auto_answer(session, max_steps=300)
        for _ in range(120):
            if session.finished:
                break
            time.sleep(0.5)
        self.assertTrue(session.finished, f"Session not finished after {consumed} steps. Error: {session.error}")
        self.assertIsNone(session.error, f"Session finished with error: {session.error}")

    def test_multi_mode_completes(self):
        session = start_session("multi")
        consumed = _auto_answer(session, max_steps=300)
        for _ in range(120):
            if session.finished:
                break
            time.sleep(0.5)
        self.assertTrue(session.finished, f"Session not finished after {consumed} steps. Error: {session.error}")
        self.assertIsNone(session.error, f"Session finished with error: {session.error}")


if __name__ == "__main__":
    unittest.main()

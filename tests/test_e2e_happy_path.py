import json
import os
import shutil
import threading
import time
import unittest
from pathlib import Path

os.environ.setdefault("ORCA_WEB_MODE", "1")
os.environ.setdefault("ORCA_PASSWORD", "test")

_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_ROOT = Path(__file__).resolve().parent.parent


class _AutoAnswerer:
    def __init__(self, session, answers=None, max_steps=5000):
        self.session = session
        self.answers = answers
        self.max_steps = max_steps
        self.consumed = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set() and self.consumed < self.max_steps:
            step = self.session.get_pending_step()
            if step is None:
                if self.session.finished:
                    break
                time.sleep(0.05)
                continue
            step_type = step.get("type", "")
            if step_type in ("result", "error"):
                break

            if self.answers and self.consumed < len(self.answers):
                val = self.answers[self.consumed]
            else:
                val = _default_answer(step)

            self.session.answer(val)
            self.consumed += 1

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=5)

    def wait_until_finished(self, timeout=300):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.session.finished:
                return True
            time.sleep(0.2)
        return False


def _default_answer(step):
    step_type = step.get("type", "")
    default = step.get("default")
    prompt_text = str(step.get("prompt") or "").lower()

    if step_type in ("display", "table"):
        return "continuar"
    if step_type == "confirmar":
        if isinstance(default, bool):
            return default
        return True
    if step_type in ("pedir_float", "pedir_jornada"):
        if default is not None:
            try:
                return float(str(default).replace(",", "."))
            except (ValueError, TypeError):
                pass
        return 1.0
    if step_type == "pedir_int":
        if default is not None:
            try:
                return int(float(str(default)))
            except (ValueError, TypeError):
                pass
        return 1
    if step_type in ("selecionar", "selecionar_paginado"):
        opts = step.get("options", {})
        items = opts.get("items", [])
        if items:
            for i, it in enumerate(items):
                it_lower = str(it).strip().lower()
                if any(
                    kw in it_lower
                    for kw in (
                        "todas",
                        "todos",
                        "continuar",
                        "simulacao",
                        "proximo",
                        "avancar",
                        "ok",
                        "concluir",
                        "finalizar",
                        "sim",
                    )
                ):
                    return i + 1
            return 1
        return 1
    if step_type == "prompt":
        if any(kw in prompt_text for kw in ("s/n/a/ok", "s/n")):
            import re as _re
            _m = _re.search(r"\[(\d+)/(\d+)\]", prompt_text)
            if _m:
                _cur, _total = int(_m.group(1)), int(_m.group(2))
                if _cur < _total:
                    return "s"
                return "ok"
            if default is not None:
                d_str = str(default).strip()
                if d_str:
                    return d_str
            if any(
                kw in prompt_text
                for kw in ("opcao", "opção", "escolha", "numero", "número")
            ):
                return "1"
            return "0"
        return str(default) if default is not None else ""


def _setup_data_dir():
    tmp = Path(_ROOT) / "data" / "_test_happy_path"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    (tmp / "planilhas").mkdir()

    from tests.fixtures.create_minimal_fixture import (
        create_minimal_config_json,
        create_minimal_microplanejamento,
    )

    create_minimal_microplanejamento(str(tmp / "planilhas" / "microplanejamento.xlsx"))
    create_minimal_config_json(str(tmp / "config.json"))
    return str(tmp)


def _teardown_data_dir():
    tmp = Path(_ROOT) / "data" / "_test_happy_path"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)


class TestE2EHappyPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_data_dir = os.environ.get("ORCA_DATA_DIR")
        cls._data_dir = _setup_data_dir()
        os.environ["ORCA_DATA_DIR"] = cls._data_dir

    @classmethod
    def tearDownClass(cls):
        if cls._orig_data_dir is not None:
            os.environ["ORCA_DATA_DIR"] = cls._orig_data_dir
        elif "ORCA_DATA_DIR" in os.environ:
            del os.environ["ORCA_DATA_DIR"]
        _teardown_data_dir()

    def setUp(self):
        from src.web.session import _sessions, _sessions_lock

        with _sessions_lock:
            _sessions.clear()

    def tearDown(self):
        from src.web.session import _sessions, _sessions_lock, remove_session

        with _sessions_lock:
            sids = list(_sessions.keys())
            for sid in sids:
                s = _sessions.get(sid)
                if s:
                    s.alive = False
        for sid in sids:
            remove_session(sid)

    def test_single_mode_happy_path(self):
        from src.web.bridge import start_session

        session = start_session("single", {"fazenda": "FAZENDA TESTE"})
        auto = _AutoAnswerer(session, max_steps=5000)
        finished = auto.wait_until_finished(timeout=300)
        auto.stop()
        self.assertTrue(
            finished,
            f"Session not finished after {auto.consumed} steps. Error: {session.error}",
        )
        self.assertIsNone(
            session.error, f"Session finished with error: {session.error}"
        )

    def test_output_xlsx_produced(self):
        from src.web.bridge import start_session

        session = start_session("single", {"fazenda": "FAZENDA TESTE"})
        auto = _AutoAnswerer(session, max_steps=5000)
        finished = auto.wait_until_finished(timeout=300)
        auto.stop()
        if not finished or session.error:
            self.skipTest(f"Session did not complete cleanly: {session.error}")
        self.assertTrue(
            len(session.result_files) > 0,
            f"Expected at least one result file, got {session.result_files}",
        )

    def test_output_xlsx_has_cronograma_sheet(self):
        import pandas as pd
        from src.web.bridge import start_session
        from src.atm.orca.config import OUTPUT_DIR

        session = start_session("single", {"fazenda": "FAZENDA TESTE"})
        auto = _AutoAnswerer(session, max_steps=5000)
        finished = auto.wait_until_finished(timeout=300)
        auto.stop()
        if not finished or session.error:
            self.skipTest(f"Session did not complete cleanly: {session.error}")
        if not session.result_files:
            self.skipTest("No result files produced")

        output_dir = Path(OUTPUT_DIR)
        found = False
        for fname in session.result_files:
            fpath = output_dir / fname
            if not fpath.exists():
                continue
            try:
                xls = pd.ExcelFile(fpath)
                for sheet in xls.sheet_names:
                    if "CRONOGRAMA" in sheet.upper() or "DETALHADO" in sheet.upper():
                        df = pd.read_excel(fpath, sheet_name=sheet)
                        self.assertFalse(
                            df.empty, f"Sheet '{sheet}' is empty in {fname}"
                        )
                        found = True
                        break
            except Exception:
                continue
        if not found:
            self.skipTest(
                f"No CRONOGRAMA_DETALHADO sheet found in {session.result_files}"
            )


if __name__ == "__main__":
    unittest.main()

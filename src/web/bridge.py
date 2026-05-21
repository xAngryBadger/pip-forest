import contextlib
import os
import re
import sys
import threading
import traceback
from io import StringIO
from pathlib import Path

from src.atm.srf import ui as cli_ui
from src.web.session import (
    Session,
    _cfgp_lock,
    get_current_session,
    register_session,
    remove_session,
    set_current_session,
)


def _load_session_config(session: Session):
    import src.atm.orca.config as _cfg
    with _cfgp_lock:
        _old = _cfg.CFGP
        _cfg.CFGP = str(session.data_dir / "config.json")
        try:
            return _cfg.carregar_config()
        finally:
            _cfg.CFGP = _old


_LOOP_DETECTION_MAX = 3
_GLOBAL_STEP_MAX = 2000

_ANSI_RE = re.compile(r'\033\[[0-9;]*m')


class _TeeStream:
    def __init__(self, original, capture_buf):
        self._original = original
        self._capture = capture_buf

    def write(self, s):
        self._capture.write(s)
        return self._original.write(s)

    def flush(self):
        self._capture.flush()
        return self._original.flush()

    def __getattr__(self, name):
        return getattr(self._original, name)


class _TeeStringIO(StringIO):
    def __init__(self, parent_buf):
        super().__init__()
        self._parent_buf = parent_buf

    def write(self, s):
        self._parent_buf.write(s)
        return super().write(s)

    def flush(self):
        self._parent_buf.flush()
        super().flush()


class _ChainRedirect:
    def __init__(self, parent_buf):
        self._parent_buf = parent_buf
        self._original_redirect_stdout = contextlib.redirect_stdout
        self._original_redirect_stderr = contextlib.redirect_stderr
        self._saved_stdout = None
        self._saved_stderr = None

    def _chain_stdout(self, target):
        if target is self._parent_buf or (hasattr(target, '_capture') and target._capture is self._parent_buf):
            return self._original_redirect_stdout(target)
        tee = _TeeStringIO(self._parent_buf)
        return self._original_redirect_stdout(tee)

    def _chain_stderr(self, target):
        if target is self._parent_buf or (hasattr(target, '_capture') and target._capture is self._parent_buf):
            return self._original_redirect_stderr(target)
        tee = _TeeStringIO(self._parent_buf)
        return self._original_redirect_stderr(tee)

    def install(self):
        contextlib.redirect_stdout = self._chain_stdout
        contextlib.redirect_stderr = self._chain_stderr

    def uninstall(self):
        contextlib.redirect_stdout = self._original_redirect_stdout
        contextlib.redirect_stderr = self._original_redirect_stderr

    def install_tee(self, buf):
        self._saved_stdout = sys.stdout
        self._saved_stderr = sys.stderr
        sys.stdout = _TeeStream(self._saved_stdout, buf)
        sys.stderr = _TeeStream(self._saved_stderr, buf)

    def uninstall_tee(self):
        if self._saved_stdout is not None:
            sys.stdout = self._saved_stdout
            self._saved_stderr = self._saved_stderr
            self._saved_stdout = None
            self._saved_stderr = None


_chain_redirector = _ChainRedirect(None)
_redirect_lock = threading.Lock()


class WebBridge:
    def __init__(self):
        self._recent_prompts = []
        self._prompt_counts = {}
        self._prompt_cycle_len = 0
        self._global_step_count = 0
        self._accumulated_body = ""

    def _flush_output(self):
        session = get_current_session()
        buf = getattr(session, '_output_buf', None)
        if not buf:
            return self._accumulated_body
        text = buf.getvalue()
        buf.truncate(0)
        buf.seek(0)
        stripped = _ANSI_RE.sub('', text).strip()
        if stripped:
            self._accumulated_body += ("\n" + stripped) if self._accumulated_body else stripped
        return self._accumulated_body

    def _consume_body(self):
        body = self._accumulated_body
        self._accumulated_body = ""
        return body

    def _normalize_prompt(self, titulo):
        return re.sub(r'Atividade:.*$', '', titulo).strip()

    def _check_loop(self, titulo, itens):
        self._global_step_count += 1
        if self._global_step_count > _GLOBAL_STEP_MAX:
            for i, it in enumerate(itens):
                it_lower = str(it).strip().lower()
                if any(kw in it_lower for kw in ("continuar", "simulacao", "proximo", "avancar", "ok", "confirmar", "concluir", "finalizar")):
                    return i
            return len(itens) - 1 if itens else True
        norm = self._normalize_prompt(titulo)
        self._prompt_counts[norm] = self._prompt_counts.get(norm, 0) + 1
        self._recent_prompts.append(norm)
        if len(self._recent_prompts) > 60:
            self._recent_prompts = self._recent_prompts[-60:]
        n = len(self._recent_prompts)
        if n >= 4:
            for cycle_len in range(1, min(n // 2, 20) + 1):
                tail = self._recent_prompts[-cycle_len:]
                prev = self._recent_prompts[-2 * cycle_len:-cycle_len]
                if tail == prev and cycle_len > 0:
                    self._prompt_cycle_len = cycle_len
                    self._recent_prompts.clear()
                    self._prompt_counts.clear()
                    for i, it in enumerate(itens):
                        it_lower = str(it).strip().lower()
                        if any(kw in it_lower for kw in ("sim", "continuar", "simulacao", "proximo", "avancar", "ok", "confirmar", "concluir")):
                            return i
                    return True if not itens else None
        count = self._prompt_counts.get(norm, 0)
        if count >= _LOOP_DETECTION_MAX:
            self._recent_prompts.clear()
            self._prompt_counts.clear()
            for i, it in enumerate(itens):
                it_lower = str(it).strip().lower()
                if any(kw in it_lower for kw in ("continuar", "simulacao", "proximo", "avancar", "finalizar", "sim", "ok", "concluir", "confirmar")):
                    return i
            return len(itens) - 1 if itens else True
        return None

    def confirmar(self, msg, default=True):
        loop_idx = self._check_loop(msg, ["Sim", "Nao"])
        if loop_idx is not None:
            return default
        self._flush_output()
        body = self._consume_body()
        session = get_current_session()
        result = session.step("confirmar", msg, default, {"body": body})
        if isinstance(result, bool):
            return result
        if isinstance(result, str):
            return result.strip().lower() in ("sim", "s", "yes", "y", "true", "1")
        return bool(result) if result is not None else default

    def pedir_float(self, msg, default, allow_zero=False):
        self._flush_output()
        body = self._consume_body()
        session = get_current_session()
        return session.step("pedir_float", msg, default, {"allow_zero": allow_zero, "body": body})

    def pedir_int(self, msg, default, allow_zero=False):
        self._flush_output()
        body = self._consume_body()
        session = get_current_session()
        result = session.step("pedir_int", msg, default, {"allow_zero": allow_zero, "body": body})
        return int(float(result)) if result is not None else int(float(default))

    def pedir_jornada(self, msg, default):
        self._flush_output()
        body = self._consume_body()
        session = get_current_session()
        return session.step("pedir_jornada", msg, default, {"body": body})

    @staticmethod
    def _items_have_navigation(itens):
        nav_kws = ("continuar", "voltar", "cancelar", "concluir", "finalizar", "sair", "proximo")
        for it in itens:
            it_lower = str(it).strip().lower()
            if any(kw in it_lower for kw in nav_kws):
                return True
        return False

    def selecionar(self, titulo, itens, zero_label="Voltar"):
        loop_idx = self._check_loop(titulo, itens)
        if loop_idx is not None:
            if isinstance(loop_idx, bool):
                return None
            return itens[loop_idx]
        self._flush_output()
        body = self._consume_body()
        hide_zero = self._items_have_navigation(itens)
        effective_zero = "" if hide_zero else zero_label
        session = get_current_session()
        result = session.step("selecionar", titulo, None, {
            "items": [str(i) for i in itens],
            "zero_label": effective_zero,
            "body": body,
        })
        if result is None or result == -1 or result == "0":
            return None
        try:
            idx = int(result) - 1
            if 0 <= idx < len(itens):
                return itens[idx]
        except (ValueError, IndexError):
            pass
        for i, it in enumerate(itens):
            if str(it) == str(result):
                return itens[i]
        return None

    def selecionar_paginado(self, titulo, itens, page_size=5, zero_label="Voltar"):
        loop_idx = self._check_loop(titulo, itens)
        if loop_idx is not None:
            if isinstance(loop_idx, bool):
                return -1
            return loop_idx
        self._flush_output()
        body = self._consume_body()
        hide_zero = self._items_have_navigation(itens)
        effective_zero = "" if hide_zero else zero_label
        session = get_current_session()
        result = session.step("selecionar_paginado", titulo, None, {
            "items": [str(i) for i in itens],
            "page_size": page_size,
            "zero_label": effective_zero,
            "body": body,
        })
        if result is None or result == -1 or result == "0":
            return -1
        try:
            return int(result) - 1
        except (ValueError, TypeError):
            return -1

    def prompt(self, msg, default=None):
        self._flush_output()
        body = self._consume_body()
        session = get_current_session()
        result = session.step("prompt", msg, default, {"body": body})
        if result is None or result == "":
            return str(default) if default is not None else ""
        return str(result)

    def esperar(self, msg):
        self._flush_output()
        body = self._consume_body()
        session = get_current_session()
        session.step("display", msg, None, {"body": body, "level": "info"})

    def escolha(self, msg, default="0"):
        count = self._prompt_counts.get(msg, 0) + 1
        self._prompt_counts[msg] = count
        self._recent_prompts.append(msg)
        if len(self._recent_prompts) > 60:
            self._recent_prompts = self._recent_prompts[-60:]
        n = len(self._recent_prompts)
        cycle_detected = False
        if n >= 4:
            for cycle_len in range(1, min(n // 2, 10) + 1):
                tail = self._recent_prompts[-cycle_len:]
                prev = self._recent_prompts[-2 * cycle_len:-cycle_len]
                if tail == prev and cycle_len > 0:
                    cycle_detected = True
                    break
        if count >= _LOOP_DETECTION_MAX or cycle_detected:
            if cycle_detected:
                for key in list(self._prompt_counts.keys()):
                    if key != msg:
                        self._prompt_counts[key] = self._prompt_counts.get(key, 0) + 1
            self._recent_prompts.clear()
            msg_lower = msg.lower()
            if any(kw in msg_lower for kw in ("opcao", "opção", "voltar", "cancelar", "menu")):
                return "0"
            if any(kw in msg_lower for kw in ("concluir", "finalizar", "sair")):
                return "0"
            return str(default)
        self._flush_output()
        body = self._consume_body()
        session = get_current_session()
        result = session.step("prompt", msg, default, {"body": body})
        return str(result).strip() if result else str(default)


bridge = WebBridge()


def install_bridge():
    session = get_current_session()
    bridge = WebBridge()
    session._bridge = bridge
    cli_ui._tl._web_bridge = bridge
    cli_ui._tl._WEB_MODE = True
    with _redirect_lock:
        _chain_redirector.install()


def uninstall_bridge():
    with _redirect_lock:
        _chain_redirector.uninstall()
    cli_ui._tl._web_bridge = None
    cli_ui._tl._WEB_MODE = cli_ui._WEB_MODE_INIT


def _load_micro_df(session, cfg):
    from src.atm.orca.io import carregar_planilha_microplanejamento
    planilhas_dir = session.data_dir / "planilhas"
    candidates = []
    for key in ("micro_atual", "arquivo"):
        c = cfg.get(key, "")
        if c:
            p = str(planilhas_dir / c)
            if os.path.exists(p):
                candidates.append(p)
    if planilhas_dir.exists():
        files = sorted(os.listdir(planilhas_dir))
        xlsx = [f for f in files if f.lower().endswith((".xlsx", ".xlsm", ".xls"))]
        for pref in ("consolidado", "microplanejamento", "planejamento"):
            for f in xlsx:
                if pref in f.lower():
                    p = str(planilhas_dir / f)
                    if p not in candidates:
                        candidates.append(p)
        for f in xlsx:
            p = str(planilhas_dir / f)
            if p not in candidates:
                candidates.append(p)
    for path in candidates:
        try:
            df = carregar_planilha_microplanejamento(cfg, caminho=path, modo_auto=True)
            if df is not None and not df.empty:
                return path, df
        except Exception:
            continue
    return None, None


def _run_scheduler_single(session: Session, fazenda: str):
    from src.atm.orca.app import _executar_scheduler_fazenda_interativo
    from src.atm.orca.context import contexto_sessao

    set_current_session(session)
    install_bridge()

    cfg = _load_session_config(session)
    session.cfg = cfg

    session._output_buf = StringIO()
    _chain_redirector._parent_buf = session._output_buf

    try:
        with _redirect_lock:
            _chain_redirector.install_tee(session._output_buf)
        from src.atm.orca.app import _aplicar_filtro_empresa_e_escopo, _aplicar_filtro_regiao

        micro_path, df = _load_micro_df(session, cfg)
        if df is None:
            session.mark_finished("Nenhum arquivo micro valido encontrado")
            return

        df_scope, regiao_info = _aplicar_filtro_regiao(df)
        if df_scope is None or df_scope.empty:
            session.mark_finished("Nenhum dado apos filtro de regiao")
            return
        df_scope, empresa_filtro = _aplicar_filtro_empresa_e_escopo(df_scope)
        if df_scope is None or df_scope.empty:
            session.mark_finished("Nenhum dado apos filtros")
            return

        faz_norm = fazenda.strip().upper()
        faz_col_stripped = df_scope["fazenda"].astype(str).str.strip().str.upper()
        match = df_scope[faz_col_stripped == faz_norm]
        if match.empty:
            faz_col_stripped_contains = df_scope["fazenda"].astype(str).str.strip().str.upper()
            match = df_scope[faz_col_stripped_contains.str.contains(faz_norm, na=False)]
        if match.empty:
            disponiveis = sorted(df_scope["fazenda"].dropna().unique().tolist())
            session.mark_finished(f"Fazenda '{fazenda}' nao encontrada. Disponiveis: {disponiveis[:10]}")
            return
        fazenda_real = match.iloc[0]["fazenda"]
        df_faz_base = match.copy()

        contexto_sessao.atualizar_fazenda(fazenda_real, df_faz_base)
        session.dashboard = {
            "fazenda_selecionada": fazenda_real,
            "equipe_selecionada": contexto_sessao.equipe_selecionada,
            "talhoes_selecionados": contexto_sessao.talhoes_selecionados,
            "total_talhoes_fazenda": contexto_sessao.total_talhoes_fazenda,
            "area_total_fazenda": contexto_sessao.area_total_fazenda,
            "atividades_distribuidas": contexto_sessao.atividades_distribuidas,
            "total_atividades": contexto_sessao.total_atividades,
            "modo_atual": contexto_sessao.modo_atual,
            "orcamento_estrito": contexto_sessao.orcamento_estrito,
        }

        _executar_scheduler_fazenda_interativo(cfg, df_scope, fazenda_real, None)
        _collect_result_files(session, fazenda_real)
        session.mark_finished()

    except Exception as e:
        session.mark_finished(str(e))
        traceback.print_exc()
    finally:
        with _redirect_lock:
            _chain_redirector.uninstall_tee()
        uninstall_bridge()
        set_current_session(None)

def _run_scheduler_batch(session: Session):
    from src.atm.orca.context import contexto_sessao
    from src.atm.orca.scheduler_core import _executar_lote_fazendas

    set_current_session(session)
    install_bridge()

    cfg = _load_session_config(session)
    session.cfg = cfg

    session._output_buf = StringIO()
    _chain_redirector._parent_buf = session._output_buf

    try:
        with _chain_redirector._original_redirect_stdout(session._output_buf), _chain_redirector._original_redirect_stderr(session._output_buf):
            from src.atm.orca.app import _aplicar_filtro_empresa_e_escopo, _aplicar_filtro_regiao

            micro_path, df = _load_micro_df(session, cfg)
            if df is None:
                session.mark_finished("Nenhum arquivo micro valido encontrado")
                return

            df_scope, regiao_info = _aplicar_filtro_regiao(df)
            if df_scope is None or df_scope.empty:
                session.mark_finished("Nenhum dado apos filtro de regiao")
                return
            df_scope, empresa_filtro = _aplicar_filtro_empresa_e_escopo(df_scope)
            if df_scope is None or df_scope.empty:
                session.mark_finished("Nenhum dado apos filtros")
                return

            fazendas = sorted(df_scope["fazenda"].unique().tolist())
            contexto_sessao.atualizar_modo("lote")
            _executar_lote_fazendas(cfg, df_scope, fazendas, empresa_filtro=empresa_filtro)
        _collect_result_files(session)
        session.mark_finished()

    except Exception as e:
        session.mark_finished(str(e))
        traceback.print_exc()
    finally:
        uninstall_bridge()
        set_current_session(None)


def _run_scheduler_multi(session: Session):
    from src.atm.orca.context import contexto_sessao
    from src.atm.orca.scheduler_core import _executar_multi_equipes

    set_current_session(session)
    install_bridge()

    cfg = _load_session_config(session)
    session.cfg = cfg

    session._output_buf = StringIO()
    _chain_redirector._parent_buf = session._output_buf

    try:
        with _chain_redirector._original_redirect_stdout(session._output_buf), _chain_redirector._original_redirect_stderr(session._output_buf):
            from src.atm.orca.app import _aplicar_filtro_empresa_e_escopo, _aplicar_filtro_regiao

            micro_path, df = _load_micro_df(session, cfg)
            if df is None:
                session.mark_finished("Nenhum arquivo micro valido encontrado")
                return

            df_scope, regiao_info = _aplicar_filtro_regiao(df)
            if df_scope is None or df_scope.empty:
                session.mark_finished("Nenhum dado apos filtro de regiao")
                return
            df_scope, empresa_filtro = _aplicar_filtro_empresa_e_escopo(df_scope)
            if df_scope is None or df_scope.empty:
                session.mark_finished("Nenhum dado apos filtros")
                return

            fazendas = sorted(df_scope["fazenda"].unique().tolist())
            contexto_sessao.atualizar_modo("multi_equipes")
            _executar_multi_equipes(cfg, df_scope, fazendas, empresa_filtro=empresa_filtro)
        _collect_result_files(session)
        session.mark_finished()

    except Exception as e:
        session.mark_finished(str(e))
        traceback.print_exc()
    finally:
        uninstall_bridge()
        set_current_session(None)


def _collect_result_files(session, fazenda=None):
    from src.atm.orca.config import OUTPUT_DIR
    dossier_dir = Path(OUTPUT_DIR)
    if not dossier_dir.exists():
        return
    created_ts = session.created_at.timestamp()
    existing = set(session.result_files)
    for f in sorted(dossier_dir.glob("*.xlsx")):
        if f.name not in existing:
            if f.stat().st_mtime > created_ts:
                session.result_files.append(f.name)
                existing.add(f.name)


def start_session(mode: str = "single", params: dict | None = None) -> Session:
    params = params or {}
    session = Session()
    register_session(session)

    if mode == "single":
        fazenda = params.get("fazenda", "")
        t = threading.Thread(
            target=_run_scheduler_single,
            args=(session, fazenda),
            daemon=True,
        )
        session.thread = t
        t.start()
    elif mode == "batch":
        t = threading.Thread(
            target=_run_scheduler_batch,
            args=(session,),
            daemon=True,
        )
        session.thread = t
        t.start()
    elif mode == "multi":
        t = threading.Thread(
            target=_run_scheduler_multi,
            args=(session,),
            daemon=True,
        )
        session.thread = t
        t.start()

    return session


def abort_session(session_id: str) -> bool:
    session = get_session(session_id)
    if session and session.alive:
        session.alive = False
        session.answer(None)
        remove_session(session_id)
        return True
    return False

"""
SRF monitor subsystem — emit state/relatorio/rendimentos to external monitor.

Gracefully degrades to no-ops when srf_monitor_state is unavailable.
Dependencies: none internal (contexto_sessao is injected at init time).
External: srf_monitor_state (optional), os, json, subprocess
"""

import os
import sys

# ──────────────────────────────────────────────
# OPTIONAL MONITOR STATE IMPORT
# ──────────────────────────────────────────────
try:
    from orca_monitor_state import (
        append_relatorio as _monitor_append_relatorio,
    )
    from orca_monitor_state import (
        build_rendimentos_from_demandas as _monitor_build_rendimentos,
    )
    from orca_monitor_state import (
        default_state_path as _monitor_default_state_path,
    )
    from orca_monitor_state import (
        merge_emit as _monitor_merge_emit,
    )
except Exception:
    _monitor_append_relatorio = None
    _monitor_build_rendimentos = None
    _monitor_default_state_path = None
    _monitor_merge_emit = None


# ──────────────────────────────────────────────
# STATE PATH
# ──────────────────────────────────────────────
_MONITOR_STATE_PATH = (
    _monitor_default_state_path(os.getpid())
    if callable(_monitor_default_state_path)
    else None
)

# Reference to contexto_sessao — set by the application at startup.
# This avoids circular imports while allowing monitor to access session context.
_contexto_sessao = None


def init_monitor(contexto_sessao):
    """Inject the global ContextoSessao instance. Call once at app startup."""
    global _contexto_sessao
    _contexto_sessao = contexto_sessao


# ──────────────────────────────────────────────
# EMIT FUNCTIONS (safe no-ops when monitor unavailable)
# ──────────────────────────────────────────────

def _emitir_monitor_state(partial):
    if _MONITOR_STATE_PATH and callable(_monitor_merge_emit):
        try:
            _monitor_merge_emit(_MONITOR_STATE_PATH, partial)
        except Exception:
            pass


def _emitir_monitor_relatorio(titulo, texto):
    if _MONITOR_STATE_PATH and callable(_monitor_append_relatorio):
        try:
            _monitor_append_relatorio(_MONITOR_STATE_PATH, titulo, texto)
        except Exception:
            pass


def _emitir_monitor_atual():
    """Emite o estado atual do contexto para os monitores."""
    if not (_MONITOR_STATE_PATH and callable(_monitor_merge_emit)):
        return
    if _contexto_sessao is None:
        return

    try:
        estado = {}

        if _contexto_sessao.fazenda_selecionada:
            estado["operacao"] = {
                "fazenda_atual": str(_contexto_sessao.fazenda_selecionada),
                "modo": str(_contexto_sessao.modo_atual or ""),
                "equipe_atual": str(_contexto_sessao.equipe_selecionada or ""),
                "status_geral": "em_execucao",
            }

            msg_parts = []
            if _contexto_sessao.fazenda_selecionada:
                msg_parts.append(str(_contexto_sessao.fazenda_selecionada))
            if _contexto_sessao.equipe_selecionada:
                msg_parts.append(f"Eq:{_contexto_sessao.equipe_selecionada}")
            if msg_parts:
                estado["operacao"]["mensagem_curta"] = " | ".join(msg_parts)

        if _contexto_sessao.talhoes_selecionados is not None:
            estado["lote"] = {
                "talhoes_selecionados": len(_contexto_sessao.talhoes_selecionados),
                "talhoes_total": _contexto_sessao.total_talhoes_fazenda,
                "area_ha": _contexto_sessao.area_total_fazenda,
                "dias_meta": 0,
                "dias_consumidos": 0,
                "saldo_dias": 0,
                "status_meta_continuo": "OK",
                "prazo_absoluto": True,
            }

        if _contexto_sessao.total_atividades > 0 and _contexto_sessao.atividades_distribuidas > 0:
            estado["rendimentos_sessao"] = [{
                "atividade": f"{_contexto_sessao.atividades_distribuidas}/{_contexto_sessao.total_atividades} atividades",
                "hh_ha": 0.0,
                "origem": "sessao",
                "chave_tarifa": "progresso"
            }]

        if _contexto_sessao.timestamp_atualizacao:
            estado["timestamp"] = _contexto_sessao.timestamp_atualizacao.timestamp()
            estado["timestamp_iso"] = _contexto_sessao.timestamp_atualizacao.strftime("%Y-%m-%dT%H:%M:%S")

        _monitor_merge_emit(_MONITOR_STATE_PATH, estado)
    except Exception:
        pass


def _emitir_monitor_rendimentos(
    atividade_nome: str,
    vincular: bool,
    hh_ha: float = 0.0,
    origem: str = "",
    chave_tarifa: str = "",
):
    """Emite atualizacao de rendimento quando uma atividade e vinculada/desvinculada."""
    if not (_MONITOR_STATE_PATH and callable(_monitor_merge_emit)):
        return
    if _contexto_sessao is None:
        return

    try:
        rendimentos_existentes = []

        if _MONITOR_STATE_PATH and os.path.exists(_MONITOR_STATE_PATH):
            try:
                import json as _json
                with open(_MONITOR_STATE_PATH, encoding="utf-8") as f:
                    dados_existentes = _json.load(f)
                rendimentos_existentes = dados_existentes.get("rendimentos_sessao", []).copy()
            except Exception:
                rendimentos_existentes = []

        if atividade_nome and vincular and hh_ha > 0:
            atividade_encontrada = False
            novas_rendimentos = []
            for rend in rendimentos_existentes:
                if rend.get("atividade") == str(atividade_nome):
                    novas_rendimentos.append({
                        "atividade": str(atividade_nome),
                        "hh_ha": float(hh_ha),
                        "origem": str(origem) if origem else rend.get("origem", "sessao"),
                        "chave_tarifa": str(chave_tarifa) if chave_tarifa else rend.get("chave_tarifa", "vinculada"),
                    })
                    atividade_encontrada = True
                else:
                    novas_rendimentos.append(rend)

            if not atividade_encontrada:
                novas_rendimentos.append({
                    "atividade": str(atividade_nome),
                    "hh_ha": float(hh_ha),
                    "origem": str(origem) if origem else "sessao",
                    "chave_tarifa": str(chave_tarifa) if chave_tarifa else "vinculada",
                })

            estado = {"rendimentos_sessao": novas_rendimentos}
        elif not vincular:
            novas_rendimentos = [
                rend for rend in rendimentos_existentes
                if rend.get("atividade") != str(atividade_nome)
            ]
            estado = {"rendimentos_sessao": novas_rendimentos}
        else:
            estado = {"rendimentos_sessao": rendimentos_existentes}

        # Tambem atualizar o estado geral
        estado_geral = {}
        if _contexto_sessao.fazenda_selecionada:
            estado_geral["operacao"] = {
                "fazenda_atual": str(_contexto_sessao.fazenda_selecionada),
                "modo": str(_contexto_sessao.modo_atual or ""),
                "equipe_atual": str(_contexto_sessao.equipe_selecionada or ""),
                "status_geral": "em_execucao",
            }
            msg_parts = []
            if _contexto_sessao.fazenda_selecionada:
                msg_parts.append(str(_contexto_sessao.fazenda_selecionada))
            if _contexto_sessao.equipe_selecionada:
                msg_parts.append(f"Eq:{_contexto_sessao.equipe_selecionada}")
            if msg_parts:
                estado_geral["operacao"]["mensagem_curta"] = " | ".join(msg_parts)

        if _contexto_sessao.talhoes_selecionados is not None:
            estado_geral["lote"] = {
                "talhoes_selecionados": len(_contexto_sessao.talhoes_selecionados),
                "talhoes_total": _contexto_sessao.total_talhoes_fazenda,
                "area_ha": _contexto_sessao.area_total_fazenda,
                "dias_meta": 0,
                "dias_consumidos": 0,
                "saldo_dias": 0,
                "status_meta_continuo": "OK",
                "prazo_absoluto": True,
            }

        if _contexto_sessao.timestamp_atualizacao:
            estado_geral["timestamp"] = _contexto_sessao.timestamp_atualizacao.timestamp()
            estado_geral["timestamp_iso"] = _contexto_sessao.timestamp_atualizacao.strftime("%Y-%m-%dT%H:%M:%S")

        estado_geral.update(estado)
        _monitor_merge_emit(_MONITOR_STATE_PATH, estado_geral)
    except Exception:
        pass


def _abrir_monitor_janela(feed="meta", pid=None):
    """
    Abre uma janela separada com o monitor SRF.
    Usa subprocess para iniciar um terminal novo.
    """
    import subprocess

    from . import ui as _ui  # lazy import to avoid circular

    try:
        target_pid = int(pid or os.getpid())
        script_monitor = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "srf_monitor.py",
        )

        if not os.path.isfile(script_monitor):
            _ui.aviso(f"Script do monitor nao encontrado: {script_monitor}")
            return False

        cmd = [
            sys.executable,
            script_monitor,
            "--feed", str(feed),
            "--pid", str(target_pid),
        ]

        if os.name == "nt":
            subprocess.Popen(
                ["start", "cmd", "/k"] + cmd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            terminais = [
                ["kitty", "-e"] + cmd,
                ["foot"] + cmd,
                ["wezterm", "start", "--"] + cmd,
                ["alacritty", "-e"] + cmd,
                ["gnome-terminal", "--"] + cmd,
                ["konsole", "--hold", "-e"] + cmd,
                ["xfce4-terminal", "-e"] + cmd,
                ["xterm", "-hold", "-e"] + cmd,
            ]
            for term_cmd in terminais:
                try:
                    subprocess.Popen(
                        term_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    break
                except FileNotFoundError:
                    continue
            else:
                _ui.aviso("Nenhum terminal compativel encontrado para abrir o monitor.")
                return False

        _ui.ok(f"Monitor aberto (PID {target_pid}, feed={feed})")
        return True
    except Exception as e:
        _ui.aviso(f"Erro ao abrir monitor: {e}")
        return False

"""
Camada de servico importavel para UI/REST futura: delega ao nucleo atm_v5 sem duplicar regras.

Uso tipico (mesmo processo Python ou subprocess com PYTHONPATH ao diretorio do projeto):

    from srf_scheduler_service import load_monitor_state, run_cronograma_single

Evite importar este modulo no arranque do atm_v5.py para nao criar dependencia circular;
importe a partir de servidores HTTP ou testes.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

DIR = os.path.dirname(os.path.abspath(__file__))
CFGP = os.path.join(DIR, "config.json")


def load_config() -> Dict[str, Any]:
    if not os.path.isfile(CFGP):
        return {}
    with open(CFGP, encoding="utf-8") as f:
        return json.load(f)


def load_monitor_state(pid: Optional[int] = None) -> Dict[str, Any]:
    from srf_monitor_state import default_state_path, ler_estado

    return ler_estado(default_state_path(pid))


def run_cronograma_single(
    cfg: Dict[str, Any],
    df_faz,
    fazenda: str,
    *,
    esperar_enter: bool = False,
    ctx: Optional[Dict[str, Any]] = None,
    escopo_meta: Optional[Dict[str, Any]] = None,
):
    """Executa um ciclo Smart Scheduler (delega a calcular_cronograma_inteligente)."""
    import importlib

    mod = importlib.import_module("atm_v5")
    return mod.calcular_cronograma_inteligente(
        cfg,
        df_faz,
        fazenda,
        esperar_enter=esperar_enter,
        ctx=ctx,
        escopo_meta=escopo_meta,
    )

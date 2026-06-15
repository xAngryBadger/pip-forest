"""Orchestrator runner — main entry point coordinating all phases."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from ...logging_config import get_logger

logger = get_logger(__name__)

from .phase1_setup import _phase1_setup
from .phase2_linking import _phase2_linking
from .phase3_checkpoint import _phase3_checkpoint
from .phase4_demands import _phase4_demands
from .phase5_scheduler_loop import _phase5_scheduler_loop
from .phase6_mecanizado import _phase6_mecanizado
from .phase7_audit_export import _phase7_audit_export
from .phase8_comparativo import _phase8_comparativo


def calcular_cronograma_inteligente(
    cfg: Dict[str, Any],
    df_faz: pd.DataFrame,
    fazenda: str,
    esperar_enter: bool = True,
    ctx: Optional[Dict[str, Any]] = None,
    escopo_meta: Optional[Dict[str, Any]] = None,
    atividades_catalogo: Optional[Dict[str, Any]] = None,
    modo_comparativo: bool = False,
    substituicoes_comparativo: Optional[Dict[str, Any]] = None,
    avaliar_terreno_fn: Optional[Any] = None,
    ajustar_escopo_fn: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Main orchestrator — coordinates all scheduling phases.
    
    ctx: optional dict with preconfigured session state for batch mode.
    When ctx is provided, interactive setup questions are skipped.
    
    avaliar_terreno_fn: optional callable(df_faz) -> df_faz for terrain evaluation UI.
    ajustar_escopo_fn: optional callable(df_faz, cfg, atividades_catalogo) -> df_faz for scope adjustment UI.
    """
    # Phase 1: Setup, validation, initial configuration
    setup = _phase1_setup(
        cfg, df_faz, fazenda, esperar_enter, ctx, escopo_meta,
        atividades_catalogo, modo_comparativo, substituicoes_comparativo,
        avaliar_terreno_fn, ajustar_escopo_fn,
    )
    if setup.get("status") != "ok":
        return {}

    # Phase 2: Activity linking and conflict configuration
    setup = _phase2_linking(setup, cfg, ctx, atividades_catalogo, fazenda)
    if setup.get("status") == "cancelled":
        return {}

    # Phase 3: Checkpoint retroativo and budget validation
    setup = _phase3_checkpoint(setup, cfg, ctx, atividades_catalogo, ajustar_escopo_fn)
    if setup.get("status") in ("cancelled", "error", "retroceder_escopo"):
        if setup.get("acao") == "orcamento_invalido":
            return {"acao": "orcamento_invalido"}
        return {}

    # Phase 4: Build demands and pre-scheduler checks
    setup = _phase4_demands(setup, cfg, ctx, fazenda)
    if setup.get("status") == "cancelled":
        return {}

    # Phase 5: Execute scheduler loop
    setup = _phase5_scheduler_loop(setup, cfg, fazenda)

    # Phase 6: Execute mechanizado mode and multi-fator simulation
    setup = _phase6_mecanizado(setup, cfg, ctx, fazenda)

    # Phase 7: Audit scope and export dossier
    setup = _phase7_audit_export(setup, cfg, fazenda, esperar_enter)

    # Phase 8: Execute comparativo and build final result
    resultado_final = _phase8_comparativo(
        setup, cfg, ctx, fazenda, esperar_enter,
        substituicoes_comparativo, atividades_catalogo,
    )

    return resultado_final
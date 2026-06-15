"""Phase 3: Checkpoint retroativo and budget validation."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from ...logging_config import get_logger

logger = get_logger(__name__)

from ...config import modo_somente_hh
from ...monitor import _emitir_monitor_atual
from ...scheduler import validar_e_completar_orcamento
from ...ui import aviso, esperar
from ..checkpoint import _executar_checkpoint_retroativo


def _phase3_checkpoint(
    setup: Dict[str, Any],
    cfg: Dict[str, Any],
    ctx: Optional[Dict[str, Any]],
    atividades_catalogo: Optional[Dict[str, Any]],
    ajustar_escopo_fn: Optional[Any],
) -> Dict[str, Any]:
    """
    Phase 3: Execute checkpoint retroativo, validate budget.
    
    Returns updated setup dict or error/cancel status.
    """
    _batch = setup["_batch"]
    turmas = setup["turmas"]
    atividades_reais = setup["atividades_reais"]
    catalogo_global = setup["catalogo_global"]
    executores = setup["executores"]
    jornada = setup["jornada"]
    session_hh = setup["session_hh"]
    reatribuicao = setup["reatribuicao"]
    paralelo = setup["paralelo"]
    primaria = setup["primaria"]
    df_faz = setup["df_faz"]

    def _recalcular_apos_ajuste_escopo():
        nonlocal df_faz, atividades_reais, catalogo_global
        from ...text_utils import _norm_atv
        atividades_reais = sorted(
            {
                a
                for a in df_faz["atividade"].dropna().unique().tolist()
                if _norm_atv(a)
            },
            key=str,
        )
        talhoes_ordenados = sorted(df_faz["chave"].dropna().unique().tolist())
        catalogo_global = _catalogo_atividades_completo(
            atividades_reais,
            cfg=cfg,
            atividades_catalogo=atividades_catalogo,
        )
        for t in turmas:
            cur = [a for a in (t.get("atividades") or []) if a in catalogo_global]
            t["atividades"] = sorted(set(cur), key=str)
        return atividades_reais, talhoes_ordenados, catalogo_global

    cp_result = _executar_checkpoint_retroativo(
        _batch, turmas, atividades_reais, catalogo_global,
        executores, jornada, cfg, session_hh,
        reatribuicao, paralelo, primaria, df_faz,
        _recalcular_apos_ajuste_escopo,
        ajustar_escopo_fn=ajustar_escopo_fn,
    )
    if isinstance(cp_result, dict) and cp_result.get("acao") == "retroceder_escopo":
        return {"status": "retroceder_escopo", "cp_result": cp_result}
    
    jornada = cp_result["jornada"]
    executores = cp_result["executores"]
    reatribuicao = cp_result["reatribuicao"]
    paralelo = cp_result["paralelo"]
    primaria = cp_result["primaria"]
    df_faz = cp_result["df_faz"]

    # ── Validacao orcamento estrito (antes das demandas) ──
    if not validar_e_completar_orcamento(cfg, atividades_reais, session_hh=session_hh):
        if not _batch:
            esperar("ENTER para voltar")
            return {"status": "cancelled"}
        aviso("Modo batch: validacao de orcamento falhou; cenario cancelado.")
        return {"status": "error", "acao": "orcamento_invalido"}

    setup.update({
        "jornada": jornada,
        "executores": executores,
        "reatribuicao": reatribuicao,
        "paralelo": paralelo,
        "primaria": primaria,
        "df_faz": df_faz,
        "atividades_reais": atividades_reais,
        "catalogo_global": catalogo_global,
    })
    return setup


def _catalogo_atividades_completo(atividades_reais, cfg, atividades_catalogo):
    from ...turmas import _catalogo_atividades_completo as _turmas_catalogo
    return _turmas_catalogo(atividades_reais, cfg=cfg, atividades_catalogo=atividades_catalogo)
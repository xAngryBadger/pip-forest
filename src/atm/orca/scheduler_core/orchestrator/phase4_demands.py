"""Phase 4: Build demands and pre-scheduler checks."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...logging_config import get_logger

logger = get_logger(__name__)

from ...config import modo_somente_hh
from ...scheduler import _mostrar_painel_hh_hm_pre_scheduler
from ...constants import CT317_HARDCODE_HH_BASE
from ...text_utils import _norm_atv
from ...ui import aviso, confirmar, sub
from ..demand import (
    _construir_atividade_remap,
    _construir_demandas,
    _construir_filas_e_demanda_global,
)
from ..validation import (
    _verificar_atividades_sem_executor,
    _verificar_atividades_sem_tarifa,
)


def _phase4_demands(
    setup: Dict[str, Any],
    cfg: Dict[str, Any],
    ctx: Optional[Dict[str, Any]],
    fazenda: str,
) -> Dict[str, Any]:
    """
    Phase 4: Build demands, pre-check HH/HM, verify executors.
    
    Returns updated setup dict or error/cancel status.
    """
    _batch = setup["_batch"]
    atividades_reais = setup["atividades_reais"]
    talhoes_ordenados = setup["talhoes_ordenados"]
    df_faz = setup["df_faz"]
    turmas = setup["turmas"]
    reatribuicao = setup["reatribuicao"]
    paralelo = setup["paralelo"]
    primaria = setup["primaria"]
    jornada = setup["jornada"]
    executores = setup["executores"]
    seq_cfg = setup["seq_cfg"]
    modo_seq = setup["modo_seq"]
    usar_cascata = setup["usar_cascata"]
    usar_bloqueio_global = setup["usar_bloqueio_global"]
    atividades_bloqueadas = setup["atividades_bloqueadas"]
    usar_reforco_automatico = setup["usar_reforco_automatico"]
    usar_pool_pos_bloqueio = setup["usar_pool_pos_bloqueio"]
    session_hh = setup["session_hh"]
    comparativo_cfg = setup["comparativo_cfg"]
    substituicoes_comparativo = setup["substituicoes_comparativo"]
    modo_comparativo = setup["modo_comparativo"]

    tarifas = cfg.get("tarifas", {})
    de_para = cfg.get("de_para", {})
    strict = cfg.get("orcamento_estrito", True)

    demanda_data = _construir_demandas(
        talhoes_ordenados, df_faz, cfg, tarifas, strict, session_hh, modo_somente_hh, atividades_reais,
    )
    demandas = demanda_data["demandas"]
    total_hh = demanda_data["total_hh"]
    total_hm = demanda_data["total_hm"]
    total_custo = demanda_data["total_custo"]
    hm_only_atividades = demanda_data["hm_only_atividades"]
    fallback_hh_items = demanda_data["fallback_hh_items"]

    _verificar_atividades_sem_tarifa(demandas, cfg, tarifas, strict)

    sub()
    logger.info("PRE-CHECAGEM HH/HM ANTES DO CRONOGRAMA")
    if modo_comparativo and substituicoes_comparativo:
        logger.debug("  [COMPARATIVO] Esta pre-checagem e o cronograma abaixo representam o CENARIO BASELINE (manual atual).")
    _mostrar_painel_hh_hm_pre_scheduler(demandas, fazenda, detalhado=False)
    if (not _batch) and confirmar("Exibir HH/HM detalhado por talhao?", default=False):
        _mostrar_painel_hh_hm_pre_scheduler(demandas, fazenda, detalhado=True)

    _result_sem_exec = _verificar_atividades_sem_executor(
        demandas, turmas, reatribuicao, paralelo, primaria, _batch, cfg,
    )
    if _result_sem_exec is None:
        return {"status": "cancelled"}
    if isinstance(_result_sem_exec, dict):
        if _result_sem_exec.get("status") == "needs_confirmation":
            if _batch:
                logger.warning("Atividades sem executora detectadas; HH serao zeradas no modo batch.")
                total_hh = _result_sem_exec["totals"]["total_hh"]
                total_custo = _result_sem_exec["totals"]["total_custo"]
                total_hm = _result_sem_exec["totals"]["total_hm"]
            else:
                logger.error("Atividades sem executora. Use modo batch ou corrija as turmas.")
                return {"status": "cancelled"}
        else:
            total_hh = _result_sem_exec["totals"]["total_hh"]
            total_custo = _result_sem_exec["totals"]["total_custo"]
            total_hm = _result_sem_exec["totals"]["total_hm"]
    else:
        total_hh, total_custo, total_hm = _result_sem_exec

    sub()
    logger.info("GERANDO CRONOGRAMA (talhao a talhao)...")

    turma_filas, demanda_global, atividades_plantio, atividades_irrig, \
    tem_plantio_por_talhao = _construir_filas_e_demanda_global(
        turmas, talhoes_ordenados, demandas, reatribuicao, paralelo, primaria,
        atividades_reais, seq_cfg, modo_seq, usar_cascata,
    )
    dia_termino_plantio = {}

    setup.update({
        "demandas": demandas,
        "total_hh": total_hh,
        "total_hm": total_hm,
        "total_custo": total_custo,
        "hm_only_atividades": hm_only_atividades,
        "fallback_hh_items": fallback_hh_items,
        "turma_filas": turma_filas,
        "demanda_global": demanda_global,
        "atividades_plantio": atividades_plantio,
        "atividades_irrig": atividades_irrig,
        "tem_plantio_por_talhao": tem_plantio_por_talhao,
        "dia_termino_plantio": dia_termino_plantio,
    })
    return setup
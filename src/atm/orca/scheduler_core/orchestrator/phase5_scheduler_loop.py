"""Phase 5: Execute scheduler loop."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...logging_config import get_logger

logger = get_logger(__name__)

from ...config import modo_somente_hh
from ...scheduler import _mostrar_painel_hh_hm_pre_scheduler
from ..scheduler_loop import _SchedulerLoopConfig, _executar_scheduler_loop
from ..merge import _merge_cronograma_base_e_metricas
from ..display import _mostrar_tabela_semanal


def _phase5_scheduler_loop(
    setup: Dict[str, Any],
    cfg: Dict[str, Any],
    fazenda: str,
) -> Dict[str, Any]:
    """
    Phase 5: Execute the scheduler loop.
    
    Returns updated setup dict with cronograma results.
    """
    _batch = setup["_batch"]
    turmas = setup["turmas"]
    turma_filas = setup["turma_filas"]
    demanda_global = setup["demanda_global"]
    demandas = setup["demandas"]
    talhoes_ordenados = setup["talhoes_ordenados"]
    jornada = setup["jornada"]
    executores = setup["executores"]
    seq_cfg = setup["seq_cfg"]
    modo_seq = setup["modo_seq"]
    usar_cascata = setup["usar_cascata"]
    usar_bloqueio_global = setup["usar_bloqueio_global"]
    atividades_bloqueadas = setup["atividades_bloqueadas"]
    usar_reforco_automatico = setup["usar_reforco_automatico"]
    usar_pool_pos_bloqueio = setup["usar_pool_pos_bloqueio"]
    atividades_plantio = setup["atividades_plantio"]
    atividades_irrig = setup["atividades_irrig"]
    dia_termino_plantio = setup["dia_termino_plantio"]
    tem_plantio_por_talhao = setup["tem_plantio_por_talhao"]
    total_hh = setup["total_hh"]
    mes_ref = setup["mes_ref"]
    ano_ref = setup["ano_ref"]
    prazo_meses = setup["prazo_meses"]
    tarifas = cfg.get("tarifas", {})

    config = _SchedulerLoopConfig(
        turmas=turmas,
        turma_filas=turma_filas,
        demanda_global=demanda_global,
        demandas=demandas,
        talhoes_ordenados=talhoes_ordenados,
        jornada=jornada,
        executores=executores,
        seq_cfg=seq_cfg,
        modo_seq=modo_seq,
        usar_cascata=usar_cascata,
        usar_bloqueio_global=usar_bloqueio_global,
        atividades_bloqueadas=atividades_bloqueadas,
        usar_reforco_automatico=usar_reforco_automatico,
        usar_pool_pos_bloqueio=usar_pool_pos_bloqueio,
        atividades_plantio=atividades_plantio,
        atividades_irrig=atividades_irrig,
        fazenda=fazenda,
        cfg=cfg,
        tarifas=tarifas,
        modo_somente_hh_fn=modo_somente_hh,
        dia_termino_plantio=dia_termino_plantio,
        tem_plantio_por_talhao=tem_plantio_por_talhao,
    )
    cronograma, dia, demanda_global = _executar_scheduler_loop(config)

    cronograma_base, dias_simulado_hum, dias_simulado, dias_meta, \
    meses_simulado, hh_por_turma, n_demandas, n_fb, pct_fallback, \
    hm_only_list, cronograma_mec_base = _merge_cronograma_base_e_metricas(
        setup["hm_only_atividades"], demandas, cronograma, fazenda, jornada,
        cfg, tarifas, dia, mes_ref, ano_ref, prazo_meses,
        total_hh, executores,
        mostrar_tabela_fn=_mostrar_tabela_semanal,
    )

    setup.update({
        "cronograma": cronograma,
        "dia": dia,
        "demanda_global": demanda_global,
        "cronograma_base": cronograma_base,
        "dias_simulado_hum": dias_simulado_hum,
        "dias_simulado": dias_simulado,
        "dias_meta": dias_meta,
        "meses_simulado": meses_simulado,
        "hh_por_turma": hh_por_turma,
        "n_demandas": n_demandas,
        "n_fb": n_fb,
        "pct_fallback": pct_fallback,
        "hm_only_list": hm_only_list,
        "cronograma_mec_base": cronograma_mec_base,
    })
    return setup
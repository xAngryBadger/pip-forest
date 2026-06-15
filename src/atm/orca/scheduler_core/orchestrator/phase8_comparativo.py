"""Phase 8: Execute comparativo and build final result."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...logging_config import get_logger

logger = get_logger(__name__)

from ...comparativo_config import _configurar_modo_comparativo
from ..comparativo import (
    _ComparativoExecutionConfig,
    _ComparativoResult,
    _ComparativoUIConfig,
    _executar_modo_comparativo,
)
from ..resultados import _build_resultado_final


def _phase8_comparativo(
    setup: Dict[str, Any],
    cfg: Dict[str, Any],
    ctx: Optional[Dict[str, Any]],
    fazenda: str,
    esperar_enter: bool,
    substituicoes_comparativo: Optional[Dict[str, Any]],
    atividades_catalogo: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Phase 8: Execute comparativo and build final result.
    
    Returns final result dict.
    """
    _batch = setup["_batch"]
    modo_comparativo = setup["modo_comparativo"]
    session_hh = setup["session_hh"]
    df_faz = setup["df_faz"]
    modo_seq = setup["modo_seq"]
    usar_bloqueio_global = setup["usar_bloqueio_global"]
    usar_reforco_automatico = setup["usar_reforco_automatico"]
    usar_pool_pos_bloqueio = setup["usar_pool_pos_bloqueio"]
    prazo_meses = setup["prazo_meses"]
    mes_ref = setup["mes_ref"]
    ano_ref = setup["ano_ref"]
    data_inicio_txt = setup["data_inicio_txt"]
    data_fim_txt = setup["data_fim_txt"]
    jornada = setup["jornada"]
    executores = setup["executores"]
    turmas = setup["turmas"]
    preencher_orfas = False
    reatribuicao = setup["reatribuicao"]
    paralelo = setup["paralelo"]
    primaria = setup["primaria"]
    escopo_meta = setup.get("escopo_meta")
    total_hh = setup["total_hh"]
    total_hm = setup["total_hm"]
    dias_simulado = setup["dias_simulado"]
    cronograma_base = setup["cronograma_base"]
    recursos_mec = setup["recursos_mec"]
    cronograma_com_mec = setup["cronograma_com_mec"]
    demandas = setup["demandas"]
    resultado_mecanizado = setup.get("resultado_mecanizado")
    resultado_mecanizado_valido = setup.get("resultado_mecanizado_valido")
    result_files = setup["result_files"]

    _ui_ctx = _ComparativoUIConfig(
        modo_comparativo=modo_comparativo,
        substituicoes_comparativo=substituicoes_comparativo,
        session_hh=session_hh,
    )
    _exec_ctx = _ComparativoExecutionConfig(
        cfg=cfg,
        df_faz=df_faz,
        fazenda=fazenda,
        modo_seq=modo_seq,
        usar_bloqueio_global=usar_bloqueio_global,
        usar_reforco_automatico=usar_reforco_automatico,
        usar_pool_pos_bloqueio=usar_pool_pos_bloqueio,
        prazo_meses=prazo_meses,
        mes_ref=mes_ref,
        ano_ref=ano_ref,
        data_inicio_txt=data_inicio_txt,
        data_fim_txt=data_fim_txt,
        jornada=jornada,
        executores=executores,
        turmas=turmas,
        preencher_orfas=preencher_orfas,
        reatribuicao=reatribuicao,
        paralelo=paralelo,
        primaria=primaria,
        escopo_meta=escopo_meta,
        atividades_catalogo=atividades_catalogo,
    )
    _result_ctx = _ComparativoResult(
        total_hh=total_hh,
        total_hm=total_hm,
        dias_simulado=dias_simulado,
    )
    resultado_mecanizado, resultado_mecanizado_valido = _executar_modo_comparativo(_ui_ctx, _exec_ctx, _result_ctx)

    resultado_final = _build_resultado_final(
        esperar_enter, fazenda, dias_simulado, setup["meses_simulado"],
        prazo_meses, setup["dias_meta"], total_hh, setup["total_custo"], total_hm,
        cronograma_base, turmas, resultado_mecanizado,
        resultado_mecanizado_valido, substituicoes_comparativo,
        recursos_mec, cronograma_com_mec, demandas,
        result_files=result_files,
    )

    return resultado_final
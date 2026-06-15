"""Phase 6: Execute mechanizado mode and multi-fator simulation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...logging_config import get_logger

logger = get_logger(__name__)

from ...comparativo_config import _configurar_modo_comparativo
from ...ui import aviso, confirmar
from ..mechanizado import _executar_modo_mecanizado_opcional
from ..multi_fator import _executar_multi_fator_simulation
from ..display import _mostrar_tabela_ocupacao


def _phase6_mecanizado(
    setup: Dict[str, Any],
    cfg: Dict[str, Any],
    ctx: Optional[Dict[str, Any]],
    fazenda: str,
) -> Dict[str, Any]:
    """
    Phase 6: Execute mechanizado mode and multi-fator simulation.
    
    Returns updated setup dict with mechanizado results.
    """
    _batch = setup["_batch"]
    modo_comparativo = setup["modo_comparativo"]
    substituicoes_comparativo = setup["substituicoes_comparativo"]
    atividades_reais = setup["atividades_reais"]
    hm_only_list = setup["hm_only_list"]
    catalogo_global = setup["catalogo_global"]
    demandas = setup["demandas"]
    jornada = setup["jornada"]
    cronograma = setup["cronograma"]
    turmas = setup["turmas"]
    executores = setup["executores"]
    cronograma_base = setup["cronograma_base"]
    cronograma_mec_base = setup["cronograma_mec_base"]
    dias_simulado = setup["dias_simulado"]
    dias_meta = setup["dias_meta"]
    total_hh = setup["total_hh"]
    usar_bloqueio_global = setup["usar_bloqueio_global"]
    usar_pool_pos_bloqueio = setup["usar_pool_pos_bloqueio"]
    n_fb = setup["n_fb"]
    pct_fallback = setup["pct_fallback"]
    n_demandas = setup["n_demandas"]
    hh_por_turma = setup["hh_por_turma"]
    dias_simulado_hum = setup["dias_simulado_hum"]
    comparativo_cfg = setup["comparativo_cfg"]

    recursos_mec, cronograma_mec, cronograma_com_mec, atividades_mec_set = \
        _executar_modo_mecanizado_opcional(
            _batch, modo_comparativo, substituicoes_comparativo,
            atividades_reais, cfg, hm_only_list, catalogo_global,
            demandas, fazenda, jornada, cronograma, turmas, executores,
            cronograma_base, cronograma_mec_base, dias_simulado,
        )

    _mostrar_tabela_ocupacao(
        turmas, dias_simulado_hum, jornada, hh_por_turma, cronograma,
        executores, usar_pool_pos_bloqueio, usar_bloqueio_global,
        n_fb, pct_fallback, n_demandas,
    )

    cenarios_rows = _executar_multi_fator_simulation(
        comparativo_cfg, _batch, recursos_mec, cronograma_com_mec,
        total_hh, dias_meta, executores, jornada,
    )

    setup.update({
        "recursos_mec": recursos_mec,
        "cronograma_mec": cronograma_mec,
        "cronograma_com_mec": cronograma_com_mec,
        "atividades_mec_set": atividades_mec_set,
        "cenarios_rows": cenarios_rows,
    })
    return setup
"""Merge cronograma base with metrics."""

from collections import defaultdict
from typing import Callable, Optional

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..cronograma import construir_cronograma_mecanizado_auto_hm_tarifa
from ..scheduler import dias_uteis_no_periodo

from . import _HH_EPSILON, DIAS_UTEIS_POR_MES


def _merge_cronograma_base_e_metricas(hm_only_atividades, demandas, cronograma, fazenda, jornada, cfg, tarifas, dia, mes_ref, ano_ref, prazo_meses, total_hh, executores, mostrar_tabela_fn: Optional[Callable] = None):
    hm_only_list = sorted(hm_only_atividades, key=str)
    cronograma_mec_base = []
    if hm_only_list:
        cronograma_mec_base, _ = construir_cronograma_mecanizado_auto_hm_tarifa(
            demandas, fazenda, jornada, cfg, tarifas, atividades_alvo=hm_only_list,
        )
    if cronograma_mec_base:
        logger.info(f"Cronograma base incluiu {len(cronograma_mec_base)} linha(s) mecanizadas (HM do orcamento).")

    cronograma_base = sorted(
        cronograma + cronograma_mec_base,
        key=lambda r: (int(r.get("Dia", 0)), str(r.get("Turma", ""))),
    )

    dias_simulado_hum = dia
    d_mec_base = max([int(x.get("Dia", 0)) for x in cronograma_mec_base], default=0)
    dias_simulado = max(dias_simulado_hum, d_mec_base)

    dias_meta = dias_uteis_no_periodo(mes_ref, ano_ref, prazo_meses)
    meses_simulado = dias_simulado / DIAS_UTEIS_POR_MES if dias_simulado > 0 else 0

    if mostrar_tabela_fn is not None:
        mostrar_tabela_fn(cronograma_base, fazenda, executores)

    hh_por_turma = defaultdict(float)
    for c in cronograma:
        hh_por_turma[c["Turma"]] += float(c["HH"])

    n_demandas = sum(1 for tarefas in demandas.values() for t in tarefas)
    n_fb = sum(1 for tarefas in demandas.values() for t in tarefas if t.get("origem") == "fallback")
    pct_fallback = (100.0 * n_fb / n_demandas) if n_demandas > 0 else 0.0

    return cronograma_base, dias_simulado_hum, dias_simulado, dias_meta, \
        meses_simulado, hh_por_turma, n_demandas, n_fb, pct_fallback, \
        hm_only_list, cronograma_mec_base

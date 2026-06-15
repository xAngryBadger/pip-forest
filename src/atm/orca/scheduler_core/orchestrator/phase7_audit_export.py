"""Phase 7: Audit scope and export dossier."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...logging_config import get_logger

logger = get_logger(__name__)

from ..diagnostics import _auditar_escopo_cronograma, _diagnostico_prazo
from ..display import _exportar_dossier_excel


def _phase7_audit_export(
    setup: Dict[str, Any],
    cfg: Dict[str, Any],
    fazenda: str,
    esperar_enter: bool,
) -> Dict[str, Any]:
    """
    Phase 7: Audit scope and export dossier.
    
    Returns updated setup dict with audit and export results.
    """
    _batch = setup["_batch"]
    df_faz = setup["df_faz"]
    cronograma_com_mec = setup["cronograma_com_mec"]
    cronograma_base = setup["cronograma_base"]
    demandas = setup["demandas"]
    atividades_mec_set = setup["atividades_mec_set"]
    recursos_mec = setup["recursos_mec"]
    mes_ref = setup["mes_ref"]
    ano_ref = setup["ano_ref"]
    dia_ref = setup["dia_ref"]
    prazo_meses = setup["prazo_meses"]
    dias_meta = setup["dias_meta"]
    dias_simulado = setup["dias_simulado"]
    meses_simulado = setup["meses_simulado"]
    total_hh = setup["total_hh"]
    total_custo = setup["total_custo"]
    executores = setup["executores"]
    jornada = setup["jornada"]
    cronograma = setup["cronograma"]
    cronograma_mec = setup["cronograma_mec"]
    cronograma_mec_base = setup["cronograma_mec_base"]
    turmas = setup["turmas"]
    dias_simulado_hum = setup["dias_simulado_hum"]
    pct_fallback = setup["pct_fallback"]
    n_fb = setup["n_fb"]
    escopo_meta = setup.get("escopo_meta")
    cenarios_rows = setup["cenarios_rows"]

    audit = _auditar_escopo_cronograma(
        df_faz, cronograma_com_mec, cronograma_base, demandas, atividades_mec_set, recursos_mec,
    )
    atividades_escopo = audit["atividades_escopo"]
    escopo_set = audit["escopo_set"]
    ag_hum_set = audit["ag_hum_set"]
    ag_mec_set = audit["ag_mec_set"]
    faltantes_set = audit["faltantes_set"]
    df_audit = audit["df_audit"]

    result_files = _exportar_dossier_excel(
        cronograma_base, escopo_meta, fazenda, executores, jornada,
        prazo_meses, dias_meta, dias_simulado, meses_simulado,
        total_hh, total_custo, pct_fallback, n_fb,
        atividades_escopo, ag_hum_set, escopo_set, ag_mec_set, faltantes_set,
        recursos_mec, cronograma, turmas, dias_simulado_hum,
        cronograma_mec, cronograma_com_mec, cronograma_mec_base,
        df_audit, cenarios_rows, mes_ref, ano_ref, dia_ref, cfg,
        output_dir=cfg.get("output_dir"),
    )

    _diagnostico_prazo(
        prazo_meses, dias_meta, mes_ref, ano_ref,
        dias_simulado, meses_simulado,
        executores, jornada, total_hh,
        recursos_mec, cronograma_com_mec,
    )

    setup.update({
        "audit": audit,
        "atividades_escopo": atividades_escopo,
        "escopo_set": escopo_set,
        "ag_hum_set": ag_hum_set,
        "ag_mec_set": ag_mec_set,
        "faltantes_set": faltantes_set,
        "df_audit": df_audit,
        "result_files": result_files,
    })
    return setup
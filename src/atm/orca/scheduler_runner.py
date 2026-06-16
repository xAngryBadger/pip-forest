"""
Scheduler runner — high-level API to execute scheduler from config.

Provides `run_scheduler(cfg, config, farm, micro_path, output_dir) -> ScheduleResult`.
Used by: web API headless endpoint, wizard background jobs, CLI batch mode.
"""

import src.atm.orca.scheduler_core as _sc

from .config import OUTPUT_DIR
from .io import carregar_planilha_microplanejamento
from .scheduler_config import SchedulerConfig, ScheduleResult
from .scheduler_core import calcular_cronograma_inteligente


def _expand_todas(ctx, df_faz):
    turmas = ctx.get("turmas", [])
    if not turmas:
        return
    fazenda_atividades = sorted(
        {str(a).strip() for a in df_faz["atividade"].dropna().unique() if str(a).strip()},
        key=str,
    )
    if not fazenda_atividades:
        return
    for turma in turmas:
        atvs = turma.get("atividades", [])
        if atvs == "todas" or atvs == ["todas"]:
            turma["atividades"] = fazenda_atividades


def run_scheduler(cfg, config: SchedulerConfig, farm: str = None, micro_path: str = None, output_dir: str = None) -> ScheduleResult:
    ctx = config.to_ctx_dict()
    cfg["orcamento_estrito"] = config.orcamento_estrito
    cfg["filtros_bloqueio_global"] = config.filtros_bloqueio_global
    df = carregar_planilha_microplanejamento(cfg, caminho=micro_path, modo_auto=True)
    if df is None or df.empty:
        return ScheduleResult(success=False, error="No data loaded from spreadsheet")
    fazenda = farm or (config.turmas[0].nome if config.turmas else "ALL")
    df_faz = df[df["fazenda"] == fazenda].copy()
    if df_faz.empty:
        return ScheduleResult(success=False, error=f"No data for farm '{fazenda}'")
    _expand_todas(ctx, df_faz)
    _old_output_dir = None
    if output_dir:
        cfg["output_dir"] = output_dir
        _old_output_dir = _sc.OUTPUT_DIR
        _sc.OUTPUT_DIR = output_dir
    try:
        resultado = calcular_cronograma_inteligente(
            cfg, df_faz, fazenda, esperar_enter=False, ctx=ctx
        )
    finally:
        if _old_output_dir is not None:
            _sc.OUTPUT_DIR = _old_output_dir
        if "output_dir" in cfg:
            del cfg["output_dir"]
    if resultado is None:
        return ScheduleResult(success=False, error="Scheduler returned None (missing columns)")
    if isinstance(resultado, dict) and resultado.get("acao") == "orcamento_invalido":
        return ScheduleResult(success=False, error="Budget validation failed: no tariffs loaded and orcamento_estrito=True")
    return ScheduleResult(
        success=True,
        fazenda=resultado.get("fazenda", fazenda),
        dias_simulado=resultado.get("dias_simulado", 0),
        meses_simulado=resultado.get("meses_simulado", 0.0),
        dias_mecanizado=resultado.get("dias_mecanizado"),
        ganho_mecanizado_dias=resultado.get("ganho_mecanizado_dias", 0),
        total_hh=resultado.get("total_hh", 0.0),
        total_custo=resultado.get("total_custo", 0.0),
        total_hm=resultado.get("total_hm", 0.0),
        cronograma=resultado.get("cronograma", []),
        turmas_snapshot=resultado.get("turmas_snapshot", []),
        comparativo_mecanizado=resultado.get("comparativo_mecanizado"),
        modo_usado=resultado.get("modo_seq", config.modo_seq),
    )
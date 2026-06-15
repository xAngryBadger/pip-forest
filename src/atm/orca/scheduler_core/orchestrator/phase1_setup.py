"""Phase 1: Setup, validation, and initial configuration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from ...logging_config import get_logger

logger = get_logger(__name__)

from ...comparativo_config import _configurar_modo_comparativo
from ...config import _merge_sequencia_defaults, modo_somente_hh, salvar_config
from ...context import contexto_sessao, dashboard_header
from ...de_para import aplicar_depara_padrao_exame, auto_mapear_de_para
from ...monitor import _emitir_monitor_atual, _emitir_monitor_state
from ...scheduler import validar_e_completar_orcamento
from ...tarifas import aviso_politica_tarifas_planas
from ...text_utils import _norm_atv
from ...turmas import _catalogo_atividades_completo
from ...ui import (
    BL, C, DM, G, RS, Y,
    aviso, confirmar, erro, esperar, ok, sub, subcabecalho,
)

from .. import _HH_EPSILON
from ..setup import _configurar_projeto_dados, _configurar_sequencia_bloqueio


def _phase1_setup(
    cfg: Dict[str, Any],
    df_faz: pd.DataFrame,
    fazenda: str,
    esperar_enter: bool,
    ctx: Optional[Dict[str, Any]],
    escopo_meta: Optional[Dict[str, Any]],
    atividades_catalogo: Optional[Dict[str, Any]],
    modo_comparativo: bool,
    substituicoes_comparativo: Optional[Dict[str, Any]],
    avaliar_terreno_fn: Optional[Any],
    ajustar_escopo_fn: Optional[Any],
) -> Dict[str, Any]:
    """
    Phase 1: Validate input, setup session, configure project data.
    
    Returns a dict with all the setup results needed for subsequent phases.
    """
    _batch = ctx is not None
    comparativo_cfg = None

    erro_colunas, df_faz = _validar_input(df_faz)
    if erro_colunas:
        return {"status": "error", "error": erro_colunas}
    tarifas = cfg.get("tarifas") or {}
    if not tarifas:
        aviso("Nenhuma tarifa carregada — rendimentos serao estimados (fallback)")

    contexto_sessao.atualizar_configuracoes(cfg)
    contexto_sessao.atualizar_fazenda(fazenda, df_faz)
    _emitir_monitor_atual()
    dashboard_header()

    if not _batch:
        subcabecalho(f"SMART SCHEDULER - {fazenda}")
        if avaliar_terreno_fn is not None:
            df_faz = avaliar_terreno_fn(df_faz)
        aviso_politica_tarifas_planas()
    else:
        sub()
        logger.info(f"SMART SCHEDULER - {fazenda}")
        df_faz["penalidade"] = float(ctx.get("penalidade", 1.0))

        _emitir_monitor_state(
            {
                "operacao": {
                    "fazenda_atual": str(fazenda),
                    "modo": "batch" if _batch else "single",
                    "micro_basename": str(cfg.get("arquivo_micro", "")),
                    "status_geral": "iniciando_scheduler",
                    "mensagem_curta": f"Scheduler iniciado para {fazenda}",
                }
            }
        )

    # ── Extrair atividades REAIS da fazenda ──
    df_faz = df_faz.copy()
    _norm = lambda x: _norm_atv(x) if pd.notna(x) else x
    df_faz["atividade"] = df_faz["atividade"].map(_norm)
    if not _batch and confirmar(
        "Ajustar escopo de atividades (substituir/remover/adicionar) nesta execucao?",
        default=False,
    ):
        if ajustar_escopo_fn is not None:
            df_faz = ajustar_escopo_fn(df_faz, cfg=cfg, atividades_catalogo=atividades_catalogo)
    atividades_reais = sorted(
        {a for a in df_faz["atividade"].dropna().unique().tolist() if _norm_atv(a)},
        key=str,
    )
    catalogo_global = _catalogo_atividades_completo(
        atividades_reais,
        cfg=cfg,
        atividades_catalogo=atividades_catalogo,
    )
    talhoes_ordenados = sorted(df_faz["chave"].dropna().unique().tolist())
    escopo_talhoes = []
    if isinstance(escopo_meta, dict):
        escopo_talhoes = list(escopo_meta.get("talhoes") or [])

    if escopo_talhoes:
        contexto_sessao.definir_escopo_talhoes(escopo_talhoes, talhoes_ordenados)
    else:
        contexto_sessao.definir_escopo_talhoes(talhoes_ordenados, talhoes_ordenados)
    contexto_sessao.atualizar_atividades(0, len(atividades_reais))
    _emitir_monitor_atual()

    novos_fixos = aplicar_depara_padrao_exame(cfg, atividades_reais)
    if novos_fixos > 0:
        ok(f"de_para PADRAO aplicado: {novos_fixos} mapeamento(s) fixos EXAME->CT_313.")
    if not cfg.get("orcamento_estrito", True):
        novos_de_para = auto_mapear_de_para(cfg, atividades_reais)
        if novos_de_para > 0:
            ok(f"de_para complementar: {novos_de_para} mapeamento(s) adicionais.")

    if not _batch:
        sub()
        logger.debug(
            "Orcamento estrito (sem mediana silenciosa; lacunas pedem input): "
            + str(cfg.get("orcamento_estrito", True))
        )
        if confirmar("  Alternar orcamento_estrito para esta execucao?", default=False):
            cfg["orcamento_estrito"] = not cfg.get("orcamento_estrito", True)
            salvar_config(cfg)
            ok(f"orcamento_estrito = {cfg['orcamento_estrito']}")

    sub()
    logger.info("ATIVIDADES ENCONTRADAS NESTA FAZENDA:")
    for i, a in enumerate(atividades_reais, 1):
        logger.info(f"  {i:2}. {a}")
    logger.info(f"Talhoes: {len(talhoes_ordenados)}")
    if escopo_talhoes:
        n_show = min(8, len(escopo_talhoes))
        base = ", ".join(str(x)[:24] for x in escopo_talhoes[:n_show])
        if len(escopo_talhoes) > n_show:
            base += f", ... (+{len(escopo_talhoes) - n_show})"
            logger.debug(f"Escopo talhoes selecionados: {base}")
    sub()

    seq_cfg = cfg.get("sequencia") or {}

    modo_comparativo, substituicoes_comparativo = _configurar_modo_comparativo(
        atividades_reais, _batch,
    )
    _merge_sequencia_defaults(seq_cfg)
    cfg["sequencia"] = seq_cfg

    modo_seq, usar_cascata, usar_bloqueio_global, atividades_bloqueadas, \
    usar_reforco_automatico, usar_pool_pos_bloqueio = _configurar_sequencia_bloqueio(
        cfg, seq_cfg, atividades_reais, ctx, _batch,
    )

    _proj_result = _configurar_projeto_dados(cfg, ctx, _batch)
    if _proj_result is None:
        return {"status": "cancelled"}
    prazo_meses, mes_ref, ano_ref, dia_ref, data_inicio_txt, \
    data_fim_txt, jornada, executores, comparativo_cfg, turmas = _proj_result

    return {
        "status": "ok",
        "_batch": _batch,
        "df_faz": df_faz,
        "atividades_reais": atividades_reais,
        "catalogo_global": catalogo_global,
        "talhoes_ordenados": talhoes_ordenados,
        "escopo_talhoes": escopo_talhoes,
        "modo_comparativo": modo_comparativo,
        "substituicoes_comparativo": substituicoes_comparativo,
        "comparativo_cfg": comparativo_cfg,
        "seq_cfg": seq_cfg,
        "modo_seq": modo_seq,
        "usar_cascata": usar_cascata,
        "usar_bloqueio_global": usar_bloqueio_global,
        "atividades_bloqueadas": atividades_bloqueadas,
        "usar_reforco_automatico": usar_reforco_automatico,
        "usar_pool_pos_bloqueio": usar_pool_pos_bloqueio,
        "prazo_meses": prazo_meses,
        "mes_ref": mes_ref,
        "ano_ref": ano_ref,
        "dia_ref": dia_ref,
        "data_inicio_txt": data_inicio_txt,
        "data_fim_txt": data_fim_txt,
        "jornada": jornada,
        "executores": executores,
        "turmas": turmas,
    }


def _validar_input(df_faz: pd.DataFrame):
    """Validate input DataFrame has required columns."""
    required = ["fazenda", "chave", "area_ha", "atividade"]
    missing = [c for c in required if c not in df_faz.columns]
    if missing:
        return f"Colunas ausentes: {missing}", df_faz
    return None, df_faz
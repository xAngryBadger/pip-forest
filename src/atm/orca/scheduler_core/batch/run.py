"""Batch execution — continuous lot and farm-by-farm processing."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from ...logging_config import get_logger

logger = get_logger(__name__)

from ...scheduler import dias_uteis_no_periodo
from ...config import modo_somente_hh
from ...excel_export import (
    _checkpoint_editar_template,
    _exportar_excel_consolidado_lote,
    _imprimir_recomendacao_ep,
    _recomendar_equipes_padrao,
)
from ...ui import (
    BL, C, DM, G, R, RS, Y,
    confirmar, console, erro, esperar, linha, ok, sub, subcabecalho, Table,
)
from ...context import dashboard_header
from ...turmas import menu_vincular_atividades_turma
from ...text_utils import _norm_atv

from . import setup as batch_setup
from .. import _HH_EPSILON


def _executar_lote_continuo(cfg, df_scope, fazendas, ctx_base, prazo_absoluto, dias_meta, cap_ep_dia, jornada, todas_atvs):
    resultados = []
    dias_acumulados = 0
    for i_f, fz in enumerate(fazendas, 1):
        linha()
        logger.info(f"[{i_f}/{len(fazendas)}] FAZENDA: {fz}")
        if prazo_absoluto:
            saldo_pre = dias_meta - dias_acumulados
            pct_consumido = (
                (dias_acumulados / dias_meta * 100) if dias_meta > 0 else 0.0
            )
            logger.debug(f"Meta: {dias_meta} dias | Consumido: {dias_acumulados} dias ({pct_consumido:.0f}%) | Saldo: {saldo_pre} dias")
            if pct_consumido >= 100:
                logger.warning("!! META GLOBAL JA EXCEDIDA antes desta fazenda !!")
            elif pct_consumido >= 80:
                logger.warning(f"Atencao: {pct_consumido:.0f}% da meta ja consumida.")
        linha()

        if i_f > 1:
            turmas = _checkpoint_editar_template(ctx_base["turmas"], todas_atvs)
            ctx_base["turmas"] = turmas
            ctx_base["executores"] = sum(t["operarios"] for t in turmas)

        try:
            from ..orchestrator import calcular_cronograma_inteligente
            r = calcular_cronograma_inteligente(
                cfg,
                df_scope[df_scope["fazenda"] == fz].copy(),
                fz,
                esperar_enter=False,
                ctx=dict(ctx_base),
            )
        except Exception as _err_faz:
            logger.exception("Falha ao processar fazenda %s: %s", fz, _err_faz)
            erro(f"Falha ao processar fazenda {fz}: {_err_faz}")
            r = None
        if r:
            dias_faz = int(r.get("dias_simulado", 0))
            dia_inicio_acum = dias_acumulados + 1
            dias_acumulados += dias_faz
            r["dia_inicio_acumulado"] = dia_inicio_acum
            r["dia_fim_acumulado"] = dias_acumulados
            r["saldo_meta_apos"] = max(0, dias_meta - dias_acumulados)
            r["pct_meta_consumida"] = round(
                (dias_acumulados / dias_meta * 100) if dias_meta > 0 else 0.0, 1
            )
            if dias_acumulados > dias_meta:
                r["status_meta_continuo"] = "EXCEDIDO"
            elif dias_acumulados >= dias_meta * 0.8:
                r["status_meta_continuo"] = "RISCO"
            else:
                r["status_meta_continuo"] = "OK"

            hh_faz = float(r.get("total_hh", 0))
            rec = _recomendar_equipes_padrao(
                hh_faz, dias_meta, cap_ep_dia, jornada, prazo_absoluto
            )
            r["rec_ep"] = rec
            if rec and prazo_absoluto:
                _imprimir_recomendacao_ep(rec, fz, prazo_absoluto)

            if prazo_absoluto:
                st_lbl = r["status_meta_continuo"]
                sub()
                logger.info(f"LOTE CONTINUO — apos '{fz}':")
                logger.info(f"  Dia {dia_inicio_acum} a {dias_acumulados} | "
                    f"Saldo: {r['saldo_meta_apos']} dias | "
                    f"Consumo: {r['pct_meta_consumida']:.0f}% | "
                    f"Status: {st_lbl}")
            resultados.append(r)

    return resultados, dias_acumulados


def _exibir_consolidado_lote(resultados, dias_acumulados, dias_meta, turmas, jornada, cap_ep_dia, prazo_meses, prazo_absoluto, modo_seq, data_inicio_txt, data_fim_txt, preencher_orfas_template, empresa_filtro, nome_arquivo_micro, cfg):
    if not resultados:
        return
    linha()
    logger.info("CONSOLIDADO FINAL (TODAS AS FAZENDAS)")
    tit_cons = (
        f"Consolidado — {empresa_filtro}"
        if empresa_filtro
        else "Consolidado — todas as empresas (sem filtro EQUIPE)"
    )
    t_all = Table(title=tit_cons)
    t_all.add_column("Metrica", style="cyan")
    t_all.add_column("Valor", justify="right")
    t_all.add_row("Fazendas processadas", str(len(resultados)))
    t_all.add_row(
        "HH total (soma)",
        f"{sum(float(x.get('total_hh', 0)) for x in resultados):,.1f}",
    )
    dias_max_isolado = max(int(x.get("dias_simulado", 0)) for x in resultados)
    t_all.add_row("Dias simulados (maior fazenda isolada)", str(dias_max_isolado))
    t_all.add_row("Dias acumulados lote continuo", str(dias_acumulados))
    t_all.add_row("Meta (dias uteis)", str(dias_meta))
    if dias_meta > 0:
        saldo_final = max(0, dias_meta - dias_acumulados)
        st_final = "DENTRO" if dias_acumulados <= dias_meta else "EXCEDIDO"
        cor_final = "[green]" if st_final == "DENTRO" else "[red]"
        t_all.add_row(
            "Saldo apos todas as fazendas", f"{cor_final}{saldo_final} dias[/]"
        )
        t_all.add_row("Status meta global", f"{cor_final}{st_final}[/]")
    d_mec_vals = [
        int(x.get("dias_mecanizado") or 0)
        for x in resultados
        if x.get("dias_mecanizado")
    ]
    if d_mec_vals:
        t_all.add_row("Dias cenario mecanizado (max)", str(max(d_mec_vals)))
        t_all.add_row(
            "Ganho mecanizado total (dias)",
            f"{sum(int(x.get('ganho_mecanizado_dias', 0)) for x in resultados):+d}",
        )
    console.print(t_all)

    if prazo_absoluto:
        sub()
        logger.info("ANALISE EQUIPE PADRAO — CONSOLIDADO")
        ep_cap = sum(t["operarios"] for t in turmas)
        logger.info(f"Equipe padrao: {ep_cap} executores @ {jornada}h/dia = {cap_ep_dia:.1f} HH/dia")
        logger.info(f"Meta: {prazo_meses} meses = {dias_meta} dias uteis (ABSOLUTO)")

        t_ep = Table(title=f"Cascata de execucao — {tit_cons}")
        t_ep.add_column("Fazenda", style="cyan")
        t_ep.add_column("HH", justify="right")
        if not modo_somente_hh(cfg):
            t_ep.add_column("Custo R$", justify="right")
        t_ep.add_column("Dias", justify="right")
        t_ep.add_column("Inicio", justify="right")
        t_ep.add_column("Fim", justify="right")
        t_ep.add_column("Meta consumida", justify="right")
        t_ep.add_column("Saldo", justify="right")
        t_ep.add_column("Status", justify="center")
        for r in resultados:
            pct = r.get("pct_meta_consumida", 0)
            st = r.get("status_meta_continuo", "?")
            if st == "OK":
                cor_st = "[green]"
            elif st == "RISCO":
                cor_st = "[yellow]"
            else:
                cor_st = "[red]"
            t_ep.add_row(
                str(r["fazenda"])[:28],
                f"{float(r.get('total_hh', 0)):,.1f}",
                *([f"R$ {float(r.get('total_custo', 0)):,.2f}"] if not modo_somente_hh(cfg) else []),
                str(r.get("dias_simulado", 0)),
                f"Dia {r.get('dia_inicio_acumulado', '?')}",
                f"Dia {r.get('dia_fim_acumulado', '?')}",
                f"{pct:.0f}%",
                f"{r.get('saldo_meta_apos', '?')} dias",
                f"{cor_st}{st}[/]",
            )
        hh_total_all = sum(float(x.get("total_hh", 0)) for x in resultados)
        st_global = "OK" if dias_acumulados <= dias_meta else "EXCEDIDO"
        cor_g = "[green]" if st_global == "OK" else "[red]"
        t_ep.add_row(
            "TOTAL",
            f"{hh_total_all:,.1f}",
            *([f"R$ {sum(float(x.get('total_custo', 0)) for x in resultados):,.2f}"] if not modo_somente_hh(cfg) else []),
            str(dias_acumulados),
            "Dia 1",
            f"Dia {dias_acumulados}",
            f"{(dias_acumulados / dias_meta * 100) if dias_meta > 0 else 0:.0f}%",
            f"{max(0, dias_meta - dias_acumulados)} dias",
            f"{cor_g}{st_global}[/]",
        )
        console.print(t_ep)

    _exportar_excel_consolidado_lote(
        resultados,
        empresa_filtro=empresa_filtro,
        nome_arquivo_micro=nome_arquivo_micro,
        extras={
            "Prazo_meses": prazo_meses,
            "Meta_absoluta": prazo_absoluto,
            "Modo_sequencia": modo_seq,
            "Jornada_h": jornada,
            "Executores_equipe_padrao": sum(t["operarios"] for t in turmas),
            "Preencher_orfas_auto": preencher_orfas_template,
            "Dias_meta": dias_meta,
            "Dias_acumulados_lote": dias_acumulados,
            "Data_inicio": data_inicio_txt,
            "Data_termino": data_fim_txt,
        },
    )

    linha()
    esperar("ENTER para voltar ao menu")


def _executar_lote_fazendas(
    cfg: Dict[str, Any],
    df_scope: pd.DataFrame,
    fazendas: List[str],
    empresa_filtro: Optional[str] = None,
    nome_arquivo_micro: str = "",
) -> None:
    """Orchestrate all-farms batch: one-time setup, per-farm checkpoint, consolidated report."""
    dashboard_header()
    subcabecalho("CONFIGURACAO GLOBAL — TODAS AS FAZENDAS")

    todas_atvs = sorted(
        {_norm_atv(x) for x in df_scope["atividade"].dropna().unique() if _norm_atv(x)},
        key=str,
    )

    glb = batch_setup._configurar_lote_global(cfg, todas_atvs)
    turmas, executores = batch_setup._configurar_equipe_template_lote(todas_atvs, glb["jornada"])
    if turmas is None:
        return

    preencher_orfas_template = confirmar(
        "  Por fazenda: distribuir automaticamente demandas sem turma para a turma com mais operarios?",
        default=False,
    )

    cap_ep_dia = float(executores) * float(glb["jornada"])
    dias_meta = dias_uteis_no_periodo(glb["mes_ref"], glb["ano_ref"], glb["prazo_meses"])

    ctx_base = {
        "modo_seq": glb["modo_seq"],
        "usar_bloqueio_global": glb["usar_bloqueio_global"],
        "usar_reforco_automatico": glb["usar_reforco_automatico"],
        "usar_pool_pos_bloqueio": glb["usar_pool_pos_bloqueio"],
        "prazo_meses": glb["prazo_meses"],
        "mes_ref": glb["mes_ref"],
        "ano_ref": glb["ano_ref"],
        "data_inicio_txt": glb["data_inicio_txt"],
        "data_fim_txt": glb["data_fim_txt"],
        "jornada": glb["jornada"],
        "executores": executores,
        "turmas": turmas,
        "penalidade": 1.0,
        "preencher_orfas_template": preencher_orfas_template,
    }

    resultados, dias_acumulados = _executar_lote_continuo(
        cfg, df_scope, fazendas, ctx_base, glb["prazo_absoluto"], dias_meta,
        cap_ep_dia, glb["jornada"], todas_atvs,
    )

    if resultados:
        _exibir_consolidado_lote(
            resultados, dias_acumulados, dias_meta, turmas, glb["jornada"],
            cap_ep_dia, glb["prazo_meses"], glb["prazo_absoluto"], glb["modo_seq"],
            glb["data_inicio_txt"], glb["data_fim_txt"],
            preencher_orfas_template, empresa_filtro, nome_arquivo_micro, cfg,
        )

"""Multi-team processing — executes teams and consolidates results."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import os

import pandas as pd

from ....logging_config import get_logger

logger = get_logger(__name__)

from ....config import OUTPUT_DIR, modo_somente_hh
from ....context import contexto_sessao
from ....monitor import _emitir_monitor_atual, _emitir_monitor_state
from ....scheduler import dias_uteis_no_periodo
from ....text_utils import _slug_ficheiro_seguro
from ....ui import (
    BL, C, DM, G, RS, Y,
    aviso, console, erro, esperar, linha, ok, sub, Table,
)


def _processar_equipes_e_consolidar(cfg, df_scope, equipes_config, empresa_filtro, nome_arquivo_micro):
    from ...orchestrator import calcular_cronograma_inteligente
    all_eq_results = []
    for ec in equipes_config:
        linha()
        logger.info(f"PROCESSANDO EQUIPE: {ec['nome']} ({len(ec['fazendas'])} fazendas)")
        linha()

        dias_meta_eq = dias_uteis_no_periodo(ec["mes_ref"], ec["ano_ref"], ec["prazo_meses"])
        cap_eq_dia = float(ec["executores"]) * float(ec["jornada"])
        eq_resultados = []
        dias_acum_eq = 0

        ctx_eq = {
            "modo_seq": ec["modo_seq"],
            "usar_bloqueio_global": False,
            "usar_reforco_automatico": True,
            "usar_pool_pos_bloqueio": False,
            "prazo_meses": ec["prazo_meses"],
            "mes_ref": ec["mes_ref"],
            "ano_ref": ec["ano_ref"],
            "data_inicio_txt": ec.get("data_inicio_txt"),
            "data_fim_txt": ec.get("data_fim_txt"),
            "jornada": ec["jornada"],
            "executores": ec["executores"],
            "turmas": ec["turmas"],
            "penalidade": 1.0,
            "preencher_orfas_template": True,
        }
        contexto_sessao.atualizar_modo("multi_equipes")
        contexto_sessao.atualizar_equipe(ec["nome"])
        contexto_sessao.definir_datas(ec.get("data_inicio_txt"), ec.get("data_fim_txt"))
        _emitir_monitor_atual()
        _emitir_monitor_state({
            "operacao": {
                "modo": "multi_equipes",
                "equipe_atual": str(ec["nome"]),
                "status_geral": "processando_equipe",
                "mensagem_curta": f"Equipe {ec['nome']} ({len(ec['fazendas'])} fazendas)",
            },
            "lote": {
                "dias_meta": int(dias_meta_eq),
                "dias_consumidos": int(dias_acum_eq),
                "saldo_dias": int(max(0, int(dias_meta_eq) - int(dias_acum_eq))),
                "fazenda_indice": 0,
                "n_fazendas": int(len(ec["fazendas"])),
                "status_meta_continuo": "OK",
                "prazo_absoluto": True,
            },
        })

        for fz in ec["fazendas"]:
            r = calcular_cronograma_inteligente(
                cfg, df_scope[df_scope["fazenda"] == fz].copy(), fz,
                esperar_enter=False, ctx=dict(ctx_eq),
            )
            if r:
                dias_faz = int(r.get("dias_simulado", 0))
                r["dia_inicio_acumulado"] = dias_acum_eq + 1
                dias_acum_eq += dias_faz
                r["dia_fim_acumulado"] = dias_acum_eq
                r["saldo_meta_apos"] = max(0, dias_meta_eq - dias_acum_eq)
                r["pct_meta_consumida"] = round(
                    (dias_acum_eq / dias_meta_eq * 100) if dias_meta_eq > 0 else 0.0, 1
                )
                r["status_meta_continuo"] = (
                    "EXCEDIDO" if dias_acum_eq > dias_meta_eq
                    else ("RISCO" if dias_acum_eq >= dias_meta_eq * 0.8 else "OK")
                )
                eq_resultados.append(r)

        all_eq_results.append({
            "equipe": ec["nome"],
            "executores": ec["executores"],
            "jornada": ec["jornada"],
            "prazo_meses": ec["prazo_meses"],
            "data_inicio_txt": ec.get("data_inicio_txt"),
            "data_fim_txt": ec.get("data_fim_txt"),
            "dias_meta": dias_meta_eq,
            "dias_acumulados": dias_acum_eq,
            "hh_total": sum(float(x.get("total_hh", 0)) for x in eq_resultados),
            "total_custo": sum(float(x.get("total_custo", 0)) for x in eq_resultados),
            "n_fazendas": len(ec["fazendas"]),
            "status": "DENTRO" if dias_acum_eq <= dias_meta_eq else "EXCEDIDO",
            "resultados_fazendas": eq_resultados,
        })

    linha()
    logger.info("CONSOLIDADO MULTI-EQUIPES")
    t_meq = Table(title="Comparativo entre equipes")
    t_meq.add_column("Equipe", style="cyan")
    t_meq.add_column("Exec.", justify="right")
    t_meq.add_column("Fazendas", justify="right")
    t_meq.add_column("HH", justify="right")
    if not modo_somente_hh(cfg):
        t_meq.add_column("Custo R$", justify="right")
    t_meq.add_column("Dias acum.", justify="right")
    t_meq.add_column("Meta (dias)", justify="right")
    t_meq.add_column("Saldo", justify="right")
    t_meq.add_column("Status", justify="center")
    for eq in all_eq_results:
        saldo = max(0, eq["dias_meta"] - eq["dias_acumulados"])
        st = eq["status"]
        cor = "[green]" if st == "DENTRO" else "[red]"
        t_meq.add_row(
            eq["equipe"], str(eq["executores"]), str(eq["n_fazendas"]),
            f"{eq['hh_total']:,.1f}",
            *([f"R$ {eq.get('total_custo', 0):,.2f}"] if not modo_somente_hh(cfg) else []),
            str(eq["dias_acumulados"]), str(eq["dias_meta"]),
            f"{saldo} dias", f"{cor}{st}[/]",
        )
    console.print(t_meq)

    try:
        pasta = OUTPUT_DIR
        os.makedirs(pasta, exist_ok=True)
        emp_slug = _slug_ficheiro_seguro(empresa_filtro) if empresa_filtro else "Todas"
        nome_xlsx = f"MultiEquipes_{emp_slug}.xlsx"
        caminho = os.path.join(pasta, nome_xlsx)
        rows_eq = []
        for eq in all_eq_results:
            for r in eq["resultados_fazendas"]:
                rows_eq.append({
                    "Equipe": eq["equipe"],
                    "Data_inicio": eq.get("data_inicio_txt"),
                    "Data_termino": eq.get("data_fim_txt"),
                    "Fazenda": r.get("fazenda"),
                    "Dias": r.get("dias_simulado"),
                    "Dia_inicio_acum": r.get("dia_inicio_acumulado"),
                    "Dia_fim_acum": r.get("dia_fim_acumulado"),
                    "Meta_consumida_%": r.get("pct_meta_consumida"),
                    "Saldo": r.get("saldo_meta_apos"),
                    "Status": r.get("status_meta_continuo"),
                    "HH": r.get("total_hh"),
                    "Custo_MO": r.get("total_custo") if not modo_somente_hh(cfg) else None,
                })
        rows_sumario = [
            {
                "Equipe": eq["equipe"],
                "Data_inicio": eq.get("data_inicio_txt"),
                "Data_termino": eq.get("data_fim_txt"),
                "Executores": eq["executores"],
                "Jornada": eq["jornada"],
                "Fazendas": eq["n_fazendas"],
                "HH_total": eq["hh_total"],
                "Custo_total": eq.get("total_custo", 0) if not modo_somente_hh(cfg) else None,
                "Dias_acumulados": eq["dias_acumulados"],
                "Meta_dias": eq["dias_meta"],
                "Status": eq["status"],
            }
            for eq in all_eq_results
        ]
        with pd.ExcelWriter(caminho, engine="openpyxl") as w:
            pd.DataFrame(rows_sumario).to_excel(w, sheet_name="SUMARIO_EQUIPES", index=False)
            pd.DataFrame(rows_eq).to_excel(w, sheet_name="DETALHE_POR_FAZENDA", index=False)
        ok(f"Multi-equipes exportado: {nome_xlsx}")
    except Exception as ex:
        logger.exception("Erro ao exportar multi-equipes")
        aviso(f"Erro ao exportar multi-equipes: {ex}")

    linha()
    esperar("ENTER para voltar ao menu")
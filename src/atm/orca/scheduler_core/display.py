"""Display functions — tables, comparisons, Excel export."""

import math
import os
from collections import defaultdict

import pandas as pd

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..config import _proximo_caminho_livre
from . import OUTPUT_DIR
from ..config import modo_somente_hh
from ..cronograma import (
    construir_cronograma_humano_sem_mecanizadas,
    construir_cronograma_mecanizado,
)
from ..datas import _formatar_data_dia
from ..excel_export import (
    _aplicar_cores_ocupacao_excel,
    _checkpoint_editar_template,
    _df_crono_operacional,
    _exportar_excel_consolidado_lote,
    _gerar_aba_cascata_explicada,
    _gerar_aba_ocupacao_turmas,
    _imprimir_recomendacao_ep,
    _listar_perfis_equipe,
    _recomendar_equipes_padrao,
    _salvar_perfil_equipe,
)
from ..tarifas import resolver_chave_tarifa, resolver_custo_hora
from ..scheduler import dias_uteis_no_periodo
from ..text_utils import _slug_ficheiro_seguro
from ..ui import (
    BL, C, DM, G, R, RS, Y,
    aviso, confirmar, console, erro, esperar, linha, ok, pedir_float, pedir_int,
    pedir_jornada, prompt, selecionar, selecionar_paginado, sub, subcabecalho, Table,
)
from ..turmas import (
    _cadastrar_recursos_mecanizados_sn,
    _catalogo_atividades_completo,
    menu_vincular_atividades_turma,
    resolver_conflitos_e_reatribuir,
    sequencia_manutencao_seco_placeholder,
    sequencia_manutencao_umido_placeholder,
    turmas_que_executam,
)

from . import _HH_EPSILON

from .comparativo import _ComparativoUIConfig, _ComparativoExecutionConfig, _ComparativoResult


def _mostrar_tabela_semanal(cronograma_base, fazenda, executores):
    table = Table(title=f"Cronograma - {fazenda} ({executores} Exec.)")
    table.add_column("Semana", justify="center", style="cyan")
    table.add_column("Dias", justify="center")
    table.add_column("Talhoes / Atividades", style="green")

    semanas = defaultdict(lambda: {"dias": set(), "acoes": set()})
    for c in cronograma_base:
        sem = math.ceil(c["Dia"] / 5)
        semanas[sem]["dias"].add(c["Dia"])
        semanas[sem]["acoes"].add(f"[{c['Talhao']}] {c['Atividade'][:18]}")

    for sem in sorted(semanas.keys())[:8]:
        d = semanas[sem]
        dias_str = f"Dia {min(d['dias'])} a {max(d['dias'])}"
        acoes = ", ".join(list(d["acoes"])[:3])
        if len(d["acoes"]) > 3:
            acoes += " (+)"
        table.add_row(f"Sem {sem}", dias_str, acoes)

    console.print(table)
    if len(semanas) > 8:
        logger.debug(f"... e mais {len(semanas) - 8} semanas no Excel.")


def _mostrar_tabela_ocupacao(turmas, dias_simulado_hum, jornada, hh_por_turma, cronograma, executores, usar_pool_pos_bloqueio, usar_bloqueio_global, n_fb, pct_fallback, n_demandas):
    sub()
    print(G + BL + "  OCUPACAO POR TURMA" + RS)
    t_occ = Table()
    t_occ.add_column("Turma", style="cyan")
    t_occ.add_column("HH", justify="right")
    t_occ.add_column("Cap. max", justify="right")
    t_occ.add_column("Uso %", justify="right")
    crit_nm, crit_pct = "", 0.0
    for turma in turmas:
        nm = turma["nome"]
        cap = float(dias_simulado_hum) * float(turma["operarios"]) * float(jornada)
        us = hh_por_turma.get(nm, 0.0)
        pct = (100.0 * us / cap) if cap > _HH_EPSILON else 0.0
        if pct > crit_pct:
            crit_pct, crit_nm = pct, nm
        t_occ.add_row(nm, f"{us:.1f}", f"{cap:.1f}", f"{pct:.0f}%")
    if hh_por_turma.get("Pelotao_Unificado", 0) > _HH_EPSILON:
        d_pool = len(set(c["Dia"] for c in cronograma if c.get("Turma") == "Pelotao_Unificado"))
        pu = hh_por_turma["Pelotao_Unificado"]
        cap_p = float(d_pool) * float(executores) * float(jornada)
        pct_p = (100.0 * pu / cap_p) if cap_p > _HH_EPSILON else 0.0
        t_occ.add_row("Pelotao_Unificado", f"{pu:.1f}", f"{cap_p:.1f}", f"{pct_p:.0f}%")
    console.print(t_occ)
    logger.debug("Uso %% = HH no cronograma com o nome da turma / (dias simulados x operarios x jornada).")
    logger.debug("Reforco nao aumenta n_ops; bloqueio global impede reforco em plantio/irrigacao ate liberar tudo.")
    if usar_pool_pos_bloqueio and usar_bloqueio_global:
        logger.debug("Pelotao_Unificado: plantio/irrigacao apos liberacao usam todos os executores num so pelotao.")
    if crit_nm:
        logger.debug(f"Heuristica caminho critico (maior Uso %%): turma '{crit_nm}' (~{crit_pct:.0f}%%).")
    if n_fb > 0:
        logger.debug(f"Cobertura CT no escopo: {100 - pct_fallback:.0f}%% (fallback em {n_fb}/{n_demandas} item(ns)).")


def _exibir_comparativo_resultado(ui_config: _ComparativoUIConfig, exec_config: _ComparativoExecutionConfig, result: _ComparativoResult, resultado_mecanizado: dict):
    """Exibe o resultado do comparativo mecanizado vs manual."""
    d_manual = float(result.dias_simulado)
    d_mec = float(resultado_mecanizado.get("dias_simulado") or 0)
    hh_manual = float(result.total_hh)
    hh_mec = float(resultado_mecanizado.get("total_hh") or 0)
    hm_manual = float(result.total_hm)
    hm_mec = float(resultado_mecanizado.get("total_hm") or 0)

    economia_dias = int(d_manual - d_mec)
    economia_hh = hh_manual - hh_mec
    economia_hm = hm_mec - hm_manual
    cap_hh_dia = float(exec_config.executores) * float(exec_config.jornada)
    dias_eq_hh_manual = (hh_manual / cap_hh_dia) if cap_hh_dia > _HH_EPSILON else 0.0
    dias_eq_hh_mec = (hh_mec / cap_hh_dia) if cap_hh_dia > _HH_EPSILON else 0.0
    delta_dias_eq_hh = dias_eq_hh_manual - dias_eq_hh_mec
    cronograma_mec_ref = resultado_mecanizado.get("cronograma") or []
    turmas_mec_comp = sorted(
        {
            str(x.get("Turma", ""))
            for x in cronograma_mec_ref
            if str(x.get("Turma", "")).startswith("MEC_")
        },
        key=str,
    )

    sub()
    print(G + BL + "══════════════════════════════════════════════════════════════════" + RS)
    print(G + BL + "       COMPARATIVO: MANUAL vs MECANIZADO" + RS)
    print(G + BL + "══════════════════════════════════════════════════════════════════" + RS)
    print()

    print(f"  {C}Métrica{RS}                    {C}Manual{RS}          {C}Mecanizado{RS}      {C}Diferença{RS}")
    print(f"  {DM}{'─' * 70}{RS}")
    print(f"  {'Dias necessários':<25} {d_manual:>10.0f}      {d_mec:>10.0f}      {Y}{economia_dias:>+10.0f}{RS}")
    print(f"  {'HH totais':<25} {hh_manual:>10.1f}      {hh_mec:>10.1f}      {Y}{economia_hh:>+10.1f}{RS}")
    print(f"  {'HM totais':<25} {hm_manual:>10.1f}      {hm_mec:>10.1f}      {Y}{economia_hm:>+10.1f}{RS}")
    print(f"  {'Dias eq. via HH/cap':<25} {dias_eq_hh_manual:>10.2f}      {dias_eq_hh_mec:>10.2f}      {Y}{delta_dias_eq_hh:>+10.2f}{RS}")
    print()
    if turmas_mec_comp:
        print(G + BL + "  TURMAS MECANIZADAS NO CENARIO:" + RS)
        for nm_turma in turmas_mec_comp:
            print(DM + f"    - {nm_turma}" + RS)
        print()
    if ui_config.substituicoes_comparativo:
        print(G + BL + "  SUBSTITUICOES APLICADAS:" + RS)
        from ..comparativo_mec import _formatar_substituicao_comparativo
        for manual, mec in ui_config.substituicoes_comparativo.items():
            print(f"  \u2022 {manual[:50]} \u2192 {C}{_formatar_substituicao_comparativo(mec)}{RS}")
        print()

    print(G + BL + "  DESTAQUES:" + RS)
    if economia_dias > 0:
        print(f"  {G}\u2713{RS} Redução de {G}{economia_dias}{RS} dias com mecanização")
    if economia_hh > 0:
        print(f"  {G}\u2713{RS} Economia de {G}{economia_hh:.1f}{RS} HH (mão de obra humana)")
    if economia_dias <= 0 and economia_hh > 0 and cap_hh_dia > _HH_EPSILON:
        print(
            DM
            + f"  Nota: a reducao de HH equivale a ~{delta_dias_eq_hh:.2f} dia(s), "
            + "mas o cronograma fecha por dias inteiros e caminho critico; por isso pode manter o mesmo total de dias."
            + RS
        )
    print()
    print(G + BL + "══════════════════════════════════════════════════════════════════" + RS)
    sub()


def _exportar_dossier_excel(
    cronograma_base, escopo_meta, fazenda, executores, jornada,
    prazo_meses, dias_meta, dias_simulado, meses_simulado,
    total_hh, total_custo, pct_fallback, n_fb,
    atividades_escopo, ag_hum_set, escopo_set, ag_mec_set, faltantes_set,
    recursos_mec, cronograma, turmas, dias_simulado_hum,
    cronograma_mec, cronograma_com_mec, cronograma_mec_base,
    df_audit, cenarios_rows, mes_ref, ano_ref, dia_ref, cfg,
    output_dir=None,
):
    if not cronograma_base:
        return []
    result_files = []

    def _slug_nome(v):
        return str(v).replace("/", "_").replace(" ", "_")

    try:
        scope_tag = "__FAZENDA_TODOS"
        if isinstance(escopo_meta, dict):
            modo_th = str(escopo_meta.get("modo_talhao") or "")
            ths = [
                str(x) for x in (escopo_meta.get("talhoes") or []) if str(x).strip()
            ]
            if modo_th in ("unico", "parcial") and len(ths) == 1:
                scope_tag = f"__TH_{_slug_nome(ths[0])}"
            elif modo_th == "parcial" and len(ths) > 1:
                scope_tag = f"__TH_MULTI_{len(ths)}"
            elif modo_th in ("todos", "fallback_todos"):
                scope_tag = "__FAZENDA_TODOS"

        nome_base = f"Dossier_{_slug_nome(fazenda)}{scope_tag}"
        nome_op = f"{nome_base}_OPERACIONAL.xlsx"
        pasta_dossier = output_dir or OUTPUT_DIR
        os.makedirs(pasta_dossier, exist_ok=True)
        nome_op, caminho_op = _proximo_caminho_livre(pasta_dossier, nome_op)

        df_crono = pd.DataFrame(cronograma_base)
        if "Dia" in df_crono.columns:
            df_crono["Semana"] = df_crono["Dia"].apply(
                lambda d: int(math.ceil(float(d) / 5.0)) if pd.notna(d) else ""
            )

        rows_op = [
            {"Metrica": "Fazenda", "Valor": fazenda},
            {"Metrica": "Arquivo operacional", "Valor": nome_op},
            {"Metrica": "Executores", "Valor": executores},
            {"Metrica": "Jornada (h/dia)", "Valor": jornada},
            {"Metrica": "Prazo Meta (meses)", "Valor": prazo_meses},
            {"Metrica": "Dias Uteis Meta", "Valor": dias_meta},
            {"Metrica": "Duracao Simulada (dias uteis)", "Valor": dias_simulado},
            {"Metrica": "Duracao Simulada (meses)", "Valor": f"{meses_simulado:.1f}"},
            {"Metrica": "HH Total Simulado", "Valor": f"{total_hh:,.1f}"},
            {
                "Metrica": "Custo MO Total",
                "Valor": f"R$ {total_custo:,.2f}" if not modo_somente_hh(cfg) else "N/A",
            },
            {
                "Metrica": "Fonte dos dados",
                "Valor": "100% CT"
                if pct_fallback < _HH_EPSILON
                else f"{100 - pct_fallback:.0f}% CT ({n_fb} fallbacks)",
            },
            {"Metrica": "", "Valor": ""},
            {"Metrica": "Atividades no escopo", "Valor": len(atividades_escopo)},
            {"Metrica": "Agendadas (humano)", "Valor": len(ag_hum_set & escopo_set)},
            {"Metrica": "Agendadas (mecanizado)", "Valor": len(ag_mec_set & escopo_set)},
            {"Metrica": "Nao agendadas", "Valor": len(faltantes_set)},
        ]
        if isinstance(escopo_meta, dict):
            rows_op.append(
                {
                    "Metrica": "Escopo talhoes",
                    "Valor": ", ".join(
                        str(x) for x in (escopo_meta.get("talhoes") or [])
                    )
                    or "todos",
                }
            )
        if recursos_mec:
            rows_op += [{"Metrica": "", "Valor": ""}]
            for rec in recursos_mec:
                rows_op.append(
                    {
                        "Metrica": f"Mecanizado: {rec['nome']}",
                        "Valor": f"{rec['prod_ha_h']} ha/h",
                    }
                )
                rows_op.append(
                    {
                        "Metrica": f"  Atividades ({rec['nome']})",
                        "Valor": str(len(rec.get("atividades", set()))),
                    }
                )
        resumo_op = pd.DataFrame(rows_op)

        df_cascata = _gerar_aba_cascata_explicada(
            cronograma_base, jornada, dia_ref, mes_ref, ano_ref
        )
        df_ocupacao = _gerar_aba_ocupacao_turmas(
            cronograma, turmas, jornada, dias_simulado_hum, dia_ref, mes_ref, ano_ref
        )
        df_crono_op = _df_crono_operacional(df_crono, dia_ref, mes_ref, ano_ref)

        with pd.ExcelWriter(caminho_op, engine="openpyxl") as writer_op:
            resumo_op.to_excel(writer_op, sheet_name="RESUMO_OPERACIONAL", index=False)
            df_crono_op.to_excel(writer_op, sheet_name="CRONOGRAMA_DETALHADO", index=False)
            if not df_cascata.empty:
                df_cascata.to_excel(writer_op, sheet_name="CASCATA_EXPLICADA", index=False)
            if not df_ocupacao.empty:
                df_ocupacao.to_excel(writer_op, sheet_name="OCUPACAO_TURMAS_DIA", index=False)
            if recursos_mec and cronograma_mec:
                df_mec_crono = _df_crono_operacional(pd.DataFrame(cronograma_mec))
                df_mec_crono.to_excel(writer_op, sheet_name="CRONOGRAMA_MECANIZADO", index=False)
                df_combinado = _df_crono_operacional(pd.DataFrame(cronograma_com_mec))
                df_combinado.to_excel(writer_op, sheet_name="CRONOGRAMA_COMBINADO", index=False)
            if cronograma_mec_base:
                df_mec_base = _df_crono_operacional(pd.DataFrame(cronograma_mec_base))
                df_mec_base.to_excel(writer_op, sheet_name="CRONOGRAMA_MEC_BASE", index=False)
            if not df_audit.empty:
                df_audit.to_excel(writer_op, sheet_name="AUDITORIA_ESCOPO", index=False)
            wb_op = writer_op.book
            _aplicar_cores_ocupacao_excel(wb_op, "OCUPACAO_TURMAS_DIA")
            try:
                from src.atm.orca.orca_excel_format import aplicar_formatacao_operacional

                aplicar_formatacao_operacional(wb_op, dias_simulado, cronograma_base)
            except Exception as _fmt_err:
                aviso(f"Formatacao operacional falhou (formatador externo): {_fmt_err}")

        ok(f"Dossier operacional exportado: {nome_op}")
        result_files.append(nome_op)

        if cenarios_rows:
            nome_xlsx_cmp = f"Dossier_{fazenda.replace('/', '_').replace(' ', '_')}_COMPARATIVO_CENARIOS.xlsx"
            nome_xlsx_cmp, caminho_xlsx_cmp = _proximo_caminho_livre(
                pasta_dossier, nome_xlsx_cmp
            )
            with pd.ExcelWriter(caminho_xlsx_cmp, engine="openpyxl") as writer3:
                pd.DataFrame(cenarios_rows).to_excel(
                    writer3, sheet_name="COMPARATIVO_CENARIOS", index=False
                )
            ok(f"Dossier comparativo de cenarios exportado: {nome_xlsx_cmp}")
            result_files.append(nome_xlsx_cmp)

        if recursos_mec and cronograma_com_mec:
            nome_mec_op = f"{nome_base}_COM_MECANIZADO_OPERACIONAL.xlsx"
            nome_mec_op, caminho_mec_op = _proximo_caminho_livre(
                pasta_dossier, nome_mec_op
            )
            df_mec_full = pd.DataFrame(cronograma_com_mec)
            if "Dia" in df_mec_full.columns:
                df_mec_full["Semana"] = df_mec_full["Dia"].apply(
                    lambda d: int(math.ceil(float(d) / 5.0)) if pd.notna(d) else ""
                )
            d_comb = max(
                [int(x.get("Dia", 0)) for x in cronograma_com_mec], default=0
            )
            rows_mec_op = [
                {"Metrica": "Fazenda", "Valor": fazenda},
                {"Metrica": "Arquivo operacional", "Valor": nome_mec_op},
                {"Metrica": "Cenario", "Valor": "Humano + Mecanizado"},
                {"Metrica": "Dias baseline (humano)", "Valor": dias_simulado},
                {"Metrica": "Dias cenario combinado", "Valor": d_comb},
                {
                    "Metrica": "Ganho de prazo (dias)",
                    "Valor": int(dias_simulado) - int(d_comb),
                },
                {
                    "Metrica": "Custo MO Total",
                    "Valor": f"R$ {total_custo:,.2f}" if not modo_somente_hh(cfg) else "N/A",
                },
            ]
            for rec in recursos_mec:
                rows_mec_op.append(
                    {
                        "Metrica": f"Recurso: {rec['nome']}",
                        "Valor": f"{rec['prod_ha_h']} ha/h",
                    }
                )

            df_cascata_mec = _gerar_aba_cascata_explicada(
                cronograma_com_mec, jornada, dia_ref, mes_ref, ano_ref
            )
            df_mec_op = _df_crono_operacional(
                df_mec_full, dia_ref, mes_ref, ano_ref
            )

            with pd.ExcelWriter(caminho_mec_op, engine="openpyxl") as writer_mo:
                pd.DataFrame(rows_mec_op).to_excel(
                    writer_mo, sheet_name="RESUMO_OPERACIONAL", index=False
                )
                df_mec_op.to_excel(
                    writer_mo, sheet_name="CRONOGRAMA_DETALHADO", index=False
                )
                if not df_cascata_mec.empty:
                    df_cascata_mec.to_excel(
                        writer_mo, sheet_name="CASCATA_EXPLICADA", index=False
                    )
                wb_mo = writer_mo.book
                try:
                    from orca_excel_format import aplicar_formatacao_operacional

                    aplicar_formatacao_operacional(wb_mo, d_comb, cronograma_com_mec)
                except Exception as _fmt_err:
                    aviso(f"Formatacao mecanizado falhou (formatador externo): {_fmt_err}")

            ok(f"Dossier cenario mecanizado (operacional): {nome_mec_op}")
            result_files.append(nome_mec_op)
    except Exception as ex:
        logger.exception("Falha ao salvar dossier mecanizado")
        aviso(f"Nao foi possivel salvar Dossier: {ex}")
    return result_files

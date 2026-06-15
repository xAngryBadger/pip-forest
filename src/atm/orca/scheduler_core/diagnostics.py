"""Diagnostics and audit functions."""

import math
from collections import defaultdict

import pandas as pd

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..text_utils import normalizar_chave
from ..ui import (
    BL, C, DM, G, R, RS, Y,
    console, linha, sub, Table,
)

from . import _HH_EPSILON, DIAS_UTEIS_POR_MES


def _auditar_escopo_cronograma(
    df_faz, cronograma_com_mec, cronograma_base, demandas, atividades_mec_set, recursos_mec,
):
    atividades_escopo = sorted(
        {
            str(a).strip()
            for a in df_faz["atividade"].dropna().tolist()
            if str(a).strip()
        },
        key=str,
    )
    escopo_set = set(atividades_escopo)
    ag_hum_set = set()
    ag_mec_set = set()
    cronograma_ref = cronograma_com_mec if cronograma_com_mec else cronograma_base
    for item in cronograma_ref or []:
        atividade_item = str(item.get("Atividade", "") or "").strip()
        if not atividade_item:
            continue
        hh_item = float(item.get("HH", 0) or 0)
        hm_item = float(item.get("HM", 0) or 0)
        turma_item = str(item.get("Turma", "") or "")
        if turma_item.startswith("MEC_") or (hm_item > 0 and hh_item <= 0):
            ag_mec_set.add(atividade_item)
        else:
            ag_hum_set.add(atividade_item)
    faltantes_set = escopo_set - (ag_hum_set | ag_mec_set)

    hh_por_atividade = defaultdict(float)
    for tarefas in demandas.values():
        for t in tarefas:
            atividade_t = str(t.get("atividade", "") or "").strip()
            if not atividade_t:
                continue
            hh_por_atividade[atividade_t] += float(t.get("hh_total", 0) or 0)

    rows_audit = []
    for a in atividades_escopo:
        if a in ag_hum_set:
            status = "agendada_humana"
        elif a in ag_mec_set:
            status = "agendada_mecanizada"
        else:
            status = "nao_agendada"

        motivo = ""
        if status == "nao_agendada":
            if a in atividades_mec_set and not recursos_mec:
                motivo = "atividade mecanizada sem recurso cadastrado"
            else:
                motivo = "sem alocacao no cronograma"

        rows_audit.append(
            {
                "Atividade": a,
                "HH_Escopo": round(float(hh_por_atividade.get(a, 0) or 0), 2),
                "Status": status,
                "Motivo": motivo,
            }
        )
    df_audit = pd.DataFrame(rows_audit)
    sub()
    logger.info("AUDITORIA DO ESCOPO (ANTES DA EXPORTACAO)")
    logger.debug(f"Atividades no escopo: {len(atividades_escopo)}")
    logger.debug(f"Agendadas no humano: {len(ag_hum_set & escopo_set)}")
    logger.debug(f"Agendadas no mecanizado: {len(ag_mec_set & escopo_set)}")
    logger.debug(f"Nao agendadas: {len(faltantes_set)}")
    rocadas_escopo = [a for a in atividades_escopo if "rocada" in normalizar_chave(a)]
    if rocadas_escopo:
        for rcv in rocadas_escopo:
            if rcv in ag_hum_set:
                st = "agendada_humana"
            elif rcv in ag_mec_set:
                st = "agendada_mecanizada"
            else:
                st = "nao_agendada"
            logger.debug(f"rocada: {rcv[:56]} -> {st}")

    return {
        "atividades_escopo": atividades_escopo,
        "escopo_set": escopo_set,
        "ag_hum_set": ag_hum_set,
        "ag_mec_set": ag_mec_set,
        "faltantes_set": faltantes_set,
        "df_audit": df_audit,
    }


def _diagnostico_prazo(
    prazo_meses, dias_meta, mes_ref, ano_ref,
    dias_simulado, meses_simulado,
    executores, jornada, total_hh,
    recursos_mec, cronograma_com_mec,
):
    linha()
    logger.info("DIAGNOSTICO DE PRAZO")
    sub()
    logger.info(f"Meta informada             : {prazo_meses} meses ({dias_meta} dias uteis a partir de {mes_ref:02d}/{ano_ref})")
    logger.info(f"Duracao simulada           : {dias_simulado} dias ({meses_simulado:.1f} meses)")
    if recursos_mec and cronograma_com_mec:
        d_mc = max([int(x.get("Dia", 0)) for x in cronograma_com_mec], default=0)
        m_mc = d_mc / DIAS_UTEIS_POR_MES if d_mc > 0 else 0.0
        logger.info(f"Duracao cenario mecanizado : {d_mc} dias ({m_mc:.1f} meses)")
        logger.info(f"Ganho operacional estimado : {int(dias_simulado) - int(d_mc):+d} dias")
    sub()

    if meses_simulado <= prazo_meses:
        logger.info("STATUS: DENTRO DO PRAZO")
        logger.info(f"Equipe de {executores} executores conclui antes da meta.")
    else:
        logger.warning("STATUS: PRAZO EXCEDIDO")
        logger.warning(f"Equipe atual levara {meses_simulado:.1f} meses (meta: {prazo_meses}).")
        exec_teoricos = (
            math.ceil(total_hh / (dias_meta * jornada)) if (dias_meta * jornada) > 0 else 1
        )
        logger.info(f"[SUGESTAO] ~{exec_teoricos} executores @ {jornada}h/dia cumpririam a meta.")
        if dias_meta > 0 and total_hh > _HH_EPSILON:
            ex5 = math.ceil(total_hh / (dias_meta * 5.0))
            ex6 = math.ceil(total_hh / (dias_meta * 6.0))
            logger.debug(f"[DICA] Com a mesma jornada na meta, ~{ex5} executores @ 5h/dia ou ~{ex6} @ 6h/dia "
                f"(aprox.: HH total / {dias_meta} dias uteis / jornada).")

    linha()

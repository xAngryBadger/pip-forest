"""Multi-team configuration — interactive setup for N independent teams."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import calendar
import datetime
import os

import pandas as pd

from ....logging_config import get_logger

logger = get_logger(__name__)

from ....config import (
    OUTPUT_DIR,
    _agrupar_fazendas_por_empresa,
    _detectar_cidade_por_fazenda,
    _distribuir_fazendas_por_territorio,
    _merge_sequencia_defaults,
    _sugerir_config_empresa,
    modo_somente_hh,
)
from ....context import contexto_sessao, dashboard_header
from ....datas import _calcular_data_fim_por_meses, _formatar_data_dia
from ....monitor import _emitir_monitor_atual, _emitir_monitor_state
from ....scheduler import _selecionar_sequencia_padrao_sn, dias_uteis_no_periodo
from ....text_utils import _norm_atv, _slug_ficheiro_seguro, parse_intervalos_escolha
from ....turmas import menu_vincular_atividades_turma
from ....ui import (
    BL, C, DM, G, RS, Y,
    aviso, confirmar, console, erro, esperar, linha, ok, pedir_float, pedir_int,
    prompt, selecionar, sub, subcabecalho, Table,
)

from ....excel_export import (
    _carregar_perfil_equipe_menu,
    _listar_perfis_equipe,
)


def _configurar_data_multi_equipes():
    hoje = datetime.datetime.now()
    mes_ref = pedir_int("Mes inicial (1-12)", hoje.month)
    mes_ref = max(1, min(12, int(mes_ref)))
    ano_ref = pedir_int("Ano inicial", hoje.year)
    dia_max = calendar.monthrange(ano_ref, mes_ref)[1]
    dia_ref = pedir_int(f"Dia inicial (1-{dia_max})", min(hoje.day, dia_max))
    dia_ref = max(1, min(dia_max, int(dia_ref)))
    data_inicio_txt = _formatar_data_dia(dia_ref, mes_ref, ano_ref)
    return mes_ref, ano_ref, dia_ref, data_inicio_txt


def _agrupar_e_sugerir_equipes(cfg, fazendas, df_scope, n_equipes):
    usar_modo_empresa = False
    config_empresa = None

    fazendas_por_empresa = _agrupar_fazendas_por_empresa(df_scope)

    if fazendas_por_empresa:
        n_emp = len(fazendas_por_empresa)
        if confirmar(
            f"Distribuir {len(fazendas)} fazenda(s) automaticamente por empresa ({n_emp} empresa(s) detectada(s) no micro)?",
            default=True,
        ):
            dashboard_header()
            subcabecalho("DISTRIBUICAO POR EMPRESA")
            logger.debug("Agrupando fazendas por empresa...")

            config_empresa = _sugerir_config_empresa(fazendas_por_empresa, cfg)

            logger.info("Distribuicao detectada:")
            for sug in config_empresa["sugestoes"]:
                logger.info(
                    f" [{sug['nome_empresa']}]: "
                    f"{sug['n_fazendas']} fazenda(s), "
                    f"{sug['n_equipes']} equipe(s) "
                    f"({sug['total_operarios']} operarios)"
                )
                for f in sug["fazendas"]:
                    cidade = _detectar_cidade_por_fazenda(f)
                    cidade_str = f" ({cidade})" if cidade else ""
                    logger.debug(f" - {f}{cidade_str}")

            fazendas_com_empresa = set()
            for fazs in fazendas_por_empresa.values():
                fazendas_com_empresa.update(fazs)
            nao_id = [f for f in fazendas if f not in fazendas_com_empresa]
            if nao_id:
                logger.warning(f"Fazendas sem empresa no micro ({len(nao_id)}):")
                for f in nao_id[:5]:
                    logger.warning(f" - {f}")
                if len(nao_id) > 5:
                    logger.warning(f" ... e mais {len(nao_id) - 5}")

            logger.info(
                f"Total: {config_empresa['total_equipes']} equipes, "
                f"{config_empresa['total_operarios']} operarios"
            )

            if confirmar("Aceitar esta distribuicao automatica?", default=True):
                usar_modo_empresa = True
                n_equipes = config_empresa["total_equipes"]
                ok(f"Modo empresa ativado: {n_emp} empresa(s), {n_equipes} equipes automaticas.")
            else:
                aviso("Modo automatico cancelado. Prossiga com configuracao manual.")

            sub()
            esperar("ENTER para continuar")

    if not usar_modo_empresa and confirmar(
        "Usar modo automatico de distribuicao por territorio/cidade?",
        default=False,
    ):
        dashboard_header()
        subcabecalho("DISTRIBUICAO POR TERRITORIO")
        logger.debug("Analisando fazendas e distribuindo por cidade...")

        distribuicao, nao_id = _distribuir_fazendas_por_territorio(fazendas)

        logger.info("Distribuicao por cidade:")
        for cidade, fazs in distribuicao.items():
            if fazs:
                logger.info(f" [{cidade}]: {len(fazs)} fazenda(s)")
                for f in fazs:
                    logger.debug(f" - {f}")

        if nao_id:
            logger.warning(f"Fazendas nao identificadas ({len(nao_id)}):")
            for f in nao_id[:5]:
                logger.warning(f" - {f}")
            if len(nao_id) > 5:
                logger.warning(f" ... e mais {len(nao_id) - 5}")

        n_equipes = sum(1 for v in distribuicao.values() if v) or 1
        ok(f"Modo territorio: {n_equipes} grupo(s) por cidade.")
        usar_modo_empresa = True

        config_empresa = {
            "sugestoes": [
                {
                    "empresa": cidade,
                    "nome_empresa": cidade,
                    "n_equipes": 1,
                    "operarios_por_equipe": 10,
                    "coordenadores_por_equipe": 1,
                    "total_por_equipe": 11,
                    "total_operarios": 10,
                    "total_coordenadores": 1,
                    "total_geral": 11,
                    "jornada": 4.3,
                    "fazendas": fazs,
                    "n_fazendas": len(fazs),
                }
                for cidade, fazs in distribuicao.items()
                if fazs
            ],
            "total_equipes": n_equipes,
            "total_operarios": n_equipes * 10,
        }

        sub()
        esperar("ENTER para continuar")

    return usar_modo_empresa, config_empresa, n_equipes


def _configurar_uma_equipe(ie, n_equipes, todas_atvs, fazendas_restantes, mes_ref, ano_ref, dia_ref, data_inicio_txt, modo_seq, usar_modo_empresa, config_empresa):
    sub()
    logger.info(f" EQUIPE {ie}/{n_equipes}")

    if usar_modo_empresa and config_empresa:
        cfg_empresa_eq = None
        equipe_idx_atual = ie - 1
        acum_equipes = 0

        for sug in config_empresa["sugestoes"]:
            n_eq_emp = sug["n_equipes"]
            if equipe_idx_atual < acum_equipes + n_eq_emp:
                nome_eq = f"{sug['nome_empresa']} Eq{equipe_idx_atual - acum_equipes + 1}"
                j_eq = sug.get("jornada", 4.3)
                exec_eq = sug["operarios_por_equipe"]
                turmas_eq = [
                    {
                        "nome": sug["nome_empresa"],
                        "operarios": exec_eq,
                        "atividades": [],
                    }
                ]
                fazs_emp = sug["fazendas"]
                n_por_eq = max(1, len(fazs_emp) // n_eq_emp)
                inicio_emp = equipe_idx_atual - acum_equipes
                faz_eq = fazs_emp[inicio_emp:inicio_emp + n_por_eq]
                if equipe_idx_atual - acum_equipes + 1 == n_eq_emp and len(fazs_emp) > inicio_emp + n_por_eq:
                    faz_eq = fazs_emp[inicio_emp:]

                if not faz_eq:
                    aviso(f"{nome_eq}: nenhuma fazenda atribuivel — pulando equipe.")
                    return None

                ok(f"Configuracao automatica: {nome_eq}")
                logger.info(f"Empresa: {sug['nome_empresa']}")
                logger.info(f"Operarios: {exec_eq}")
                logger.info(f"Fazendas: {len(faz_eq)}")
                for f in faz_eq:
                    if f in fazendas_restantes:
                        fazendas_restantes.remove(f)
                prazo_eq = pedir_float(f"Prazo meta para '{nome_eq}' (meses)", 3.0)
                data_fim_txt = _perguntar_data_fim_equipe(nome_eq, mes_ref, ano_ref, dia_ref, prazo_eq)
                return {
                    "nome": nome_eq,
                    "prazo_meses": prazo_eq,
                    "jornada": j_eq,
                    "executores": exec_eq,
                    "turmas": turmas_eq,
                    "fazendas": faz_eq,
                    "modo_seq": modo_seq,
                    "mes_ref": mes_ref,
                    "ano_ref": ano_ref,
                    "data_inicio_txt": data_inicio_txt,
                    "data_fim_txt": data_fim_txt,
                }
            acum_equipes += n_eq_emp

    # Manual config
    nome_eq = prompt(f"Nome da equipe {ie}", f"Equipe {ie}")
    prazo_eq = pedir_float(f"Prazo meta para '{nome_eq}' (meses)", 3.0)
    j_eq = pedir_float(f"Jornada diaria '{nome_eq}' (horas)", 4.3)
    exec_eq = pedir_int(f"Executores '{nome_eq}'", 10)
    data_fim_txt = _perguntar_data_fim_equipe(nome_eq, mes_ref, ano_ref, dia_ref, prazo_eq)

    perfil_carregado = None
    perfis = _listar_perfis_equipe()
    if perfis and confirmar(f"Carregar perfil de equipe para '{nome_eq}'?", default=False):
        perfil_carregado = _carregar_perfil_equipe_menu()

    if perfil_carregado:
        turmas_eq = [
            {
                "nome": t["nome"],
                "operarios": t["operarios"],
                "atividades": list(t.get("atividades") or []),
            }
            for t in perfil_carregado.get("turmas", [])
        ]
        exec_eq = sum(t["operarios"] for t in turmas_eq)
        ok(f"Perfil carregado: {len(turmas_eq)} turma(s), {exec_eq} executores.")
    else:
        turmas_eq = [{"nome": nome_eq, "operarios": exec_eq, "atividades": []}]
        menu_vincular_atividades_turma(turmas_eq[0], todas_atvs)

    if not fazendas_restantes:
        aviso("Todas as fazendas ja foram atribuidas. Esta equipe ficara vazia.")
        faz_eq = []
    elif ie == n_equipes:
        faz_eq = list(fazendas_restantes)
        ok(f"Restantes ({len(faz_eq)}) atribuidas a '{nome_eq}'.")
        for f in faz_eq:
            if f in fazendas_restantes:
                fazendas_restantes.remove(f)
    else:
        logger.info(f"Fazendas disponiveis ({len(fazendas_restantes)}):")
        for idx_f, f in enumerate(fazendas_restantes, 1):
            logger.info(f" {idx_f:3}. {f}")
        sel_txt = prompt(
            f"Indices das fazendas para '{nome_eq}' (ex: 1,3,5-7) ou ENTER=todas restantes", "",
        )
        if not sel_txt.strip():
            faz_eq = list(fazendas_restantes)
        else:
            idxs = parse_intervalos_escolha(sel_txt, len(fazendas_restantes))
            faz_eq = [fazendas_restantes[i] for i in idxs]
        for f in faz_eq:
            if f in fazendas_restantes:
                fazendas_restantes.remove(f)
        ok(f"{len(faz_eq)} fazenda(s) para '{nome_eq}'.")

    return {
        "nome": nome_eq,
        "prazo_meses": prazo_eq,
        "jornada": j_eq,
        "executores": exec_eq,
        "turmas": turmas_eq,
        "fazendas": faz_eq,
        "modo_seq": modo_seq,
        "mes_ref": mes_ref,
        "ano_ref": ano_ref,
        "data_inicio_txt": data_inicio_txt,
        "data_fim_txt": data_fim_txt,
    }


def _perguntar_data_fim_equipe(nome_equipe, mes_ref, ano_ref, dia_ref, prazo_eq):
    if confirmar(f"Informar dia final manualmente para '{nome_equipe}'?", default=False):
        mes_fim = pedir_int("Mes final (1-12)", mes_ref)
        mes_fim = max(1, min(12, int(mes_fim)))
        ano_fim = pedir_int("Ano final", ano_ref)
        dia_max_fim = calendar.monthrange(ano_fim, mes_fim)[1]
        dia_fim = pedir_int(f"Dia final (1-{dia_max_fim})", min(dia_ref, dia_max_fim))
        dia_fim = max(1, min(dia_max_fim, int(dia_fim)))
        return _formatar_data_dia(dia_fim, mes_fim, ano_fim)
    fim_calc = _calcular_data_fim_por_meses(dia_ref, mes_ref, ano_ref, prazo_eq)
    if fim_calc:
        return _formatar_data_dia(fim_calc[0], fim_calc[1], fim_calc[2])
    return None
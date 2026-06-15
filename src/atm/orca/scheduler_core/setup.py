"""Project setup functions — interactive and batch."""

import calendar
import datetime

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..comparativo_mec import coletar_config_comparativo_multifator
from ..config import salvar_config, _merge_sequencia_defaults
from ..context import contexto_sessao
from ..datas import _calcular_data_fim_por_meses, _formatar_data_dia
from ..scheduler import (
    _selecionar_sequencia_padrao_sn,
    diagnosticar_sequencia_atividades,
)
from ..text_utils import _norm_atv, atividades_por_filtro
from ..turmas import (
    sequencia_manutencao_seco_placeholder,
    sequencia_manutencao_umido_placeholder,
)
from ..ui import (
    BL, C, DM, G, RS, Y,
    aviso, confirmar, console, erro, esperar, linha, ok, pedir_float, pedir_int,
    pedir_jornada, prompt, selecionar, sub, subcabecalho,
)

from . import _JORNADA_DEFAULT_H


def _configurar_projeto_interativo(cfg):
    logger.info("CONFIGURACAO DO PROJETO")

    prazo_meses = pedir_float("Prazo META para conclusao (meses)", 6.0)
    hoje = datetime.datetime.now()
    logger.info("  Referencia do calendario para DIAS UTEIS da meta (meses corridos a partir de): ")
    mes_ref = pedir_int("Mes inicial (1-12)", hoje.month)
    mes_ref = max(1, min(12, int(mes_ref)))
    ano_ref = pedir_int("Ano inicial", hoje.year)
    dia_max = calendar.monthrange(ano_ref, mes_ref)[1]
    dia_ref = pedir_int(f"Dia inicial (1-{dia_max})", min(hoje.day, dia_max))
    dia_ref = max(1, min(dia_max, int(dia_ref)))

    data_inicio_txt = _formatar_data_dia(dia_ref, mes_ref, ano_ref)
    data_fim_txt = None
    if confirmar("Informar dia final manualmente?", default=False):
        mes_fim = pedir_int("Mes final (1-12)", mes_ref)
        mes_fim = max(1, min(12, int(mes_fim)))
        ano_fim = pedir_int("Ano final", ano_ref)
        dia_max_fim = calendar.monthrange(ano_fim, mes_fim)[1]
        dia_fim = pedir_int(
            f"Dia final (1-{dia_max_fim})", min(dia_ref, dia_max_fim)
        )
        dia_fim = max(1, min(dia_max_fim, int(dia_fim)))
        data_fim_txt = _formatar_data_dia(dia_fim, mes_fim, ano_fim)
    else:
        fim_calc = _calcular_data_fim_por_meses(
            dia_ref, mes_ref, ano_ref, prazo_meses
        )
        if fim_calc:
            data_fim_txt = _formatar_data_dia(fim_calc[0], fim_calc[1], fim_calc[2])

    contexto_sessao.definir_datas(data_inicio_txt, data_fim_txt)

    j_def = float(cfg.get("jornada_horas") or _JORNADA_DEFAULT_H)
    if j_def <= 0:
        j_def = _JORNADA_DEFAULT_H
    executores = pedir_int(
        "Operarios totais (quem realmente trabalha)",
        9,
    )
    jornada = pedir_jornada(
        "Jornada efetiva diaria (ex: 6.5 ou 6:30 = 6h30)", round(j_def, 2)
    )
    cfg["jornada_horas"] = jornada
    salvar_config(cfg)

    if executores <= 0:
        erro("Precisa de pelo menos 1 executor.")
        return None
    logger.info(f"Equipe Operacional: {executores} operarios @ {jornada}h/dia")
    if confirmar(
        "Configurar COMPARATIVO MULTI-FATOR agora (para exportar no Excel)?",
        default=False,
    ):
        comparativo_cfg = coletar_config_comparativo_multifator(executores, jornada)
    else:
        comparativo_cfg = None

    sub()
    logger.info("ETAPA 1: CRIAR TURMAS / FUNCOES")
    logger.debug("Defina grupos de trabalho (ex: Rocadores, Adubadores, Geral).")
    logger.debug("Depois voce vinculara quais atividades cada turma executa.")

    turmas = []
    restantes = executores

    while restantes > 0:
        logger.info(f"Operarios disponiveis: {restantes}")
        nome_turma = prompt(
            "Nome da turma (ex: Rocadores)", f"Turma {len(turmas) + 1}"
        )
        def_pad = min(restantes, max(1, restantes // 2 or restantes))
        qtd = pedir_int(f"  Quantos operarios na turma '{nome_turma}'", def_pad)
        if qtd > restantes:
            aviso(f"Maximo disponivel: {restantes}. Ajustando.")
            qtd = restantes
        turmas.append({"nome": nome_turma, "operarios": qtd, "atividades": []})
        restantes -= qtd
        if restantes > 0:
            if not confirmar(
                f"Criar outra turma? ({restantes} restantes)", default=True
            ):
                turmas.append(
                    {"nome": "Geral", "operarios": restantes, "atividades": []}
                )
                restantes = 0

    sub()
    logger.info("TURMAS CRIADAS:")
    for t in turmas:
        logger.info(f"  - {t['nome']}: {t['operarios']} operarios")
    sub()

    return {
        "prazo_meses": prazo_meses,
        "mes_ref": mes_ref,
        "ano_ref": ano_ref,
        "dia_ref": dia_ref,
        "data_inicio_txt": data_inicio_txt,
        "data_fim_txt": data_fim_txt,
        "jornada": jornada,
        "executores": executores,
        "comparativo_cfg": comparativo_cfg,
        "turmas": turmas,
    }


def _configurar_projeto_dados(cfg, ctx, _batch):
    if _batch:
        prazo_meses = ctx["prazo_meses"]
        mes_ref = ctx["mes_ref"]
        ano_ref = ctx["ano_ref"]
        dia_ref = ctx.get("dia_ref", 1)
        data_inicio_txt = ctx.get("data_inicio_txt")
        data_fim_txt = ctx.get("data_fim_txt")
        if data_inicio_txt or data_fim_txt:
            contexto_sessao.definir_datas(data_inicio_txt, data_fim_txt)
        jornada = ctx["jornada"]
        executores = ctx["executores"]
        comparativo_cfg = ctx.get("comparativo_cfg")
        turmas = []
        for t in ctx["turmas"]:
            turmas.append(
                {
                    "nome": t["nome"],
                    "operarios": t["operarios"],
                    "atividades": [
                        _norm_atv(a) for a in (t.get("atividades") or []) if _norm_atv(a)
                    ],
                }
            )
    else:
        proj = _configurar_projeto_interativo(cfg)
        if proj is None:
            return None
        prazo_meses = proj["prazo_meses"]
        mes_ref = proj["mes_ref"]
        ano_ref = proj["ano_ref"]
        dia_ref = proj["dia_ref"]
        data_inicio_txt = proj["data_inicio_txt"]
        data_fim_txt = proj["data_fim_txt"]
        jornada = proj["jornada"]
        executores = proj["executores"]
        comparativo_cfg = proj["comparativo_cfg"]
        turmas = proj["turmas"]
    return prazo_meses, mes_ref, ano_ref, dia_ref, data_inicio_txt, \
        data_fim_txt, jornada, executores, comparativo_cfg, turmas


def _configurar_sequencia_bloqueio(cfg, seq_cfg, atividades_reais, ctx, _batch):
    if _batch:
        modo_seq = ctx["modo_seq"]
    else:
        modo_seq = _selecionar_sequencia_padrao_sn(cfg, seq_cfg, atividades_reais)

    modo_ctx = f"seq:{modo_seq}"
    modo_existente = contexto_sessao.modo_atual
    if modo_existente:
        if modo_ctx not in str(modo_existente):
            contexto_sessao.atualizar_modo(f"{modo_existente} | {modo_ctx}")
    else:
        contexto_sessao.atualizar_modo(modo_ctx)

    if modo_seq == "manutencao_seco":
        sequencia_manutencao_seco_placeholder(cfg)
    elif modo_seq == "manutencao_umido":
        sequencia_manutencao_umido_placeholder(cfg)
    usar_cascata = modo_seq in ("implantacao", "personalizado")
    diagnosticar_sequencia_atividades(atividades_reais, seq_cfg, modo_seq)

    if _batch:
        usar_bloqueio_global = ctx.get("usar_bloqueio_global", False)
        atividades_bloqueadas = set()
        if usar_bloqueio_global:
            filtros_bloqueio = cfg.get("filtros_bloqueio_global", ["plantio", "irrig"])
            atividades_bloqueadas = set(
                atividades_por_filtro(atividades_reais, filtros_bloqueio)
            )
        usar_reforco_automatico = ctx.get("usar_reforco_automatico", True)
        usar_pool_pos_bloqueio = ctx.get("usar_pool_pos_bloqueio", False)
    else:
        filtros_bloqueio = cfg.get("filtros_bloqueio_global", ["plantio", "irrig"])
        candidatas_bloqueio = atividades_por_filtro(atividades_reais, filtros_bloqueio)
        usar_bloqueio_global = False
        atividades_bloqueadas = set()
        if modo_seq == "personalizado":
            logger.debug("Modo PERSONALIZADO: bloqueio global plantio/irrigacao DESLIGADO.")
        elif candidatas_bloqueio:
            usar_bloqueio_global = confirmar(
                "Aplicar BLOQUEIO GLOBAL (plantio/irrigacao so iniciam quando TODO o resto zerar na fazenda)?",
                default=True,
            )
            if usar_bloqueio_global:
                atividades_bloqueadas = set(candidatas_bloqueio)
                logger.warning(f"BLOQUEADAS ATE LIBERACAO GLOBAL ({len(atividades_bloqueadas)}):")
                for a in sorted(atividades_bloqueadas, key=lambda x: str(x))[:20]:
                    logger.warning(f"    - {str(a)[:58]}")
                if len(atividades_bloqueadas) > 20:
                    logger.debug(f"    ... +{len(atividades_bloqueadas) - 20}")
                if confirmar(
                    "Salvar estes filtros de bloqueio no config para proximas execucoes?",
                    default=True,
                ):
                    cfg["filtros_bloqueio_global"] = filtros_bloqueio
                    salvar_config(cfg)
        usar_reforco_automatico = confirmar(
            "Ativar REFORCO AUTOMATICO (turma ociosa ajuda outras atividades nao bloqueadas)?",
            default=True,
        )
        usar_pool_pos_bloqueio = False
        if usar_bloqueio_global:
            usar_pool_pos_bloqueio = confirmar(
                "Usar PELOTAO UNIFICADO (todos os executores) so em plantio/irrigacao apos liberacao global?",
                default=True,
            )
    return modo_seq, usar_cascata, usar_bloqueio_global, atividades_bloqueadas, usar_reforco_automatico, usar_pool_pos_bloqueio

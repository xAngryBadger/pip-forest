"""Batch mode setup — global config and team template."""

import calendar
import datetime

from ...logging_config import get_logger

logger = get_logger(__name__)

from ...config import _merge_sequencia_defaults, salvar_config
from ...context import contexto_sessao
from ...datas import _calcular_data_fim_por_meses, _formatar_data_dia
from ...scheduler import _selecionar_sequencia_padrao_sn
from ...turmas import menu_vincular_atividades_turma
from ...ui import (
    BL, C, DM, G, RS,
    aviso, confirmar, erro, ok, pedir_float, pedir_int, pedir_jornada,
    prompt, sub,
)

from .. import _JORNADA_DEFAULT_H
from ...excel_export import (
    _listar_perfis_equipe,
    _carregar_perfil_equipe_menu,
    _salvar_perfil_equipe,
)


def _configurar_lote_global(cfg, todas_atvs):
    seq_cfg = cfg.get("sequencia") or {}
    _merge_sequencia_defaults(seq_cfg)
    cfg["sequencia"] = seq_cfg
    modo_seq = _selecionar_sequencia_padrao_sn(cfg, seq_cfg, todas_atvs)

    usar_bloqueio_global = False
    if modo_seq != "personalizado":
        usar_bloqueio_global = confirmar(
            "Aplicar BLOQUEIO GLOBAL (plantio/irrigacao so iniciam quando TODO o resto zerar)?",
            default=True,
        )
    usar_reforco_automatico = confirmar("Ativar REFORCO AUTOMATICO?", default=True)
    usar_pool_pos_bloqueio = False
    if usar_bloqueio_global:
        usar_pool_pos_bloqueio = confirmar(
            "Usar PELOTAO UNIFICADO apos liberacao global?", default=True
        )

    prazo_meses = pedir_float("Prazo META para conclusao (meses)", 6.0)
    prazo_absoluto = confirmar(
        f"  {prazo_meses} meses e o periodo ABSOLUTO? Se sim, havera sugestoes se necessario",
        default=True,
    )
    hoje = datetime.datetime.now()
    mes_ref = pedir_int("Mes inicial (1-12)", hoje.month)
    mes_ref = max(1, min(12, int(mes_ref)))
    ano_ref = pedir_int("Ano inicial", hoje.year)
    dia_max = calendar.monthrange(ano_ref, mes_ref)[1]
    dia_ref = pedir_int(f"Dia inicial (1-{dia_max})", min(hoje.day, dia_max))
    dia_ref = max(1, min(dia_max, int(dia_ref)))

    data_inicio_txt = _formatar_data_dia(dia_ref, mes_ref, ano_ref)
    data_fim_txt = None
    if confirmar("Informar dia final manualmente para o lote?", default=False):
        mes_fim = pedir_int("Mes final (1-12)", mes_ref)
        mes_fim = max(1, min(12, int(mes_fim)))
        ano_fim = pedir_int("Ano final", ano_ref)
        dia_max_fim = calendar.monthrange(ano_fim, mes_fim)[1]
        dia_fim = pedir_int(f"Dia final (1-{dia_max_fim})", min(dia_ref, dia_max_fim))
        dia_fim = max(1, min(dia_max_fim, int(dia_fim)))
        data_fim_txt = _formatar_data_dia(dia_fim, mes_fim, ano_fim)
    else:
        fim_calc = _calcular_data_fim_por_meses(dia_ref, mes_ref, ano_ref, prazo_meses)
        if fim_calc:
            data_fim_txt = _formatar_data_dia(fim_calc[0], fim_calc[1], fim_calc[2])

    contexto_sessao.definir_datas(data_inicio_txt, data_fim_txt)
    j_def = float(cfg.get("jornada_horas") or _JORNADA_DEFAULT_H)
    if j_def <= 0:
        j_def = _JORNADA_DEFAULT_H
    jornada = pedir_jornada("Jornada efetiva diaria (ex: 6.5 ou 6:30 = 6h30)", round(j_def, 2))
    cfg["jornada_horas"] = jornada
    salvar_config(cfg)

    return {
        "modo_seq": modo_seq,
        "usar_bloqueio_global": usar_bloqueio_global,
        "usar_reforco_automatico": usar_reforco_automatico,
        "usar_pool_pos_bloqueio": usar_pool_pos_bloqueio,
        "prazo_meses": prazo_meses,
        "prazo_absoluto": prazo_absoluto,
        "mes_ref": mes_ref,
        "ano_ref": ano_ref,
        "dia_ref": dia_ref,
        "data_inicio_txt": data_inicio_txt,
        "data_fim_txt": data_fim_txt,
        "jornada": jornada,
    }


def _configurar_equipe_template_lote(todas_atvs, jornada):
    sub()
    logger.info("CONFIGURAR EQUIPE PADRAO")
    logger.debug("Defina as turmas que serao reutilizadas em todas as fazendas.")
    logger.debug("Voce podera ajustar antes de cada fazenda no checkpoint.")

    perfil_carregado = None
    perfis_existentes = _listar_perfis_equipe()
    if perfis_existentes:
        if confirmar("Carregar perfil de equipe salvo anteriormente?", default=False):
            perfil_carregado = _carregar_perfil_equipe_menu()

    if perfil_carregado:
        turmas = [
            {
                "nome": t["nome"],
                "operarios": t["operarios"],
                "atividades": list(t.get("atividades") or []),
            }
            for t in perfil_carregado.get("turmas", [])
        ]
        executores = perfil_carregado.get(
            "executores", sum(t["operarios"] for t in turmas)
        )
        ok(
            f"Perfil '{perfil_carregado['nome']}' carregado: {executores} executores, {len(turmas)} turma(s)."
        )
        for t in turmas:
            logger.info(f"  - {t['nome']}: {t['operarios']} ops, {len(t.get('atividades', []))} atividades")
        if confirmar("Editar este perfil antes de usar?", default=False):
            for turma in turmas:
                menu_vincular_atividades_turma(turma, todas_atvs)
    else:
        executores = pedir_int(
            "Operarios totais da equipe padrao (quem realmente trabalha)",
            9,
        )
        if executores <= 0:
            erro("Precisa de pelo menos 1 executor.")
            return None, None

        turmas = []
        restantes = executores
        while restantes > 0:
            logger.info(f"Operarios disponiveis: {restantes}")
            nome_turma = prompt("Nome da turma", f"Turma {len(turmas) + 1}")
            def_pad = min(restantes, max(1, restantes // 2 or restantes))
            qtd = pedir_int(f"  Quantos operarios na turma '{nome_turma}'", def_pad)
            if qtd > restantes:
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
        logger.info("VINCULAR ATIVIDADES (usa todas as atividades do escopo)")
        for turma in turmas:
            menu_vincular_atividades_turma(turma, todas_atvs)

    if confirmar("Salvar este perfil de equipe para reusar depois?", default=False):
        nome_p = prompt("Nome do perfil", "padrao")
        cam_p = _salvar_perfil_equipe(turmas, executores, jornada, nome_p)
        ok(f"Perfil salvo: {cam_p}")

    return turmas, executores

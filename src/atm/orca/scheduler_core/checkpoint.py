"""Checkpoint retroactive review."""

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..config import salvar_config
from ..scheduler import menu_ajustes_hh_apenas_sessao
from ..turmas import menu_vincular_atividades_turma, resolver_conflitos_e_reatribuir
from ..ui import (
    BL, C, DM, G, RS,
    confirmar, ok, pedir_int, pedir_jornada, selecionar, sub,
)


def _executar_checkpoint_retroativo(
    _batch, turmas, atividades_reais, catalogo_global,
    executores, jornada, cfg, session_hh,
    reatribuicao, paralelo, primaria, df_faz,
    recalcular_callback,
    ajustar_escopo_fn=None,
):
    if not _batch:
        if confirmar(
            "Ajustar HH/ha por atividade APENAS nesta execucao (nao grava config)?",
            default=False,
        ):
            menu_ajustes_hh_apenas_sessao(atividades_reais, cfg, session_hh)

    while True:
        if _batch:
            break
        
        sub()
        logger.info("CHECKPOINT RETROATIVO")
        op_cp = selecionar(
            "O QUE DESEJA REVISAR?",
            [
                "Editar atividades de uma turma",
                "Reprocessar conflitos/reatribuicao",
                "Ajustar HH/ha desta sessao",
                "Ajustar escopo de atividades desta execucao",
                "Revisar jornada/equipe",
                "Voltar ao seletor de fazenda/escopo",
                "Continuar para simulacao",
            ],
        )

        if not op_cp or op_cp == "Continuar para simulacao":
            break

        if op_cp == "Voltar ao seletor de fazenda/escopo":
            return {"acao": "retroceder_escopo"}

        if op_cp == "Revisar jornada/equipe":
            logger.debug(f"Atual: {executores} operarios @ {jornada}h/dia")
            alterou = False
            if confirmar("Alterar jornada?", default=False):
                jornada = pedir_jornada(
                    "Nova jornada (ex: 6.5 ou 6:30 = 6h30)", round(jornada, 2)
                )
                cfg["jornada_horas"] = jornada
                salvar_config(cfg)
                ok(f"Jornada atualizada: {jornada}h/dia")
                alterou = True
            if confirmar("Alterar operarios?", default=False):
                executores = pedir_int("Operarios totais", executores)
                logger.info(f"Equipe: {executores} operarios @ {jornada}h/dia = {executores * jornada:.1f} HH/dia")
                alterou = True
            if not alterou:
                ok("Jornada/equipe mantidos sem alteracao.")
            continue

        if op_cp == "Editar atividades de uma turma":
            nomes_t = [t["nome"] for t in turmas]
            nm = selecionar("TURMA", nomes_t)
            if nm:
                for t in turmas:
                    if t["nome"] == nm:
                        menu_vincular_atividades_turma(
                            t,
                            atividades_reais,
                            atividades_catalogo=catalogo_global,
                        )
                        ok(f"Turma '{nm}' — edicao concluida.")
                        break
            else:
                ok("Nenhuma turma selecionada.")
            continue

        if op_cp == "Reprocessar conflitos/reatribuicao":
            reatribuicao, paralelo, primaria = resolver_conflitos_e_reatribuir(
                turmas, atividades_reais
            )
            if not paralelo and not reatribuicao:
                ok("Nenhum conflito multi-turma encontrado.")
            continue

        if op_cp == "Ajustar HH/ha desta sessao":
            menu_ajustes_hh_apenas_sessao(atividades_reais, cfg, session_hh)
            continue

        if op_cp == "Ajustar escopo de atividades desta execucao":
            if ajustar_escopo_fn is not None:
                df_faz = ajustar_escopo_fn(df_faz, cfg=cfg, atividades_catalogo=catalogo_global)
            atividades_reais, talhoes_ordenados, catalogo_global = recalcular_callback()
            reatribuicao, paralelo, primaria = resolver_conflitos_e_reatribuir(
                turmas, atividades_reais
            )
            continue

    return {
        "jornada": jornada,
        "executores": executores,
        "reatribuicao": reatribuicao,
        "paralelo": paralelo,
        "primaria": primaria,
        "df_faz": df_faz,
    }

"""Linking activities to teams and conflict resolution."""

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..scheduler import _distribuir_atividades_faltantes_turmas
from ..text_utils import _norm_atv
from ..turmas import menu_vincular_atividades_turma, resolver_conflitos_e_reatribuir
from ..ui import (
    BL, C, DM, G, RS, Y,
    aviso, confirmar, ok, selecionar, sub,
)


def _vincular_atividades_turmas(
    turmas, atividades_reais, _batch, ctx, atividade_remap,
    atividades_reais_set, fazenda, modo_seq, catalogo_global,
):
    for turma in turmas:
        if not _batch:
            menu_vincular_atividades_turma(
                turma,
                atividades_reais,
                atividades_catalogo=catalogo_global,
            )
        else:
            existing = {
                _norm_atv(a) for a in (turma.get("atividades") or []) if _norm_atv(a)
            }
            remapeadas = set(existing)
            for atv in list(existing):
                alvo = atividade_remap.get(atv)
                if alvo:
                    remapeadas.add(alvo)
            matched = remapeadas & atividades_reais_set
            turma["atividades"] = sorted(matched, key=str)

    def _cobertura_atual_turmas():
        s = set()
        for t in turmas:
            for a in t.get("atividades") or []:
                na = _norm_atv(a)
                if na:
                    s.add(na)
        return s

    cob_pre = _cobertura_atual_turmas()
    orfas_pre = [a for a in atividades_reais if a not in cob_pre]
    preencher_orfas = False
    if orfas_pre:
        if _batch:
            preencher_orfas = bool(ctx.get("preencher_orfas_template", False))
        elif modo_seq == "personalizado":
            preencher_orfas = confirmar(
                "Esta fazenda tem demandas sem turma no modelo. Preencher na turma com mais operarios? "
                "(N = equipe especializada; HH dessas atividades nao entram no cronograma)",
                default=False,
            )
    if preencher_orfas:
        _distribuir_atividades_faltantes_turmas(turmas, atividades_reais, fazenda)

    for turma in turmas:
        if not turma["atividades"]:
            aviso(f"Turma '{turma['nome']}' ficou sem atividades!")

    def coletar_vinculadas():
        s = set()
        for t in turmas:
            s.update(t["atividades"])
        return s

    atividades_vinculadas = coletar_vinculadas()
    orfas = [a for a in atividades_reais if a not in atividades_vinculadas]
    if orfas:
        logger.warning(f"ATENCAO: {len(orfas)} atividades sem turma vinculada:")
        for o in orfas:
            logger.warning(f"    - {str(o)[:55]}")
        vincular_orfas = False
        turma_alvo = None
        if _batch:
            vincular_orfas = bool(ctx.get("preencher_orfas_template", False))
            if vincular_orfas and turmas:
                turma_alvo = max(
                    turmas, key=lambda t: int(t.get("operarios", 0) or 0)
                ).get("nome")
        else:
            vincular_orfas = confirmar(
                "Vincular todas as orfas a uma turma existente?", default=True
            )
            if vincular_orfas:
                nomes = [t["nome"] for t in turmas]
                turma_alvo = selecionar("TURMA PARA ORFAS", nomes)

        if vincular_orfas and turma_alvo:
            for t in turmas:
                if t["nome"] == turma_alvo:
                    t["atividades"] = sorted(
                        set(t["atividades"]) | set(orfas), key=lambda x: str(x)
                    )
                    ok(f"{len(orfas)} atividades vinculadas a '{turma_alvo}'.")
                    break
        elif _batch and vincular_orfas:
            aviso("Modo batch: sem turma destino valida para atividades orfas.")

    atividades_vinculadas = coletar_vinculadas()
    return atividades_vinculadas


def _configurar_conflitos_reatribuicao(
    _batch, ctx, atividade_remap, atividades_reais_set, turmas, atividades_reais,
):
    logger.info("ETAPA 3: CONFLITOS E REATRIBUICAO")
    if _batch:
        reatribuicao_tpl = dict((ctx.get("reatribuicao_template") if ctx else {}) or {})
        paralelo_tpl = dict((ctx.get("paralelo_template") if ctx else {}) or {})
        primaria_tpl = dict((ctx.get("primaria_template") if ctx else {}) or {})

        reatribuicao = {}
        paralelo = {}
        primaria = {}
        for atv, turma_nome in reatribuicao_tpl.items():
            atv_n = _norm_atv(atv)
            atv_n = atividade_remap.get(atv_n, atv_n)
            if atv_n in atividades_reais_set and turma_nome:
                reatribuicao[atv_n] = turma_nome
        for atv, em_paralelo in paralelo_tpl.items():
            atv_n = _norm_atv(atv)
            atv_n = atividade_remap.get(atv_n, atv_n)
            if atv_n in atividades_reais_set:
                paralelo[atv_n] = bool(em_paralelo)
        for atv, turma_nome in primaria_tpl.items():
            atv_n = _norm_atv(atv)
            atv_n = atividade_remap.get(atv_n, atv_n)
            if atv_n in atividades_reais_set and turma_nome:
                primaria[atv_n] = turma_nome
    else:
        reatribuicao, paralelo, primaria = resolver_conflitos_e_reatribuir(
            turmas, atividades_reais
        )

    return reatribuicao, paralelo, primaria

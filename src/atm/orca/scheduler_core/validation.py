"""Validation functions for scheduler input data."""

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..tarifas import resolver_chave_tarifa, resolver_rendimento_hh
from ..turmas import turmas_que_executam
from ..config import modo_somente_hh

from . import _HH_EPSILON


def _validar_input(df_faz):
    _colunas_obrigatorias = ["fazenda", "atividade", "area_ha"]
    _faltando = [c for c in _colunas_obrigatorias if c not in df_faz.columns]
    if _faltando:
        logger.error(f"Colunas obrigatorias ausentes no micro: {', '.join(_faltando)}")
        return "colunas", None
    _areas_neg = df_faz[df_faz["area_ha"].astype(float) < 0]
    if not _areas_neg.empty:
        logger.warning(f"{len(_areas_neg)} talhao(oes) com area_ha negativa — serao zerados")
        df_faz.loc[_areas_neg.index, "area_ha"] = 0.0
    return None, df_faz


def _verificar_atividades_sem_tarifa(demandas, cfg, tarifas, strict):
    sem_tarifa = []
    for talhao, tarefas in demandas.items():
        for t in tarefas:
            atv = t["atividade"]
            t_nome = resolver_chave_tarifa(cfg, tarifas, atv)
            if t_nome not in tarifas:
                sem_tarifa.append((str(atv)[:50], str(t_nome)[:50]))
    if not strict and sem_tarifa:
        est_fb = resolver_rendimento_hh(
            cfg, tarifas, "!__chave_inexistente__!", strict=False
        )
        logger.warning(
            "Chave de tarifa NAO encontrada no orcamento importado (desencontro de nome)."
        )
        logger.warning(
            f"Rendimento estimado aplicado: ~{est_fb:.2f} h/ha (mediana/config; ver doc)."
        )
        visto = set()
        for a, tn in sem_tarifa:
            key = (a, tn)
            if key in visto:
                continue
            visto.add(key)
            logger.warning(f"micro: {a}  ->  chave buscada: {tn}")
        logger.debug(
            "Correcao: menu [4] de_para ou importe tarifas [2] — no orcamento o homem/ha existe."
        )


def _verificar_atividades_sem_executor(demandas, turmas, reatribuicao, paralelo, primaria, _batch, cfg):
    sem_executor = []
    for talhao, tarefas in demandas.items():
        for t in tarefas:
            if t["hh_total"] < _HH_EPSILON:
                continue
            atv = t["atividade"]
            if not turmas_que_executam(atv, turmas, reatribuicao, paralelo, primaria):
                sem_executor.append(atv)
    if sem_executor:
        unicos = sorted(set(str(x) for x in sem_executor))
        logger.error("Atividades com demanda mas SEM turma executora:")
        for a in unicos[:15]:
            logger.error(f"  - {a[:58]}")
        if len(unicos) > 15:
            logger.debug(f"  ... +{len(unicos) - 15}")

        total_hh = sum(t["hh_total"] for tarefas in demandas.values() for t in tarefas)
        total_custo = sum(t["custo_total"] for tarefas in demandas.values() for t in tarefas)
        total_hm = sum(t.get("hm_total", 0) for tarefas in demandas.values() for t in tarefas)

        return {
            "status": "needs_confirmation",
            "message": "Continuar mesmo assim (essas HH nao serao agendadas)?",
            "items": unicos,
            "totals": {"total_hh": total_hh, "total_custo": total_custo, "total_hm": total_hm},
            "batch": _batch,
        }

    total_hh = sum(t["hh_total"] for tarefas in demandas.values() for t in tarefas)
    total_custo = sum(t["custo_total"] for tarefas in demandas.values() for t in tarefas)
    total_hm = sum(t.get("hm_total", 0) for tarefas in demandas.values() for t in tarefas)
    return {
        "status": "ok",
        "totals": {"total_hh": total_hh, "total_custo": total_custo, "total_hm": total_hm},
    }


def _zerar_hh_sem_executor(demandas, turmas, reatribuicao, paralelo, primaria):
    for talhao, tarefas in demandas.items():
        for t in tarefas:
            atv = t["atividade"]
            if t["hh_total"] > _HH_EPSILON and not turmas_que_executam(
                atv, turmas, reatribuicao, paralelo, primaria
            ):
                t["hh_total"] = 0.0
                t["custo_total"] = 0.0
    total_hh = sum(t["hh_total"] for tarefas in demandas.values() for t in tarefas)
    total_custo = sum(t["custo_total"] for tarefas in demandas.values() for t in tarefas)
    total_hm = sum(t.get("hm_total", 0) for tarefas in demandas.values() for t in tarefas)
    logger.warning("HH sem executora foram zeradas no cronograma.")
    logger.info(f"Total HH agendavel: {total_hh:.1f} horas-homem")
    if not modo_somente_hh({}):
        logger.info(f"Custo MO agendavel: R$ {total_custo:,.2f}")
    return total_hh, total_custo, total_hm

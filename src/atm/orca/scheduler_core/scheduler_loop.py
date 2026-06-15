"""Scheduler loop — the core simulation algorithm."""

from dataclasses import dataclass
from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..config import modo_somente_hh
from ..scheduler import (
    _demanda_global_touch,
    _demanda_plantio_talhao,
    _min_fase_cascata_por_talhao,
    _somente_bloqueado_restante,
    classificar_fase_cascata_valor,
    pode_agendar_atividade_cascata,
)
from ..tarifas import resolver_chave_tarifa, resolver_custo_hora

from . import _HH_EPSILON


@dataclass
class _SchedulerLoopConfig:
    turmas: Any
    turma_filas: Any
    demanda_global: Any
    demandas: Any
    talhoes_ordenados: Any
    jornada: Any
    executores: Any
    seq_cfg: Any
    modo_seq: Any
    usar_cascata: Any
    usar_bloqueio_global: Any
    atividades_bloqueadas: Any
    usar_reforco_automatico: Any
    usar_pool_pos_bloqueio: Any
    atividades_plantio: Any
    atividades_irrig: Any
    fazenda: Any
    cfg: Any
    tarifas: Any
    modo_somente_hh_fn: Any
    dia_termino_plantio: Any
    tem_plantio_por_talhao: Any


def _executar_scheduler_loop(config: _SchedulerLoopConfig):
    # Work on a copy to avoid mutating the input
    demanda_global = config.demanda_global.copy()

    cronograma = []
    dia = 0
    MAX_DIAS = 10000

    def _registrar_fim_plantio_talhao(th, dia_atual):
        if config.dia_termino_plantio.get(th) is not None:
            return
        if not _demanda_plantio_talhao(th, demanda_global, config.atividades_plantio):
            config.dia_termino_plantio[th] = dia_atual

    def _crono(dia, talhao, atv, turma, operarios, consumo, modo=None):
        custo = consumo * resolver_custo_hora(config.cfg, config.tarifas, resolver_chave_tarifa(config.cfg, config.tarifas, atv)) if not config.modo_somente_hh_fn(config.cfg) else 0.0
        e = {
            "Dia": dia, "Fazenda": config.fazenda, "Talhao": talhao, "Atividade": atv,
            "Turma": turma, "Operarios": operarios, "HH": round(consumo, 2), "Custo_MO": custo,
        }
        if modo:
            e["Modo"] = modo
        cronograma.append(e)

    while dia < MAX_DIAS:
        tem_trabalho = any(v > _HH_EPSILON for v in demanda_global.values())
        if not tem_trabalho:
            break

        dia += 1
        restante = sum(1 for v in demanda_global.values() if v > _HH_EPSILON)
        if dia % 100 == 0 or dia == 1:
            logger.debug(f"dia {dia}/{MAX_DIAS} ({restante} demandas restantes)")
        min_fase_dia_dict = _min_fase_cascata_por_talhao(
            demanda_global, config.seq_cfg, config.modo_seq, config.usar_cascata,
            config.usar_bloqueio_global, config.atividades_bloqueadas,
            config.atividades_plantio, config.atividades_irrig,
            dia, config.dia_termino_plantio, config.tem_plantio_por_talhao,
        )
        min_fase_dia = min_fase_dia_dict
        pool_only = (
            config.usar_bloqueio_global
            and config.usar_pool_pos_bloqueio
            and _somente_bloqueado_restante(demanda_global, config.atividades_bloqueadas)
        )
        if pool_only:
            cap_pool = float(config.executores) * float(config.jornada)
            while cap_pool > _HH_EPSILON:
                fez = False
                for talhao in config.talhoes_ordenados:
                    tlist = list(config.demandas.get(talhao, []))
                    tlist.sort(
                        key=lambda t: (
                            0
                            if t["atividade"] in config.atividades_plantio
                            else (1 if t["atividade"] in config.atividades_irrig else 2),
                            str(t["atividade"]),
                        )
                    )
                    for t in tlist:
                        atv = t["atividade"]
                        if atv not in config.atividades_bloqueadas:
                            continue
                        key = (talhao, atv)
                        rest = demanda_global.get(key, 0.0)
                        if rest <= _HH_EPSILON:
                            continue
                        if not pode_agendar_atividade_cascata(
                            talhao, atv, demanda_global, config.seq_cfg, config.modo_seq,
                            config.usar_cascata, config.usar_bloqueio_global, config.atividades_bloqueadas,
                            config.atividades_plantio, config.atividades_irrig,
                            dia, config.dia_termino_plantio, config.tem_plantio_por_talhao,
                            min_fase_dia,
                        ):
                            continue
                        consumo = min(rest, cap_pool)
                        demanda_global[key] -= consumo
                        _demanda_global_touch()
                        cap_pool -= consumo
                        fez = True
                        _registrar_fim_plantio_talhao(talhao, dia)
                        _crono(dia, talhao, atv, "Pelotao_Unificado", config.executores, consumo, modo="PoolPosBloqueio")
                        if cap_pool <= _HH_EPSILON:
                            break
                    if cap_pool <= _HH_EPSILON:
                        break
                if not fez:
                    break
            for turma in config.turmas:
                fila = config.turma_filas[turma["nome"]]
                while (
                    fila
                    and demanda_global.get((fila[0]["talhao"], fila[0]["atividade"]), 0)
                    < _HH_EPSILON
                ):
                    fila.pop(0)
            continue

        for turma in config.turmas:
            fila = config.turma_filas[turma["nome"]]
            n_ops = turma["operarios"]
            cap_dia = n_ops * config.jornada

            idx = 0
            while cap_dia > _HH_EPSILON and idx < len(fila):
                item = fila[idx]
                key = (item["talhao"], item["atividade"])
                rest = demanda_global.get(key, 0)

                if rest < _HH_EPSILON:
                    idx += 1
                    continue

                if not pode_agendar_atividade_cascata(
                    item["talhao"], item["atividade"], demanda_global, config.seq_cfg, config.modo_seq,
                    config.usar_cascata, config.usar_bloqueio_global, config.atividades_bloqueadas,
                    config.atividades_plantio, config.atividades_irrig,
                    dia, config.dia_termino_plantio, config.tem_plantio_por_talhao,
                    min_fase_dia,
                ):
                    idx += 1
                    continue

                consumo = min(rest, cap_dia)
                demanda_global[key] -= consumo
                _demanda_global_touch()
                cap_dia -= consumo
                _registrar_fim_plantio_talhao(item["talhao"], dia)

                _crono(dia, item["talhao"], item["atividade"], turma["nome"], n_ops, consumo)

                if demanda_global[key] < _HH_EPSILON:
                    idx += 1

            while (
                fila
                and demanda_global.get((fila[0]["talhao"], fila[0]["atividade"]), 0)
                < _HH_EPSILON
            ):
                fila.pop(0)

            if config.usar_reforco_automatico and cap_dia > _HH_EPSILON:
                for talhao in config.talhoes_ordenados:
                    if cap_dia <= _HH_EPSILON:
                        break
                    tarefas_t = list(config.demandas.get(talhao, []))
                    if config.usar_cascata:
                        tarefas_t.sort(
                            key=lambda t: (
                                classificar_fase_cascata_valor(
                                    t["atividade"],
                                    config.seq_cfg,
                                    config.modo_seq,
                                    config.atividades_plantio,
                                    config.atividades_irrig,
                                ),
                                str(t["atividade"]),
                            )
                        )
                    for t in tarefas_t:
                        atv = t["atividade"]
                        key_ref = (talhao, atv)
                        rest_ref = demanda_global.get(key_ref, 0.0)
                        if rest_ref <= _HH_EPSILON:
                            continue
                        if not pode_agendar_atividade_cascata(
                            talhao, atv, demanda_global, config.seq_cfg, config.modo_seq,
                            config.usar_cascata, config.usar_bloqueio_global, config.atividades_bloqueadas,
                            config.atividades_plantio, config.atividades_irrig,
                            dia, config.dia_termino_plantio, config.tem_plantio_por_talhao,
                            min_fase_dia,
                        ):
                            continue
                        consumo_ref = min(rest_ref, cap_dia)
                        if consumo_ref <= _HH_EPSILON:
                            continue
                        demanda_global[key_ref] -= consumo_ref
                        _demanda_global_touch()
                        cap_dia -= consumo_ref
                        _registrar_fim_plantio_talhao(talhao, dia)
                        _crono(dia, talhao, atv, turma["nome"], n_ops, consumo_ref, modo="Reforco")

    return cronograma, dia, demanda_global

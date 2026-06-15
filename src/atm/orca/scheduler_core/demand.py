"""Demand construction and global queue building."""

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..config import modo_somente_hh
from ..scheduler import (
    auditar_cadeia_dados,
    classificar_fase_cascata_valor,
)
from ..tarifas import (
    resolver_chave_tarifa,
    resolver_custo_hora,
    resolver_rendimento_hh,
    resolver_rendimento_hm,
)
from ..text_utils import _norm_atv, atividades_por_filtro
from ..turmas import turmas_que_executam

from . import _HH_EPSILON


def _construir_demandas(talhoes_ordenados, df_faz, cfg, tarifas, strict, session_hh, modo_somente_hh, atividades_reais):
    demandas = {}
    total_hh = 0.0
    total_hm = 0.0
    total_custo = 0.0
    hm_only_atividades = set()
    fallback_hh_items = []

    for talhao in talhoes_ordenados:
        df_t = df_faz[df_faz["chave"] == talhao]
        tarefas = []
        for _, row in df_t.iterrows():
            atv = row["atividade"]
            try:
                area = float(row["area_ha"])
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Valor invalido para area_ha no talhao '{talhao}' "
                    f"atividade '{atv}': {row['area_ha']!r}"
                ) from exc
            try:
                pen = float(row["penalidade"])
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Valor invalido para penalidade no talhao '{talhao}' "
                    f"atividade '{atv}': {row['penalidade']!r}"
                ) from exc

            t_nome = resolver_chave_tarifa(cfg, tarifas, atv)
            rend_base = resolver_rendimento_hh(
                cfg,
                tarifas,
                t_nome,
                strict=strict,
                session_hh=session_hh,
                atv_micro=atv,
            )
            hm_base = resolver_rendimento_hm(cfg, tarifas, t_nome, strict=strict)
            if rend_base is None:
                if float(hm_base or 0) > 0.0:
                    rend_base = 0.0
                    fallback_hh_items.append((str(atv), str(t_nome), "HM-only => HH=0"))
                else:
                    rend_fb = resolver_rendimento_hh(
                        cfg,
                        tarifas,
                        t_nome,
                        strict=False,
                        session_hh=session_hh,
                        atv_micro=atv,
                    )
                    if rend_fb is None:
                        rend_fb = 0.0
                    rend_base = float(rend_fb)
                    fallback_hh_items.append(
                        (str(atv), str(t_nome), f"fallback HH={float(rend_base):.2f}")
                    )
            rend_hh_ha = float(rend_base) * pen
            hm_ha = float(hm_base) * pen
            in_tarifa = t_nome in tarifas

            horas = area * rend_hh_ha
            hm_horas = area * hm_ha
            custo_h = resolver_custo_hora(cfg, tarifas, t_nome) or 0.0
            custo_task = horas * custo_h
            total_hh += horas
            total_hm += hm_horas
            total_custo += custo_task

            tarifa_row = tarifas.get(t_nome, {})
            tipo_tarifa = str(tarifa_row.get("tipo", "")).lower()
            is_mec = "mecaniz" in tipo_tarifa or (hm_ha > 0 and rend_hh_ha <= 0)
            if is_mec and rend_hh_ha <= 0 and hm_ha > 0:
                hm_only_atividades.add(str(atv))

            if strict:
                origem_linha = "CT"
                rfonte = "CT"
            else:
                origem_linha = "tarifa" if in_tarifa else "fallback"
                rfonte = "CT" if in_tarifa else "estimado"
            tarefas.append(
                {
                    "atividade": atv,
                    "area": area,
                    "hh_total": horas,
                    "hm_ha": hm_ha,
                    "hm_total": hm_horas,
                    "custo_hora": custo_h,
                    "custo_total": custo_task,
                    "chave_tarifa": t_nome,
                    "origem": origem_linha,
                    "rendimento_fonte": rfonte,
                    "tipo": "Mecanizada" if is_mec else "Manual",
                }
            )
        demandas[talhao] = tarefas

    logger.info(f"Total HH da fazenda (bruto): {total_hh:.1f} horas-homem")
    logger.info(f"Total HM da fazenda (bruto): {total_hm:.1f} horas-maquina")
    if not modo_somente_hh(cfg):
        logger.info(f"Custo MO total (bruto): R$ {total_custo:,.2f}")
    if total_hm > _HH_EPSILON:
        logger.info(
            "Regra de fluxo HM-only: atividades mecanizadas rodam em paralelo e a equipe humana "
            "continua o fluxo sem esperar 100% da maquina."
        )
    if fallback_hh_items:
        logger.warning(f"Fallback HH aplicado em {len(fallback_hh_items)} item(ns) do escopo.")
        for atv_fb, t_fb, motivo_fb in fallback_hh_items[:5]:
            logger.warning(
                f"  - {str(atv_fb)[:44]} | CT:{str(t_fb)[:30]} | {str(motivo_fb)[:24]}"
            )
        if len(fallback_hh_items) > 5:
            logger.warning(f"  ... +{len(fallback_hh_items) - 5}")

    auditar_cadeia_dados(cfg, demandas, atividades_reais, session_hh=session_hh)
    return {
        "demandas": demandas,
        "total_hh": total_hh,
        "total_hm": total_hm,
        "total_custo": total_custo,
        "hm_only_atividades": hm_only_atividades,
        "fallback_hh_items": fallback_hh_items,
    }


def _construir_filas_e_demanda_global(turmas, talhoes_ordenados, demandas, reatribuicao, paralelo, primaria, atividades_reais, seq_cfg, modo_seq, usar_cascata):
    turma_filas = {}
    for turma in turmas:
        fila = []
        for talhao in talhoes_ordenados:
            for tarefa in demandas.get(talhao, []):
                atv = tarefa["atividade"]
                if tarefa["hh_total"] > _HH_EPSILON and turma["nome"] in turmas_que_executam(
                    atv, turmas, reatribuicao, paralelo, primaria
                ):
                    fila.append(
                        {
                            "talhao": talhao,
                            "atividade": atv,
                            "hh_rest": tarefa["hh_total"],
                        }
                    )
        turma_filas[turma["nome"]] = fila

    demanda_global = {}
    for talhao, tarefas in demandas.items():
        for t in tarefas:
            demanda_global[(talhao, t["atividade"])] = t["hh_total"]

    atividades_plantio = set(
        atividades_por_filtro(
            atividades_reais, seq_cfg.get("filtros_plantio") or ["plantio"]
        )
    )
    atividades_irrig = set(
        atividades_por_filtro(
            atividades_reais, seq_cfg.get("filtros_irrigacao") or ["irrig"]
        )
    )
    tem_plantio_por_talhao = {}
    for th in talhoes_ordenados:
        tem_plantio_por_talhao[th] = any(
            t["atividade"] in atividades_plantio and t["hh_total"] > _HH_EPSILON
            for t in demandas.get(th, [])
        )

    if usar_cascata:
        for _tn, fila in turma_filas.items():
            fila.sort(
                key=lambda x: (
                    classificar_fase_cascata_valor(
                        x["atividade"],
                        seq_cfg,
                        modo_seq,
                        atividades_plantio,
                        atividades_irrig,
                    ),
                    str(x["talhao"]),
                    str(x["atividade"]),
                )
            )

    return turma_filas, demanda_global, atividades_plantio, atividades_irrig, tem_plantio_por_talhao


def _construir_atividade_remap(cfg, ctx=None, _batch=False):
    atividade_remap = {}
    for manual, destino in (cfg.get("de_para", {}) or {}).items():
        manual_n = _norm_atv(manual)
        destino_n = _norm_atv(destino)
        if manual_n and destino_n:
            atividade_remap[manual_n] = destino_n
    if _batch and isinstance(ctx.get("substituicoes_template"), dict):
        for manual, destino in (ctx.get("substituicoes_template") or {}).items():
            manual_n = _norm_atv(manual)
            if isinstance(destino, dict):
                destino_nome = str(
                    destino.get("atividade_mecanizada")
                    or destino.get("nome")
                    or destino.get("recurso")
                    or ""
                ).strip()
            else:
                destino_nome = str(destino).strip()
            destino_n = _norm_atv(destino_nome)
            if manual_n and destino_n:
                atividade_remap[manual_n] = destino_n
    return atividade_remap

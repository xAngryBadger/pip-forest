"""Import contract price spreadsheet (PRECO_FINAL + CUSTO_DIRETO + CUSTO_INDIRETO)."""

import os

import pandas as pd

from ..logging_config import get_logger
from ..config import salvar_config
from ..context import dashboard_header
from ..io import ExcelReader, _find_default_ct_path, selecionar_arquivo
from ..text_utils import normalizar_chave, _to_float_any
from ..ui import (
    aviso, confirmar, erro, esperar, ok, prompt, selecionar, selecionar_paginado,
    sub, subcabecalho,
)
from .ct_parser import (
    _guess_sheet, _pick_col, normalizar_ct313, carregar_stg_tarifas,
)

logger = get_logger(__name__)


def modulo_importar_precos_contrato(cfg):
    dashboard_header()
    subcabecalho("IMPORTAR PLANILHA DE PRECO (CONTRATO)")
    caminho = selecionar_arquivo(
        "PLANILHA DE PRECO (3 abas: PRECO_FINAL/CUSTO_DIRETO/CUSTO_INDIRETO)"
    )
    if not caminho:
        return
    try:
        tarifas_ct_ref = {}
        ct_path = _find_default_ct_path()
        if ct_path:
            try:
                stg_path, n_ct, _ = normalizar_ct313(ct_path)
                if stg_path and n_ct > 0:
                    tarifas_ct_ref = carregar_stg_tarifas(stg_path)
            except (OSError, ValueError):
                tarifas_ct_ref = {}
        if not tarifas_ct_ref:
            tarifas_ct_ref = dict(cfg.get("tarifas", {}) or {})
        tarifas_ct_idx = {normalizar_chave(k): v for k, v in tarifas_ct_ref.items()}
        de_para_cfg = cfg.get("de_para", {}) or {}

        xls = pd.ExcelFile(caminho)
        pf = _guess_sheet(xls, ["preco", "final"])
        cd = _guess_sheet(xls, ["custo", "direto"])
        ci = _guess_sheet(xls, ["custo", "indireto"])
        sub()
        logger.info(f"PRECO_FINAL : {pf or '??'}")
        logger.info(f"CUSTO_DIRETO : {cd or '??'}")
        logger.info(f"CUSTO_INDIRETO : {ci or '??'}")
        if not (pf and cd and ci) or not confirmar(
            "Usar mapeamento automatico de abas?", default=True
        ):
            pf = selecionar("ABA PRECO_FINAL", xls.sheet_names)
            if pf is None:
                return
            cd = selecionar("ABA CUSTO_DIRETO", xls.sheet_names)
            if cd is None:
                return
            ci = selecionar("ABA CUSTO_INDIRETO", xls.sheet_names)
            if ci is None:
                return

        df_pf = ExcelReader.read(caminho, sheet_name=pf)
        df_cd = ExcelReader.read(caminho, sheet_name=cd)
        df_ci = ExcelReader.read(caminho, sheet_name=ci)

        col_atv_pf = _pick_col(df_pf, [["atividade"], ["servico"], ["descricao"]])
        col_preco = _pick_col(df_pf, [["preco", "final"], ["preco"], ["valor"]])
        col_hh = _pick_col(df_pf, [["hh"], ["homem", "hora"], ["rendimento", "hh"]])
        col_hm = _pick_col(df_pf, [["hm"], ["hora", "maquina"], ["rendimento", "hm"]])
        col_tipo = _pick_col(df_pf, [["tipo"]])

        col_atv_cd = _pick_col(df_cd, [["atividade"], ["servico"], ["descricao"]])
        col_cd = _pick_col(df_cd, [["custo", "direto"], ["direto"], ["valor"]])
        col_atv_ci = _pick_col(df_ci, [["atividade"], ["servico"], ["descricao"]])
        col_ci = _pick_col(df_ci, [["custo", "indireto"], ["indireto"], ["valor"]])

        if not col_atv_pf or not col_preco:
            erro(
                "Nao foi possivel identificar colunas minimas de PRECO_FINAL (atividade/preco)."
            )
            esperar(DM + "\n [ENTER] " + RS)
            return

        custo_direto = {}
        if col_atv_cd and col_cd:
            for _, r in df_cd.iterrows():
                atv = str(r.get(col_atv_cd, "")).strip()
                if not atv:
                    continue
                try:
                    custo_direto[normalizar_chave(atv)] = float(
                        str(r.get(col_cd, 0)).replace(",", ".")
                    )
                except (TypeError, ValueError):
                    pass
        custo_indireto = {}
        if col_atv_ci and col_ci:
            for _, r in df_ci.iterrows():
                atv = str(r.get(col_atv_ci, "")).strip()
                if not atv:
                    continue
                try:
                    custo_indireto[normalizar_chave(atv)] = float(
                        str(r.get(col_ci, 0)).replace(",", ".")
                    )
                except (TypeError, ValueError):
                    pass

        tarifas = {}
        total_cells = 0
        failed_cells = 0
        for _, r in df_pf.iterrows():
            atv = str(r.get(col_atv_pf, "")).strip()
            if not atv:
                continue
            try:
                preco = float(str(r.get(col_preco, 0)).replace(",", "."))
            except (TypeError, ValueError):
                preco = 0.0
                failed_cells += 1
            try:
                hh_pf = (
                    float(str(r.get(col_hh, 0)).replace(",", ".")) if col_hh else 0.0
                )
            except (TypeError, ValueError):
                hh_pf = 0.0
                failed_cells += 1
            try:
                hm = float(str(r.get(col_hm, 0)).replace(",", ".")) if col_hm else 0.0
            except (TypeError, ValueError):
                hm = 0.0
                failed_cells += 1
            total_cells += 3
            nk = normalizar_chave(atv)
            chave_ct = str(de_para_cfg.get(atv, atv) or atv).strip()
            nk_ct = normalizar_chave(chave_ct)
            row_ct = tarifas_ct_idx.get(nk_ct, tarifas_ct_idx.get(nk, {}))
            try:
                hh_ct = float(row_ct.get("rendimento_hh", 0) or 0.0)
            except (TypeError, ValueError):
                hh_ct = 0.0
            try:
                hm_ct = float(row_ct.get("rendimento_hm", 0) or 0.0)
            except (TypeError, ValueError):
                hm_ct = 0.0
            hh = hh_ct if hh_ct > 0 else hh_pf
            hm = max(hm, hm_ct)
            tipo = (
                str(r.get(col_tipo, "")).strip()
                if col_tipo and str(r.get(col_tipo, "")).strip()
                else str(row_ct.get("tipo", "")).strip()
            )
            if not tipo:
                tipo = "Mecanizada" if hm > 0 else "Manual"
            cd_v = float(custo_direto.get(nk, 0.0))
            ci_v = float(custo_indireto.get(nk, 0.0))
            try:
                c_h = float(row_ct.get("custo_hora", 0) or 0.0)
            except (TypeError, ValueError):
                c_h = 0.0
            if c_h <= 0:
                c_h = float(cfg.get("custo_hora_tf") or 0.0)
            if hh <= 0.01 and hm > 0:
                c_h = 0.0
            payload = {
                "rendimento_hh": hh,
                "rendimento_hm": hm,
                "preco_ha": preco,
                "preco_unit": preco,
                "custo_hora": c_h,
                "custo_ha": (hh * c_h) if c_h > 0 else 0.0,
                "tipo": tipo,
                "recurso": "maquina" if hm > 0 and hh <= 0.01 else "homem",
                "eficiencia": 1.0,
                "custo_direto": cd_v,
                "custo_indireto": ci_v,
            }
            tarifas[atv] = payload
            if nk_ct and nk_ct != nk:
                tarifas[chave_ct] = dict(payload)
        if total_cells > 0 and failed_cells / total_cells > 0.5:
            logger.warning(
                "High parse failure rate in PRECO_FINAL: %d/%d cells failed (%.1f%%)",
                failed_cells,
                total_cells,
                failed_cells / total_cells * 100,
            )

        if not tarifas:
            erro("Nenhuma atividade valida encontrada na planilha de preco.")
            esperar(DM + "\n [ENTER] " + RS)
            return

        cfg["tarifas"] = tarifas
        cfg["precos_contrato"] = {
            "arquivo": os.path.basename(caminho),
            "sheet_preco_final": pf,
            "sheet_custo_direto": cd,
            "sheet_custo_indireto": ci,
        }
        salvar_config(cfg)
        ok(f"{len(tarifas)} tarifas importadas da planilha de contrato.")
        sem_hh = [
            k
            for k, v in tarifas.items()
            if float(v.get("rendimento_hh", 0) or 0) <= 0
            and float(v.get("rendimento_hm", 0) or 0) <= 0
        ]
        sem_preco = [
            k for k, v in tarifas.items() if float(v.get("preco_unit", 0) or 0) <= 0
        ]
        if sem_hh:
            logger.warning(f"Pos-import: {len(sem_hh)} tarifa(s) sem rendimento (HH e HM zerados):")
            for x in sem_hh[:5]:
                logger.warning(f" - {str(x)[:55]}")
            if len(sem_hh) > 5:
                logger.warning(f" ... +{len(sem_hh) - 5}")
        if sem_preco:
            logger.warning(f"Pos-import: {len(sem_preco)} tarifa(s) com preco zerado:")
            for x in sem_preco[:5]:
                logger.warning(f" - {str(x)[:55]}")
            if len(sem_preco) > 5:
                logger.warning(f" ... +{len(sem_preco) - 5}")
        if not sem_hh and not sem_preco:
            ok("Pos-import: todas as tarifas possuem HH e preco validos.")
        esperar(DM + "\n [ENTER para voltar] " + RS)
    except Exception as ex:  # noqa: broad-except — UI guard
        logger.exception("modulo_importar_precos_contrato: falha")
        erro(f"Falha ao importar planilha de preco: {ex}")
        esperar(DM + "\n [ENTER] " + RS)

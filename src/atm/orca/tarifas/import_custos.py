"""Import global raw costs (CUSTO_DIRETO + CUSTO_INDIRETO sheets)."""

import os

import pandas as pd

from ..logging_config import get_logger
from ..config import salvar_config
from ..context import dashboard_header
from ..io import selecionar_arquivo
from ..ui import (
    confirmar, erro, esperar, ok, selecionar,
    sub, subcabecalho,
)
from .ct_parser import _guess_sheet, _extrair_custos_globais_brutos

logger = get_logger(__name__)


def modulo_importar_custos_globais_brutos(cfg):
    dashboard_header()
    subcabecalho("IMPORTAR CUSTOS GLOBAIS (BRUTO)")
    caminho = selecionar_arquivo(
        "PLANILHA BRUTA DE CUSTOS (CUSTO_DIRETO/CUSTO_INDIRETO)"
    )
    if not caminho:
        return
    try:
        xls = pd.ExcelFile(caminho)
        cd = _guess_sheet(xls, ["custo", "direto"])
        ci = _guess_sheet(xls, ["custo", "indireto"])
        sub()
        logger.info(f"CUSTO_DIRETO : {cd or '??'}")
        logger.info(f"CUSTO_INDIRETO : {ci or '??'}")
        if not (cd and ci) or not confirmar(
            "Usar mapeamento automatico de abas?", default=True
        ):
            cd = selecionar("ABA CUSTO_DIRETO", xls.sheet_names)
            if cd is None:
                return
            ci = selecionar("ABA CUSTO_INDIRETO", xls.sheet_names)
            if ci is None:
                return

        ext = _extrair_custos_globais_brutos(caminho, cd, ci)
        cfg["custos_globais"] = {
            "arquivo": os.path.basename(caminho),
            "sheet_custo_direto": cd,
            "sheet_custo_indireto": ci,
            "valor_direto_total": ext["valor_direto_total"],
            "valor_indireto_total": ext["valor_indireto_total"],
            "criterio": "ultimo_valor_na_linha",
            "itens_direto": ext["itens_direto"],
            "itens_indireto": ext["itens_indireto"],
        }
        salvar_config(cfg)
        ok(
            "Custos globais importados: "
            f"Direto R$ {ext['valor_direto_total']:,.2f} | "
            f"Indireto R$ {ext['valor_indireto_total']:,.2f}"
        )
        logger.info(
            f"Itens lidos: direto={len(ext['itens_direto'])} | indireto={len(ext['itens_indireto'])}"
        )
    except Exception as ex:  # noqa: broad-except — UI guard
        logger.exception("modulo_importar_custos_globais_brutos: falha")
        erro(f"Falha ao importar custos globais brutos: {ex}")
        esperar(DM + "\n [ENTER para voltar] " + RS)

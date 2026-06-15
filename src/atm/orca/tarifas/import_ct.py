"""CT313 import and normalization — extracted from app.py."""

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..config import (
    STG_FILENAME,
    modo_somente_hh,
    salvar_config,
)
from ..io import (
    ExcelReader,
    _to_float_br,
    encontrar_coluna,
    selecionar_arquivo,
)
from ..tarifas import (
    carregar_stg_tarifas,
    normalizar_ct313,
    resolver_rendimento_hh,
)
from ..ui import (
    DM,
    Y,
    aviso,
    confirmar,
    erro,
    esperar,
    ok,
    selecionar,
    selecionar_paginado,
    sub,
    subcabecalho,
)
from ..text_utils import normalizar_chave


def modulo_normalizar_ct(cfg):
    """Menu: selecionar CT bruta, gerar STG, integrar em config.tarifas."""
    from ..context import dashboard_header
    dashboard_header()
    subcabecalho("NORMALIZAR CT (CT317 REAL) -> STG_TARIFAS")
    caminho = selecionar_arquivo("CT BRUTA/REAL (.xlsm ou .xlsx)")
    if not caminho:
        return

    logger.info("Processando CT313... pode demorar alguns segundos.")
    stg_path, n, custo_h = normalizar_ct313(caminho)
    if not stg_path:
        erro("Aba 'Preco Final' nao encontrada neste arquivo.")
        esperar()
        return

    if modo_somente_hh(cfg):
        ok(f"Gerado {STG_FILENAME}: {n} atividades (modo somente HH).")
    else:
        ok(f"Gerado {STG_FILENAME}: {n} atividades | custo/hora TF = R${custo_h:.2f}")

    if confirmar(
        "Integrar STG_TARIFAS em config.json (substitui tarifas existentes)?",
        default=True,
    ):
        tarifas = carregar_stg_tarifas(stg_path)
        cfg["tarifas"] = tarifas
        cfg["custo_hora_tf"] = round(custo_h, 4)
        salvar_config(cfg)
        ok(f"{len(tarifas)} tarifas integradas no config.")
    esperar("ENTER para voltar")


def modulo_importar_tarifas(cfg):
    """Menu: importar tarifas orcadas (CT_313) via mapeamento de colunas."""
    from ..context import dashboard_header
    dashboard_header()
    subcabecalho("IMPORTAR TARIFAS ORCADAS (CT_313)")
    caminho = selecionar_arquivo("PLANILHA DE ORCAMENTO (CT_313 ou Tarifas)")
    if not caminho:
        return

    try:
        logger.info("Carregando arquivo...")
        import pandas as pd
        xls = pd.ExcelFile(caminho)
        aba = selecionar("SELECIONE A ABA (ex: Preco Final)", xls.sheet_names)
        if aba is None:
            return

        logger.info(f"Lendo aba '{aba}'...")
        df = ExcelReader.read(caminho, sheet_name=aba, nrows=1000)
        cols_ct = df.columns.tolist()

        # Tentar mapear automaticamente
        col_atv = encontrar_coluna(cols_ct, "atividade")
        sub()
        subcabecalho(f"MAPEAMENTO: Atividade -> {col_atv or '???'}")
        sub()

        if not col_atv or not confirmar("Usar este mapeamento?", default=True):
            idx = selecionar_paginado("COLUNA DA ATIVIDADE", cols_ct)
            col_atv = cols_ct[idx] if idx >= 0 else None
            if not col_atv:
                aviso("Atividade obrigatoria.")
                return

        # Para HH e Preco, perguntar diretamente
            subcabecalho("Selecione as colunas adicionais (0 = ignorar):")
        idx = selecionar_paginado("COLUNA DE HH/HA", cols_ct)
        col_hh = cols_ct[idx] if idx >= 0 else None

        idx = selecionar_paginado("COLUNA DE PRECO UNITARIO", cols_ct)
        col_preco = cols_ct[idx] if idx >= 0 else None

        tarifas = cfg.get("tarifas", {})
        importadas = 0
        for _, row in df.iterrows():
            nome = str(row.get(col_atv, "")).strip()
            if not nome or nome.lower() == "nan":
                continue
            hh = 0 if not col_hh else row.get(col_hh, 0)
            preco = 0 if not col_preco else row.get(col_preco, 0)
            if pd.notna(hh) and str(hh).strip() != "":
                hh_val = _to_float_br(hh)
            else:
                hh_val = resolver_rendimento_hh(cfg, tarifas, nome)
            preco_val = _to_float_br(preco) if pd.notna(preco) else 0.0
            tarifas[nome] = {
                "rendimento_hh": hh_val,
                "preco_unit": preco_val,
                "recurso": "homem",
                "eficiencia": 1.0,
            }
            importadas += 1

        cfg["tarifas"] = tarifas
        salvar_config(cfg)
        ok(f"{importadas} tarifas integradas!")
        sem_hh = [
            k for k, v in tarifas.items() if float(v.get("rendimento_hh", 0) or 0) <= 0
        ]
        sem_preco = [
            k for k, v in tarifas.items() if float(v.get("preco_unit", 0) or 0) <= 0
        ]
        if sem_hh:
            logger.warning(f"Pos-import: {len(sem_hh)} tarifa(s) com HH zerado.")
            for x in sem_hh[:5]:
                logger.debug(f"    - {str(x)[:55]}")
        if sem_preco:
            logger.warning(f"Pos-import: {len(sem_preco)} tarifa(s) com preco zerado.")
            for x in sem_preco[:5]:
                logger.debug(f"    - {str(x)[:55]}")
    except Exception as e:
        logger.exception("Erro ao importar tarifas")
        erro(f"Erro ao importar: {e}")

    esperar("ENTER para voltar")
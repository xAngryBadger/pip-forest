"""De-para CRUD and tariff policy warnings."""

from ..logging_config import get_logger
from ..config import salvar_config
from ..context import dashboard_header
from ..text_utils import normalizar_chave
from ..ui import (
    aviso, confirmar, esperar, ok, prompt, selecionar_paginado,
    sub, subcabecalho,
)

logger = get_logger(__name__)


def modulo_mapeamentos_de_para(cfg, df_micro=None):
    """CRUD de_para: nome no microplanejamento -> nome da tarifa em config.tarifas."""
    tarifas = cfg.get("tarifas", {})
    nomes_tarifa = sorted(tarifas.keys(), key=lambda x: str(x))
    atividades_micro = []
    if (
        df_micro is not None
        and getattr(df_micro, "columns", None) is not None
        and "atividade" in df_micro.columns
    ):
        atividades_micro = sorted(
            df_micro["atividade"].dropna().unique().tolist(), key=str
        )

    while True:
        dashboard_header()
        subcabecalho("MAPEAMENTOS de_para (micro -> tarifa)")
        d = cfg.get("de_para", {})
        pairs = [(k, v) for k, v in d.items() if not str(k).startswith("_")]
        if not pairs:
            logger.info("Nenhum par (o sistema usa nome micro = nome na tarifa, ou default 8 h/ha).")
        else:
            for k, v in sorted(pairs, key=lambda x: str(x[0]))[:35]:
                logger.info(f"{str(k)[:36]:36} -> {str(v)[:36]}")
            if len(pairs) > 35:
                logger.info(f"... +{len(pairs) - 35} pares no arquivo")
        sub()
        logger.info("[1] Incluir ou alterar par")
        logger.info("[2] Remover par")
        logger.info("[3] Listar catalogo de TARIFAS (nomes em config)")
        logger.info("[0] Voltar")
        op = prompt("Opcao").strip()
        if op == "0":
            return
        if op == "1":
            chave_micro = ""
            if atividades_micro and confirmar(
                "Escolher atividade da planilha carregada?", default=True
            ):
                idx = selecionar_paginado(
                    "ATIVIDADE no micro", atividades_micro, page_size=8
                )
                if idx >= 0:
                    chave_micro = atividades_micro[idx]
            if not chave_micro:
                chave_micro = prompt("Nome EXATO da atividade no microplanejamento", "")
            if not chave_micro:
                aviso("Nome vazio.")
                continue
            val_tarifa = ""
            if nomes_tarifa and confirmar(
                "Escolher tarifa na lista importada?", default=True
            ):
                idx = selecionar_paginado(
                    "TARIFA (orcamento)", nomes_tarifa, page_size=8
                )
                if idx >= 0:
                    val_tarifa = nomes_tarifa[idx]
            if not val_tarifa:
                val_tarifa = prompt("Nome da TARIFA (chave em tarifas)", "")
            if not val_tarifa:
                aviso("Tarifa vazio.")
                continue
            if val_tarifa not in tarifas:
                if not confirmar(
                    f" '{str(val_tarifa)[:42]}' nao esta em tarifas. Gravar mesmo assim?",
                    default=False,
                ):
                    continue
            cfg.setdefault("de_para", {})
            cfg["de_para"][chave_micro] = val_tarifa
            salvar_config(cfg)
            ok("Mapeamento salvo em config.json.")
        elif op == "2":
            keys = sorted([k for k in d.keys() if not str(k).startswith("_")], key=str)
            if not keys:
                aviso("Nada para remover.")
                continue
            idx = selecionar_paginado("REMOVER mapeamento", [str(k) for k in keys])
            if idx >= 0:
                del cfg["de_para"][keys[idx]]
                salvar_config(cfg)
                ok("Removido.")
        elif op == "3":
            if not nomes_tarifa:
                aviso("Nenhuma tarifa em config. Use menu [2] Importar.")
            else:
                for i, n in enumerate(nomes_tarifa[:60], 1):
                    logger.info(f"{i:3}. {str(n)[:58]}")
                if len(nomes_tarifa) > 60:
                    logger.info(f"... +{len(nomes_tarifa) - 60}")
                esperar()
        else:
            aviso("Opcao invalida.")


def aviso_politica_tarifas_planas():
    """Politica comercial-executiva: base CT sempre 'plana' (Classe I) onde o micro nao discrimina."""
    sub()
    logger.warning("POLITICA DE DECLIVIDADE E ROCADA MANUAL (CT)")
    logger.info(
        "Na CT, ROCADA MANUAL CLASSE I = terreno mais plano (menos HH/ha, menor R$/ha); "
        "CLASSE V = declive maximo (mais HH, mais R$/ha — obra mais cara e precos mais altos)."
    )
    logger.warning(
        "Padrao deste app: o exame nao informa a classe por talhao — usamos sempre as linhas "
        "EQUIVALENTES AO CENARIO MAIS PLANO (ex.: ROCADA MANUAL CLASSE I) no de_para fixo."
    )
    logger.info(
        "Interpretacao: simulacao conservadora em LUCRO — como se nao houvesse premio de "
        "declividade na mixagem; em campo inclinado real, revise o menu [4] de_para para "
        "Classes II-V conforme a CT."
    )
    sub()


def _depara_heuristico_exame_ct317(kn, tarifas):
    """Fallback heuristic deliberately deactivated.

    The tool now uses exact CT317 sheet names only.
    If a name is not found, the sheet will request manual mapping.
    """
    return None

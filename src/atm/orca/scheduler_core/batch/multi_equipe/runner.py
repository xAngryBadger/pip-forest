"""Multi-team runner — main entry point for multi-equipes mode."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from ....logging_config import get_logger

logger = get_logger(__name__)

from ....config import _merge_sequencia_defaults
from ....context import dashboard_header
from ....scheduler import _selecionar_sequencia_padrao_sn
from ....text_utils import _norm_atv
from ....ui import aviso, ok, pedir_int, sub, subcabecalho, esperar

from .config import (
    _configurar_data_multi_equipes,
    _agrupar_e_sugerir_equipes,
    _configurar_uma_equipe,
)
from .processor import _processar_equipes_e_consolidar


def _executar_multi_equipes(
    cfg: Dict[str, Any],
    df_scope: pd.DataFrame,
    fazendas: List[str],
    empresa_filtro: Optional[str] = None,
    nome_arquivo_micro: str = "",
) -> None:
    """Modo avançado: N equipes independentes, cada uma com carteira de fazendas e meta própria."""
    dashboard_header()
    subcabecalho("MODO MULTI-EQUIPES")
    logger.debug("Cada equipe tera sua propria configuracao, meta e carteira de fazendas.")
    logger.debug("Ao final, um consolidado comparativo mostra a situacao de cada equipe.")

    n_equipes = pedir_int("Quantas equipes independentes?", 2)
    if n_equipes < 1:
        aviso("Precisa de pelo menos 1 equipe.")
        return

    todas_atvs = sorted(
        {_norm_atv(x) for x in df_scope["atividade"].dropna().unique() if _norm_atv(x)},
        key=str,
    )

    seq_cfg = cfg.get("sequencia") or {}
    _merge_sequencia_defaults(seq_cfg)
    cfg["sequencia"] = seq_cfg
    modo_seq = _selecionar_sequencia_padrao_sn(cfg, seq_cfg, todas_atvs)

    mes_ref, ano_ref, dia_ref, data_inicio_txt = _configurar_data_multi_equipes()

    usar_modo_empresa, config_empresa, n_equipes = _agrupar_e_sugerir_equipes(
        cfg, fazendas, df_scope, n_equipes,
    )

    equipes_config = []
    fazendas_restantes = list(fazendas)

    for ie in range(1, n_equipes + 1):
        ec = _configurar_uma_equipe(
            ie, n_equipes, todas_atvs, fazendas_restantes,
            mes_ref, ano_ref, dia_ref, data_inicio_txt, modo_seq,
            usar_modo_empresa, config_empresa,
        )
        if ec:
            equipes_config.append(ec)

    if usar_modo_empresa and fazendas_restantes:
        orfas = list(fazendas_restantes)
        if equipes_config:
            maior = max(equipes_config, key=lambda e: len(e["fazendas"]))
            maior["fazendas"] = maior["fazendas"] + orfas
            ok(f"{len(orfas)} fazenda(s) orfa(s) (sem empresa) atribuidas a '{maior['nome']}'.")
        else:
            n_equipes += 1
            nome_orfa = f"Equipe Orfa {n_equipes}"
            equipes_config.append({
                "nome": nome_orfa, "prazo_meses": 3.0, "jornada": 4.3,
                "executores": 10,
                "turmas": [{"nome": nome_orfa, "operarios": 10, "atividades": []}],
                "fazendas": orfas, "modo_seq": modo_seq,
                "mes_ref": mes_ref, "ano_ref": ano_ref,
                "data_inicio_txt": data_inicio_txt, "data_fim_txt": None,
            })
            ok(f"{len(orfas)} fazenda(s) orfa(s) atribuidas a '{nome_orfa}' (equipe extra).")
        fazendas_restantes.clear()

    if equipes_config:
        _processar_equipes_e_consolidar(cfg, df_scope, equipes_config, empresa_filtro, nome_arquivo_micro)
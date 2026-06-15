"""Comparativo mode configuration — auto-detect mechanized substitutions."""
from typing import Tuple, Dict, List

from .constants import COMPARATIVO_MANUAL_MEC


def _configurar_modo_comparativo(
    atividades_reais: List[str],
    _batch: bool = False,
) -> Tuple[str, Dict[str, str]]:
    """Returns (modo_comparativo, substituicoes_comparativo) based on available activities.

    modo_comparativo: 'off' | 'simple' | 'multi-factor'
    substituicoes_comparativo: dict mapping manual activity -> mechanized replacement
    """
    substituicoes = {}
    for atv in atividades_reais:
        if atv in COMPARATIVO_MANUAL_MEC:
            substituicoes[atv] = COMPARATIVO_MANUAL_MEC[atv]

    if not substituicoes:
        return "off", {}

    if _batch:
        return "off", substituicoes

    return "simple", substituicoes

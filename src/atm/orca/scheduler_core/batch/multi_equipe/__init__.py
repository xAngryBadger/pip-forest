"""Multi-team execution package — N independent teams with their own farm portfolios."""

from .config import (
    _configurar_data_multi_equipes,
    _agrupar_e_sugerir_equipes,
    _configurar_uma_equipe,
    _perguntar_data_fim_equipe,
)
from .processor import _processar_equipes_e_consolidar
from .runner import _executar_multi_equipes

__all__ = [
    "_configurar_data_multi_equipes",
    "_agrupar_e_sugerir_equipes",
    "_configurar_uma_equipe",
    "_perguntar_data_fim_equipe",
    "_processar_equipes_e_consolidar",
    "_executar_multi_equipes",
]
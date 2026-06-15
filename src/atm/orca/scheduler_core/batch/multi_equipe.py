"""Multi-team execution — N independent teams with their own farm portfolios.

This module is a thin wrapper that re-exports from the multi_equipe package.
The actual implementation is split into:
- config.py: interactive configuration functions
- processor.py: team processing and consolidation
- runner.py: main entry point
"""

from .multi_equipe import (
    _configurar_data_multi_equipes,
    _agrupar_e_sugerir_equipes,
    _configurar_uma_equipe,
    _perguntar_data_fim_equipe,
    _processar_equipes_e_consolidar,
    _executar_multi_equipes,
)

__all__ = [
    "_configurar_data_multi_equipes",
    "_agrupar_e_sugerir_equipes",
    "_configurar_uma_equipe",
    "_perguntar_data_fim_equipe",
    "_processar_equipes_e_consolidar",
    "_executar_multi_equipes",
]
"""SRF UI — thin re-export wrapper for orca.ui"""

from src.atm.orca.ui import (
    G, Y, R, C, DM, BL, RS,
    console, linha, sub, subcabecalho,
    aviso, erro, ok, prompt,
    pedir_float, pedir_int, pedir_jornada,
    selecionar, selecionar_paginado, confirmar,
    esperar, escolha,
    Table,
)

__all__ = [
    "G", "Y", "R", "C", "DM", "BL", "RS",
    "console", "linha", "sub", "subcabecalho",
    "aviso", "erro", "ok", "prompt",
    "pedir_float", "pedir_int", "pedir_jornada",
    "selecionar", "selecionar_paginado", "confirmar",
    "esperar", "escolha",
    "Table",
]
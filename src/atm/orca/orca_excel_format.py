"""Optional Excel formatting module for operational dossier output.

This is a stub implementation. Replace with a full formatter if needed.
"""

from typing import Any
from openpyxl import Workbook


def aplicar_formatacao_operacional(wb: Workbook, dias_simulado: int, cronograma: list[dict[str, Any]]) -> None:
    """Apply operational formatting to the workbook.

    Args:
        wb: openpyxl Workbook instance
        dias_simulado: Total simulated days
        cronograma: List of schedule rows
    """
    pass


def aplicar_formatacao_comparativo(wb: Workbook, dias_simulado: int, cronograma: list[dict[str, Any]]) -> None:
    """Apply comparative formatting to the workbook.

    Args:
        wb: openpyxl Workbook instance
        dias_simulado: Total simulated days
        cronograma: List of schedule rows
    """
    pass

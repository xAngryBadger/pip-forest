"""Date utilities — formatting, conversion, calendar calculations."""

import calendar
from datetime import date, timedelta

def _formatar_data_dia(dia, mes, ano):
    """Formata data DD/MM/AAAA; assume valores inteiros validos."""
    return f"{int(dia):02d}/{int(mes):02d}/{int(ano)}"


# Mapeamento de dias da semana para abreviacoes brasileiras
_DIAS_SEMANA_CURTO = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
_DIAS_SEMANA_COMPLETO = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]


def _converter_dia_simulado_para_data(
    dia_simulado: int, dia_ref: int, mes_ref: int, ano_ref: int
):
    """
    Converte dia simulado (1, 2, 3...) para data real.
    Dia simulado = dia UTIL (seg-sex). Fins de semana sao pulados.

    Retorna: (data_str, dia_semana_curto, dia_semana_completo, data_obj)
    Ex: (1, 20, 4, 2025) -> ("20/04/2025", "Dom", "Domingo", date_obj)
    """
    try:
        dia_simulado = int(dia_simulado)
        dia_ref = int(dia_ref)
        mes_ref = int(mes_ref)
        ano_ref = int(ano_ref)

        data_inicio = date(ano_ref, mes_ref, dia_ref)

        uteis_restantes = dia_simulado
        data_real = data_inicio
        while uteis_restantes > 0:
            if data_real.weekday() < 5:
                uteis_restantes -= 1
                if uteis_restantes == 0:
                    break
            data_real += timedelta(days=1)

        data_str = f"{data_real.day:02d}/{data_real.month:02d}/{data_real.year}"

        dia_semana_idx = data_real.weekday()
        dia_semana_curto = _DIAS_SEMANA_CURTO[dia_semana_idx]
        dia_semana_completo = _DIAS_SEMANA_COMPLETO[dia_semana_idx]

        return (data_str, dia_semana_curto, dia_semana_completo, data_real)
    except Exception:
        return (f"Dia_{dia_simulado}", "-", "-", None)


def _calcular_data_fim_por_meses(dia_inicio, mes_ref, ano_ref, prazo_meses):
    """
    Calcula data final (dia/mes/ano) a partir de um dia inicial e prazo em meses.
    Ajusta o dia para o maximo do mes final.
    """
    try:
        dia_inicio = int(dia_inicio)
        mes_ref = int(mes_ref)
        ano_ref = int(ano_ref)
        prazo_meses = int(round(float(prazo_meses)))
    except Exception:
        return None
    if prazo_meses <= 0:
        return (dia_inicio, mes_ref, ano_ref)
    mes_fim = mes_ref + (prazo_meses - 1)
    ano_fim = ano_ref + (mes_fim - 1) // 12
    mes_fim = ((mes_fim - 1) % 12) + 1
    ultimo_dia = calendar.monthrange(ano_fim, mes_fim)[1]
    dia_fim = min(max(1, dia_inicio), int(ultimo_dia))
    return (dia_fim, mes_fim, ano_fim)

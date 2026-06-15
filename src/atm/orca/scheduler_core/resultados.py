"""Result building functions."""

from collections import defaultdict

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..monitor import _monitor_build_rendimentos, _emitir_monitor_state, _emitir_monitor_relatorio
from ..comparativo_mec import _formatar_substituicao_comparativo
from ..ui import esperar

from . import _HH_EPSILON


def _build_resultado_final(
    esperar_enter, fazenda, dias_simulado, meses_simulado,
    prazo_meses, dias_meta, total_hh, total_custo, total_hm,
    cronograma_base, turmas, resultado_mecanizado,
    resultado_mecanizado_valido, substituicoes_comparativo,
    recursos_mec, cronograma_com_mec, demandas,
    result_files=None,
):
    if esperar_enter:
        esperar("ENTER para voltar ao menu")
    d_mc = (
        max([int(x.get("Dia", 0)) for x in cronograma_com_mec], default=0)
        if (recursos_mec and cronograma_com_mec)
        else None
    )
    ganho_mc = (int(dias_simulado) - int(d_mc)) if d_mc is not None else 0
    rendimentos_feed = []
    if callable(_monitor_build_rendimentos):
        try:
            rendimentos_feed = _monitor_build_rendimentos(demandas)
        except (TypeError, ValueError, KeyError):
            logger.warning("Falha ao processar rendimentos do monitor", exc_info=True)
            rendimentos_feed = []
    _emitir_monitor_state(
        {
            "operacao": {
                "fazenda_atual": str(fazenda),
                "status_geral": "concluido",
                "mensagem_curta": f"{dias_simulado} dia(s) simulados | HH {total_hh:.1f}",
            },
            "lote": {
                "dias_meta": int(dias_meta),
                "dias_consumidos": int(dias_simulado),
                "saldo_dias": int(max(0, int(dias_meta) - int(dias_simulado))),
                "status_meta_continuo": "OK"
                if meses_simulado <= prazo_meses
                else "EXCEDIDO",
                "prazo_absoluto": True,
            },
            "rendimentos_sessao": rendimentos_feed,
        }
    )
    resumo_monitor = [
        f"Fazenda: {fazenda}",
        f"Dias simulados: {int(dias_simulado)}",
        f"HH total: {float(total_hh):.1f}",
    ]
    _emitir_monitor_relatorio(f"Resumo {fazenda}", "\n".join(resumo_monitor))

    resultado_final = {
        "fazenda": fazenda,
        "dias_simulado": int(dias_simulado),
        "meses_simulado": float(meses_simulado),
        "dias_mecanizado": d_mc,
        "ganho_mecanizado_dias": int(ganho_mc),
        "total_hh": float(total_hh),
        "total_custo": float(total_custo),
        "total_hm": float(total_hm),
        "cronograma": cronograma_base,
        "turmas_snapshot": [
            {"nome": t["nome"], "operarios": t["operarios"]} for t in turmas
        ],
        "result_files": result_files or [],
    }

    if resultado_mecanizado_valido:
        resultado_final["comparativo_mecanizado"] = {
            "dias_simulado": resultado_mecanizado.get("dias_simulado"),
            "total_hh": resultado_mecanizado.get("total_hh"),
            "total_hm": resultado_mecanizado.get("total_hm"),
            "total_custo": resultado_mecanizado.get("total_custo", 0),
            "substituicoes_aplicadas": [
                {
                    "manual": manual,
                    "mecanizado": _formatar_substituicao_comparativo(mec),
                }
                for manual, mec in (substituicoes_comparativo or {}).items()
            ],
        }

    return resultado_final

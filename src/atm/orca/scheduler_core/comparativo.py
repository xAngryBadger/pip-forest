"""Comparativo manual vs mecanizado execution."""

import io
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..comparativo_mec import (
    _clonar_cfg_comparativo_mecanizado,
    _formatar_substituicao_comparativo,
    _substituir_por_mecanizado,
)


@dataclass
class _ComparativoUIConfig:
    modo_comparativo: Any
    substituicoes_comparativo: Any
    session_hh: Any


@dataclass
class _ComparativoExecutionConfig:
    cfg: Any
    df_faz: Any
    fazenda: Any
    modo_seq: Any
    usar_bloqueio_global: Any
    usar_reforco_automatico: Any
    usar_pool_pos_bloqueio: Any
    prazo_meses: Any
    mes_ref: Any
    ano_ref: Any
    data_inicio_txt: Any
    data_fim_txt: Any
    jornada: Any
    executores: Any
    turmas: Any
    preencher_orfas: Any
    reatribuicao: Any
    paralelo: Any
    primaria: Any
    escopo_meta: Any
    atividades_catalogo: Any


@dataclass
class _ComparativoResult:
    total_hh: Any
    total_hm: Any
    dias_simulado: Any


def _executar_modo_comparativo(ui_config: _ComparativoUIConfig, exec_config: _ComparativoExecutionConfig, result: _ComparativoResult):
    # Lazy import to avoid circular dependency with orchestrator
    from .orchestrator import calcular_cronograma_inteligente

    resultado_mecanizado = None
    resultado_mecanizado_valido = False
    if ui_config.modo_comparativo and ui_config.substituicoes_comparativo:
        comparativo_cfg = exec_config.cfg.get("comparativo", {}) if isinstance(exec_config.cfg, dict) else {}
        execucao_compacta = bool(comparativo_cfg.get("execucao_compacta", True))

        df_mec = _substituir_por_mecanizado(exec_config.df_faz, ui_config.substituicoes_comparativo)
        cfg_mec = _clonar_cfg_comparativo_mecanizado(exec_config.cfg, ui_config.substituicoes_comparativo)

        n_substituicoes = 0
        for manual, mec in ui_config.substituicoes_comparativo.items():
            if (exec_config.df_faz["atividade"] == manual).any():
                n_substituicoes += (exec_config.df_faz["atividade"] == manual).sum()

        ctx_mec = {
            "modo_seq": exec_config.modo_seq,
            "usar_bloqueio_global": exec_config.usar_bloqueio_global,
            "usar_reforco_automatico": exec_config.usar_reforco_automatico,
            "usar_pool_pos_bloqueio": exec_config.usar_pool_pos_bloqueio,
            "prazo_meses": exec_config.prazo_meses,
            "mes_ref": exec_config.mes_ref,
            "ano_ref": exec_config.ano_ref,
            "data_inicio_txt": exec_config.data_inicio_txt,
            "data_fim_txt": exec_config.data_fim_txt,
            "jornada": exec_config.jornada,
            "executores": exec_config.executores,
            "turmas": exec_config.turmas,
            "preencher_orfas_template": exec_config.preencher_orfas,
            "substituicoes_template": ui_config.substituicoes_comparativo,
            "reatribuicao_template": exec_config.reatribuicao,
            "paralelo_template": exec_config.paralelo,
            "primaria_template": exec_config.primaria,
            "session_hh": ui_config.session_hh,
        }

        if execucao_compacta:
            _buf_cmp = io.StringIO()
            try:
                with redirect_stdout(_buf_cmp), redirect_stderr(_buf_cmp):
                    resultado_mecanizado = calcular_cronograma_inteligente(
                        cfg_mec,
                        df_mec,
                        exec_config.fazenda + " (MECANIZADO)",
                        esperar_enter=False,
                        ctx=ctx_mec,
                        escopo_meta=exec_config.escopo_meta,
                        atividades_catalogo=exec_config.atividades_catalogo,
                        modo_comparativo=False,
                        substituicoes_comparativo=None,
                    )
            except Exception as e:
                logger.exception("Falha ao calcular cronograma mecanizado")
                resultado_mecanizado = None
        else:
            resultado_mecanizado = calcular_cronograma_inteligente(
                cfg_mec,
                df_mec,
                exec_config.fazenda + " (MECANIZADO)",
                esperar_enter=False,
                ctx=ctx_mec,
                escopo_meta=exec_config.escopo_meta,
                atividades_catalogo=exec_config.atividades_catalogo,
                modo_comparativo=False,
                substituicoes_comparativo=None,
            )

        if isinstance(resultado_mecanizado, dict) and resultado_mecanizado.get("acao") == "retroceder_escopo":
            resultado_mecanizado = None
        elif isinstance(resultado_mecanizado, dict) and resultado_mecanizado.get("acao"):
            resultado_mecanizado = None
        elif not isinstance(resultado_mecanizado, dict):
            resultado_mecanizado = None
        else:
            chaves_obrigatorias = (
                "dias_simulado",
                "total_hh",
            )
            faltantes = [k for k in chaves_obrigatorias if k not in resultado_mecanizado]
            if faltantes:
                resultado_mecanizado = None
            else:
                resultado_mecanizado_valido = True

    return resultado_mecanizado, resultado_mecanizado_valido

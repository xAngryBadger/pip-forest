"""Phase 2: Activity linking and conflict configuration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...logging_config import get_logger

logger = get_logger(__name__)

from ...config import _merge_sequencia_defaults
from ...context import contexto_sessao
from ...de_para import aplicar_depara_padrao_exame
from ...monitor import _emitir_monitor_atual
from ...text_utils import _norm_atv
from ...turmas import _catalogo_atividades_completo
from ..linking import _configurar_conflitos_reatribuicao, _vincular_atividades_turmas


def _phase2_linking(
    setup: Dict[str, Any],
    cfg: Dict[str, Any],
    ctx: Optional[Dict[str, Any]],
    atividades_catalogo: Optional[Dict[str, Any]],
    fazenda: str,
) -> Dict[str, Any]:
    """
    Phase 2: Build activity remap, link activities to turmas, configure conflicts.
    
    Returns updated setup dict with linking results.
    """
    _batch = setup["_batch"]
    atividades_reais = setup["atividades_reais"]
    catalogo_global = setup["catalogo_global"]
    turmas = setup["turmas"]
    modo_seq = setup["modo_seq"]

    atividade_remap = _construir_atividade_remap(cfg, ctx, _batch)

    atividades_reais_set = set(atividades_reais)

    atividades_vinculadas = _vincular_atividades_turmas(
        turmas, atividades_reais, _batch, ctx, atividade_remap,
        atividades_reais_set, fazenda, modo_seq, catalogo_global,
    )
    contexto_sessao.atualizar_atividades(
        len(atividades_vinculadas), len(atividades_reais)
    )

    reatribuicao, paralelo, primaria = _configurar_conflitos_reatribuicao(
        _batch, ctx, atividade_remap, atividades_reais_set, turmas, atividades_reais,
    )

    session_hh = {}
    if ctx and isinstance(ctx.get("session_hh"), dict):
        session_hh.update(ctx["session_hh"])

    setup.update({
        "atividade_remap": atividade_remap,
        "atividades_vinculadas": atividades_vinculadas,
        "reatribuicao": reatribuicao,
        "paralelo": paralelo,
        "primaria": primaria,
        "session_hh": session_hh,
    })
    return setup


def _construir_atividade_remap(cfg: Dict[str, Any], ctx: Optional[Dict[str, Any]], _batch: bool) -> Dict[str, str]:
    """Build activity remap from config and context."""
    # This function is imported from demand module
    from ..demand import _construir_atividade_remap as _demand_construir_atividade_remap
    return _demand_construir_atividade_remap(cfg, ctx, _batch)
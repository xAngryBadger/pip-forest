"""scheduler_core package — split from the original monolith."""

_HH_EPSILON = 0.01
DIAS_UTEIS_POR_MES = 22.0
_JORNADA_DEFAULT_H = 4.6

from ..logging_config import get_logger

logger = get_logger(__name__)

from ..config import OUTPUT_DIR
from ..scheduler import _selecionar_sequencia_padrao_sn, dias_uteis_no_periodo
from ..config import _merge_sequencia_defaults

from .scheduler_loop import _SchedulerLoopConfig, _executar_scheduler_loop
from .validation import (
    _validar_input,
    _verificar_atividades_sem_executor,
    _verificar_atividades_sem_tarifa,
)
from .demand import (
    _construir_atividade_remap,
    _construir_demandas,
    _construir_filas_e_demanda_global,
)
from .diagnostics import _auditar_escopo_cronograma, _diagnostico_prazo
from .resultados import _build_resultado_final
from .display import (
    _exibir_comparativo_resultado,
    _exportar_dossier_excel,
    _mostrar_tabela_ocupacao,
    _mostrar_tabela_semanal,
)
from .linking import _configurar_conflitos_reatribuicao, _vincular_atividades_turmas
from .setup import (
    _configurar_projeto_dados,
    _configurar_projeto_interativo,
    _configurar_sequencia_bloqueio,
)
from .checkpoint import _executar_checkpoint_retroativo
from .merge import _merge_cronograma_base_e_metricas
from .mechanizado import _executar_modo_mecanizado_opcional
from .comparativo import (
    _ComparativoExecutionConfig,
    _ComparativoResult,
    _ComparativoUIConfig,
    _executar_modo_comparativo,
)
from .multi_fator import _executar_multi_fator_simulation, _render_tabela_cenarios
from .batch.setup import _configurar_equipe_template_lote, _configurar_lote_global
from .batch.run import (
    _executar_lote_continuo,
    _executar_lote_fazendas,
    _exibir_consolidado_lote,
)
from .batch.multi_equipe import (
    _agrupar_e_sugerir_equipes,
    _configurar_data_multi_equipes,
    _configurar_uma_equipe,
    _executar_multi_equipes,
    _perguntar_data_fim_equipe,
    _processar_equipes_e_consolidar,
)

from .orchestrator import calcular_cronograma_inteligente

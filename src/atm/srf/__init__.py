"""
SRF — Sistema de Restauracao Florestal v6.3
Smart Scheduler com Comparativo Manual/Mecanizado

Modular package — split from the original monolith (atm_v6_3.py).
Each submodule is a logical grouping; the original file can re-export
everything for backward compatibility.
"""

__version__ = "6.3"
__app_name__ = "SRF - Sistema de Restauracao Florestal"

# ──────────────────────────────────────────────
# CONVENIENCE RE-EXPORTS
# ──────────────────────────────────────────────

# text_utils (zero-dep pure utilities)
from .text_utils import (
    remover_acentos,
    normalizar_chave,
    _normalizar_chave_atividade_semantica,
    _candidatos_chave_atividade,
    _formatar_periodo_meta,
    _formatar_data_dia,
    _converter_dia_simulado_para_data,
    _calcular_data_fim_por_meses,
    _norm_atv,
    _slug_ficheiro_seguro,
    parse_intervalos_escolha,
    filtrar_atividades_por_texto,
    atividades_por_filtro,
)

# ui (terminal display)
from .ui import (
    G, Y, R, C, DM, BL, RS, W,
    console,
    ASCII_ART,
    VERSION,
    APP_NAME,
    linha,
    sub,
    cabecalho,
    subcabecalho,
    aviso,
    erro,
    ok,
    prompt,
    pedir_float,
    _parse_jornada,
    pedir_jornada,
    pedir_int,
    selecionar,
    selecionar_paginado,
    confirmar,
)

# config (paths, modes, sequence defaults, territory, persistence)
from .config import (
    DIR, CFGP, DOSSIER_DIRNAME, ROOT_DIR, DATA_DIR, INPUT_DIR, OUTPUT_DIR,
    PROFILES_DIR, PERFIS_DIR,
    PRECO_FINAL_JSON_DEFAULT, PRECO_FINAL_JSON_DOWNLOADS, _PRECO_FINAL_JSON_CACHE,
    MODO_SOMENTE_HH, CT_REAL_FILENAME, STG_FILENAME,
    KNOWN_COLUMNS,
    _is_legacy_mode, _is_beta_mode,
    _default_sequencia_dict, _merge_sequencia_defaults, _SEQUENCIAS_DISPONIVEIS,
    _territorio_config, _detectar_cidade_por_fazenda,
    _distribuir_fazendas_por_territorio, _calcular_equipes_territorio,
    _sugerir_config_territorio,
    carregar_config, salvar_config,
)

# constants (pure data dicts)
from .constants import (
    DEFAULT_DEPARA_EXAME_CT317,
    CT317_HARDCODE_HH_BASE,
    COMPARATIVO_MANUAL_MEC,
    _FASE_CORES_HEX,
)

# context (session state singleton)
from .context import (
    ContextoSessao,
    contexto_sessao,
    dashboard_header,
)

# monitor (external monitor bridge, graceful no-op fallback)
from .monitor import (
    init_monitor,
    _emitir_monitor_state,
    _emitir_monitor_relatorio,
    _emitir_monitor_atual,
    _emitir_monitor_rendimentos,
    _abrir_monitor_janela,
)

# Initialize monitor with the shared contexto_sessao singleton
init_monitor(contexto_sessao)

# territorio (territory validation)
from .territorio import (
    _indice_fazendas_ct,
    micro_fazendas_ausentes_na_lista_ct,
    aviso_fazendas_micro_sem_cadastro_ct,
    modulo_validar_fazendas_ct,
    fazendas_unicas_micro,
)

# cronograma (schedule builders)
from .cronograma import (
    _eh_rocada,
    construir_cronograma_humano_sem_rocada,
    construir_cronograma_robo_rocada,
    construir_cronograma_mecanizado,
    construir_cronograma_mecanizado_auto_hm_tarifa,
    construir_cronograma_humano_sem_mecanizadas,
)
from .scheduler import (
    _match_filtros_fase,
    eh_limpeza_quimica_pos_plantio,
    _fases_ordem_config,
    classificar_fase_cascata_valor,
    _demanda_plantio_talhao,
    limpeza_permitida_por_talhao,
    _min_fase_cascata,
    pode_agendar_atividade_cascata,
    diagnosticar_sequencia_atividades,
    _ha_trabalho_nao_bloqueado,
    auditar_cadeia_dados,
    _somente_bloqueado_restante,
    _mostrar_painel_hh_hm_pre_scheduler,
    menu_ajustes_hh_apenas_sessao,
    validar_e_completar_orcamento,
    dias_uteis_no_periodo,
    _selecionar_sequencia_padrao_sn,
    _distribuir_atividades_faltantes_turmas,
)
from .turmas import (
    _menu_editar_recurso_mecanizado,
    _cadastrar_recursos_mecanizados_sn,
    _catalogo_atividades_completo,
    _mostrar_catalogo_atividades,
    menu_vincular_atividades_turma,
    resolver_conflitos_e_reatribuir,
    turmas_que_executam,
    _FILTROS_NOME_CANDIDATAS_MECANIZADO,
    atividades_candidatas_mecanizado,
    sequencia_manutencao_seco_placeholder,
    sequencia_manutencao_umido_placeholder,
)
from .io import (
    encontrar_coluna,
    buscar_arquivos_excel,
    _find_default_micro_path,
    _prefer_micro_sheet,
    _find_default_ct_path,
    selecionar_arquivo,
    carregar_planilha_microplanejamento,
    _to_float_br,
    garantir_fazendas_micro_no_ct,
)
from .datas import (
    _formatar_data_dia,
    _DIAS_SEMANA_CURTO,
    _DIAS_SEMANA_COMPLETO,
    _converter_dia_simulado_para_data,
    _calcular_data_fim_por_meses,
)
from .excel_export import (
    _FASE_CORES_HEX,
    _fase_nome_pt,
    _classificar_fase_nome,
    _gerar_aba_timeline,
    _gerar_aba_cascata_explicada,
    _gerar_aba_ocupacao_turmas,
    _df_crono_operacional,
    _escrever_cronograma_e_cascata,
    _aplicar_cores_timeline_excel,
    _aplicar_cores_ocupacao_excel,
    _salvar_perfil_equipe,
    _listar_perfis_equipe,
    _carregar_perfil_equipe_menu,
    _checkpoint_editar_template,
    _recomendar_equipes_padrao,
    _imprimir_recomendacao_ep,
    _exportar_excel_consolidado_lote,
)
from .app import (
    modulo_normalizar_ct,
    modulo_importar_tarifas,
    avaliar_terreno,
    _aplicar_filtro_empresa_e_escopo,
    _selecionar_talhoes_fazenda,
    _metodologias_presentes,
    _prompt_proximas_metodologias,
    _menu_ajustar_escopo_atividades,
    _proximo_caminho_livre,
)
from .scheduler_core import (
    calcular_cronograma_inteligente,
    _executar_lote_fazendas,
    _executar_multi_equipes,
    _executar_scheduler_fazenda_interativo,
)
from .entry import (
    menu_principal,
    main,
    _cleanup_estado_sessao,
)

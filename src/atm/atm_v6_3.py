"""
SRF — Sistema de Restauracao Florestal v6.3
Smart Scheduler com Comparativo Manual/Mecanizado
Uso : python atm_v6_3.py
ATM_DEMO=1 python atm_v6_3.py
python atm_v6_3.py --demo
Modo DEMO: se existir USEESTAPLANILHAULIANOPOLIS.xlsx, gera/atualiza ulianopolisswg.xlsx;
tarifas CT 313 como no fluxo normal; [1] usa a fazenda com mais linhas (micro municipio Ulianopolis).
"""

import atexit
import calendar
import datetime
import copy
import io
import json
import math
import os
import re
import subprocess
import sys
import unicodedata
from collections import OrderedDict, defaultdict
from contextlib import redirect_stderr, redirect_stdout
from statistics import median

import pandas as pd

try:
    from srf_monitor_state import (
        append_relatorio as _monitor_append_relatorio,
    )
    from srf_monitor_state import (
        build_rendimentos_from_demandas as _monitor_build_rendimentos,
    )
    from srf_monitor_state import (
        default_state_path as _monitor_default_state_path,
    )
    from srf_monitor_state import (
        merge_emit as _monitor_merge_emit,
    )
except Exception:
    _monitor_append_relatorio = None
    _monitor_build_rendimentos = None
    _monitor_default_state_path = None
    _monitor_merge_emit = None

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("Instale: pip install rich pandas openpyxl")
    sys.exit(1)

# ──────────────────────────────────────────────
#  CORES & UI (estilo ATM v3)
# ──────────────────────────────────────────────
try:
    import colorama

    colorama.init()
    G = "\033[92m"
    Y = "\033[93m"
    R = "\033[91m"
    C = "\033[96m"
    DM = "\033[2m"
    BL = "\033[1m"
    RS = "\033[0m"
except ImportError:
    G = Y = R = C = DM = BL = RS = ""

W = 66
console = Console()


# ATM 6.1: foco operacional (atividades + HH). Valores em R$ ficam desativados temporariamente.

# Modo DEMO (Ulianópolis): ATM_DEMO=1 ou --demo
# Fonte de verdade para reconstruir o demo: USEESTAPLANILHAULIANOPOLIS.xlsx (municipio Ulianopolis)



# ──────────────────────────────────────────────
# MODULAR IMPORTS (Phase 2 — territorio + tarifas + de_para)
# ──────────────────────────────────────────────
try:
    from srf.territorio import (
        _indice_fazendas_ct,
        micro_fazendas_ausentes_na_lista_ct,
        aviso_fazendas_micro_sem_cadastro_ct,
        modulo_validar_fazendas_ct,
        fazendas_unicas_micro,
    )
    from srf.tarifas import (
        mediana_rendimento_hh,
        resolver_rendimento_hh,
        resolver_rendimento_hm,
        _to_float_json,
        _candidatos_preco_final_json,
        _score_payload_preco,
        _carregar_mapa_preco_final_json,
        _aplicar_mapa_preco_final_em_tarifas,
        _aplicar_mapa_preco_final_em_rows_by_name,
        _depara_heuristico_exame_ct317,
        _find_preco_final_sheet,
        normalizar_ct313,
        carregar_stg_tarifas,
        _to_float_any,
        resolver_chave_tarifa,
        modulo_mapeamentos_de_para,
        aviso_politica_tarifas_planas,
    )
    from srf.de_para import (
        auto_mapear_de_para,
        aplicar_depara_padrao_exame,
    )
    from srf.constants import (
        DEFAULT_DEPARA_EXAME_CT317,
        CT317_HARDCODE_HH_BASE,
        COMPARATIVO_MANUAL_MEC,
    )
    from srf.config import (
        STG_FILENAME, MODO_SOMENTE_HH, CT_REAL_FILENAME,
        DEMO_MICRO_FILENAME, DEMO_MICRO_SOURCE_FILENAME, KNOWN_COLUMNS,
        _is_demo_micro_path, _is_demo_mode, _is_legacy_mode, _is_beta_mode,
        _default_sequencia_dict, _territorio_config, _detectar_cidade_por_fazenda,
        _distribuir_fazendas_por_territorio, _calcular_equipes_territorio,
        _sugerir_config_territorio,
        DIR, CFGP, DOSSIER_DIRNAME, ROOT_DIR, DATA_DIR, INPUT_DIR, OUTPUT_DIR, PROFILES_DIR,
        PRECO_FINAL_JSON_DEFAULT, PRECO_FINAL_JSON_DOWNLOADS, _PRECO_FINAL_JSON_CACHE,
        carregar_config,
    )
    from srf.comparativo_mec import (
        _atividades_com_mecanizado_disponivel,
        _substituir_por_mecanizado,
        _formatar_substituicao_comparativo,
        _clonar_cfg_comparativo_mecanizado,
        _cadastrar_recurso_mecanizado_externo,
        _parse_lista_numeros,
        coletar_config_comparativo_multifator,
        simular_cenarios_multifator,
    )
    from srf.cronograma import (
        _eh_rocada,
        construir_cronograma_humano_sem_rocada,
        construir_cronograma_robo_rocada,
        construir_cronograma_mecanizado,
        construir_cronograma_mecanizado_auto_hm_tarifa,
        construir_cronograma_humano_sem_mecanizadas,
    )
    from srf.text_utils import (
        filtrar_atividades_por_texto,
        atividades_por_filtro,
        _norm_atv,
        _slug_ficheiro_seguro,
        normalizar_chave,
        remover_acentos,
        _normalizar_chave_atividade_semantica,
        _candidatos_chave_atividade,
        _formatar_periodo_meta,
        parse_intervalos_escolha,
    )
    from srf.ui import (
        linha, sub, cabecalho, subcabecalho, aviso, erro, ok, prompt,
        pedir_float, pedir_int, pedir_jornada,
        selecionar, selecionar_paginado, confirmar,
        _parse_jornada, W,
    )
    from srf.context import ContextoSessao, dashboard_header, contexto_sessao
    from srf.monitor import (
        _emitir_monitor_state, _emitir_monitor_relatorio,
        _emitir_monitor_atual, _emitir_monitor_rendimentos,
        _abrir_monitor_janela, _MONITOR_STATE_PATH,
    )
    from srf.scheduler import (
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
    from srf.turmas import (
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
    from srf.io import (
        encontrar_coluna,
        buscar_arquivos_excel,
        _find_default_micro_path,
        _prefer_micro_sheet,
        _find_default_ct_path,
        selecionar_arquivo,
        carregar_planilha_microplanejamento,
        _to_float_br,
        _resolver_fazenda_demo_ulianopolis,
        garantir_fazenda_ulianopolis_no_ct,
        reconstruir_demo_ulianopolis_a_partir_da_fonte,
    )
    from srf.datas import (
        _formatar_data_dia,
        _DIAS_SEMANA_CURTO,
        _DIAS_SEMANA_COMPLETO,
        _converter_dia_simulado_para_data,
        _calcular_data_fim_por_meses,
    )
    from srf.excel_export import (
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
    from srf.app import (
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
    from srf.scheduler_core import (
        calcular_cronograma_inteligente,
        _executar_lote_fazendas,
        _executar_multi_equipes,
        _executar_scheduler_fazenda_interativo,
    )
    from srf.entry import (
        menu_principal,
        main,
        _cleanup_estado_sessao,
    )
except ModuleNotFoundError:
    from .srf.territorio import (
    _indice_fazendas_ct,
    micro_fazendas_ausentes_na_lista_ct,
    aviso_fazendas_micro_sem_cadastro_ct,
    modulo_validar_fazendas_ct,
    fazendas_unicas_micro,
)
    from .srf.tarifas import (
        mediana_rendimento_hh,
        resolver_rendimento_hh,
        resolver_rendimento_hm,
        _to_float_json,
        _candidatos_preco_final_json,
        _score_payload_preco,
        _carregar_mapa_preco_final_json,
        _aplicar_mapa_preco_final_em_tarifas,
        _aplicar_mapa_preco_final_em_rows_by_name,
        _depara_heuristico_exame_ct317,
        _find_preco_final_sheet,
        normalizar_ct313,
        carregar_stg_tarifas,
        _to_float_any,
        resolver_chave_tarifa,
        modulo_mapeamentos_de_para,
        aviso_politica_tarifas_planas,
    )
    from .srf.de_para import (
        auto_mapear_de_para,
        aplicar_depara_padrao_exame,
    )
    from .srf.constants import (
        DEFAULT_DEPARA_EXAME_CT317,
        CT317_HARDCODE_HH_BASE,
        COMPARATIVO_MANUAL_MEC,
    )
    from .srf.config import (
        STG_FILENAME, MODO_SOMENTE_HH, CT_REAL_FILENAME,
        DEMO_MICRO_FILENAME, DEMO_MICRO_SOURCE_FILENAME, KNOWN_COLUMNS,
        _is_demo_micro_path, _is_demo_mode, _is_legacy_mode, _is_beta_mode,
        _default_sequencia_dict, _territorio_config, _detectar_cidade_por_fazenda,
        _distribuir_fazendas_por_territorio, _calcular_equipes_territorio,
        _sugerir_config_territorio,
        DIR, CFGP, DOSSIER_DIRNAME, ROOT_DIR, DATA_DIR, INPUT_DIR, OUTPUT_DIR, PROFILES_DIR,
        PRECO_FINAL_JSON_DEFAULT, PRECO_FINAL_JSON_DOWNLOADS, _PRECO_FINAL_JSON_CACHE,
        carregar_config,
    )
    from .srf.comparativo_mec import (
        _atividades_com_mecanizado_disponivel,
        _substituir_por_mecanizado,
        _formatar_substituicao_comparativo,
        _clonar_cfg_comparativo_mecanizado,
        _cadastrar_recurso_mecanizado_externo,
        _parse_lista_numeros,
        coletar_config_comparativo_multifator,
        simular_cenarios_multifator,
    )
    from .srf.cronograma import (
        _eh_rocada,
        construir_cronograma_humano_sem_rocada,
        construir_cronograma_robo_rocada,
        construir_cronograma_mecanizado,
        construir_cronograma_mecanizado_auto_hm_tarifa,
        construir_cronograma_humano_sem_mecanizadas,
    )
    from .srf.text_utils import (
        filtrar_atividades_por_texto,
        atividades_por_filtro,
        _norm_atv,
        _slug_ficheiro_seguro,
        normalizar_chave,
        remover_acentos,
        _normalizar_chave_atividade_semantica,
        _candidatos_chave_atividade,
        _formatar_periodo_meta,
        parse_intervalos_escolha,
    )
    from .srf.ui import (
        linha, sub, cabecalho, subcabecalho, aviso, erro, ok, prompt,
        pedir_float, pedir_int, pedir_jornada,
        selecionar, selecionar_paginado, confirmar,
        _parse_jornada, W,
    )
    from .srf.context import ContextoSessao, dashboard_header, contexto_sessao
    from .srf.monitor import (
        _emitir_monitor_state, _emitir_monitor_relatorio,
        _emitir_monitor_atual, _emitir_monitor_rendimentos,
        _abrir_monitor_janela, _MONITOR_STATE_PATH,
    )
    from .srf.scheduler import (
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
    from .srf.turmas import (
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
    from .srf.io import (
        encontrar_coluna,
        buscar_arquivos_excel,
        _find_default_micro_path,
        _prefer_micro_sheet,
        _find_default_ct_path,
        selecionar_arquivo,
        carregar_planilha_microplanejamento,
        _to_float_br,
        _resolver_fazenda_demo_ulianopolis,
        garantir_fazenda_ulianopolis_no_ct,
        reconstruir_demo_ulianopolis_a_partir_da_fonte,
    )
    from .srf.datas import (
        _formatar_data_dia,
        _DIAS_SEMANA_CURTO,
        _DIAS_SEMANA_COMPLETO,
        _converter_dia_simulado_para_data,
        _calcular_data_fim_por_meses,
    )
    from .srf.excel_export import (
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
    from .srf.app import (
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
    from .srf.scheduler_core import (
        calcular_cronograma_inteligente,
        _executar_lote_fazendas,
        _executar_multi_equipes,
        _executar_scheduler_fazenda_interativo,
    )
    from .srf.entry import (
        menu_principal,
        main,
        _cleanup_estado_sessao,
    )

atexit.register(_cleanup_estado_sessao)


if __name__ == "__main__":
    main()

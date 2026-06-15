"""SRF Config — thin re-export wrapper for orca.config"""

from src.atm.orca.config import (
    DIR, CFGP, DOSSIER_DIRNAME, ROOT_DIR, DATA_DIR, INPUT_DIR, OUTPUT_DIR,
    PROFILES_DIR, PERFIS_DIR,
    PRECO_FINAL_JSON_DEFAULT, PRECO_FINAL_JSON_DOWNLOADS,
    MODO_SOMENTE_HH, CT_REAL_FILENAME, STG_FILENAME,
    KNOWN_COLUMNS,
    modo_somente_hh,
    _is_legacy_mode, _is_beta_mode,
    _default_sequencia_dict, _merge_sequencia_defaults,
    _SEQUENCIAS_DISPONIVEIS,
    _detectar_cidade_por_fazenda, _distribuir_fazendas_por_territorio,
    _agrupar_fazendas_por_empresa, _calcular_config_empresa, _sugerir_config_empresa,
    carregar_config, salvar_config,
    _proximo_caminho_livre,
)

__all__ = [
    "DIR", "CFGP", "DOSSIER_DIRNAME", "ROOT_DIR", "DATA_DIR", "INPUT_DIR", "OUTPUT_DIR",
    "PROFILES_DIR", "PERFIS_DIR",
    "PRECO_FINAL_JSON_DEFAULT", "PRECO_FINAL_JSON_DOWNLOADS",
    "MODO_SOMENTE_HH", "CT_REAL_FILENAME", "STG_FILENAME",
    "KNOWN_COLUMNS",
    "modo_somente_hh",
    "_is_legacy_mode", "_is_beta_mode",
    "_default_sequencia_dict", "_merge_sequencia_defaults",
    "_SEQUENCIAS_DISPONIVEIS",
    "_detectar_cidade_por_fazenda", "_distribuir_fazendas_por_territorio",
    "_agrupar_fazendas_por_empresa", "_calcular_config_empresa", "_sugerir_config_empresa",
    "carregar_config", "salvar_config",
    "_proximo_caminho_livre",
]
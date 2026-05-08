"""
SRF configuration — loading, saving, sequence defaults, territory config.

Depends on: srf.text_utils (normalizar_chave)
External: os, json
"""

import json
import os

from .text_utils import normalizar_chave

# ──────────────────────────────────────────────
# PATH CONSTANTS
# ──────────────────────────────────────────────

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFGP = os.path.join(DIR, "config.json")
DOSSIER_DIRNAME = "dossiês"
ROOT_DIR = os.path.dirname(os.path.dirname(DIR))
DATA_DIR = os.path.join(ROOT_DIR, "data")
INPUT_DIR = os.path.join(DATA_DIR, "planilhas")
OUTPUT_DIR = os.path.join(DATA_DIR, DOSSIER_DIRNAME)
PROFILES_DIR = os.path.join(DATA_DIR, "perfis_equipe")
PERFIS_DIR = PROFILES_DIR  # Alias (original line 7999 in monolith)

PRECO_FINAL_JSON_DEFAULT = "preco_final.json"
PRECO_FINAL_JSON_DOWNLOADS = os.path.join(
    os.path.expanduser("~"), "Downloads", PRECO_FINAL_JSON_DEFAULT
)
_PRECO_FINAL_JSON_CACHE = {"path": "", "mtime": None, "mapa": {}}

# ATM 6.1: foco operacional (atividades + HH). Valores em R$ ficam desativados temporariamente.
MODO_SOMENTE_HH = True
CT_REAL_FILENAME = "ct317real.xlsx"
STG_FILENAME = "CT_317_NORMALIZADA.xlsx"

# Known column mapping (fallback semantico so se nenhuma bater)
KNOWN_COLUMNS = {
    "fazenda": ["NOME FAZENDA", "CODIGO FAZENDA"],
    "chave": ["CHAVE POLIGONO", "CHAVE POLIGONO"],
    "area": [
        "AREA TRABALHADA ESTIMADA (HECTARE)",
        "AREA POLIGONO (HECTARE)",
        "AREA POLIGONO (HECTARE)",
        "AREA TRABALHADA ESTIMADA (HECTARE)",
    ],
    "atividade": ["ATIVIDADES", "ATIVIDADE"],
}


# ──────────────────────────────────────────────
# MODE DETECTION
# ──────────────────────────────────────────────


def _is_legacy_mode():
    import sys as _sys

    v = os.environ.get("ATM_LEGACY", "").strip().lower()
    if v in ("1", "true", "yes", "sim", "on"):
        return True
    return "--legacy" in _sys.argv


def _is_beta_mode():
    import sys as _sys

    # Fluxo beta promovido a padrao; legado fica opt-in por flag/env.
    if _is_legacy_mode():
        return False
    v = os.environ.get("ATM_BETA", "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    return True


# ──────────────────────────────────────────────
# SEQUENCE DEFAULTS
# ──────────────────────────────────────────────


def _default_sequencia_dict():
    return {
        "modo": "implantacao",
        "offset_limpeza_quimica_dias": 30,
        "filtros_plantio": ["plantio"],
        "filtros_irrigacao": ["irrig"],
        "limpeza_quimica_filtros": ["limpeza", "quim"],
        "limpeza_quimica_exclusoes": ["impl", "impl."],
        "implantacao_outras_fase": 5.5,
        "implantacao_fases": [
            {"id": "rocada", "filtros": ["rocada", "rocada"], "exclusoes": []},
            {
                "id": "formiga",
                "filtros": ["formiga", "combate a formiga", "combate a formigas"],
                "exclusoes": [],
            },
            {"id": "coroamento", "filtros": ["coroamento", "coroa"], "exclusoes": []},
            {"id": "coveamento", "filtros": ["coveamento", "coveam"], "exclusoes": []},
            {
                "id": "adubacao_quimica",
                "filtros": ["adubacao quim", "adubacao quim", "melhora quim"],
                "exclusoes": [],
            },
        ],
        "personalizado_ordem": [],
    }


def _merge_sequencia_defaults(seq):
    """Preenche chaves ausentes em cfg['sequencia'] (muta seq)."""
    d0 = _default_sequencia_dict()
    for k, v in d0.items():
        if k not in seq:
            seq[k] = v
        elif k in ("implantacao_fases", "personalizado_ordem") and not seq[k]:
            seq[k] = v


_SEQUENCIAS_DISPONIVEIS = [
    (
        "implantacao",
        "Rocada > Formiga > Coroamento > Coveamento > Adubacao > Plantio > Irrigacao (cascata)",
    ),
    (
        "manutencao_seco",
        "[EM PROGRESSO] Manutencao periodo seco — regras ainda nao definidas",
    ),
    (
        "manutencao_umido",
        "[EM PROGRESSO] Manutencao periodo umido — regras ainda nao definidas",
    ),
    ("personalizado", "Ordem livre (sem bloqueio global plantio/irrigacao)"),
]


# ──────────────────────────────────────────────
# TERRITORY CONFIG (V6)
# ──────────────────────────────────────────────


def _territorio_config():
    """
    Configuracao de territorios/cidades para distribuicao automatica de equipes.
    """
    return {
        "cidades": {
            "acailandia": {"nome": "Acailandia"},
            "dom_eliseu": {"nome": "Dom Eliseu"},
            "cidelandia": {"nome": "Cidelandia"},
        },
        "empresas": {},
    }


def _detectar_cidade_por_fazenda(nome_fazenda: str) -> str:
    """
    Detecta a cidade/territorio baseado no nome da fazenda.
    Retorna o codigo da cidade ou None se nao detectar.
    """
    nome_norm = normalizar_chave(str(nome_fazenda))
    cidade_keywords = {
        "acailandia": ["acailandia", "acailand", "ailandia"],
        "dom_eliseu": ["dom eliseu", "eliseu", "dom_eliseu"],
        "cidelandia": ["cidelandia", "cideland", "cidelndia", "buritirana"],
    }
    for cidade, keywords in cidade_keywords.items():
        for kw in keywords:
            if kw in nome_norm:
                return cidade
    return None


def _distribuir_fazendas_por_territorio(fazendas: list) -> dict:
    """
    Distribui fazendas por territorio/cidade automaticamente.
    Retorna: (distribuicao_dict, nao_identificadas_list)
    """
    distribuicao = {"acailandia": [], "dom_eliseu": [], "cidelandia": []}
    nao_identificadas = []

    for faz in fazendas:
        cidade = _detectar_cidade_por_fazenda(faz)
        if cidade:
            distribuicao[cidade].append(faz)
        else:
            nao_identificadas.append(faz)

    return distribuicao, nao_identificadas


def _calcular_equipes_territorio(cidade: str, empresa: str = "auto") -> dict:
    """
    Calcula configuracao de equipes para um territorio.
    empresa: nome da empresa (deve existir em cfg_territorio["empresas"]) ou "auto"
    """
    cfg_territorio = _territorio_config()
    if cidade not in cfg_territorio["cidades"]:
        return None

    info_cidade = cfg_territorio["cidades"][cidade]

    if empresa == "auto":
        if not cfg_territorio["empresas"]:
            return None
        empresa = next(iter(cfg_territorio["empresas"]))

    if empresa not in cfg_territorio["empresas"]:
        return None

    info_empresa = cfg_territorio["empresas"][empresa]
    n_equipes = info_empresa["equipes_por_cidade"].get(cidade, 1)
    operarios_por_eq = info_empresa["operarios_por_equipe"]
    coordenadores = info_empresa["coordenadores_por_equipe"]
    total_por_eq = operarios_por_eq + coordenadores

    return {
        "cidade": cidade,
        "nome_cidade": info_cidade["nome"],
        "empresa": empresa,
        "nome_empresa": info_empresa["nome"],
        "n_equipes": n_equipes,
        "operarios_por_equipe": operarios_por_eq,
        "coordenadores_por_equipe": coordenadores,
        "total_por_equipe": total_por_eq,
        "total_operarios": n_equipes * operarios_por_eq,
        "total_coordenadores": n_equipes * coordenadores,
        "total_geral": n_equipes * total_por_eq,
    }


def _sugerir_config_territorio(fazendas: list, modo_simplificado: bool = True) -> dict:
    """
    Sugere configuracao completa de equipes baseada na distribuicao de fazendas.
    """
    distribuicao, nao_id = _distribuir_fazendas_por_territorio(fazendas)
    sugestoes = []

    for cidade, fazs in distribuicao.items():
        if not fazs:
            continue
        config = _calcular_equipes_territorio(cidade)
        if config:
            config["fazendas"] = fazs
            config["n_fazendas"] = len(fazs)
            sugestoes.append(config)

    return {
        "distribuicao": distribuicao,
        "nao_identificadas": nao_id,
        "sugestoes": sugestoes,
        "total_equipes": sum(s["n_equipes"] for s in sugestoes),
        "total_operarios": sum(s["total_operarios"] for s in sugestoes),
    }


# ──────────────────────────────────────────────
# CONFIG PERSISTENCE
# ──────────────────────────────────────────────


def carregar_config():
    """Load (or create) config.json, apply defaults, apply preco_final overrides if available."""
    if not os.path.exists(CFGP):
        with open(CFGP, "w", encoding="utf-8") as f:
            json.dump({"de_para": {}, "tarifas": {}, "atividades": {}}, f)
    with open(CFGP, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for k in ("de_para", "tarifas", "atividades"):
        if k not in cfg:
            cfg[k] = {}
    if "orcamento_estrito" not in cfg:
        cfg["orcamento_estrito"] = True
    if "filtros_bloqueio_global" not in cfg:
        cfg["filtros_bloqueio_global"] = ["plantio", "irrig"]
    if "fazendas_ct" not in cfg:
        cfg["fazendas_ct"] = []
    if "sequencia" not in cfg or not isinstance(cfg.get("sequencia"), dict):
        cfg["sequencia"] = {}
    _merge_sequencia_defaults(cfg["sequencia"])
    if "preco_final_json_path" not in cfg:
        cfg["preco_final_json_path"] = ""
    if "comparativo" not in cfg or not isinstance(cfg.get("comparativo"), dict):
        cfg["comparativo"] = {}
    if "execucao_compacta" not in cfg["comparativo"]:
        cfg["comparativo"]["execucao_compacta"] = True
    # NOTE: preco_final JSON loading depends on tarifas sub-system;
    # the caller (original monolith) handles this inline.
    # When full modularization is complete, this will be a hook.
    return cfg


def salvar_config(cfg):
    """Persist cfg to config.json."""
    with open(CFGP, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

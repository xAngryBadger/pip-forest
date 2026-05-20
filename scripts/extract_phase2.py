#!/usr/bin/env python3
"""
Phase 2 extraction: territorio + tarifas + de_para
Creates srf modules and patches monolith.
"""
import os, ast, sys

BASE = os.path.join(os.path.dirname(__file__), "src", "atm")
MONO = os.path.join(BASE, "atm_v6_3.py")
SRF = os.path.join(BASE, "srf")

def read_mono():
    with open(MONO, "r", encoding="utf-8") as f:
        return f.readlines()

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def extract_lines(lines, start, end):
    return "".join(lines[start-1:end])

lines = read_mono()
original_count = len(lines)
print(f"Monolith: {original_count} lines")

# ──────────────────────────────────────────────
# 1a. territorio.py
# ──────────────────────────────────────────────
territorio_funcs = [
    ("_indice_fazendas_ct", 3780, 3791),
    ("micro_fazendas_ausentes_na_lista_ct", 3793, 3806),
    ("aviso_fazendas_micro_sem_cadastro_ct", 3808, 3834),
    ("modulo_validar_fazendas_ct", 3836, 3938),
]

territorio_code = "".join(extract_lines(lines, s, e) for _, s, e in territorio_funcs)

territorio_module = '''\
"""Territorio — validacao de fazendas CT vs microplanejamento."""

from .config import salvar_config
from .ui import sub, aviso, ok, prompt, confirmar, selecionar_paginado, G, C, Y, DM, RS
from .text_utils import normalizar_chave
from .context import dashboard_header, subcabecalho

''' + territorio_code

write_file(os.path.join(SRF, "territorio.py"), territorio_module)
print("Written srf/territorio.py")

# ──────────────────────────────────────────────
# 1b. tarifas.py
# ──────────────────────────────────────────────
# modulo_importar_tarifas references encontrar_coluna and selecionar_arquivo
# which aren't extracted yet (they're in io_loading). For now, the tarifas
# module will import them from the monolith at runtime, OR we defer 
# modulo_importar_tarifas extraction. Actually - modulo_importar_tarifas
# uses encontrar_coluna (line 2914) and selecionar_arquivo (line 2898).
# selecionar_arquivo starts at 2566 and is huge. Let's keep modulo_importar_tarifas
# in the monolith for now and only extract the pure tarifas functions.

# Check: what does modulo_importar_tarifas use?
# - dashboard_header, subcabecalho, selecionar_arquivo, encontrar_coluna, 
#   selecionar_paginado, confirmar, aviso, ok, erro, prompt, sub,
#   resolver_rendimento_hh, salvar_config, G, C, Y, DM, BL, RS
# selecionar_arquivo is NOT yet extracted. So we'll skip modulo_importar_tarifas
# for now and add it in Phase 4 (io_loading).

# Similarly, modulo_normalizar_ct uses selecionar_arquivo (line 2248).
# We need to handle this carefully.

# Decision: Extract modulo_importar_tarifas to tarifas BUT make it import
# selecionar_arquivo lazily or from a future io_loading module.
# Actually, the simplest approach: don't extract modulo_importar_tarifas and
# modulo_normalizar_ct yet since they depend on selecionar_arquivo.
# We'll extract them with io_loading.

# For now, extract the PURE tarifas functions (no selecionar_arquivo dependency)

tarifas_funcs = [
    ("mediana_rendimento_hh", 1226, 1245),
    ("resolver_rendimento_hh", 1248, 1295),
    ("resolver_rendimento_hm", 1297, 1322),
    ("_to_float_json", 1672, 1692),
    ("_candidatos_preco_final_json", 1694, 1714),
    ("_score_payload_preco", 1716, 1721),
    ("_carregar_mapa_preco_final_json", 1723, 1833),
    ("_aplicar_mapa_preco_final_em_tarifas", 1835, 1917),
    ("_aplicar_mapa_preco_final_em_rows_by_name", 1919, 1999),
    ("_depara_heuristico_exame_ct317", 2001, 2008),
    ("_find_preco_final_sheet", 2011, 2017),
    ("normalizar_ct313", 2019, 2218),
    ("carregar_stg_tarifas", 2220, 2242),
    ("_to_float_any", 2276, 2295),
    ("resolver_chave_tarifa", 2296, 2347),
    ("modulo_mapeamentos_de_para", 2349, 2447),
    ("aviso_politica_tarifas_planas", 2983, 3006),
]

tarifas_code = "".join(extract_lines(lines, s, e) for _, s, e in tarifas_funcs)

tarifas_module = '''\
"""Tarifas — resolucao de rendimento, CT317 normalizer, de-para CRUD, precos."""

import copy
import datetime
import json
import math
import os
from statistics import median

import pandas as pd

from .config import (
    INPUT_DIR, PRECO_FINAL_JSON_DEFAULT, PRECO_FINAL_JSON_DOWNLOADS,
    _PRECO_FINAL_JSON_CACHE, MODO_SOMENTE_HH, STG_FILENAME,
    CT_REAL_FILENAME, salvar_config, carregar_config,
)
from .constants import CT317_HARDCODE_HH_BASE, DEFAULT_DEPARA_EXAME_CT317
from .ui import (
    G, Y, C, DM, BL, RS,
    sub, aviso, ok, erro, prompt, pedir_float,
    confirmar, selecionar, selecionar_paginado, subcabecalho,
)
from .text_utils import normalizar_chave, remover_acentos
from .context import dashboard_header

''' + tarifas_code

write_file(os.path.join(SRF, "tarifas.py"), tarifas_module)
print("Written srf/tarifas.py")

# ──────────────────────────────────────────────
# 1c. de_para.py
# ──────────────────────────────────────────────
de_para_funcs = [
    ("auto_mapear_de_para", 4722, 4761),
    ("aplicar_depara_padrao_exame", 4763, 4788),
]

de_para_code = "".join(extract_lines(lines, s, e) for _, s, e in de_para_funcs)

de_para_module = '''\
"""De-para — auto-mapping e aplicacao de mapeamento padrao EXAME->CT317."""

from .config import salvar_config
from .constants import DEFAULT_DEPARA_EXAME_CT317
from .text_utils import normalizar_chave, _candidatos_chave_atividade
from .tarifas import _depara_heuristico_exame_ct317

''' + de_para_code

write_file(os.path.join(SRF, "de_para.py"), de_para_module)
print("Written srf/de_para.py")

# ──────────────────────────────────────────────
# Verify syntax of all new modules
# ──────────────────────────────────────────────
for mod in ["territorio.py", "tarifas.py", "de_para.py"]:
    path = os.path.join(SRF, mod)
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    try:
        ast.parse(src)
        print(f"srf/{mod} syntax: OK ({len(src.splitlines())} lines)")
    except SyntaxError as e:
        print(f"srf/{mod} syntax ERROR: {e}")
        sys.exit(1)

# ──────────────────────────────────────────────
# Patch the monolith
# ──────────────────────────────────────────────
# Strategy: Mark lines to remove, then add import blocks.
# We need to be careful about the ordering.

# Lines to remove from monolith (1-indexed, inclusive)
remove_ranges = []

# Territory functions
for _, s, e in territorio_funcs:
    remove_ranges.append((s, e))

# Tarifas functions (only the ones we extracted)
for _, s, e in tarifas_funcs:
    remove_ranges.append((s, e))

# De_para functions
for _, s, e in de_para_funcs:
    remove_ranges.append((s, e))

# Inline constants block (lines 1324-1541): section comment + STG_FILENAME + 
# DEFAULT_DEPARA_EXAME_CT317 + CT317_HARDCODE_HH_BASE + COMPARATIVO_MANUAL_MEC
# These are already in srf/constants.py and srf/config.py
remove_ranges.append((1324, 1541))

# modulo_normalizar_ct (2244-2273) - we extracted this in tarifas
# It's already in the tarifas_funcs list

# Sort and merge overlapping ranges
remove_ranges.sort()

# Build set of lines to remove
lines_to_remove = set()
for s, e in remove_ranges:
    for i in range(s, e + 1):
        lines_to_remove.add(i)

# Build new monolith
new_lines = []
for i, line in enumerate(lines, 1):
    if i not in lines_to_remove:
        new_lines.append(line)

# Find insertion point: right before the first function def
insert_idx = None
for i, line in enumerate(new_lines):
    stripped = line.lstrip()
    if stripped.startswith("def ") and not line.startswith(" ") and not line.startswith("\t"):
        insert_idx = i
        break

if insert_idx is None:
    print("ERROR: Could not find insertion point")
    sys.exit(1)

# Build the import block to insert
import_block = """
# ──────────────────────────────────────────────
# MODULAR IMPORTS (Phase 2 — territorio + tarifas + de_para)
# ──────────────────────────────────────────────
from srf.territorio import (
    _indice_fazendas_ct,
    micro_fazendas_ausentes_na_lista_ct,
    aviso_fazendas_micro_sem_cadastro_ct,
    modulo_validar_fazendas_ct,
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
    modulo_normalizar_ct,
    _to_float_any,
    resolver_chave_tarifa,
    modulo_mapeamentos_de_para,
    aviso_politica_tarifas_planas,
)
from srf.de_para import (
    auto_mapear_de_para,
    aplicar_depara_padrao_exame,
)

"""

new_lines.insert(insert_idx, import_block)

# Write modified monolith
new_content = "".join(new_lines)
write_file(MONO, new_content)
print(f"Patched monolith: now {len(new_lines)} lines (was {original_count})")

# Verify monolith syntax
try:
    ast.parse(new_content)
    print("Monolith syntax: OK")
except SyntaxError as e:
    print(f"Monolith syntax ERROR: {e}")
    sys.exit(1)

print("\nPhase 2 extraction complete!")

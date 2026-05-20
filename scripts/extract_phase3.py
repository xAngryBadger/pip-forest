#!/usr/bin/env python3
"""Phase 3 extraction: comparativo_mec"""
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
print(f"Monolith: {len(lines)} lines")

comparativo_funcs = [
    ("_atividades_com_mecanizado_disponivel", 1308, 1318),
    ("_substituir_por_mecanizado", 1320, 1348),
    ("_formatar_substituicao_comparativo", 1350, 1365),
    ("_clonar_cfg_comparativo_mecanizado", 1367, 1409),
    ("_cadastrar_recurso_mecanizado_externo", 1411, 1436),
    ("_parse_lista_numeros", 2693, 2708),
    ("coletar_config_comparativo_multifator", 2710, 2730),
    ("simular_cenarios_multifator", 2732, 2787),
]

comparativo_code = "".join(extract_lines(lines, s, e) for _, s, e in comparativo_funcs)

comparativo_module = '''\
"""Comparativo mecanizado — substituicao manual/mec, cenarios multi-fator."""

import copy
import math

from .constants import COMPARATIVO_MANUAL_MEC
from .ui import sub, C, BL, RS, aviso, ok, prompt, pedir_float

''' + comparativo_code

write_file(os.path.join(SRF, "comparativo_mec.py"), comparativo_module)
print("Written srf/comparativo_mec.py")

# Verify syntax
with open(os.path.join(SRF, "comparativo_mec.py"), "r", encoding="utf-8") as f:
    src = f.read()
try:
    ast.parse(src)
    print(f"srf/comparativo_mec.py syntax: OK ({len(src.splitlines())} lines)")
except SyntaxError as e:
    print(f"srf/comparativo_mec.py syntax ERROR: {e}")
    sys.exit(1)

# Patch monolith: remove extracted lines
lines_to_remove = set()
for _, s, e in comparativo_funcs:
    for i in range(s, e + 1):
        lines_to_remove.add(i)

new_lines = [line for i, line in enumerate(lines, 1) if i not in lines_to_remove]

# Add imports in the Phase 2 import block area
# Find the "from srf.de_para" or "from .srf.de_para" lines
insert_text = """from srf.comparativo_mec import (
    _atividades_com_mecanizado_disponivel,
    _substituir_por_mecanizado,
    _formatar_substituicao_comparativo,
    _clonar_cfg_comparativo_mecanizado,
    _cadastrar_recurso_mecanizado_externo,
    _parse_lista_numeros,
    coletar_config_comparativo_multifator,
    simular_cenarios_multifator,
)
"""

# Find the end of the try block (before "except ModuleNotFoundError")
found_try = False
found_except = False
insert_done = False
final_lines = []
for i, line in enumerate(new_lines):
    final_lines.append(line)
    if not insert_done:
        if 'from srf.constants import' in line or 'from .srf.constants import' in line:
            # Insert after the constants import block closes
            # Look ahead for the closing paren
            pass
        if 'from srf.config import STG_FILENAME' in line:
            final_lines.append(insert_text)
            insert_done = True

# Also add to except branch
if not insert_done:
    # Fallback: find a good insertion point
    for i, line in enumerate(new_lines):
        if 'from .srf.config import STG_FILENAME' in line:
            new_lines.insert(i + 1, insert_text)
            insert_done = True
            break

if not insert_done:
    print("ERROR: Could not find insertion point for comparativo_mec imports")
    sys.exit(1)

# Write monolith
new_content = "".join(final_lines)
write_file(MONO, new_content)
print(f"Patched monolith: {len(final_lines)} lines")

try:
    ast.parse(new_content)
    print("Monolith syntax: OK")
except SyntaxError as e:
    print(f"Monolith syntax ERROR: {e}")
    sys.exit(1)

print("Phase 3 extraction complete!")

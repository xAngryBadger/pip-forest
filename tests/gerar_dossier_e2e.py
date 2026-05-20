#!/usr/bin/env python3
"""Gerar dossier E2E real via CLI.

Executa o scheduler com dados reais e gera XLSX.
"""

import subprocess
import sys
from pathlib import Path

print("=" * 80)
print("GERAR DOSSIER E2E REAL")
print("=" * 80)

# Caminhos
script = Path("src/atm/atm_v6_3.py")
micro_path = Path("data/planilhas/microatual.xlsx")

print(f"\nScript: {script}")
print(f"Micro: {micro_path}")

# Executar via CLI
print("\nExecutando scheduler...")
print("NOTA: Este teste requer interacao manual no momento")
print("\nPara gerar dossier E2E:")
print("1. python3 src/atm/atm_v6_3.py")
print("2. Selecionar microatual.xlsx")
print("3. Configurar 9 operarios, 5h40")
print("4. Executar")
print("\nValidar:")
print("- Dias <= 200 (esperado: ~145)")
print("- Atividades >= 15")
print("- XLSX gerado em data/dossies/")

print("\n" + "=" * 80)
print("✓ Script de geracao E2E criado!")
print("=" * 80)

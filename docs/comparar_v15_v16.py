#!/usr/bin/env python3
"""Comparar CASCATA_EXPLICADA de v15 e v16 para validar correção."""

import pandas as pd

print("=" * 80)
print("COMPARACAO V15 (CORRETO) vs V16 (QUEBRADO)")
print("=" * 80)

# Carregar dados
v15_cascata = pd.read_excel('data/dossiês/Dossier_FORMOSA__FAZENDA_TODOS_OPERACIONAL_v15.xlsx', sheet_name='CASCATA_EXPLICADA')
v16_cascata = pd.read_excel('data/dossiês/Dossier_FORMOSA__FAZENDA_TODOS_OPERACIONAL_v16.xlsx', sheet_name='CASCATA_EXPLICADA')

# V15 resumo
v15_resumo = pd.read_excel('data/dossiês/Dossier_FORMOSA__FAZENDA_TODOS_OPERACIONAL_v15.xlsx', sheet_name='RESUMO_OPERACIONAL')
v16_resumo = pd.read_excel('data/dossiês/Dossier_FORMOSA__FAZENDA_TODOS_OPERACIONAL_v16.xlsx', sheet_name='RESUMO_OPERACIONAL')

print("\n=== RESUMO ===")
print(f"V15: {v15_resumo[v15_resumo['Metrica'] == 'Duracao Simulada (dias uteis)']['Valor'].values[0]} dias")
print(f"V16: {v16_resumo[v16_resumo['Metrica'] == 'Duracao Simulada (dias uteis)']['Valor'].values[0]} dias")

# Analise do Dia 1
print("\n=== DIA 1 ===")
print("\nV15 - Dia 1 (ordem correta):")
v15_dia1 = v15_cascata[v15_cascata['Dia'] == 1][['Talhao', 'Atividade', 'HH_Atividade_Consumido']]
print(v15_dia1.to_string())

print("\nV16 - Dia 1 (ordem quebrada):")
v16_dia1 = v16_cascata[v16_cascata['Dia'] == 1][['Talhao', 'Atividade', 'HH_Atividade_Consumido']]
print(v16_dia1.to_string())

# Verificar se ROCADA vem antes de PREPARO
print("\n=== ANALISE DE ORDEM ===")
v15_first = v15_dia1.iloc[0]['Atividade'] if len(v15_dia1) > 0 else "N/A"
v16_first = v16_dia1.iloc[0]['Atividade'] if len(v16_dia1) > 0 else "N/A"

print(f"V15 primeira atividade: {v15_first}")
print(f"V16 primeira atividade: {v16_first}")

if "ROCADA" in v15_first and "ROCADA" in v16_first:
    print("✓ Ambos começam com ROCADA")
elif "ROCADA" in v15_first and "ROCADA" not in v16_first:
    print("✗ V16 está QUEBRADO: não começa com ROCADA")
elif "PREPARO" in v16_first:
    print("✗ V16 está QUEBRADO: começa com PREPARO ao invés de ROCADA")

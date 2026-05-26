# PLANO DE TESTES E2E PERMANENTE - SRF CLI

## Visão Geral
Este documento descreve o modelo de testes E2E permanente para validar todas as funcionalidades do CLI após cada mudança.

## Configuração Padrão de Teste

### Parâmetros Base
```python
CONFIG_PADRAO = {
    "executores": 9,
    "jornada": 5.67,  # 5h40 = 5.67 horas
    "prazo_meses": 6,
    "mes_ref": 5,
    "ano_ref": 2026,
    "dia_ref": 1,
}
```

### Estrutura de Teste
Cada teste E2E deve validar:
1. ✅ Import do scheduler
2. ✅ Carregamento de dados (microatual.xlsx + ct317real.xlsx)
3. ✅ Execução do scheduler (batch mode)
4. ✅ Validação do resultado (dias, atividades, HH)
5. ✅ Geração de dossier (opcional)

---

## Modelo de Teste 1: Time Único, Todas as Atividades

### Objetivo
Validar que um único time executa TODAS as atividades em sequência.

### Configuração
```python
TESTE_1 = {
    "nome": "Time único - todas as atividades",
    "executores": 9,
    "jornada": 5.67,
    "turmas": [
        {
            "nome": "Time Geral",
            "operarios": 9,
            "atividades": ["todas"]  # Todas as atividades
        }
    ],
    "resultado_esperado": {
        "dias_max": 200,  # Baseado em v15: 145 dias
        "atividades_min": 15,
        "hh_total_min": 7000
    }
}
```

### Validações
- [ ] Scheduler completa sem erros
- [ ] Dias ≤ 200
- [ ] Atividades ≥ 15
- [ ] HH total ≥ 7000
- [ ] Cascata respeitada (ROCADA antes de PREPARO)

---

## Modelo de Teste 2: Dois Times, Atividades Distintas

### Objetivo
Validar que dois times com atividades distintas não conflitam.

### Configuração
```python
TESTE_2 = {
    "nome": "Dois times - atividades distintas",
    "executores": 9,
    "jornada": 5.67,
    "turmas": [
        {
            "nome": "Time Roçada",
            "operarios": 5,
            "atividades": ["ROCADA MANUAL", "COMBATE FORMIGA"]
        },
        {
            "nome": "Time Plantio",
            "operarios": 4,
            "atividades": ["PLANTIO", "ADUBACAO"]
        }
    ],
    "prioridades": {
        "Time Roçada": 1,  # Prioridade maior
        "Time Plantio": 2  # Prioridade menor (depende de roçada)
    },
    "resultado_esperado": {
        "dias_max": 180,
        "atividades_min": 14,
        "conflitos": 0
    }
}
```

### Validações
- [ ] Time Roçada começa primeiro (prioridade 1)
- [ ] Time Plantio espera roçada completar
- [ ] Sem conflitos de sobreposição
- [ ] Dias ≤ 180
- [ ] Atividades ≥ 14

---

## Modelo de Teste 3: Cascata com Bloqueio Global

### Objetivo
Validar que o bloqueio global (plantio/irrigação) funciona corretamente.

### Configuração
```python
TESTE_3 = {
    "nome": "Cascata com bloqueio global",
    "executores": 9,
    "jornada": 5.67,
    "usar_bloqueio_global": True,
    "filtros_bloqueio": ["plantio", "irrig"],
    "turmas": [
        {
            "nome": "Time Geral",
            "operarios": 9,
            "atividades": ["todas"]
        }
    ],
    "resultado_esperado": {
        "dias_max": 200,
        "atividades_min": 15,
        "bloqueio_respeitado": True
    }
}
```

### Validações
- [ ] Plantio/irrigação bloqueados até resto completar
- [ ] Cascata respeitada
- [ ] Dias ≤ 200
- [ ] Atividades ≥ 15

---

## Modelo de Teste 4: Múltiplas Fazendas

### Objetivo
Validar scheduler com múltiplas fazendas simultâneas.

### Configuração
```python
TESTE_4 = {
    "nome": "Múltiplas fazendas",
    "executores": 9,
    "jornada": 5.67,
    "fazendas": ["CONQUISTADORA VLF", "SENHOR DO BOMFIM 1"],
    "turmas": [
        {
            "nome": "Time Multi",
            "operarios": 9,
            "fazendas": ["todas"]
        }
    ],
    "resultado_esperado": {
        "dias_max": 250,
        "atividades_min": 28,  # 14 por fazenda
        "fazendas_processadas": 2
    }
}
```

### Validações
- [ ] Todas as fazendas processadas
- [ ] Sem sobreposição entre fazendas
- [ ] Dias ≤ 250
- [ ] Atividades ≥ 28

---

## Script de Execução de Testes

```python
#!/usr/bin/env python3
"""Executar todos os testes E2E permanentes."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_e2e_permanente import (
    TesteTimeUnico,
    TesteDoisTimes,
    TesteBloqueioGlobal,
    TesteMultiplasFazendas
)

if __name__ == '__main__':
    # Configurar loader
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Adicionar todos os testes
    suite.addTests(loader.loadTestsFromTestCase(TesteTimeUnico))
    suite.addTests(loader.loadTestsFromTestCase(TesteDoisTimes))
    suite.addTests(loader.loadTestsFromTestCase(TesteBloqueioGlobal))
    suite.addTests(loader.loadTestsFromTestCase(TesteMultiplasFazendas))
    
    # Executar
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Relatório
    print("\n" + "=" * 80)
    print("RELATÓRIO DE TESTES E2E")
    print("=" * 80)
    print(f"Total: {result.testsRun} testes")
    print(f"Aprovados: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Falhas: {len(result.failures)}")
    print(f"Erros: {len(result.errors)}")
    
    if result.failures:
        print("\nFalhas:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nErros:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    # Exit code
    sys.exit(0 if result.wasSuccessful() else 1)
```

---

## Execução

### Teste Rápido (CI/CD)
```bash
# Rodar apenas teste de cascata (crítico)
python3 -m unittest tests.test_cascata_global -v

# Duração: ~1 segundo
# Validação: Lógica de cascata GLOBAL
```

### Teste Completo (E2E)
```bash
# Rodar todos os testes E2E
python3 tests/run_all_e2e.py

# Duração: ~5-10 minutos
# Validação: Todas as funcionalidades
```

### Teste Específico
```bash
# Rodar apenas teste de time único
python3 -m unittest tests.test_e2e_permanente.TesteTimeUnico -v

# Rodar apenas teste de dois times
python3 -m unittest tests.test_e2e_permanente.TesteDoisTimes -v
```

---

## Critérios de Aprovação

### Mínimos (Obrigatórios)
- [ ] Todos os testes passam (100%)
- [ ] Dias ≤ 200 (baseado em v15: 145 dias)
- [ ] Atividades ≥ 15/16
- [ ] Sem erros de execução
- [ ] Cascata respeitada

### Desejáveis
- [ ] Dias ≤ 150 (otimizado)
- [ ] 16/16 atividades agendadas
- [ ] HH total dentro de 10% do esperado
- [ ] Sem avisos/críticas no log

### Críticos (Bloqueantes)
- [ ] Erro de import
- [ ] Erro de sintaxe
- [ ] Erro de execução (crash)
- [ ] Dias > 500 (regressão grave)
- [ ] Atividades < 10 (regressão grave)

---

## Integração Contínua

### GitHub Actions
```yaml
name: Testes E2E

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Instalar dependências
        run: |
          pip install -r requirements.txt
          pip install pandas openpyxl
      
      - name: Teste de cascata (crítico)
        run: python3 -m unittest tests.test_cascata_global -v
      
      - name: Testes E2E completos
        run: python3 tests/run_all_e2e.py
      
      - name: Upload resultados
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: resultados-testes
          path: |
            data/dossiês/*.xlsx
            tests/*.log
```

---

## Dados de Teste

### Planilhas
- **Microplanejamento**: `data/planilhas/microatual.xlsx`
  - Sheet: `MICROPL_IMPL_ABR_JUN_V5` (661 linhas)
  - Colunas necessárias: DATA, CÓDIGO FAZENDA, NOME FAZENDA, CHAVE POLÍGONO, ATIVIDADES, ÁREA POLÍGONO (HECTARE)

- **Custos**: `data/planilhas/ct317real.xlsx`
  - Sheet: `Preço Final` (106 linhas)
  - Colunas necessárias: N, OPERAÇÕES, Rendimento HH/ha, Custo Hora, PREÇO R$

### Golden Files
- **Referência**: `data/dossiês/Dossier_FORMOSA__FAZENDA_TODOS_OPERACIONAL_v15.xlsx`
  - Dias: 145
  - Atividades: 15/16
  - HH Total: 7,824.2

---

## Manutenção

### Atualizar Testes
Sem que mudar:
1. Estrutura de dados (novas colunas)
2. Regras de negócio (novas fases)
3. Configuração padrão (executores, jornada)

### Atualizar Golden Files
Sem que:
1. Mudar planilha de entrada (microatual.xlsx)
2. Mudar regras de cascata
3. Adicionar/remover atividades

### Frequência
- **Testes rápidos**: Todo commit
- **Testes completos**: Todo PR
- **Golden files**: Todo mês ou quando mudar dados

---

## Responsáveis

| Função | Responsável |
|--------|-------------|
| Criação dos testes | Time de desenvolvimento |
| Execução CI/CD | GitHub Actions |
| Revisão de falhas | Desenvolvedor do PR |
| Atualização golden files | Tech Lead |
| Manutenção | Time de QA |

---

**Status**: ✅ Plano definido  
**Data**: 19/mai/2026  
**Próxima Ação**: Implementar testes no arquivo `tests/test_e2e_permanente.py`

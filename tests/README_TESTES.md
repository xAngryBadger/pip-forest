# TESTES E2E PERMANENTES - SRF CLI

## Visão Geral
Conjunto de testes E2E permanentes para validar todas as funcionalidades do CLI após cada mudança.

## Configuração Padrão
```python
{
    "executores": 9,          # 9 operários
    "jornada": 5.67,          # 5h40 = 5.67 horas
    "prazo_meses": 6,
    "mes_ref": 5,
    "ano_ref": 2026,
    "dia_ref": 1,
}
```

## Testes Implementados

### 1. TesteValidacaoDados
**Objetivo**: Validar dados de entrada

**O que testa**:
- `microatual.xlsx` carrega (661 linhas)
- `ct317real.xlsx` carrega (106 linhas)
- Colunas necessárias presentes

**Execução**:
```bash
python3 -m unittest tests.test_e2e_permanente.TesteValidacaoDados -v
```

### 2. TesteCascataGlobal
**Objetivo**: Validar cascata GLOBAL (N+1)

**O que testa**:
- Fase N+1 só quando TODOS completam fase N
- MIN GLOBAL extraído corretamente
- Sem violação de cascata

**Execução**:
```bash
python3 -m unittest tests.test_e2e_permanente.TesteCascataGlobal -v
```

### 3. TesteTimeUnico
**Objetivo**: 1 time executa TODAS as atividades

**Configuração**:
- 9 operários, 5h40 jornada
- 1 time: todas as atividades

**Valida**:
- Dias ≤ 200 (v15: 145 dias)
- Atividades ≥ 15
- HH total ≥ 7000

**Execução**:
```bash
python3 -m unittest tests.test_e2e_permanente.TesteTimeUnico -v
```

### 4. TesteDoisTimes
**Objetivo**: 2 times com atividades distintas

**Configuração**:
- Time Roçada (5 operários): ROCADA, COMBATE FORMIGA
- Time Plantio (4 operários): PLANTIO, ADUBACAO
- Prioridade: Roçada > Plantio

**Valida**:
- Time Roçada começa primeiro
- Time Plantio espera roçada
- Sem conflitos
- Dias ≤ 180

**Execução**:
```bash
python3 -m unittest tests.test_e2e_permanente.TesteDoisTimes -v
```

### 5. TesteBloqueioGlobal
**Objetivo**: Bloqueio global de plantio/irrigação

**Configuração**:
- Bloqueio global: ATIVADO
- Filtros: ["plantio", "irrig"]
- 1 time: todas as atividades

**Valida**:
- Plantio/irrigação bloqueados até resto completar
- Cascata respeitada
- Dias ≤ 200

**Execução**:
```bash
python3 -m unittest tests.test_e2e_permanente.TesteBloqueioGlobal -v
```

### 6. TesteMultiplasFazendas
**Objetivo**: Múltiplas fazendas simultâneas

**Configuração**:
- 2 fazendas: CONQUISTADORA VLF, SENHOR DO BOMFIM 1
- 1 time: todas as fazendas

**Valida**:
- Todas as fazendas processadas
- Sem sobreposição
- Dias ≤ 250

**Execução**:
```bash
python3 -m unittest tests.test_e2e_permanente.TesteMultiplasFazendas -v
```

## Executar Todos os Testes

### Rápido (CLI)
```bash
python3 tests/run_all_e2e.py
# Duração: ~1 segundo
# 10 testes
```

### Completo (CI/CD)
```bash
# GitHub Actions roda automaticamente em push/PR
# Ver: .github/workflows/testes-e2e.yml
```

## Critérios de Aprovação

### Mínimos (Obrigatórios)
- ✅ 100% dos testes passam
- ✅ Dias ≤ 200 (baseado em v15: 145 dias)
- ✅ Atividades ≥ 15/16
- ✅ Sem erros de execução
- ✅ Cascata respeitada

### Desejáveis
- Dias ≤ 150 (otimizado)
- 16/16 atividades agendadas
- HH total dentro de 10% do esperado
- Sem avisos/críticas no log

### Críticos (Bloqueantes)
- ❌ Erro de import
- ❌ Erro de sintaxe
- ❌ Erro de execução (crash)
- ❌ Dias > 500 (regressão grave)
- ❌ Atividades < 10 (regressão grave)

## CI/CD (GitHub Actions)

### Workflow
```yaml
name: Testes E2E
on: [push, pull_request]
jobs:
  testes:
    runs-on: ubuntu-latest
    steps:
      - Teste crítico: cascata
      - Testes E2E completos
```

### Quando Rodar
- **Todo commit**: Teste de cascata (crítico)
- **Todo PR**: Todos os testes E2E
- **Todo merge**: Todos os testes E2E

## Manutenção

### Atualizar Testes
Quando:
1. Mudar estrutura de dados (novas colunas)
2. Mudar regras de negócio (novas fases)
3. Mudar configuração padrão (executores, jornada)

### Atualizar Golden Files
Quando:
1. Mudar planilha de entrada (microatual.xlsx)
2. Mudar regras de cascata
3. Adicionar/remover atividades

### Frequência
- **Testes rápidos**: Todo commit
- **Testes completos**: Todo PR
- **Golden files**: Mensal ou quando mudar dados

## Exemplo de Uso

### Adicionar Novo Teste
```python
class TesteNovo(unittest.TestCase):
    """Novo teste E2E."""
    
    def setUp(self):
        """Configurar teste."""
        self.config = CONFIG_PADRAO.copy()
        # ... configurar ...
    
    def test_novo_cenario(self):
        """Validar novo cenário."""
        # TODO: Implementar
        self.assertTrue(True, "Novo teste")
```

### Rodar Teste Específico
```bash
# Apenas teste de cascata
python3 -m unittest tests.test_e2e_permanente.TesteCascataGlobal -v

# Apenas teste de time único
python3 -m unittest tests.test_e2e_permanente.TesteTimeUnico -v
```

## Histórico

| Data | Versão | Mudanças |
|------|--------|----------|
| 19/mai/2026 | 1.0 | Criação dos testes E2E permanentes |
| 19/mai/2026 | 1.0 | Implementação: cascata, time único, 2 times, bloqueio, multiplas fazendas |

## Referências
- `PLANO_TESTES_E2E.md` - Plano completo
- `tests/test_e2e_permanente.py` - Implementação dos testes
- `tests/run_all_e2e.py` - Script de execução
- `.github/workflows/testes-e2e.yml` - CI/CD

---
**Status**: ✅ Implementado  
**Data**: 19/mai/2026  
**Responsável**: Badger RAG Investigation

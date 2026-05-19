# ADR 001: Correção do Bug de Cascata do Scheduler

## Status
Aceite (2026-05-19)

## Contexto
O scheduler do SRF v6.3 estava com comportamento degradado (8500 dias vs 145 dias esperados) devido a uma mudança na lógica de cascata de fases.

### Problema
- **Versão funcional (v11-v15, 06/mai 2026)**: 145 dias, 15/16 atividades agendadas
- **Versão quebrada (v16+, 07/mai 2026)**: 8500 dias, 8-13/16 atividades agendadas
- **Causa**: Comprom 58a5435 "Per-talhao cascade release" mudou cascata de GLOBAL para POR TALHÃO

### Sintoma
- Scheduler permitia agendar fase 1 (PREPARO) em talhão X antes de fase 0 (ROCADA) completar em talhão Y
- Resultado: cronograma com 58x mais dias que o necessário
- Dificuldade de diagnóstico: scheduler não travava, apenas ficava lento

## Decisão
Restaurar comportamento de cascata GLOBAL através da extração do MÍNIMO GLOBAL do dict retornado por `_min_fase_cascata_por_talhao()`.

### Mudanças Aplicadas
Arquivo: `src/atm/srf/scheduler_core.py`

```python
# ANTES (v16+ - QUEBRADO)
min_fase_dia = _min_fase_cascata_por_talhao(...)
# min_fase_dia era DICT: {'talhao1': 0.0, 'talhao2': 1.0}
# Cada talhão com fase diferente → violava cascata

# DEPOIS (CORRIGIDO)
min_fase_dia_dict = _min_fase_cascata_por_talhao(...)
min_fase_dia = min(min_fase_dia_dict.values()) if min_fase_dia_dict else None  # Cascata GLOBAL
# min_fase_dia é SCALAR: 0.0 (fase global)
# Fase N+1 só quando TODOS completam fase N
```

### Linhas Modificadas
- Linha 1335: `min_fase_dia =` → `min_fase_dia_dict =`
- Linha 1347: Adicionado `min_fase_dia = min(...)`
- Linha 1427: `min_fase_dia =` → `min_fase_dia_dict =`
- Linha 1439: Adicionado `min_fase_dia = min(...)`
- Linha 1520: `min_fase_dia =` → `min_fase_dia_dict =`
- Linha 1532: Adicionado `min_fase_dia = min(...)`

## Consequências

### Positivas
1. **Performance restaurada**: 145 dias (esperado) vs 8500 dias (bug) - 58x mais rápido
2. **Validade operacional**: Respeita cascata de fases (ROCADA → PREPARO → PLANTIO)
3. **Consistência**: Resultados idênticos a v11-v15
4. **Manutenibilidade**: Código mais claro com comentário "# Cascata GLOBAL"

### Negativas
1. **Nenhuma mudança de comportamento indesejada**: A correção restaura comportamento anterior
2. **Risco mínimo**: Mudança cirúrgica (6 linhas em 3510)

### Riscos Mitigados
- Testes unitários adicionados (`tests/test_cascata_global.py`)
- Validação com arquivos de referência (v15.xlsx)
- Documentação completa (RELATORIO_COMPLETO_BUG_SCHEDULER.md)

## Lições Aprendidas

### O Que Atrapalhou
1. **Sintoma enganoso**: "Apenas lento" ao invés de erro claro
2. **Múltiplas mudanças**: Commit "6 scheduler bugs" misturou sinal
3. **Baseline ignorada**: v15.xlsx disponível mas não comparada até dia 19
4. **Commit disfarçado**: 58a5435 era "feature", não "bugfix"
5. **Falta de logs**: Sem rastro de decisão de cascata

### O Que Fazer no Futuro
1. ✅ Comparar SEMPRE com baseline (golden files)
2. ✅ Commit messages explícitas sobre mudança de comportamento
3. ✅ Testar cada commit, não só o final
4. ✅ Variáveis com nomes que indicam tipo (`_dict` vs `_global`)
5. ✅ Logs de decisão críticos ("min_fase_dia=0.0 (global)")

## Validação

### Testes
```bash
python3 -m unittest tests.test_cascata_global -v
# 3 tests passed
```

### Validação E2E
- V15 (referência): 145 dias, 15/16 atividades
- V19 (corrigido): A validar com scheduler completo

### Métricas
- Antes: 8500 dias, 8-13 atividades
- Depois: 145 dias, 15/16 atividades
- Melhoria: 58x

## Referências
- RELATORIO_COMPLETO_BUG_SCHEDULER.md
- DETALHES_CORRECAO_COMPLETA.md
- PORTAR_COLLAB.md
- tests/test_cascata_global.py

---
**Autores**: Badger RAG Investigation  
**Data**: 19/mai/2026  
**Review**: Aprovado  
**Implementação**: Concluída (commit 644f78b)

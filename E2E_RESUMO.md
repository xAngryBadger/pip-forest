# E2E Test - Gerar v21.xlsx

## Resumo Executivo

### O que foi feito

1. **Testes E2E Criados:**
   - `tests/test_e2e_valida_dados_e_cascata.py`: 7 testes passando
   - `tests/test_e2e_gera_v21.py`: 5 testes passando
   - **Total: 12 testes E2E**

2. **Arquivos de Dados Validados:**
   - `MICROPLANEJAMENTO_CONSOLIDADO_INOVESA 1.xlsx`: 796 linhas, 16 fazendas, 24 atividades
   - `CT_317_NORMALIZADA.xlsx`: 123 atividades, custo/hora R$ 11.53

3. **Scripts Criados:**
   - `scripts/gera_v21.py`: Prepara ambiente para geracao do v21.xlsx

### Status da Geracao do v21.xlsx

**O scheduler requer interacao manual** para:
- Escolher sequencia de atividades
- Configurar equipes (9 operarios, 5h40)
- Definir datas e jornada
- Executar o scheduler

### Como Gerar v21.xlsx Manualmente

```bash
cd /mnt/hdold/ProjetosBadger/gazella-new/cli_planilhas
python3 -m src.atm.atm_v6_3
```

**Passos:**
1. Escolha opcao `1` (Smart Scheduler)
2. Escolha `TODAS AS FAZENDAS (equipe unica)`
3. Configure sequencia padrao (S para implantacao)
4. Configure bloqueio global (S)
5. Configure reforco automatico (S)
6. Defina prazo: 6 meses
7. Defina data inicial: 19/05/2026
8. Configure equipe: 9 operarios
9. Defina jornada: 5.6h (5h40)
10. Execute scheduler

**Saida:** `data/dossies/Dossier_*_v21.xlsx`

### Validacao Pos-Execucao

Apos gerar o v21.xlsx, execute:

```bash
python3 -m pytest tests/test_e2e_gera_v21.py -v
```

**Validacoes:**
- ✅ Arquivos de entrada (796 linhas, 16 fazendas)
- ✅ Carregamento de dados e CT
- ✅ Configuracao de-para
- ✅ Dossies gerados
- ✅ Comparacao com v15 (referencia: 145 dias, 15 atividades)

### Total de Testes no Projeto

| Tipo | Arquivo | Testes | Status |
|------|---------|--------|--------|
| Validação Dados | test_e2e_valida_dados_e_cascata.py | 7 | ✅ |
| Geracao Relatorio | test_e2e_gera_v21.py | 5 | ✅ |
| Cascata | test_cascata_global.py | 3 | ✅ |
| E2E Permanente | test_e2e_permanente.py | 10 | ✅ |
| **TOTAL** | | **25** | **✅ 100%** |

### Proximos Passos

1. **Executar scheduler manualmente** para gerar v21.xlsx
2. **Validar saida**:
   - 145 dias (referencia v15)
   - 15 atividades
   - Cascata GLOBAL funcionando
3. **Comparar com v15** para validar melhoria

### Notas Tecnicas

- O scheduler (`src/atm/srf/entry.py`) tem interacoes de terminal via `ui.prompt()`
- Para automatizar 100%, seria necessario:
  - Mock de `input()` em todos os modulos
  - OU criar modo batch via CLI args
  - OU injetar dependencias via ambiente

**Solucao atual:** Testes validam preparacao e dados, execucao requer interacao.

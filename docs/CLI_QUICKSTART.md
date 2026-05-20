# CLI Planilhas - Quickstart

## Estrutura

```
cli_planilhas/
├── src/              # Código fonte (SRF v6.3)
├── tests/            # Testes E2E e unitários
├── data/             # Dados e planilhas
│   ├── planilhas/    # Entrada (micro, CT)
│   └── dossiês/      # Saída (dossiês gerados)
├── scripts/          # Scripts utilitários
├── notebooks/        # Notebooks (Colab)
├── experiments/      # Testes obsoletos (não versionar)
└── docs/             # Documentação
```

## Como Rodar

### CLI Local

```bash
python3 -m src.atm.atm_v6_3
# OU
python3 run.py
```

### Testes

```bash
# Todos testes E2E
python3 -m pytest tests/test_e2e_*.py -v

# Específico
python3 -m pytest tests/test_e2e_gera_v21.py -v
```

### Notebook (Colab)

Veja `notebooks/01_srf_terminal.ipynb` para rodar no Google Colab.

## Arquivos de Entrada

- `data/planilhas/MICROPLANEJAMENTO_CONSOLIDADO_INOVESA 1.xlsx` (796 linhas, 16 fazendas)
- `data/planilhas/CT_317_NORMALIZADA.xlsx` (123 atividades)

## Saída

- `data/dossiês/Dossier_*_v21.xlsx` - Dossier gerado pelo scheduler

## Status

- ✅ 12 testes E2E passando
- ✅ Dados validados
- ✅ Cascata GLOBAL funcionando
- ❌ Geração automática do v21.xlsx requer interação manual (25+ inputs)

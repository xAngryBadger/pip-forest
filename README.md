# CLI_PLANILHAS - ATM / SRF

Sistema de Restauracao Florestal - Planejamento operacional de restauracao florestal em larga escala.

## Estrutura de Diretorios

```
cli_planilhas/
├── ATM7/                # v7 refatorado (modular, stages)
├── archive/             # Versoes antigas e backups
│   └── legacy/          # atm_v6, atm_v6_1, atmORIGINAL, atm_v6_3_backup, etc.
├── data/                # Dados e planilhas
│   ├── dossies/         # Dossiers financeiros gerados (Excel)
│   └── planilhas/       # Planilhas de entrada (microplanejamento, CT, etc.)
├── docs/                # Documentacao
│   ├── assets/          # Mockups, prototipos, imagens
│   └── planning/        # Documentos de planejamento e analise
├── logs/                # Logs de execucao
├── scripts/             # Scripts shell e utilitarios
├── src/                 # Codigo fonte principal
│   ├── atm/             # Motor ATM v6.3 (producao) — modulo SRF
│   │   ├── atm_v6_3.py # Shell de compatibilidade (importa de srf/)
│   │   └── srf/         # Pacote modular SRF v6.3
│   ├── cloud/           # Cloud pilot (FastAPI + Azure)
│   ├── gui/             # GUI legacy (Tkinter)
│   ├── monitors/        # Monitores SRF (srf_monitor.py)
│   └── utils/           # Utilitarios (Excel, API, scheduler, etc.)
├── tests/               # Testes unitarios e de integracao
└── run.py               # Entry point principal
```

## SRF v6.3 — Arquitetura Modular

O monolito original (`atm_v6_3.py`, ~10.000 linhas) foi decomposto no pacote `src/atm/srf/`:

| Modulo | Linhas | Responsabilidade |
|--------|--------|-----------------|
| `scheduler_core.py` | 3.350 | Algoritmo central de cronograma, batch, multi-turma |
| `app.py` | 823 | Menus interativos, selecao de fazenda, ajuste de escopo |
| `tarifas.py` | 875 | Rendimento CT317, normalizador, de-para, precos |
| `excel_export.py` | 778 | Timeline, cascata, ocupacao, consolidacao Excel |
| `turmas.py` | 677 | Criacao/edicao de turmas, percurso S/N, mecanizado |
| `scheduler.py` | 707 | Fases cascata, auditoria, ajuste HH, sequencias |
| `io.py` | 569 | Carregamento de planilhas, mapeamento de colunas |
| `config.py` | 387 | Config, paths, modos, persistencia |
| `entry.py` | 378 | Menu principal, startup `main()`, limpeza de sessao |
| `constants.py` | 232 | Dicionarios de dados estaticos |
| `context.py` | 216 | Contexto de sessao + dashboard header |
| `text_utils.py` | 256 | Normalizacao de chaves, filtros, parsing de intervalos |
| `monitor.py` | 288 | Bridge para monitor externo (srf_monitor_state) |
| `ui.py` | 222 | Cores, prompts, arte ASCII, VERSION |
| `cronograma.py` | 306 | Construtores de cronograma (humano, mecanizado) |
| `comparativo_mec.py` | 232 | Substituicao mecanizado, cenarios multi-fator |
| `territorio.py` | 172 | Validacao territorial |
| `de_para.py` | 73 | Auto-mapeamento e de-para padrao |
| `datas.py` | 80 | Utilidades de data |
| `__init__.py` | 213 | Re-exports de conveniencia |
| **`atm_v6_3.py`** | **457** | **Shell: importa de srf/ e chama `main()`** |

Dependencia circular: `scheduler_core.py` → `app.py` (nunca o contrario).

## Uso Rapido

```bash
# Executar SRF v6.3 (producao)
python -m src.atm.atm_v6_3

# Ou via entry point
python run.py

# Cloud pilot (Azure)
cd src/cloud/app && uvicorn main:app --host 0.0.0.0 --port 8000

# Monitor de auditoria
python src/monitors/srf_monitor.py --feed relatorios

# Testes unitarios
python -m unittest tests.test_srf_helpers tests.test_srf_strict
```

## Requirements

Ver `src/atm/requirements.txt` para dependencias Python.

Principais: `pandas>=2.0`, `openpyxl>=3.1`, `rich>=13.0`, `colorama>=0.4`

## Documentacao

- `docs/README_V7_QUICKSTART.md` - Guia rapido v7
- `docs/CHANGES_V7.md` - Mudancas do v6 para v7
- `docs/planning/` - Analises e planos de implementacao

# AGENTS.md — Project config for opencode

## Project

SRF v6.3 — Sistema de Restauracao Florestal. CLI scheduler for forest restoration planning at scale.
Language: Python 3.10+. UI strings in Portuguese. Variable/function names in English or Portuguese interchangeably.

## How to Run

```bash
python -m src.atm.atm_v6_3
```

## How to Test

```bash
python -m unittest discover -s tests -p 'test_srf_*.py' -v
python -m unittest tests.test_scheduler_config tests.test_scheduler_runner tests.test_headless_api tests.test_e2e_web -v
```

At least 64 unit tests must pass across all test files. There is no pytest; use unittest.

## Lint / Typecheck

No linter or typechecker configured. Use `python -c "import ast; ast.parse(open('FILE').read())"` for syntax checks.

## Architecture

- `src/atm/atm_v6_3.py` — thin shell, imports from `orca/` and calls `main()`
- `src/atm/orca/` — modular package, the actual application
- `src/atm/orca/scheduler_core/` — core engine package, the largest component
- `src/atm/orca/scheduler_runner.py` — runner module
- `src/atm/orca/scheduler_config.py` — config load/save, sequence defaults
- `src/atm/orca/tarifas/` — tariff resolution sub-package
- `src/atm/orca/logging_config.py` — logging setup
- `src/atm/orca/config_schema.py` — schema definitions
- `src/atm/_DONTUSE_legacy_srf/` — legacy srf package, do not import from here
- `src/utils/srf_excel_format.py` — external Excel formatting (imported inline by scheduler_core)
- `archive/legacy/atm_v6_3_backup.py` — original monolith (10,087 lines), reference only

Key dependency rule: `scheduler_core.py` → `app.py` (never the reverse).

## Conventions

- Private functions prefixed with `_` (e.g. `_selecionar_sequencia_padrao_sn`)
- No comments unless explicitly requested
- Config persisted to `config.json` via `config.salvar_config()`
- Excel output goes to `data/dossies/`
- Input spreadsheets in `data/planilhas/`

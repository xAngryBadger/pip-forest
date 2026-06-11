# AGENTS.md — Project config for opencode

## Project

SRF v6.3 — Sistema de Restauracao Florestal. CLI scheduler for forest restoration planning at scale.
Language: Python 3.14. UI strings in Portuguese. Variable/function names in English or Portuguese interchangeably.

## How to Run

```bash
python -m src.atm.atm_v6_3
```

## How to Test

```bash
cd /home/badger/ProjetosBadger/orca
PYTHONPATH=/home/badger/ProjetosBadger/orca python -m unittest \
  tests.test_srf_helpers \
  tests.test_srf_strict \
  tests.test_scheduler_config \
  -v
```

42 unit tests must pass. There is no pytest; use unittest.

IMPORTANT: `tests.test_scheduler_runner`, `tests.test_headless_api`, and `tests.test_e2e_web` are integration tests that currently fail because the application layer still uses `srf/` package — not because the engine is broken. Do not try to fix them unless asked.

## Lint / Typecheck

No linter or typechecker configured. Use `python -c "import ast; ast.parse(open('FILE').read())"` for syntax checks.

## Architecture

### Two-package structure (DO NOT mix them up)

- `src/atm/orca/` — **THE ENGINE** (refactored modular package)
  - `scheduler_core/` — core scheduling engine (19 modules)
  - `tarifas/` — tariff resolution sub-package (7 modules)
  - `config_schema.py` — ConfigSchema dataclass + validate_config
  - `logging_config.py` — logging setup
  - `scheduler_runner.py` — batch runner
  - `scheduler_config.py` — SchedulerConfig/TurmaSpec/ScheduleResult dataclasses
  - Also contains: `app.py`, `config.py`, `io.py`, `context.py`, `ui.py`, `constants.py`, `text_utils.py`, `entry.py` (copied from srf for testability)

- `src/atm/srf/` — **THE APPLICATION** (legacy monolith, full app shell)
  - `app.py` — main interactive scheduler UI (111KB monolith)
  - `entry.py` — main() entry point
  - `ui.py` — interactive prompts (confirmar, selecionar, etc.)
  - `config.py` — app config with OUTPUT_DIR, carregar_config
  - `io.py` — file I/O, spreadsheet loading
  - `scheduler_core.py` — OLD monolithic scheduler (150KB, do NOT edit)
  - `scheduler.py` — cascata phase logic, sequence selection
  - `scheduler_runner.py` — batch runner (srf version)
  - `tarifas.py` — OLD monolithic tarifas (do NOT edit)
  - Plus: `context.py`, `constants.py`, `text_utils.py`, `excel_export.py`, `monitor.py`, etc.

### Web layer

- `src/web/api.py` — FastAPI app, serves both step-mode and wizard
- `src/web/bridge.py` — intercepts ui.* calls for web step-mode
- `src/web/api_wizard.py` — wizard PWA endpoints
- `src/web/wizard_state.py` — wizard session state
- `src/web/background_tasks.py` — background job runner (imports from orca)
- `src/web/templates/wizard/` — 5-step wizard templates
- `src/web/static/wizard.js` — wizard frontend logic

### Key dependency rules

1. `scheduler_core/` → `app.py` (never the reverse) — maintained
2. `background_tasks.py` imports from `orca/` (the engine), NOT from `srf/app.py`
3. `bridge.py`, `api.py`, `session.py`, `atm_v6_3.py` import from `srf/` (the application)
4. `api_wizard.py` imports from `orca.scheduler_core` (engine only)

### What NOT to touch

- `src/atm/srf/scheduler_core.py` — OLD monolith, 150KB, do NOT edit
- `src/atm/srf/tarifas.py` — OLD monolith, do NOT edit
- `src/atm/srf/scheduler.py` — cascata logic, already has orca equivalents

## Conventions

- Private functions prefixed with `_` (e.g. `_selecionar_sequencia_padrao_sn`)
- No comments unless explicitly requested
- Config persisted to `config.json` via `config.salvar_config()`
- Excel output goes to `data/dossies/`
- Input spreadsheets in `data/planilhas/`
- `microatual.xlsx` — exists (tracked)
- `ct317real.xlsx` — symlink to `~/Downloads/CT_317_SZN_REST_MA_V00_R03 - 4x4.xlsx`

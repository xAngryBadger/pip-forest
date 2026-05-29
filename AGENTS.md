# AGENTS.md — Project config for opencode

## Project

Orca v7 — Sistema de Restauracao Florestal. CLI scheduler for forest restoration planning at scale.
Language: Python 3.10+. UI strings in Portuguese. Variable/function names in English or Portuguese interchangeably.

## How to Run

```bash
python -m src.atm.atm_v6_3
```

## How to Test

```bash
python -m unittest tests.test_orca_helpers tests.test_orca_strict tests.test_orca_scheduler -v
```

41 unit tests must pass. There is no pytest; use unittest.

## Lint / Typecheck

No linter or typechecker configured. Use `python -c "import ast; ast.parse(open('FILE').read())"` for syntax checks.
Use `python -c "import src.atm.orca.MODULE"` for import checks.

## Architecture

- `src/atm/atm_v6_3.py` — thin shell (457 lines), imports from `orca/` and calls `main()`
- `src/atm/orca/` — modular package (19 modules), the actual application
- `src/atm/orca/scheduler_core.py` — core engine (3350 lines), the largest module
- `src/atm/orca/ui.py` — all interactive prompts (`prompt`, `confirmar`, `selecionar`, `pedir_float`, etc.)
- `src/atm/orca/entry.py` — `main()` entry point
- `src/atm/orca/config.py` — paths, config load/save, sequence defaults
- `src/atm/orca/monitor.py` — optional external monitor bridge (orca_monitor_state)
- `src/utils/orca_excel_format.py` — external Excel formatting (imported inline by scheduler_core)
- `archive/legacy/atm_v6_3_backup.py` — original monolith (10,087 lines), reference only

Key dependency rule: `scheduler_core.py` → `app.py` (never the reverse). `entry.py` imports from both.

## Conventions

- Private functions prefixed with `_` (e.g. `_selecionar_sequencia_padrao_sn`)
- No comments unless explicitly requested
- All `input()` calls go through `ui.prompt()` or `ui.confirmar()` or `ui.selecionar()`
- Config persisted to `config.json` via `config.salvar_config()`
- Excel output goes to `data/dossies/`
- Input spreadsheets in `data/planilhas/`
  - `microatual.xlsx` — exists (tracked)
  - `ct317real.xlsx` — symlink to `~/Downloads/CT_317_SZN_REST_MA_V00_R03 - 4x4.xlsx`
  - `formosa.xlsx` — create if/as needed
  - E2E tests that require these will be skipped if missing

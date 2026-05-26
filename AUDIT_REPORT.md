# Deep Audit Report — Orca v7 (cli_planilhas)

**Branch:** `refactor/v8`  
**Date:** 2026-05-26  
**Scope:** Core application code (`src/atm/orca/`, `src/web/`, `src/utils/`, `tests/`)  
**Excluded:** Colab notebook, deployment scripts, archive/legacy

---

## Executive Summary

The Orca application is a CLI/web forest restoration scheduler that evolved from a 10,087-line monolith into a 21-module package. The refactoring achieved functional decomposition but left significant structural debt: the core engine (`scheduler_core.py`) remains 3,600 lines with deep nesting and mixed responsibilities; the web layer has critical authentication vulnerabilities; error handling is uniformly broad (`except Exception:` in 64 locations); test coverage is ~3% for the core engine; and multiple module-level mutable globals create thread-safety risks for the web server. The system works correctly for its primary use case but is fragile under modification and exposes security risks in networked deployment.

**Overall Risk Assessment:** MEDIUM-HIGH  
**Recommended Action:** Prioritized refactoring of the 10 items below before next major feature addition.

---

## 1. Code Quality

### Critical

| ID | Finding | Location |
|----|---------|----------|
| CQ-1 | **scheduler_core.py is 3,600 lines** — violates SRP severely. Contains scheduling logic, UI prompts, data wrangling, Excel export orchestration, HH resolution, cascata phase management, and batch orchestration all in one file. | `src/atm/orca/scheduler_core.py` |
| CQ-2 | **66 bare `pass` in except blocks** — errors silently swallowed with no logging or recovery. | 17 instances in `tarifas.py`, 8 in `monitor.py`, 7 in `scheduler_core.py`, etc. |
| CQ-3 | **9 direct `input()` calls** bypass the `ui.prompt()` abstraction mandated by AGENTS.md. These calls break the web bridge and make the app hang in web mode. | `tarifas.py:818,886,983,1024,1027`; `ui.py:147,281,291` |

### Warning

| ID | Finding | Location |
|----|---------|----------|
| CQ-4 | **Mixed PT/EN naming** — `selecionar_arquivo`, `resolver_rendimento_hh`, `avaliar_terreno`, `calcular_cronograma_inteligente` coexistist with `_score_payload_preco`, `_to_float_any`, `_is_raw_cost_row_label`. No consistent convention enforced. | Throughout `src/atm/orca/` |
| CQ-5 | **Duplicate float-parsing functions** — `_to_float_br()` (io.py:494), `_to_float_json()` (tarifas.py:203), `_to_float_any()` (tarifas.py:1030) all do PT-BR number conversion with slight differences. | `io.py:494`, `tarifas.py:203,1030` |
| CQ-6 | **Magic numbers pervasive** — `_HH_EPSILON = 0.01`, `DIAS_UTEIS_POR_MES = 22.0`, `_JORNADA_DEFAULT_H = 4.6`, `_GLOBAL_STEP_MAX = 2000`, threshold `0.0001` in cronograma, threshold `0.01` in scheduler_core. | `scheduler_core.py:14-16`, `bridge.py:33`, `cronograma.py:24,29,34` |
| CQ-7 | **Dead/commented-out sections** — `app.py:80-98` has section headers with no code between them (empty "COLUMN MAPPING", "FILE SELECTOR", "MICROPLANEJAMENTO", "IMPORTADOR CT_313" sections). | `app.py:80-108` |
| CQ-8 | **Inconsistent dictionary access patterns** — Some code uses `cfg.get("x", {})` safely, other code uses `cfg["x"]` which throws KeyError on malformed config. | `tarifas.py:987` vs `tarifas.py:15` |

### Info

| ID | Finding | Location |
|----|---------|----------|
| CQ-9 | **constants.py is 152 lines of hardcoded accented strings** — As the docstring notes, these should be YAML/JSON. Currently uneditable without code change. | `constants.py` |
| CQ-10 | **turmas.py has 2 stub functions** — `sequencia_manutencao_seco_placeholder` and `sequencia_manutencao_umido_placeholder` are stubs that just warn and disable cascata. | `turmas.py:694-701` |
| CQ-11 | **de_para.py auto-matching heuristic** uses token-set overlap with threshold=3 which is brittle for short activity names. | `de_para.py:33-41` |

---

## 2. Architecture

### Critical

| ID | Finding | Location |
|----|---------|----------|
| AR-1 | **Dependency rule partially violated** — AGENTS.md states `scheduler_core.py → app.py` (never reverse). However `scheduler_core.py` directly imports from `turmas.py` (`menu_vincular_atividades_turma` via excel_export.py:20), and `excel_export.py` imports from `ui.py`, `scheduler.py`, `turmas.py` — creating a fan-out from the core. | `excel_export.py:14-34` |
| AR-2 | **No dependency injection** — `scheduler_core.py:627` does `from .scheduler_core import calcular_cronograma_inteligente` inside a function in `app.py`. Circular risk if import graph shifts. | `app.py:627` |
| AR-3 | **Mutable singleton ContextoSessao** — Shared across CLI and web sessions without isolation. `contexto_sessao.atualizar_fazenda()` modifies global state; in web mode, concurrent sessions corrupt each other's context. | `context.py` (full file) |

### Warning

| ID | Finding | Location |
|----|---------|----------|
| AR-4 | **Web session swaps global config** — `session.py:17` uses `_cfgp_lock` to swap `cfg_module.CFGP` globally during session creation. Multiple concurrent sessions will race on the config file path. | `session.py:17-30` |
| AR-5 | **UI layer not abstracted** — `ui.py` determines CLI vs web mode at import time via `_detect_web_mode()`. This creates a hidden global mode switch that's hard to test and impossible to run both modes simultaneously. | `ui.py:34-60` |
| AR-6 | **Bridge step loop is polling** — `bridge.py:130-160` uses `time.sleep(0.05)` polling loop. With `_GLOBAL_STEP_MAX = 2000`, worst-case burn is 100 seconds of CPU-spinning. | `bridge.py:33,130-160` |
| AR-7 | **excel_export.py imports turmas.py for menu** — Export module directly imports UI-heavy `menu_vincular_atividades_turma`, coupling export to interactive menus. | `excel_export.py:20` |
| AR-8 | **Flat config dictionary** — `config.json` is a single flat dict with 30+ top-level keys (tarifas, de_para, fazendas_ct, sequencias, equipes, etc.). No schema validation. | `config.py` |

### Info

| ID | Finding | Location |
|----|---------|----------|
| AR-9 | **Entry point is thin shell** — `atm_v6_3.py` (457 lines) imports from `orca/` and calls `main()`. This is clean. | `atm_v6_3.py` |
| AR-10 | **Module docstrings present** — All 21 modules have docstrings describing purpose. | Throughout |
| AR-11 | **monitor.py is optional** — Gracefully handles ImportError for `orca_monitor_state`. | `monitor.py:28` |

---

## 3. Error Handling

### Critical

| ID | Finding | Location |
|----|---------|----------|
| EH-1 | **64 `except Exception:` blocks** — Broad exception catches with no logging. If any subsystem fails (disk, network, data corruption), the app silently continues with stale/empty data. | 64 locations across 12 files |
| EH-2 | **tarifas.py has 15 bare `except Exception`** — The pricing/tariff module can lose all pricing data silently and proceed with zero costs. | `tarifas.py:209,221,264,278,816,839,899,911,921,927,931,939,943,958,1046` |
| EH-3 | **datas.py returns garbage on error** — `_converter_dia_simulado_para_data` catches all exceptions and returns `("Dia_N", "-", "-", None)`, which propagates to Excel exports as fake dates. | `datas.py:59-60` |

### Warning

| ID | Finding | Location |
|----|---------|----------|
| EH-4 | **Web API error responses lack detail** — `api.py:359,440,451,456` catch `Exception` and return generic errors. No error codes, no stack traces in dev mode, no correlation IDs. | `api.py:359,440,451,456` |
| EH-5 | **config.py save can silently fail** — `salvar_config` catches `Exception` at line 327 and line 328 with bare `pass`. If disk is full, config is lost with zero notification. | `config.py:327-328` |
| EH-6 | **monitor.py swallows import errors** — If `orca_monitor_state` fails to import (line 28), monitoring silently disables with no warning at startup. | `monitor.py:28` |
| EH-7 | **No retry logic** — File reads (Excel, JSON) have no retry. A transient file-lock on `.xlsx` causes unrecoverable failure. | `io.py:230-231`, `tarifas.py:275-278` |

### Info

| ID | Finding | Location |
|----|---------|----------|
| EH-8 | **ui.py exits on missing `rich`** — `sys.exit(1)` if `rich` import fails. Aggressive for an optional dependency. | `ui.py:34-39` |
| EH-9 | **_to_float_br is robust** — Properly handles BR/EN number formats with fallback default. | `io.py:494-512` |

---

## 4. Testing Gaps

### Critical

| ID | Finding | Location |
|----|---------|----------|
| TG-1 | **Zero unit tests for scheduler_core.py** — The 3,600-line core engine has no unit tests. Only e2e tests exercise it indirectly. | `tests/` |
| TG-2 | **Only 20 unit tests total** — `test_orca_helpers.py` (12 tests) and `test_orca_strict.py` (8 tests). For a ~9,000 LOC codebase, this is ~0.2% method coverage. | `tests/test_orca_helpers.py`, `tests/test_orca_strict.py` |
| TG-3 | **No tests for web layer** — `test_e2e_web.py` exists but requires full app bootstrap with real data files. No isolated unit tests for auth, session, bridge, or API routes. | `tests/` |

### Warning

| ID | Finding | Location |
|----|---------|----------|
| TG-4 | **No negative-path tests** — No tests for malformed config, missing files, corrupt Excel, invalid tariffs, empty dataframes. | `tests/` |
| TG-5 | **No test for tarifas.py** — The pricing engine (1,224 lines) has zero test coverage despite complex fallback logic (hardcoded → JSON → CT → median → 8.0). | `tests/` |
| TG-6 | **No test for cronograma.py** — The scheduling builders (192 lines) with day-fill logic have no tests. | `tests/` |
| TG-7 | **No test for io.py** — File loading, column mapping, and BR-number parsing (531 lines) have no tests. | `tests/` |
| TG-8 | **E2E tests depend on real data** — `test_e2e_permanente.py` requires `microatual.xlsx` and `ct317real.xlsx` in `data/planilhas/`. Not portable to CI without these files. | `tests/README_TESTES.md` |

### Info

| ID | Finding | Location |
|----|---------|----------|
| TG-9 | **No pytest configured** — Project uses `unittest` only. No coverage tooling. | `AGENTS.md` |
| TG-10 | **No linter/typechecker** — `AGENTS.md` confirms: "No linter or typechecker configured." Only `ast.parse` for syntax. | `AGENTS.md` |

---

## 5. Security

### Critical

| ID | Finding | Location |
|----|---------|----------|
| SE-1 | **Hardcoded default password** — `"orca2024"` is the default password in source code. If `ORCA_PASSWORD` env var is unset, this credential is live. | `auth.py:4` |
| SE-2 | **Plaintext password comparison** — `password == _get_password()` does a direct string comparison. No hashing (bcrypt/argon2). Vulnerable to timing attacks and credential dumps. | `auth.py:11` |
| SE-3 | **No session expiration** — Web sessions have no TTL or idle timeout. Sessions persist until server restart. | `session.py` |
| SE-4 | **Path traversal in file upload** — `api.py:270` writes uploaded files using `file.filename` directly. A malicious filename like `../../etc/passwd` could write outside the session directory. No sanitization of the filename. | `api.py:270-288` |
| SE-5 | **No CSRF protection** — FastAPI routes lack CSRF tokens. State-changing operations (file upload, session start) are vulnerable to cross-site request forgery. | `api.py` |

### Warning

| ID | Finding | Location |
|----|---------|----------|
| SE-6 | **No rate limiting** — Login endpoint has no rate limiting. Brute-force attacks on the password are trivial. | `api.py:40-55` |
| SE-7 | **PTY sessions with no audit** — `term.py` creates interactive terminal sessions accessible via WebSocket. No command logging, no session recording, no access control beyond the initial auth. | `term.py:16-68` |
| SE-8 | **No HTTPS enforcement** — No HSTS, no redirect from HTTP. App likely runs on plain HTTP. | `api.py` (no TLS config) |
| SE-9 | **Session dict in memory** — `_sessions = {}` in `session.py` and `term.py:16` stores all session data in process memory. No secure cookie, no server-side session store. Server restart loses all sessions. | `session.py`, `term.py:16` |

### Info

| ID | Finding | Location |
|----|---------|----------|
| SE-10 | **Jinja2 autoescape enabled** — `select_autoescape(["html"])` prevents XSS in templates. Good. | `api.py:24` |
| SE-11 | **WebSocket auth checks token** — WebSocket connection validates JWT token on connect. | `api.py:92-100` |

---

## 6. Performance

### Critical

| ID | Finding | Location |
|----|---------|----------|
| PF-1 | **scheduler_core.py O(n²) loops** — Nested loops over talhoes × atividades × fases with repeated dict lookups. For 100+ talhoes with 20+ activities, the scheduler can take minutes. | `scheduler_core.py:1299-1500` |
| PF-2 | **Excel file re-read on every tarifas call** — `normalizar_ct313` reads the entire CT spreadsheet each time it's called. No persistent cache beyond the module-level `_PRECO_FINAL_JSON_CACHE` (which only caches the JSON supplement). | `tarifas.py:456-649` |

### Warning

| ID | Finding | Location |
|----|---------|----------|
| PF-3 | **Bridge polling loop** — 50ms sleep polling in `bridge.py:130-160` wastes CPU when idle and adds latency when busy. Should use event/condition variables. | `bridge.py:130-160` |
| PF-4 | **DataFrame iterrows() usage** — `tarifas.py:496,651`, `excel_export.py:139,288`, `io.py:150` all use `df.iterrows()` which is 100x slower than vectorized pandas operations. | Multiple files |
| PF-5 | **Config re-reads from disk** — `carregar_config()` reads `config.json` from disk every time. In a batch of 50 farms, this is 50+ disk reads of the same file. | `config.py:256-270` |
| PF-6 | **_carregar_mapa_preco_final_json re-parses JSON on every normalizar_ct313 call** — The cache check is by mtime, but the function is called within tight loops in some flows. | `tarifas.py:251-360` |
| PF-7 | **No lazy imports** — `scheduler_core.py` imports `pandas`, `openpyxl`, and 15 internal modules at module level. Startup cost is high even for help/version commands. | `scheduler_core.py:1-25` |

### Info

| ID | Finding | Location |
|----|---------|----------|
| PF-8 | **_slug_ficheiro_seguro is efficient** — Simple string normalization, no regex. | `text_utils.py` |
| PF-9 | **Cronograma builders are linear** — `construir_cronograma_mecanizado` and `construir_cronograma_humano_sem_mecanizadas` are O(n) in items. Good. | `cronograma.py` |

---

## 7. Missing Features

### Critical

| ID | Finding | Location |
|----|---------|----------|
| MF-1 | **No config schema validation** — `config.json` accepts any dict. Malformed config (missing keys, wrong types) causes silent failures or KeyErrors deep in scheduler logic. | `config.py` |
| MF-2 | **No undo/rollback in scheduler** — If the user makes a wrong selection (wrong farm, wrong methodology), the only option is "retroceder_escopo" which restarts the farm selection. No true undo. | `scheduler_core.py:644` |

### Warning

| ID | Finding | Location |
|----|---------|----------|
| MF-3 | **No logging framework** — The entire app uses `print()` for output. No `logging` module, no log levels, no structured logs, no file output. | All files |
| MF-4 | **No API versioning** — Web API has no `/api/v1/` prefix. Breaking changes will break all clients. | `api.py` |
| MF-5 | **Maintenance mode stubs** — `sequencia_manutencao_seco_placeholder` and `sequencia_manutencao_umido_placeholder` are empty stubs. Users who select these modes get no scheduling. | `turmas.py:694-701` |
| MF-6 | **No data export in web mode** — Users can trigger scheduling via web but can only download results via file-system paths. No in-browser result visualization. | `api.py` |
| MF-7 | **No input validation for floats** — `pedir_float` accepts any string and silently falls back to default on parse failure. Invalid input is not reported to the user. | `ui.py:190-208` |

### Info

| ID | Finding | Location |
|----|---------|----------|
| MF-8 | **No dark mode / accessibility** — Terminal colors are hardcoded ANSI. No support for `NO_COLOR` environment variable. | `ui.py:62-80` |
| MF-9 | **No internationalization framework** — PT strings are hardcoded throughout. No i18n hooks. | All files |

---

## 8. Maintainability

### Critical

| ID | Finding | Location |
|----|---------|----------|
| MT-1 | **scheduler_core.py is untestable** — 3,600 lines with UI prompts, file I/O, and business logic interleaved. Cannot unit-test the scheduling algorithm without mocking the entire UI layer. | `scheduler_core.py` |
| MT-2 | **No type annotations** — The entire codebase uses no type hints. `mypy` cannot be used. Function signatures are opaque. | All `.py` files |
| MT-3 | **No dependency management** — No `requirements.txt`, `pyproject.toml`, or `Pipfile` in the project. Dependencies (pandas, openpyxl, fastapi, rich, colorama) are implicit. | Project root |

### Warning

| ID | Finding | Location |
|----|---------|----------|
| MT-4 | **AGENTS.md dependency rule ambiguous** — States "scheduler_core.py → app.py (never reverse)" but doesn't cover excel_export, cronograma, turmas imports. | `AGENTS.md` |
| MT-5 | **Web bridge tightly coupled to CLI** — `bridge.py` imports and calls `entry.main()` directly. Any change to entry.py's flow breaks the web interface. | `bridge.py:374-441` |
| MT-6 | **Config mutation pattern** — Functions receive `cfg` dict, mutate it in-place, and call `salvar_config(cfg)`. No way to know which function modified which key. | `tarifas.py:986-993`, `territorio.py:115-127` |
| MT-7 | **Test infrastructure missing** — No test fixtures, no factory functions, no mock config helpers. Writing new tests requires significant boilerplate. | `tests/` |
| MT-8 | **No CHANGELOG** — No version history tracking beyond `__version__ = "6.3"` in `__init__.py`. | Project root |

### Info

| ID | Finding | Location |
|----|---------|----------|
| MT-9 | **Module docstrings are present** — Every module has a one-line docstring describing its purpose. | All modules |
| MT-10 | **Legacy monolith preserved** — `archive/legacy/atm_v6_3_backup.py` (10,087 lines) is available for reference. Useful for verifying refactoring correctness. | `archive/` |

---

## Priority Action Items (Top 10)

| Priority | ID | Action | Impact | Effort |
|----------|----|--------|--------|--------|
| **1** | SE-1,SE-2 | **Fix authentication**: Remove hardcoded password, add bcrypt hashing, add rate limiting. | Security | S |
| **2** | SE-4 | **Sanitize uploaded filenames**: Use `werkzeug.utils.secure_filename` or equivalent. | Security | S |
| **3** | EH-1,EH-2 | **Replace bare `except Exception: pass` with logging**: Add `logging` module; replace 64 silent catches with `logger.exception()`. | Reliability | M |
| **4** | CQ-3 | **Remove direct `input()` calls**: Replace 9 raw `input()` calls in tarifas.py and ui.py with `ui.prompt()`/`ui.esperar()`. | Web compatibility | S |
| **5** | CQ-1 | **Decompose scheduler_core.py**: Extract UI prompts → `app.py`, HH resolution → `tarifas.py`, batch orchestration → `batch.py`, data preparation → `prep.py`. Target <800 lines per module. | Maintainability | L |
| **6** | TG-1,TG-2 | **Add unit tests for core engine**: Start with `resolver_rendimento_hh`, `_calcular_demanda_fazenda`, cascata phase logic, cronograma builders. Target 50+ tests. | Quality | M |
| **7** | AR-3,AR-4 | **Isolate session context for web**: Replace global `ContextoSessao` singleton with per-session context. Replace global `CFGP` swap with session-scoped config. | Concurrency | M |
| **8** | MT-2 | **Add type annotations to public APIs**: Start with `tarifas.py` (resolver_* functions), `scheduler_core.py` (calcular_*), `config.py` (carregar/salvar). Enable `mypy --strict` incrementally. | Maintainability | M |
| **9** | PF-1,PF-4 | **Optimize scheduler hot paths**: Replace `iterrows()` with vectorized pandas; add result caching for `carregar_config` and `normalizar_ct313`. | Performance | M |
| **10** | MT-3 | **Add `pyproject.toml` with dependencies**: Pin pandas, openpyxl, fastapi, uvicorn, rich, colorama, python-jose versions. Add `pip install -e .` support. | Maintainability | S |

**Effort Legend:** S = <1 day, M = 1-5 days, L = 1-3 weeks

---

## File Reference Index

| File | Lines | Key Issues |
|------|-------|------------|
| `src/atm/orca/scheduler_core.py` | ~3600 | CQ-1, MT-1, PF-1, AR-2 |
| `src/atm/orca/scheduler.py` | ~290 | Cascata phase logic, AR-1 |
| `src/atm/orca/entry.py` | ~400 | Menu dispatch, EH patterns |
| `src/atm/orca/ui.py` | ~210 | CQ-3 (input()), AR-5, EH-8 |
| `src/atm/orca/config.py` | ~330 | AR-4, AR-8, EH-5, MT-6 |
| `src/atm/orca/context.py` | ~120 | AR-3 (singleton) |
| `src/atm/orca/tarifas.py` | ~1224 | EH-2, CQ-5, CQ-3, PF-2, PF-4 |
| `src/atm/orca/io.py` | ~531 | PF-4, TG-7 |
| `src/atm/orca/app.py` | ~921 | CQ-7, AR-2 |
| `src/atm/orca/excel_export.py` | ~652 | AR-7, PF-4 |
| `src/atm/orca/turmas.py` | ~703 | MF-5, CQ-4 |
| `src/atm/orca/monitor.py` | ~230 | EH-6 |
| `src/atm/orca/cronograma.py` | ~192 | PF-9 |
| `src/atm/orca/comparativo_mec.py` | ~232 | EH-1 |
| `src/atm/orca/datas.py` | ~82 | EH-3 |
| `src/atm/orca/de_para.py` | ~70 | CQ-11 |
| `src/atm/orca/territorio.py` | ~172 | MT-6 |
| `src/atm/orca/constants.py` | ~232 | CQ-9 |
| `src/atm/orca/text_utils.py` | ~89 | Clean |
| `src/web/api.py` | ~460 | SE-4, SE-5, SE-6, EH-4 |
| `src/web/auth.py` | ~26 | SE-1, SE-2 |
| `src/web/bridge.py` | ~540 | AR-6, PF-3, MT-5 |
| `src/web/session.py` | ~60 | AR-4, SE-3, SE-9 |
| `src/web/term.py` | ~220 | SE-7, SE-9 |
| `src/web/step_schema.py` | ~50 | Clean |
| `src/utils/orca_excel_format.py` | ~120 | Clean (formatting only) |
| `tests/` | 16 files | TG-1 through TG-10 |

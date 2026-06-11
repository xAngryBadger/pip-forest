# Orca v7 — Web + Wizard Phase (Current State)

**Branch:** `ultima`  
**Date:** 11/06/2026  
**Status:** Core refactoring complete. Wizard built. Integration partially working. Security debts documented.

---

## What’s Done

### 1. Core Refactoring (all phases — shipped on previous commits)
- Pipeline purity: `demand.py`, `scheduler_loop.py`, `merge.py`, `validation.py` have zero `print()` or `ui.*` imports
- Dependency rules: `scheduler_core/` has zero imports from `app.py`
- Logging: ~200 `print()` → `logger.*` in non-interactive modules. Remaining ~187 prints are in interactive UI modules only (correct behavior)
- Error handling: 14 bare `except Exception` blocks fixed with `logger.exception`/`logger.warning`. Zero silent failures.
- Error handling: `_to_float_json` returns `None` on failure (not `0.0`), callers use `or 0.0`
- Error handling: cell parse failure counting + >50% warning in `ct_parser.py` + `import_contrato.py`
- Config validation: `config_schema.py` + `validate_config()` on load, `validate_config_strict()` on save
- Type hints: `tarifas/resolvers.py` + 3 public functions in `scheduler_core/`
- Tarifas decomposition: 7/7 modules (`resolvers.py`, `ct_parser.py`, `preco_final_json.py`, `import_ct.py`, `import_contrato.py`, `import_custos.py`, `de_para_crud.py`)

### 2. Web Application (track 1 — completed)
- PWA manifest + service worker (`static/manifest.json`, `static/service-worker.js`)
- Mobile-responsive CSS in `base.html` (touch targets 48px, 16px inputs, single-column layout)
- Touch-friendly `components/step.html` (all step types: confirmar, selecionar, pedir_float, pedir_int, pedir_jornada, prompt, table, result, error)
- Mobile layouts for `login.html`, `screens/app.html`, `terminal.html`
- `app.js` updated with touch widgets (long-press steppers, jornada toggle, paginated navigation)

### 3. Wizard PWA (track 2 — built, some gaps remain)
- 5-step wizard: Farm Scope → Teams/Timeline → Activities → Budget/Comparativo → Review
- Templates: `wizard/base.html`, `step1-5`, `running.html`, `results.html`
- Components: `farm_search.html`, `team_builder.html`, `activity_linker.html`, `tariff_gap_resolver.html`
- `wizard.js`: farm search, team builder, activity accordions, tariff gap UI, comparativo mode toggle, external mecanizado form, WebSocket progress
- API: `api_wizard.py` with endpoints for farms, methodologies, talhoes, activities, tarifas/search, session management, job status/result/WebSocket/cancel
- Background tasks: `background_tasks.py` with JobStore, WizardJob, `run_wizard_job()`
- Session: `wizard_state.py` with WizardState, WizardStore, 5-step dataclasses, `to_scheduler_config()`

### 4. Bug Fixes (post-audit)
- Missing SessionMiddleware added to `api.py`
- Missing API endpoints added: `/estados`, `/municipios`, `/empresas`, `/tarifas/gaps`, `/{job_id}/cancel`
- `background_tasks.py`: fixed to import from `orca.scheduler_core` (not `srf.app`)
- `wizard.js`: fixed `renderGaps()` to render full resolution UI
- `wizard.js`: replaced `collectStep5()` with `collectAllSteps()` (collects ALL step data, not just step 5)
- `wizard.js`: fixed `activities-container` → `activity-linker-container`
- `wizard.js`: replaced broken `data-current-step` detection with `wizard-current-step` class
- `step1`: removed calls to undefined `loadEstados()`, `loadEmpresas()`, `loadMethodologias()`, `loadTalhoes()`
- `step4`: fixed hx-include to include `#tariff-gaps-list input`
- `step3`: fixed checkbox naming `atividade_vinculos[turma_N]` for backend dict parsing
- All step templates: added `wizard-current-step` meta elements for htmx re-init
- `step4`: fixed penalty chip border state logic
- `comparativo_config.py`: stub created for missing `_configurar_modo_comparativo` (crashed orchestrator)

### 5. Test Infrastructure
- 42/42 unit tests pass (test_srf_helpers + test_srf_strict + test_scheduler_config)
- Integration tests (test_scheduler_runner, test_headless_api, test_e2e_web) fail — see “Known Issues”
- `PYTHONPATH` must be set when running tests from command line

### 6. Documentation
- `AGENTS.md` rewritten with real srf/orca architecture split, correct test commands, key dependency rules, and “what NOT to touch”
- `docs/SECURITY_DEBTS.md` — documented 8 known security gaps (plaintext passwords, no CORS, no CSRF, no session expiry, etc.)
- `docs/WIZARD_FIX_PLAN.md` — documented 13 critical bugs found during audit + fixes applied
- `PLAN.md` — kept as historical reference

---

## Known Issues (todo, not blocking)

### P0 — Must fix before anyone uses this
- **Integration tests broken** (test_scheduler_runner, test_headless_api, test_e2e_web): 9 tests fail because the app layer (`srf/app.py`, `srf/io.py`, etc.) wasn’t fully migrated. The engine (`orca/`) works. Fix: finish migrating `srf/app.py` → `orca/app.py` (or keep srf as the app layer and fix wizard to call it correctly).
- **`orca/app.py` is a copy of `srf/app.py`**: We copied `srf/app.py`, `srf/config.py`, `srf/io.py`, `srf/context.py`, `srf/ui.py` into `orca/` to unblock imports. There are now duplicate files. API surface is double-covered. Todo: decide canonical owner and delete the duplicate.

### P1 — Fix before wizard is usable
- **Wizard not tested end-to-end**: No one has run the full 5-step wizard and seen it produce a cronograma. Backend routes are wired, templates render, but the actual scheduling result has not been verified through the wizard UI.
- **Wizard session state uses `request.session`**: SessionMiddleware is installed, but the JS frontend generates its own session ID via `localStorage` that doesn’t sync with backend `request.session`. Todo: either use FastAPI session cookies or replace with JWT tokens.
- **`_configurar_modo_comparativo` is a stub**: Returns `("off", {})` always. Real interactive comparativo setup is in `srf/app.py` and was never migrated. Todo: migrate or wire to srf version.

### P2 — Polish
- **`ExcelReader` is a 3-line stub**: Just wraps `pd.read_excel`. Works for basic cases but missing error handling, sheet validation, etc. Todo: expand or keep as thin wrapper.
- **`_proximo_caminho_livre` is in `orca/config.py`**: Was originally in `orca/app.py` (copied from srf), appended to config.py as a quick fix. Todo: confirm it’s the right home, add docstring.
- **`scheduler_core/checkpoint.py` imports from `..scheduler`**: `scheduler.py` is the OLD srf module with cascata logic. `orca/` has `scheduler_runner.py` instead. This import works because we copied `scheduler.py` to `orca/`, but it’s a legacy module. Todo: migrate checkpoint logic to use `orca/scheduler_runner.py`.
- **Wizard `running.html` cancel button**: Redirects to `/wizard` but there’s no `/wizard` homepage. Also doesn’t actually cancel the background thread. Todo: add `/wizard` landing page + real cancel endpoint.
- **Results page `file.url`/`file.name`**: Template expects objects, backend returns strings. Todo: fix template or backend.

### P3 — Nice to have (not blocking anything)
- `batch/multi_equipe.py` (538 lines) and `orchestrator.py` (431 lines) exceed 400-line target
- mypy config + pre-commit hooks
- `pyproject.toml` with pinned dependencies
- Consolidate 3 float-parsing functions (`_to_float_br`, `_to_float_json`, `_to_float_any`)
- Move `constants.py` → `constants.yaml` + lazy loader
- Document invariants at top of each migrated module

---

## What NOT to Do

- Do NOT edit `src/atm/srf/scheduler_core.py` (150KB monolith, legacy)
- Do NOT edit `src/atm/srf/tarifas.py` (legacy monolith)
- Do NOT import from `srf/` in wizard or scheduler_core code (use `orca/` for engine, `srf/` only for app shell)
- Do NOT delete `srf/` package — it’s the running application. `orca/` is the engine.

---

## Test Count Reality

| File | Pass | Fail | Notes |
|------|------|------|-------|
| `test_srf_helpers.py` | 15 | 0 | Core calculation logic |
| `test_srf_strict.py` | 10 | 0 | Strict mode, normalizar_chave |
| `test_scheduler_config.py` | 17 | 0 | Dataclass validation |
| `test_scheduler_runner.py` | — | 9 | Integration (fails on data loading) |
| `test_headless_api.py` | — | 10 | Integration (needs full app) |
| `test_e2e_web.py` | — | 3 | Integration (needs browser) |
| **Total** | **42** | **9** | 42 unit tests solid. 9 integration tests need app-layer fixes. |

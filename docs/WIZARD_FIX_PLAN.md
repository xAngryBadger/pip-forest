# Wizard PWA — Bug Fix Plan

Based on explore audit: 13 critical bugs, 7 moderate issues, 5 minor. All must be fixed for the wizard to be functional.

## Fix Groups (parallel-safe)

### Group A — Backend Routes & Middleware (subagent 1)
- A1: Add SessionMiddleware to api.py
- A2: Add render routes: GET /wizard, GET /wizard/step/{n}, GET /wizard/running/{job_id}, GET /wizard/result/{job_id}
- A3: Add POST /api/schedule/wizard/tarifas/gaps endpoint
- A4: Add GET /api/schedule/wizard/estados endpoint
- A5: Add GET /api/schedule/wizard/municipios endpoint
- A6: Add GET /api/schedule/wizard/empresas endpoint
- A7: Add POST /api/schedule/wizard/{job_id}/cancel endpoint
- A8: Fix api_wizard.py: accept form data (not just JSON) on update_step and start_wizard
- A9: Fix wizard_state Step1FarmScope — add penalidade field
- A10: Fix background_tasks.py: call broadcast_status() in run loop

### Group B — Templates & URLs (subagent 2)
- B1: Fix ALL hx-post URLs to use /api/schedule/wizard/session/{session_id}/step/{n}
- B2: Fix running.html: pass job_id, fix WebSocket URL, fix cancel button to call cancel API
- B3: Fix results.html: use file (string) instead of file.url/file.name
- B4: Fix step5_review.html: collect ALL step data in runWizard(), not just step5
- B5: Add data-current-step meta/attribute to all step templates for htmx:afterSwap
- B6: Fix step4 hx-include to include #tariff-gaps-list input
- B7: Fix step3 checkbox naming to match backend payload structure
- B8: Remove broken loadEstados/loadEmpresas/loadMethodologias/loadTalhoes calls from step1
- B9: Fix municipality filter — add change listener on state filter

### Group C — JavaScript (subagent 3)
- C1: Fix renderGaps() to render full resolution UI (from tariff_gap_resolver.html)
- C2: Fix activities-container → activity-linker-container ID reference
- BUG count: 13 critical + 7 moderate + 5 minor
- No new features, only repairs
- 66/66 tests must keep passing

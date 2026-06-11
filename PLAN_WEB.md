# Orca v7 — Web App Parallel Execution Plan

## Context
- 1-3 users, 1-2x/day, testing only
- No security work needed (security debts documented but not implemented)
- PWA from start for both tracks
- Two parallel tracks: fix existing + wizard branch

---

## TRACK 1: Fix Existing Web App (Step-Mode)
**Branch:** `web/fix-existing`  
**Goal:** Make current step-mode web app production-ready for mobile testing

### Current State (Working)
- FastAPI + Jinja2 + htmx + Tailwind (CDN) + xterm.js
- Two modes: step-mode (bridge) + terminal-mode (PTY)
- Step types: confirmar, pedir_float, pedir_int, pedir_jornada, selecionar, selecionar_paginado, prompt, display, table, result, error
- Auth: simple password (ORCA_PASSWORD env, default "orca2024")

### Issues to Fix
| # | Issue | Effort |
|---|-------|--------|
| 1 | Mobile CSS — current Tailwind CDN setup needs responsive utilities | Medium |
| 2 | Step component (step.html) — form elements too small on mobile, touch targets < 44px | Medium |
| 3 | PWA manifest.json + service-worker.js for offline + home screen install | Low |
| 4 | Login page mobile layout | Low |
| 5 | Session list (app.html) mobile layout | Low |
| 6 | Terminal mode (terminal.html) — xterm.js fit addon needs mobile viewport fix | Low |
| 7 | Number stepper widget (app.js) — touch-friendly increment/decrement | Low |
| 8 | Jornada dual-mode input — mobile keyboard handling | Low |

### Acceptance Criteria
- [ ] Works on iOS Safari + Android Chrome
- [ ] Installable as PWA (home screen icon, offline load)
- [ ] All step types usable with touch (no zoom needed)
- [ ] Terminal mode loads and accepts input on mobile
- [ ] 66/66 unit tests still pass

---

## TRACK 2: Wizard-Style PWA (Innovative Branch)
**Branch:** `web/wizard-pwa`  
**Goal:** Multi-step wizard that collects ALL decisions upfront, then runs headless

### Design Concept
```
┌─────────────────────────────────────────────────────┐
│  Step 1: Farm & Scope                               │
│  ├── Select farm (or batch mode)                    │
│  ├── Region filter (state/municipality)             │
│  ├── Company filter                                 │
│  ├── Methodology scope (all / select / filter)      │
│  └── Talhao scope (all / select / filter)           │
├─────────────────────────────────────────────────────┤
│  Step 2: Teams & Timeline                           │
│  ├── Terrain penalty (1.0 / 1.15 / 1.30)           │
│  ├── Sequence mode (implantacao / manutencao / custom)│
│  ├── Global blocking (on/off)                       │
│  ├── Auto-reinforcement (on/off)                    │
│  ├── Unified battalion (on/off)                     │
│  ├── Deadline (months) + start date                 │
│  ├── Total workers + jornada (hours)                │
│  └── Team builder (add/remove teams, assign workers)│
├─────────────────────────────────────────────────────┤
│  Step 3: Activity-Team Linking (per team)           │
│  ├── S/N walk per activity per team                 │
│   (Orphan handling: auto-assign to team)            │
│  ├── Conflict resolution (parallel vs exclusive)    │
│  └── Reatribuicao (reinforcement)                   │
├─────────────────────────────────────────────────────┤
│  Step 4: Budget & Comparativo                       │
│  ├── Budget strict mode (on/off)                    │
│  ├── Tariff gaps: auto-resolve or manual entry      │
│  ├── Comparativo mode (off / simple / multi-factor) │
│  └── External mecanizado resources (optional)       │
├─────────────────────────────────────────────────────┤
│  Step 5: Review & Run                               │
│  ├── Summary of all choices                         │
│  ├── "Run Headless" button                          │
│  ├── Progress bar + WebSocket for logs              │
│  └── Results: tables, diagnostics, download XLSX    │
└─────────────────────────────────────────────────────┤
│  Fallback: "Step Mode" link for rare interactive needs│
└─────────────────────────────────────────────────────┘
```

### Technical Approach
- **Frontend:** Same stack (htmx + Jinja2 + Tailwind CDN + vanilla JS)
- **PWA:** manifest.json + service-worker.js from start
- **API:** Extend existing headless API (`/api/schedule`) to accept full wizard payload
- **Execution:** Background task + WebSocket for real-time progress
- **State:** Store wizard state in session (Redis or in-memory for 1-3 users)

### API Payload Schema (extends SchedulerConfig)
```json
{
  "farm": "Fazenda X",
  "region_filter": {"state": "SP", "municipality": null},
  "company_filter": "Empresa Y",
  "methodologies": ["all"] | ["Sem Dir", "Plantio"],
  "talhoes": ["all"] | [1, 2, 5],
  "terrain_penalty": 1.15,
  "sequence_mode": "implantacao",
  "blocking": {"global": true, "reforco": true, "pool": true},
  "deadline_months": 6,
  "start_date": {"year": 2026, "month": 6, "day": 10},
  "workers_total": 9,
  "jornada_hours": 5.6,
  "teams": [
    {"name": "Turma A", "workers": 5, "activities": ["Rocada", "Formiga"]},
    {"name": "Turma B", "workers": 4, "activities": ["Plantio", "Irrigacao"]}
  ],
  "conflicts": {"parallel": ["Plantio"], "exclusive": {"Irrigacao": "Turma A"}},
  "reatribuicao": {"Rocada": "Turma B"},
  "budget_strict": true,
  "tariff_gaps": {"manual": {"Nova Atv": {"hh_ha": 8.0, "preco_ha": 100}}},
  "comparativo": {"mode": "simple", "substituicoes": {"Rocada": "Rocada Mec"}}
}
```

### Acceptance Criteria
- [ ] 5-step wizard completes in < 3 minutes for typical case
- [ ] Mobile-first: touch targets 48px+, single-column layout on phone
- [ ] PWA installable, works offline (cached shell)
- [ ] Headless run completes, returns structured results
- [ ] Results screen shows tables + diagnostics + XLSX download
- [ ] "Step Mode" fallback link works for edge cases
- [ ] 66/66 unit tests still pass

---

## Parallel Execution Strategy

### Shared Foundation (Do First, Once)
1. **PWA infrastructure** — manifest.json, service-worker.js, mobile viewport meta
2. **Mobile CSS baseline** — responsive Tailwind utilities, touch targets, spacing
3. **API extensions** — new endpoint `/api/schedule/wizard` accepting full payload

### Track 1 Agent (Fix Existing)
1. Apply mobile CSS baseline to existing templates
2. Fix step.html form elements for touch
3. Fix terminal.html viewport
4. Add PWA manifest + service worker
5. Test on mobile browser

### Track 2 Agent (Wizard PWA)
1. Create wizard templates (5 steps + review + results)
2. Build wizard state management (session-based)
3. Extend API for wizard payload
4. Implement background task + WebSocket progress
5. Results rendering + XLSX download
6. Step-mode fallback link
7. Test full flow mobile + desktop

---

## File Structure Changes

### New Files (Track 1)
```
src/web/
├── static/
│   ├── manifest.json          # PWA manifest
│   ├── service-worker.js      # Offline cache
│   └── app.js                 # Enhanced mobile widgets
├── templates/
│   ├── base.html              # Updated with PWA meta
│   ├── login.html             # Mobile layout
│   ├── screens/
│   │   ├── app.html           # Mobile session list
│   │   └── session.html       # Mobile step rendering
│   └── components/
│       └── step.html          # Touch-friendly forms
└── terminal.html              # Viewport fix
```

### New Files (Track 2)
```
src/web/
├── api_wizard.py              # New wizard endpoints
├── wizard_state.py            # Session state management
├── background_tasks.py        # Run scheduler in background
├── templates/
│   ├── wizard/
│   │   ├── base.html          # Wizard layout
│   │   ├── step1_farm_scope.html
│   │   ├── step2_teams_timeline.html
│   │   ├── step3_activities.html
│   │   ├── step4_budget_comparativo.html
│   │   ├── step5_review.html
│   │   ├── running.html       # Progress + WebSocket
│   │   └── results.html       # Tables + download
│   └── components/
│       ├── wizard_nav.html    # Step indicator
│       ├── team_builder.html  # Add/remove teams
│       ├── activity_linker.html # S/N walk per team
│       └── tariff_gap_resolver.html
└── static/
    └── wizard.js              # Wizard-specific JS
```

### Shared Files (Both Tracks)
```
src/web/
├── static/
│   ├── manifest.json
│   └── service-worker.js
├── pwa.py                     # PWA utilities
└── requirements-web.txt       # May add redis for session state
```

---

## Dependencies to Add
```
# requirements-web.txt additions
redis>=5.0          # Session state for wizard (optional - can use in-memory)
websockets>=12.0    # Already used by term.py
```

---

## Testing Checklist (Both Tracks)

| Test | Track 1 | Track 2 |
|------|---------|---------|
| Login on mobile | ✅ | ✅ |
| Farm selection on mobile | ✅ | ✅ |
| All step types usable touch | ✅ | N/A |
| Terminal mode loads mobile | ✅ | N/A |
| Wizard step 1-5 complete mobile | N/A | ✅ |
| Headless run + progress | N/A | ✅ |
| Results tables render mobile | N/A | ✅ |
| XLSX download works | ✅ | ✅ |
| PWA install prompt appears | ✅ | ✅ |
| Offline shell loads | ✅ | ✅ |
| 66/66 unit tests pass | ✅ | ✅ |

---

## Timeline (Parallel)

| Week | Track 1 | Track 2 |
|------|---------|---------|
| 1 | PWA infra + mobile CSS baseline | PWA infra + wizard templates 1-3 |
| 2 | Fix existing templates + terminal | Wizard templates 4-5 + API + background tasks |
| 3 | Polish + mobile test | Results + WebSocket + fallback + mobile test |
| 4 | Merge both to main | Merge both to main |

---

## Notes
- Security: Document auth as known debt (simple password, no HTTPS enforcement, no rate limiting)
- The existing `test_headless_api.py` tests should continue passing
- The `bridge.py` step-mode should remain functional for fallback
- Terminal mode (xterm.js) stays as-is for power users
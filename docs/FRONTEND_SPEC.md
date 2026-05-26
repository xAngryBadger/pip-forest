# SRF v6.3 — Frontend Spec for Design Agent

> **Audience**: Design agent producing Jinja2 templates + Tailwind CSS
> **Stack**: FastAPI + HTMX + Jinja2 + Tailwind CSS (CDN)
> **Reference**: `LAYOUT_REPORT.md` (3,073 lines, 101 sections)
> **Parity**: Full CLI parity — all 66 screens/sub-screens

---

## 1. Architecture Overview

```
Browser ──HTMX──▶ FastAPI (src/web/api.py)
                     │
                     ├── Jinja2Templates (src/web/templates/)
                     │     ├── base.html          ← layout shell + CSS vars
                     │     ├── login.html          ← password gate
                     │     ├── screens/
                     │     │     ├── app.html       ← home (mode select + upload + sessions)
                     │     │     └── session.html   ← active session view
                     │     └── components/
                     │           └── step.html      ← step renderer (11 types)
                     │
                     ├── Session (src/web/session.py) ← queues, state, data dir
                     ├── Bridge (src/web/bridge.py)   ← queue adapter to ui.py
                     └── Step Schema (src/web/step_schema.py) ← 11 step types
```

### Key Principle

The scheduler engine runs in a **background thread**, blocked on a queue per prompt.
Each step is a JSON payload from `q_out`; each answer is a value pushed to `q_in`.
The frontend renders one step at a time via HTMX partial swaps.

---

## 2. API Contract

### 2.1 Routes

| Method | Path | Purpose | Returns |
|--------|------|---------|---------|
| GET | `/login` | Login page | HTML |
| POST | `/login` | Submit password | 303 → `/app` or HTML with error |
| GET | `/logout` | Revoke auth | 303 → `/login` |
| GET | `/` | Root redirect | 303 → `/app` or `/login` |
| GET | `/app` | Home screen (mode select) | HTML |
| POST | `/start/{mode}` | Start scheduler (single/batch/multi) | 303 → `/session/{sid}` |
| GET | `/session/{sid}` | Session view | HTML |
| POST | `/step/{sid}` | Submit answer to current step | HTML partial (step.html) |
| GET | `/step/{sid}/pending` | Poll for next step | JSON |
| GET | `/download/{sid}/{filename}` | Download result file | FileResponse |
| POST | `/upload` | Upload microplanejamento xlsx | JSON `{status, filename, size}` |
| POST | `/abort/{sid}` | Abort session | JSON `{status: "aborted"}` |
| GET | `/api/sessions` | List active sessions | JSON array |
| GET | `/api/step-types` | Step type definitions | JSON dict |

### 2.2 Auth

- Cookie: `srf_token` (httponly, 24h max-age)
- Password: `SRF_PASSWORD` env var (default: `gazella2024`)
- All routes except `/login` require auth; unauthenticated → 303 → `/login`

### 2.3 HTMX Interactions

| Interaction | Trigger | Target | Swap |
|-------------|---------|--------|------|
| Submit answer | Form `hx-post="/step/{sid}"` | `#step-{step_id}` | `outerHTML` |
| Poll next step | `hx-get="/step/{sid}/pending" hx-trigger="every 1s"` | `#main-content` | `innerHTML` |
| Upload file | `hx-post="/upload"` | `#upload-status` | `innerHTML` |

### 2.4 Form Fields per Step Type

| Step type | Hidden fields | Visible field | Value format |
|-----------|---------------|---------------|-------------|
| `confirmar` | `step_type=confirmar` | Two submit buttons (name=`value`, value=`sim`/`nao`) | `sim`/`nao` |
| `pedir_float` | `step_type`, `default` | Text input name=`value`, +/− buttons | Float string (comma→dot) |
| `pedir_int` | `step_type`, `default` | Text input name=`value`, +/− buttons | Int string |
| `pedir_jornada` | `step_type` | Text input name=`value`, Decimal/HH:MM toggle | Float or `HH:MM` |
| `selecionar` | `step_type` | Submit buttons name=`value`, value=1..N or 0 | 1-indexed string or "0" |
| `selecionar_paginado` | `step_type` | Same as selecionar + `+`/`-` for page nav | 1-indexed, "0", "+" or "-" |
| `prompt` | `step_type` | Text input name=`value` | String |
| `display` | `step_type` | Submit button value=`continuar` | `continuar` |
| `table` | `step_type` | Submit button value=`continuar` | `continuar` |
| `result` | — | Link to `/app` | — |
| `error` | — | Link to `/app` | — |

---

## 3. Step JSON Schema

Every step emitted by the engine has this structure:

```json
{
  "step_id": "step_7",
  "session_id": "a1b2c3d4",
  "type": "confirmar | pedir_float | pedir_int | pedir_jornada | selecionar | selecionar_paginado | prompt | display | table | result | error",
  "prompt": "Aplicar bloqueio global?",
  "default": true,
  "options": {},
  "dashboard": {
    "fazenda_selecionada": "Fazenda São João",
    "equipe_selecionada": "Turma 1",
    "talhoes_selecionados": 12,
    "total_talhoes_fazenda": 15,
    "area_total_fazenda": 450.2,
    "atividades_distribuidas": 87,
    "total_atividades": 120,
    "data_inicio": "2026-01-15",
    "data_termino": "2026-12-20",
    "modo_atual": "Manual",
    "tarifas_carregadas": true,
    "orcamento_estrito": false,
    "timestamp_atualizacao": "2026-05-06T14:30:00"
  },
  "timestamp": "2026-05-06T14:30:00.123456"
}
```

### 3.1 Per-Type `options` Schema

| Type | `options` shape |
|------|----------------|
| `confirmar` | `{}` (default field has the bool) |
| `pedir_float` | `{"allow_zero": bool}` |
| `pedir_int` | `{"allow_zero": bool}` |
| `pedir_jornada` | `{}` |
| `selecionar` | `{"items": ["Item A", "Item B", ...], "zero_label": "Voltar"}` |
| `selecionar_paginado` | `{"items": [...], "page_size": 5, "zero_label": "Voltar"}` |
| `prompt` | `{}` (default field has the string) |
| `display` | `{"body": "multiline text\n...", "level": "info\|warn\|error\|success"}` |
| `table` | `{"headers": ["Col A", "Col B"], "rows": [["val1", "val2"], ...]}` |
| `result` | `{"files": ["dossie_fazenda.xlsx"], "error": null}` |
| `error` | `{"files": [], "error": "Full traceback..."}` |

---

## 4. Tailwind CSS Tokens

### 4.1 Variant A: Raw / Industrial (Dark)

Inject via `<style>` in `base.html` or Tailwind config:

```css
:root {
  --bg: #0A0A0A;
  --surface: #1A1A1A;
  --primary: #00FF66;
  --warning: #FFD600;
  --error: #FF3B3B;
  --info: #00E5FF;
  --muted: #666666;
  --heading: #FFFFFF;
  --on-primary: #0A0A0A;
  --on-surface: #E0E0E0;
  --border: #00FF66;
  --radius: 0px;
  --shadow: none;
  --border-width: 2px;
  --font-body: 'JetBrains Mono', 'Roboto Mono', 'Courier New', monospace;
  --font-scale: 12px/16px/20px/28px;
}
```

### 4.2 Variant B: Neo-Brutalist (Light)

```css
[data-theme="neo-brutalist"] {
  --bg: #FAFAFA;
  --surface: #FFFFFF;
  --primary: #2D6A4F;
  --warning: #E9C46A;
  --error: #E76F51;
  --info: #264653;
  --muted: #ADB5BD;
  --heading: #212529;
  --on-primary: #FFFFFF;
  --on-surface: #495057;
  --border: #1F2937;
  --radius: 4px;
  --shadow: 4px 4px 0px #000000;
  --border-width: 3px;
  --font-body: 'Inter', sans-serif;
  --font-heading: 'Space Grotesk', sans-serif;
  --font-scale: 14px/18px/24px/32px;
}
```

### 4.3 Component CSS Map

| Component | Variant A | Variant B |
|-----------|-----------|-----------|
| Card/Surface | `bg-[var(--surface)]` border 2px `var(--primary)` radius 0 | `bg-[var(--surface)]` border 3px `var(--border)` radius 4px shadow `var(--shadow)` |
| Button primary | `bg-[var(--primary)]` text `var(--on-primary)` border 2px font-bold | `bg-[var(--primary)]` text `var(--on-primary)` border 3px shadow radius 4px |
| Button muted | `bg-[var(--muted)]` text `var(--bg)` | `bg-[var(--muted)]` text `var(--heading)` shadow |
| Button danger | `bg-[var(--error)]` text #fff | `bg-[var(--error)]` text #fff shadow |
| Chip Sim | `bg-[var(--primary)]` text `var(--bg)` bold | Same + shadow |
| Chip Nao | `bg-[var(--error)]` text #fff | Same + shadow |
| Chip Abortar | `bg-[var(--warning)]` text `var(--bg)` | Same + shadow |
| Chip OK | `bg-[var(--info)]` text `var(--bg)` | Same + shadow |
| Input field | border-bottom 2px `var(--primary)`, no bg | border 3px `var(--border)`, white fill, shadow, radius 4px |
| Banner info | border-left 3px `var(--info)`, bg `rgba(0,229,255,0.1)` | Same with shadow |
| Banner warn | border-left 3px `var(--warning)`, bg `rgba(255,214,0,0.1)` | Same with shadow |
| Banner error | border-left 3px `var(--error)`, bg `rgba(255,59,59,0.1)` | Same with shadow |
| Banner success | border-left 3px `var(--primary)`, bg `rgba(0,255,102,0.1)` | Same with shadow |
| Divider | 2px solid `var(--primary)`, full-width | 3px solid `var(--border)`, full-width |
| Sub-divider | 1px dashed `var(--muted)`, full-width | 1px solid #CCC |
| Table | border 1px `var(--border)`, monospace | border 2px `var(--border)`, shadow |
| Dashboard bar | `bg-[var(--surface)]` border-bottom 1px, `text-xs text-[var(--muted)]` | Same + shadow bottom |

---

## 5. Template Structure

### 5.1 File Map

```
src/web/templates/
├── base.html                    ← Layout shell, CSS vars, HTMX, Tailwind CDN
├── login.html                   ← Password gate (extends base)
├── screens/
│   ├── app.html                 ← Home: mode selector + upload + session list
│   └── session.html             ← Active session: step renderer + poll + abort
└── components/
    └── step.html                ← Step renderer (all 11 types via {% if %})
```

### 5.2 base.html Requirements

- Load Tailwind CSS via CDN: `<script src="https://cdn.tailwindcss.com"></script>`
- Load HTMX: `<script src="https://unpkg.com/htmx.org@1.9.10"></script>`
- CSS custom properties for both variants (see §4)
- Dashboard bar at top (only when `session_id` defined) — shows 4 collapsed chips, expandable
- Main content area: `<main id="main-content" class="p-4 max-w-3xl mx-auto">`
- **No JavaScript frameworks** — only HTMX + vanilla JS for stepper buttons

### 5.3 step.html Requirements

This is the **core component**. It must handle all 11 step types.
It is rendered both on initial page load AND via HTMX swap (partial update).

Key behaviors:
- Each step wrapped in `<div id="step-{{ step.step_id }}">` for HTMX targeting
- Forms use `hx-post="/step/{{ session_id }}"` and `hx-target="#step-{{ step.step_id }}"`
- After answer, engine may take 0-5 seconds to produce next step
- If no next step immediately, show "Processando..." spinner with HTMX polling
- `selecionar_paginado` must implement client-side pagination (all items sent; JS slices pages)

### 5.4 Percurso Activity Card (Special Case)

When the step is a `confirmar` with prompt containing "Executar" or percurso activity text,
render as a **full-screen activity card** with 4 bottom chips:

```
┌─────────────────────────┐
│  Atividade: Roçada      │
│  Talhão: T1             │
│  Área: 12.5 ha          │
│                         │
│  ┌────┐ ┌────┐          │
│  │Sim │ │Nao │          │
│  └────┘ └────┘          │
│  ┌────────┐ ┌──┐        │
│  │Abortar │ │OK│        │
│  └────────┘ └──┘        │
└─────────────────────────┘
```

Detection: `step.type == "confirmar"` and activity context in dashboard.

---

## 6. Screen-by-Screen Mapping

### 6.1 Home Screen (`/app`)

Three mode cards stacked vertically:
1. **Smart Scheduler — Fazenda Única** (form with fazenda name input)
2. **Todas as Fazendas (Lote)** (immediate start)
3. **Multi-Equipes** (immediate start)

Below: Upload card (file input, accept `.xlsx,.xlsm,.xls`)
Below: Recent sessions list (clickable links)

### 6.2 Session Screen (`/session/{sid}`)

- Dashboard bar at top (context chips)
- Step content area (renders step.html)
- Abort button at bottom
- When finished: result screen with download links + "Voltar ao Menu" button
- When error: error banner + "Voltar ao Menu" button
- Polling: HTMX `hx-trigger="every 1s"` on `/step/{sid}/pending`

### 6.3 Login Screen (`/login`)

- Simple password field
- "Entrar" button
- Error message on wrong password

---

## 7. Dashboard Context Bar

Always visible during active sessions. Collapsed shows 4 chips; expanded shows all fields.

| Field | Portuguese label | Collapsed? |
|-------|-----------------|------------|
| `fazenda_selecionada` | Fazenda | Yes |
| `equipe_selecionada` | Equipe | Yes |
| `total_talhoes_fazenda` | Talhões | Yes |
| `atividades_distribuidas` / `total_atividades` | Atv | Yes |
| `modo_atual` | Modo | Yes |
| `area_total_fazenda` | Área | No (expanded) |
| `data_inicio` / `data_termino` | Período | No (expanded) |
| `tarifas_carregadas` | Tarifas | No (expanded) |
| `orcamento_estrito` | Orçamento | No (expanded) |
| `timestamp_atualizacao` | Atualizado | No (expanded) |

---

## 8. ASCII → Accented Portuguese Conversion

All `prompt` and `options` text from the CLI engine uses unaccented ASCII (e.g. "Restauracao").
The frontend must convert to proper Portuguese using these rules (from LAYOUT_REPORT §10.9):

| Pattern | Replace with | Example |
|---------|-------------|---------|
| `acao` | `ação` | Restauracao → Restauração |
| `coes` | `ções` | Opcoes → Opções |
| `ario` | `ário` | Sumario → Sumário |
| `arios` | `ários` | Sumarios → Sumários |
| `atorio` | `atório` | Obrigatorio → Obrigatório |
| `aveis` | `áveis` | Navegaveis → Navegáveis |
| `ivel` | `ível` | Possivel → Possível |
| `eis` | `éis` | Refeis → Reféis |
| `ico` | `ico` | (no change — keep as-is) |
| `izacao` | `ização` | Organizacao → Organização |
| `izar` | `izar` | (no change) |
| `logico` | `lógico` | Ecologico → Ecológico |
| `ografico` | `ográfico` | Geografico → Geográfico |
| `onomica` | `onômica` | Economica → Econômica |
| `edido` | `edido` | (no change — "pedido" is correct) |
| `esao` | `esão` | Compressao → Compressão |
| `sao` | `são` | Informacao → Informação |
| `oes` | `ões` | Opcoes → Opções |
| `uida` | `uída` | Concluida → Concluída |
| `uido` | `uído` | Concluido → Concluído |
| `uido` | `uído` | Distribuido → Distribuído |
| `uidos` | `uídos` | Distribuidos → Distribuídos |
| `uido` exception | `ido` | "Rapido" → "Rápido" (not "Rapuído") |

**Exception list** (do NOT convert): `acao` when part of `situacao` → `situação` (yes convert),
but `fracao` → `fração` (yes). Only skip when `acao`/`oes` is part of an English loanword.

### Implementation

Apply in Jinja2 via a custom filter or in the bridge before emitting the step.
The bridge (`session.py`) stores the prompt as-is; conversion is a **frontend concern**.
Recommended: JavaScript function `asciToPt(str)` applied on render.

---

## 9. Mobile Responsiveness

- **Primary target**: Android 5.5"-6.7" (360-412dp width)
- **Layout**: Single column, max-width 640px centered
- **Touch targets**: Minimum 48px height for all buttons/chips
- **Stepper controls**: +/− buttons 48x48px
- **Selection items**: Full-width tappable rows, 48px min height
- **Dashboard bar**: Sticky top, horizontal scroll on narrow screens
- **No hamburger menus** — all navigation is inline
- **Scroll**: Minimal — each step fits in viewport or max 2 scroll-lengths

---

## 10. State Flow

```
┌─────────┐     POST /start/single      ┌──────────┐
│  /app   │ ──────────────────────────▶ │ /session │
│ (home)  │                              │  (step)  │
└─────────┘                              └────┬─────┘
     ▲                                       │
     │            GET /app                   │ POST /step/{sid}
     │         (Voltar ao Menu)              │ (answer submitted)
     │                                       ▼
     │                                 ┌──────────┐
     │                                 │  Engine   │
     │                                 │  Thread   │
     │                                 │ (blocked  │
     │                                 │  on q_in) │
     │                                 └──────────┘
     │                                       │
     │          Step JSON from q_out          │
     │◀──────────────────────────────────────┘
     │
     │  Session finished
     │  (result/error screen)
     └──────────────────────────────────────
```

---

## 11. Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SRF_WEB_MODE` | (unset) | When `1`, ui.py delegates to web bridge |
| `SRF_PASSWORD` | `gazella2024` | Shared login password |
| `SRF_DATA_DIR` | `data` | Base data directory |
| `SRF_STEP_TIMEOUT` | `3600` | Seconds before step answer times out |

---

## 12. File Deliverables for Design Agent

The design agent should produce/replace these files:

| File | Purpose |
|------|---------|
| `src/web/templates/base.html` | Layout shell with both variant CSS |
| `src/web/templates/login.html` | Password gate |
| `src/web/templates/screens/app.html` | Home screen |
| `src/web/templates/screens/session.html` | Session view |
| `src/web/templates/components/step.html` | Step renderer (all 11 types) |
| `src/web/static/app.js` | Optional: stepper logic, pagination, ASCII→PT conversion |

### Constraints

1. **Must use Jinja2 syntax** — `{{ variable }}`, `{% if %}`, `{% for %}`, `{% extends %}`, `{% include %}`
2. **Must use HTMX attributes** — `hx-post`, `hx-get`, `hx-target`, `hx-swap`, `hx-trigger`
3. **Must use Tailwind CSS** (CDN) — utility classes only, no custom CSS files needed
4. **Must support both theme variants** via CSS custom properties + `[data-theme]` selector
5. **Must handle all 11 step types** in step.html
6. **All UI strings in Portuguese (BR)**
7. **No build step** — CDN-only, no npm, no bundler
8. **No JavaScript frameworks** — vanilla JS + HTMX only

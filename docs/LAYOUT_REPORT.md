# SRF v6.3 — Layout Report for Mobile Android UI

> **Target**: Google Stitch visual generation
> **Platform**: Mobile Android (primary), Web app (secondary/future)
> **Language**: All UI strings in Portuguese (BR)
> **Design**: Brutalist — two variants documented
> **Scope**: Full parity with CLI (~35 interactive screens)

---

## 1. App Overview

### Purpose

SRF (Sistema de Restauração Florestal) is a forest restoration planning tool. It takes microplanning spreadsheet data (farms, plots/parcelas, activities, areas) and generates optimized work schedules (cronogramas) with team allocation, budget tracking, and manual-vs-mechanized comparison.

### User Persona

- **Role**: Forest restoration operations planner / field coordinator
- **Context**: Standing in field or at desk, needs quick schedule generation with deep configurability
- **Tech comfort**: Moderate — uses WhatsApp, Excel, but not a developer
- **Primary device**: Android phone (5.5"-6.7" screen)
- **Work pattern**: Configure once per project, run scheduler, review cronograma, export Excel

### Mobile-First Constraints

| Constraint | Implementation |
|---|---|
| Thumb zone | Primary actions in bottom 60% of screen |
| One-handed use | S/N toggles, chips, and steppers preferred over free-text |
| Scroll limits | Max 2 scroll-lengths per screen; paginate beyond that |
| Offline | All computation runs locally; no network required |
| Data persistence | Config saved to `config.json`; session state to `estado_sessao_*.json` |
| Input methods | Numeric keypad for numbers; text keyboard only for names/filters |
| Interruptibility | CHECKPOINT RETROATIVO allows revisiting any prior decision before simulation |

### Application Name & Branding

- **App name**: SRF
- **Full name**: Sistema de Restauração Florestal
- **Version**: 6.3
- **Logo**: Stylized tree (ASCII art in CLI → simplified vector tree for mobile)
- **Tagline**: Planejamento florestal inteligente

---

## 2. Design System

Two brutalist variants are documented. Google Stitch should generate visuals for both.

### 2.1 Variant A: Raw / Industrial

| Property | Value |
|---|---|
| **Typography** | Monospace only — `JetBrains Mono` or `Roboto Mono` |
| **Font scale** | 12px body / 16px section title / 20px screen title / 28px app title |
| **Border radius** | 0px — all corners sharp |
| **Shadows** | None |
| **Borders** | 2px solid, color = primary |
| **Background** | #0A0A0A (near-black) |
| **Surface** | #1A1A1A (dark card) |
| **Dividers** | 2px solid primary, full-width (maps from CLI `linha()`) |
| **Sub-dividers** | 1px dashed secondary, full-width (maps from CLI `sub()`) |
| **Spacing grid** | 8px base; 4px half-step; 16px section gap; 24px screen padding |
| **Motion** | None — instant state changes, no animations |
| **Icon style** | Outlined, 24dp, stroke 1.5px |

#### Color Palette (Variant A)

| Token | Hex | Source (ui.py) | Usage |
|---|---|---|---|
| `primary` | #00FF66 | `G` (green) | Borders, active states, success messages, prompt prefixes |
| `warning` | #FFD600 | `Y` (yellow) | Warnings, caution prompts |
| `error` | #FF3B3B | `R` (red) | Errors, destructive actions |
| `accent` | #00E5FF | `C` (cyan) | Interactive text, item labels, user-entered values |
| `secondary` | #666666 | `DM` (dim) | Secondary text, disabled, hints, "Voltar" option |
| `heading` | #FFFFFF | `BL` (bold) + `G` | Screen titles, section headers |
| `on-primary` | #0A0A0A | — | Text on primary-color backgrounds |
| `on-surface` | #E0E0E0 | — | Body text on dark surfaces |
| `success` | #00FF66 | `G` | `ok()` messages (prefix `+`) |
| `background` | #0A0A0A | — | Screen background |

### 2.2 Variant B: Neo-Brutalist (Notion-style)

| Property | Value |
|---|---|
| **Typography** | `Inter` for body / `Space Grotesk` for headings |
| **Font scale** | 14px body / 18px section title / 24px screen title / 32px app title |
| **Border radius** | 4px — slight rounding |
| **Shadows** | 4px 4px 0px #000 (hard offset shadow on cards/buttons) |
| **Borders** | 3px solid #000 |
| **Background** | #FAFAFA (off-white) |
| **Surface** | #FFFFFF (white card) |
| **Dividers** | 3px solid #000, full-width |
| **Sub-dividers** | 1px solid #CCC |
| **Spacing grid** | 8px base; 4px half-step; 16px section gap; 20px screen padding |
| **Motion** | 150ms ease for state changes; 200ms slide for screen transitions |
| **Icon style** | Filled, 24dp, stroke 2px |

#### Color Palette (Variant B)

| Token | Hex | Source (ui.py) | Usage |
|---|---|---|---|
| `primary` | #2D6A4F | `G` remapped | Borders, active states, success |
| `warning` | #E9C46A | `Y` remapped | Warnings |
| `error` | #E76F51 | `R` remapped | Errors |
| `accent` | #264653 | `C` remapped | Interactive text, labels |
| `secondary` | #ADB5BD | `DM` remapped | Secondary text, hints |
| `heading` | #212529 | `BL` remapped | Screen titles |
| `on-primary` | #FFFFFF | — | Text on primary backgrounds |
| `on-surface` | #495057 | — | Body text on white surfaces |
| `success` | #40916C | `G` remapped | Success messages |
| `background` | #FAFAFA | — | Screen background |
| `shadow` | #000000 | — | Hard offset shadow color |

### 2.3 Component Primitives (CLI → Mobile Mapping)

Each CLI input function maps to a mobile UI component. Both variants share the same component structure; styling differs per palette.

#### 2.3.1 `prompt(msg, default)` → Text Field

| Property | Value |
|---|---|
| **Type** | Text input field |
| **Label** | `msg` text above field |
| **Placeholder** | `default` value shown as ghost text |
| **Style A** | Monospace, border-bottom only (2px primary), no background |
| **Style B** | 3px border, white fill, hard shadow, rounded 4px |
| **Keyboard** | Default keyboard; switch to numeric for `pedir_float`/`pedir_int` |
| **Return** | String; empty input returns `str(default)` if default provided |

```
Variant A:
  Nome da turma (ex: Rocadores)
  Turma 1▌

Variant B:
  Nome da turma (ex: Rocadores)
  ┌──────────────────────────────────┐
  │ Turma 1                          │  ████
  └──────────────────────────────────┘
```

#### 2.3.2 `confirmar(msg, default)` → S/N Toggle Chip Pair

| Property | Value |
|---|---|
| **Type** | Segmented toggle (two chips) |
| **Label** | `msg` text above toggle |
| **Options** | `Sim` (left) / `Não` (right) |
| **Default highlight** | Capital letter in CLI `[S/n]` or `[s/N]` → pre-selected chip |
| **Style A** | Chips with 2px border; selected = filled primary; unselected = outline only |
| **Style B** | Chips with 3px border + shadow; selected = filled primary (white text); unselected = white fill |
| **Return** | Boolean |

```
Variant A:
  Aplicar bloqueio global?
  ┌──────────┐ ┌──────────┐
  │ ██ Sim ██ │ │   Não    │
  └──────────┘ └──────────┘

Variant B:
  Aplicar bloqueio global?
  ┌──────────┐ ┌──────────┐
  │ ██ Sim ██ │ │   Não    │  ████
  └──────────┘ └──────────┘
```

#### 2.3.3 `pedir_float(msg, default, allow_zero)` → Number Stepper

| Property | Value |
|---|---|
| **Type** | Number input with stepper controls |
| **Label** | `msg` text above |
| **Default** | `default` shown as initial value |
| **Min** | 0 if `allow_zero=True`, else >0 |
| **Step** | 0.1 for float; 1 for int |
| **Validation** | Invalid → inline error toast "Valor inválido." (maps from `aviso()`) |
| **Keyboard** | Numeric with decimal separator |
| **Comma handling** | Auto-convert `,` → `.` (Portuguese locale) |
| **Return** | Float |

```
Variant A:
  Prazo META para conclusão (meses)
   [−]   6.0   [+]

Variant B:
  Prazo META para conclusão (meses)
   [−]   6.0   [+]              ████
```

#### 2.3.4 `pedir_int(msg, default, allow_zero)` → Integer Stepper

Same as `pedir_float` but:
- No decimal step (step = 1)
- Keyboard: numeric without decimal
- Return: Integer

#### 2.3.5 `pedir_jornada(msg, default)` → Dual-Mode Jornada Input

| Property | Value |
|---|---|
| **Type** | Segmented input: Decimal mode / Time mode |
| **Label** | `msg` text above |
| **Decimal mode** | Single number field (e.g., `6.5`) |
| **Time mode** | Two fields: Hours + Minutes (e.g., `6h30`) |
| **Mode toggle** | Chip pair: `Decimal` / `Horário` |
| **Validation** | Invalid → inline error "Valor inválido. Use decimal (6.5) ou horário (6:30 = 6h30)." |
| **Parsing** | Accepts: `6.5`, `6:30`, `6h30`, `6e30`, `6H30`, `6E30` |
| **Return** | Float (hours as decimal) |

```
Variant A:
  Jornada efetiva diária
  [Decimal] [Horário]
   6.5 h

Variant B:
  Jornada efetiva diária
  [Decimal] [Horário]
   6 h  30 min                   ████
```

#### 2.3.6 `selecionar(titulo, itens, zero_label)` → Selection List

| Property | Value |
|---|---|
| **Type** | Full-screen radio list |
| **Title** | `titulo` as screen header |
| **Items** | Numbered list, 1-based |
| **Zero option** | `[0] {zero_label}` (default: "Voltar") — rendered as secondary/back action at bottom |
| **Style A** | Each item: monospace, 2px left border accent on selected, radio dot |
| **Style B** | Each item: card with 3px border, hard shadow, radio button |
| **Return** | Selected item object, or `None` for zero/back |

#### 2.3.7 `selecionar_paginado(titulo, itens, page_size, zero_label)` → Paginated Selection List

| Property | Value |
|---|---|
| **Type** | Paginated radio list with page navigation |
| **Title** | `titulo` + page counter `(pag 1/3)` |
| **Page size** | Default 5 items per page |
| **Navigation** | `[−] Anterior` / `[+] Próxima` chips; `[0] Voltar` back button |
| **Page indicator** | Dots: `● ○ ○` (current/total pages) |
| **Style A** | Same as selecionar + page dots below list + nav chips |
| **Style B** | Same as selecionar + swipe gesture for page change + page dots |
| **Return** | Zero-based index of selected item, or `-1` for back |

#### 2.3.8 `aviso(m)` → Warning Toast/Banner

| Property | Value |
|---|---|
| **Type** | Inline banner (non-blocking) |
| **Prefix** | `!` icon |
| **Color** | `warning` token |
| **Duration** | Persistent until dismissed or screen change |
| **Style A** | Yellow text on dark background, `!` in left margin |
| **Style B** | Yellow banner with 3px border, hard shadow, `⚠` icon |

#### 2.3.9 `erro(m)` → Error Toast/Banner

| Property | Value |
|---|---|
| **Type** | Inline banner (non-blocking) |
| **Prefix** | `✕` icon |
| **Color** | `error` token |
| **Duration** | Persistent until dismissed |
| **Style A** | Red text on dark background |
| **Style B** | Red banner with 3px border, hard shadow, `✕` icon |

#### 2.3.10 `ok(m)` → Success Toast/Banner

| Property | Value |
|---|---|
| **Type** | Inline banner (non-blocking) |
| **Prefix** | `+` icon |
| **Color** | `success` token |
| **Duration** | Auto-dismiss after 3 seconds |
| **Style A** | Green text on dark background |
| **Style B** | Green banner with hard shadow, `✓` icon |

#### 2.3.11 `linha(c="=")` → Full-Width Divider

| Property | Value |
|---|---|
| **Type** | Horizontal rule |
| **Character** | `=` (default) or custom |
| **Style A** | 2px solid `primary`, full width |
| **Style B** | 3px solid #000, full width |

#### 2.3.12 `sub(c="-")` → Sub-Divider

| Property | Value |
|---|---|
| **Type** | Horizontal rule (secondary) |
| **Character** | `-` (default) |
| **Style A** | 1px dashed `secondary` |
| **Style B** | 1px solid #CCC |

#### 2.3.13 `cabecalho(sub_titulo)` → Screen Header (Full)

| Property | Value |
|---|---|
| **Type** | Full screen header with clear/reset |
| **Elements** | Logo → App name + version → Subtitle (if provided) → Timestamp |
| **Behavior** | Clears previous screen content (in CLI: `cls`/`clear`). In mobile: replaces screen content. |
| **Style A** | ASCII tree → `══════` → `SRF v6.3` centered → subtitle dim → timestamp dim → `══════` |
| **Style B** | Tree icon (vector) → bold title → subtitle → timestamp → divider |

#### 2.3.14 `subcabecalho(sub_titulo)` → Section Header (Incremental)

| Property | Value |
|---|---|
| **Type** | In-context section header (does NOT clear previous content) |
| **Elements** | Sub-divider → App name + version → Subtitle → Timestamp → Sub-divider |
| **Style A** | `────` → `SRF v6.3` centered → subtitle dim → timestamp dim → `────` |
| **Style B** | Thin line → bold title → subtitle → thin line |

---

## 3. Navigation Models

Three models are proposed. Google Stitch should generate visuals for all three to allow comparison.

### 3.1 Model A: Bottom Navigation Bar

```
┌──────────────────────────────────┐
│  [Dashboard Context Card]        │
│                                  │
│  ┌────────────────────────────┐  │
│  │  Main content area         │  │
│  │  (scrollable)              │  │
│  │                            │  │
│  │                            │  │
│  └────────────────────────────┘  │
│                                  │
│  ══════════════════════════════  │
│  │ 🌲  │ 📊  │ ⚙️  │ ≡  │      │
│  │Home │Sched│Conf │More│      │
│  └─────┴─────┴─────┴────┘      │
└──────────────────────────────────┘
```

**Bottom bar items (4 fixed + overflow):**

| Position | Icon | Label | Maps to CLI option |
|---|---|---|---|
| 1 | `park` | Início | Main menu loop |
| 2 | `event_note` | Cronograma | Option [1] Smart Scheduler |
| 3 | `tune` | Config | Options [2]-[6] combined |
| 4 | `dashboard` | Monitor | Option [M] Monitor |

**Overflow drawer (swipe up from "More"):**

| Icon | Label | Maps to CLI option |
|---|---|---|
| `upload_file` | Importar Tarifas | Option [2] |
| `transform` | Normalizar CT | Option [3] |
| `swap_horiz` | De/Para | Option [4] |
| `swap_horiz` | Trocar Micro | Option [5] |
| `list_alt` | Fazendas CT | Option [6] |
| `output` | Sair | Option [0] |

**Pros**: Standard Android pattern, thumb-friendly, fast access to scheduler
**Cons**: Limited to 4-5 items; secondary features hidden

### 3.2 Model B: Hamburger / Drawer Menu

```
┌──────────┬───────────────────────┐
│ ☰ ≡≡≡≡≡≡ │                       │
│          │  Main content area    │
│ 🌲 Início│  (full width)         │
│ ──────── │                       │
│ 📊 Smart │                       │
│ 📤 Import│                       │
│ 🔄 NormCT│                       │
│ ↔  De/Par│                       │
│ 📁 Trocar│                       │
│ 🏘 FazCT │                       │
│ 📡 Monitor│                      │
│ ──────── │                       │
│ 🚪 Sair  │                       │
└──────────┴───────────────────────┘
```

**Drawer items (all 8 options visible):**

| Icon | Label | Maps to CLI option |
|---|---|---|
| `park` | Início | Main menu home |
| `event_note` | Smart Scheduler | Option [1] |
| `upload_file` | Importar Tarifas | Option [2] |
| `transform` | Normalizar CT→STG | Option [3] |
| `swap_horiz` | Mapeamentos De/Para | Option [4] |
| `folder_open` | Trocar Micro | Option [5] |
| `domain` | Fazendas CT | Option [6] |
| `dashboard` | Monitor | Option [M] |
| `exit_to_app` | Sair | Option [0] |

**Pros**: All options visible, extensible, full-width content area
**Cons**: Hidden by default, requires tap to open, not thumb-friendly for top items

### 3.3 Model C: Home Screen Grid (Launchpad)

```
┌──────────────────────────────────┐
│  [Dashboard Context Card]        │
│                                  │
│  ┌──────────┐  ┌──────────┐     │
│  │ 📊       │  │ 📤       │     │
│  │ Smart    │  │ Importar │     │
│  │ Scheduler│  │ Tarifas  │     │
│  └──────────┘  └──────────┘     │
│                                  │
│  ┌──────────┐  ┌──────────┐     │
│  │ 🔄       │  │ ↔        │     │
│  │ Normaliz │  │ De/Para  │     │
│  │ CT→STG   │  │ Mapeam.  │     │
│  └──────────┘  └──────────┘     │
│                                  │
│  ┌──────────┐  ┌──────────┐     │
│  │ 📁       │  │ 🏘       │     │
│  │ Trocar   │  │ Fazendas │     │
│  │ Micro    │  │ CT       │     │
│  └──────────┘  └──────────┘     │
│                                  │
│  ┌──────────┐  ┌──────────┐     │
│  │ 📡       │  │ 🚪       │     │
│  │ Monitor  │  │ Sair     │     │
│  └──────────┘  └──────────┘     │
└──────────────────────────────────┘
```

**Pros**: Brutalist aesthetic fits perfectly, all options visible, no hidden menus, large tap targets
**Cons**: Requires a home screen visit between features, more scrolling

### 3.4 Back Stack Behavior

All three models share the same back stack logic:

| Current Screen | Back Action | Destination |
|---|---|---|
| Any scheduler sub-screen | System back / ← button | Previous screen in flow |
| CHECKPOINT RETROATIVO (hub) | Back | Main menu (option [6] = "Voltar ao seletor") or Continue (option [7]) |
| CHECKPOINT option [6] "Voltar ao seletor" | Confirms | Farm/Scope selection (Screen S0a) |
| Farm selection | Back | Main menu |
| Main menu | Back | Exit confirmation |
| Any `selecionar_paginado` | Select [0] "Voltar" | Returns -1 / None to caller |
| Any `confirmar` | N/A | Inline — no navigation, just state change |

**Key principle**: The CHECKPOINT RETROATIVO screen is a **hub** that allows jumping to any prior configuration step. On mobile, this maps to a modal bottom sheet or a dedicated "Review" floating action button that's always visible during the scheduler flow.

### 3.5 Screen Transition Model

| Transition Type | Style A | Style B |
|---|---|---|
| Forward (push) | Instant replace | 200ms slide-right |
| Back (pop) | Instant replace | 200ms slide-left |
| Modal open | Instant overlay | 200ms slide-up |
| Modal close | Instant dismiss | 200ms slide-down |
| Tab switch (bottom nav) | Instant replace | 150ms fade |

---

## 4. Persistent Elements

### 4.1 Dashboard Context Card

This element appears at the top of every major screen (maps from `context.py` → `dashboard_header()`). It is always visible and updates in real-time as the user makes choices.

#### Desktop/Tablet Layout (Rich Table)

```
┌──────────────────────────────────────────────────────────────────┐
│  Dashboard de Contexto                                           │
├───────────────┬──────────────┬──────────┬──────────┬─────────────┤
│  Fazenda      │  Equipe      │  Talhões │  Ativid. │  Datas      │
├───────────────┼──────────────┼──────────┼──────────┼─────────────┤
│  São João     │  SWG         │  12/15   │  0/8     │  Início:    │
│  12/15 talh.  │              │          │          │  01/03/2026 │
│  450,0 ha     │              │          │          │  Término:   │
│               │              │          │          │  01/09/2026 │
├───────────────┴──────────────┴──────────┴──────────┴─────────────┤
│  Modo: single │ Tarifas: 42 │ Orçamento: Flexível              │
└──────────────────────────────────────────────────────────────────┘
```

#### Mobile Adaptation: Expandable Status Bar (collapsed by default, tap to expand)

```
Collapsed:
┌──────────────────────────────────────────┐
│ 🌲 São João │ 👥 SWG │ 🗺 12/15 │ 📋 0/8 │ ▼
└──────────────────────────────────────────┘

Expanded:
┌──────────────────────────────────────────┐
│ Fazenda: São João (450,0 ha)             │
│ Equipe: SWG                              │
│ Talhões: 12/15 selecionados              │
│ Atividades: 0/8 distribuídas             │
│ Datas: 01/03/2026 → 01/09/2026           │
│ Modo: single │ Tarifas: 42 │ Flexível    │
└──────────────────────────────────────────┘
```

**Recommendation**: Expandable status bar — saves screen space on mobile while keeping key info visible. The collapsed row shows the 4 most important chips. Tapping expands to full details.

#### Data Fields

| Field | Type | Source | Updated By |
|---|---|---|---|
| `fazenda_selecionada` | string or null | `contexto_sessao` | `atualizar_fazenda()` — when farm is selected |
| `equipe_selecionada` | string or null | `contexto_sessao` | `atualizar_equipe()` — when team filter applied |
| `talhoes_selecionados` | list | `contexto_sessao` | `definir_escopo_talhoes()` — when scope is filtered |
| `total_talhoes_fazenda` | int | `contexto_sessao` | `atualizar_fazenda()` / `definir_escopo_talhoes()` |
| `area_total_fazenda` | float | `contexto_sessao` | `atualizar_fazenda()` — sum of area column |
| `atividades_distribuidas` | int | `contexto_sessao` | `atualizar_atividades()` — after turma linking |
| `total_atividades` | int | `contexto_sessao` | `atualizar_atividades()` |
| `data_inicio` | string or null | `contexto_sessao` | `definir_datas()` — in project config |
| `data_termino` | string or null | `contexto_sessao` | `definir_datas()` |
| `modo_atual` | string or null | `contexto_sessao` | `atualizar_modo()` — "single", "lote", "multi_equipes" |
| `tarifas_carregadas` | int | `contexto_sessao` | `atualizar_configuracoes()` — from config |
| `orcamento_estrito` | bool | `contexto_sessao` | `atualizar_configuracoes()` — from config |

### 4.2 Status Bar

Below the dashboard card, a secondary status line appears (maps from `menu_principal()` status text):

**Desktop**:
```
┌──────────────────────────────────────────┐
│ Base: 5 fazendas │ 23 talhões │ 8 atvs  │
│ Tarifas: 42 │ STG: Sim │ Orç. estrito: S│
└──────────────────────────────────────────┘
```

**Mobile** (single scrollable chip row below dashboard):
```
│ 5 fazendas │ 23 talhões │ 8 atvs │ 42 tarifas │ STG ✓ │ Estrito ✓  │
```

### 4.3 App Header (from `cabecalho()`)

Every screen shows a persistent app header:

**Variant A**:
```
════════════════════════════════════════
        [ SRF ] v6.3
    Subtitle (if any)
      05/05/2026 14:30
════════════════════════════════════════
```

**Variant B**:
```
┌──────────────────────────────────────┐
│  🌲 SRF v6.3                        │
│  Subtitle                            │
│  05/05/2026 14:30                    │
└──────────────────────────────────────┘
```

**Mobile**: Rendered as a top app bar with tree icon, version, and timestamp. The subtitle becomes the screen title. Collapsible on scroll.

### 4.4 CHECKPOINT Floating Action Button

During the scheduler flow (after Screen S8 through Screen S14), a **floating "Review" button** is always visible. Tapping it opens the CHECKPOINT RETROATIVO modal (Screen S15).

| Property | Value |
|---|---|
| **Icon** | `edit_note` (Material) |
| **Label** | "Revisar" |
| **Position** | Bottom-right, 16dp from edges, above bottom nav |
| **Style A** | Monospace, 2px primary border, dark fill, green icon |
| **Style B** | 3px border, hard shadow, primary fill, white icon |

---

## 5. Screen Catalog

Every interactive screen in the application, with ultra-detailed specs for mobile layout.

### Naming Convention

- **S** = Single farm flow
- **B** = Batch (all farms) flow
- **M** = Multi-equipes flow
- **H** = Home/menu screens

---

### H0 — Splash / Initialization

| Property | Value |
|---|---|
| **Screen ID** | H0 |
| **Title** | SRF — Sistema de Restauração Florestal |
| **Parent** | None (app launch) |
| **Children** | H1 (main menu) |

#### Layout Zones

| Zone | Content |
|---|---|
| **Header** | Full `cabecalho()` — tree logo, app name, version |
| **Center** | Loading spinner or "Inicializando sistema..." (dim text) |
| **Footer** | None |

#### Interactive Elements

None — auto-advances after config loads.

#### Data State

- Loads `config.json`
- Finds default micro path and CT path
- If demo mode: rebuilds demo file
- If no micro found: transitions to file picker (H5-like flow)

#### Transitions

| Trigger | Destination |
|---|---|
| Config loaded successfully | H1 (main menu) |
| No micro file found | File picker sub-flow |

---

### H1 — Main Menu

| Property | Value |
|---|---|
| **Screen ID** | H1 |
| **Title** | Menu Principal |
| **Parent** | H0 |
| **Children** | S0, H2, H3, H4, H5, H6, H7 |

#### Layout Zones

| Zone | Content |
|---|---|
| **Top** | Dashboard Context Card (collapsed) |
| **Below** | Status chip row |
| **Main** | 7 menu options + exit |
| **Bottom** | Navigation bar (if Model A) |

#### Menu Options (exact CLI labels)

| # | Icon | Label | Destination |
|---|---|---|---|
| 1 | `event_note` | Smart Scheduler (Operacional HH/HM) | S0 |
| 2 | `upload_file` | Importar Tarifas (CT real/manual) | H2 |
| 3 | `transform` | Normalizar CT317/CT → STG (auto) | H3 |
| 4 | `swap_horiz` | Mapeamentos de_para (micro → tarifa) | H4 |
| 5 | `folder_open` | Trocar planilha de microplanejamento (.xlsx) | H5 |
| 6 | `domain` | Fazendas micro vs CT (lista fazendas_ct) | H6 |
| M | `dashboard` | Abrir Monitor em Janela Separada | H7 |
| 0 | `exit_to_app` | Sair | Exit confirmation |

#### Status Lines (shown below dashboard)

| Line | Content |
|---|---|
| 1 | `Base: {N} fazendas \| {N} talhões \| {N} atividades` |
| 2 | `Tarifas: {N} carregadas \| STG: Sim/Não` |
| 3 | `Orçamento estrito: Sim/Não` |
| 4 (conditional) | `Empresas (EQUIPE): {N} ({list up to 5}...)` — only if `equipe` column exists |
| 5 (conditional) | `Microplanejamento: {basename}` — only if micro loaded |
| 6 (conditional) | `DEMO: opção [1] = maior fazenda do micro (município Ulianópolis), tarifas = CT 313.` |

#### Interactive Elements

| Element | Type | Default |
|---|---|---|
| Option selector | Selection list (maps from `prompt("Opção")`) | None |

#### Data State

- `cfg` (config dict) — loaded and saved each loop iteration
- `df` (DataFrame) — loaded micro data
- `micro_padrao` — path to current micro file
- `demo_mode` — boolean

#### Transitions

| Trigger | Destination |
|---|---|
| Select [1] | S0 (farm selection) |
| Select [2] | H2 (importar tarifas) |
| Select [3] | H3 (normalizar CT) |
| Select [4] | H4 (de/para) |
| Select [5] | H5 (trocar micro) |
| Select [6] | H6 (fazendas CT) |
| Select [M] | H7 (monitor) |
| Select [0] | Exit confirmation dialog |

---

### H2 — Importar Tarifas (CT_313)

| Property | Value |
|---|---|
| **Screen ID** | H2 |
| **Title** | Importar Tarifas Orçadas (CT_313) |
| **Parent** | H1 |
| **Children** | File picker, sheet selector, column mapper |

#### Sub-Screens

**H2a — File Picker**: `selecionar_arquivo("PLANILHA DE ORÇAMENTO (CT_313 ou Tarifas)")` — paginated folder/file navigator

**H2b — Sheet Selection**: `selecionar("SELECIONE A ABA (ex: Preço Final)", sheet_names)` — radio list of sheet names

**H2c — Column Mapping**:
1. Auto-detect activity column → show `MAPEAMENTO: Atividade: {col_name}`
2. `confirmar("Usar este mapeamento?")` — if No: manual column selection
3. `selecionar_paginado("COLUNA DA ATIVIDADE", cols)` — paginated
4. `selecionar_paginado("COLUNA DE HH/HA", cols)` — paginated, [0]=ignorar
5. `selecionar_paginado("COLUNA DE PREÇO UNITÁRIO", cols)` — paginated, [0]=ignorar
6. Post-import summary (HH zeroed, price zeroed warnings)

#### Interactive Elements

| Element | Type | Notes |
|---|---|---|
| File browser | Paginated list with folder navigation | Maps from `selecionar_arquivo()` |
| Sheet selector | Radio list | Maps from `selecionar()` |
| Column mappers | Paginated selectors (3) | Maps from `selecionar_paginado()` |
| Use auto-mapping? | S/N toggle | Maps from `confirmar()` |

#### Data State Out

- `cfg["tarifas"]` — updated with imported tariff data
- `cfg` saved to `config.json`

#### Transitions

| Trigger | Destination |
|---|---|
| Import complete + [ENTER] | H1 (main menu) |
| Cancel at any step | H1 (main menu) |

---

### H3 — Normalizar CT317/CT → STG

| Property | Value |
|---|---|
| **Screen ID** | H3 |
| **Title** | Normalizar CT (CT317 Real) → STG_TARIFAS |
| **Parent** | H1 |
| **Children** | File picker, integration confirmation |

#### Sub-Screens

**H3a — File Picker**: `selecionar_arquivo("CT BRUTA/REAL (.xlsm ou .xlsx)")`

**H3b — Processing**: Non-interactive — shows progress indicator

**H3c — Result**:
- Success: `+ Gerado CT_317_NORMALIZADA.xlsx: {N} atividades (modo somente HH).`
- Then: `confirmar("Integrar STG_TARIFAS em config.json (substitui tarifas existentes)?", default=True)`
- If Yes: `+ {N} tarifas integradas no config.`
- If "Preço Final" tab not found: `✕ Aba 'Preço Final' não encontrada neste arquivo.`

#### Interactive Elements

| Element | Type | Default |
|---|---|---|
| File browser | Paginated list | — |
| Integrate? | S/N toggle | Sim (True) |

#### Data State Out

- `cfg["tarifas"]` — replaced if integrated
- Output file: `CT_317_NORMALIZADA.xlsx`

#### Transitions

| Trigger | Destination |
|---|---|
| Complete + [ENTER] | H1 |

---

### H4 — Mapeamentos De/Para

| Property | Value |
|---|---|
| **Screen ID** | H4 |
| **Title** | Mapeamentos de_para (micro → tarifa) |
| **Parent** | H1 |
| **Children** | Include/alter pair, remove pair, list catalog |

#### Layout Zones

| Zone | Content |
|---|---|
| **Header** | `subcabecalho("MAPEAMENTOS de_para (micro → tarifa)")` |
| **List** | Existing mappings: `{key:36} → {value:36}` (up to 35 shown) |
| **Actions** | 4-option menu |

#### Menu Options

| # | Label | Sub-flow |
|---|---|---|
| 1 | Incluir ou alterar par | H4a |
| 2 | Remover par | H4b |
| 3 | Listar catálogo de TARIFAS | H4c |
| 0 | Voltar | H1 |

#### H4a — Include/Alter Mapping

1. `confirmar("Escolher atividade da planilha carregada?", default=True)`
   - If Yes: `selecionar_paginado("ATIVIDADE no micro", atividades_micro, page_size=8)`
   - If No: `prompt("Nome EXATO da atividade no microplanejamento", "")`
2. `confirmar("Escolher tarifa na lista importada?", default=True)`
   - If Yes: `selecionar_paginado("TARIFA (orçamento)", nomes_tarifa, page_size=8)`
   - If No: `prompt("Nome da TARIFA (chave em tarifas)", "")`
3. If tariff not in config: `confirmar("'{name}' não está em tarifas. Gravar mesmo assim?", default=False)`

#### H4b — Remove Mapping

`selecionar_paginado("REMOVER mapeamento", [keys])` — select mapping to remove

#### H4c — List Catalog

Display up to 60 tariff names. `[ENTER]` to continue.

#### Data State Out

- `cfg["de_para"]` — updated dict

#### Transitions

| Trigger | Destination |
|---|---|
| Select [0] | H1 |

---

### H5 — Trocar Planilha de Microplanejamento

| Property | Value |
|---|---|
| **Screen ID** | H5 |
| **Title** | Trocar Microplanejamento |
| **Parent** | H1 |
| **Children** | File picker |

#### Sub-Screens

**H5a — File Picker**: `selecionar_arquivo("NOVO MICROPLANEJAMENTO (.xlsx)")`

**H5b — Load Result**:
- Success: `+ Micro atualizado: {basename} | {N} registros | {N} fazendas | de_para +{N} novos mapeamentos.`
- If auto-load fails: warning + retry with interactive column mapping

#### Interactive Elements

| Element | Type |
|---|---|
| File browser | Paginated list |

#### Data State Out

- `cfg["micro_padrao"]` — updated path
- `df` — new DataFrame loaded
- `cfg["de_para"]` — may gain new auto-mappings

#### Transitions

| Trigger | Destination |
|---|---|
| Load complete + [ENTER] | H1 |

---

### H6 — Fazendas Micro vs CT

| Property | Value |
|---|---|
| **Screen ID** | H6 |
| **Title** | Fazendas — micro vs lista CT (orçamento) |
| **Parent** | H1 |
| **Children** | 6 sub-actions |

#### Layout Zones

| Zone | Content |
|---|---|
| **Info** | `No micro agora: {N} fazenda(s)` / `Na lista fazendas_ct: {N}` |
| **Warning** | Missing farms list (if any) |
| **Actions** | 7-option menu |

#### Menu Options

| # | Label | Sub-flow |
|---|---|---|
| 1 | Ver / listar fazendas_ct | Display list + [ENTER] |
| 2 | Adicionar uma fazenda a fazendas_ct | `prompt("Nome EXATO como no micro ou na CT", "")` |
| 3 | Importar TODAS as fazendas do micro para fazendas_ct | `confirmar("Substituir fazendas_ct pelas {N} fazendas únicas do micro? (não altera a planilha CT .xlsm)", default=False)` |
| 4 | Remover uma fazenda da lista | `selecionar_paginado("REMOVER", ct_list, page_size=10)` |
| 5 | Colar vários nomes (vírgula ou ponto-e-vírgula) | `prompt("Nomes separados por vírgula ou ;", "")` |
| 6 | Limpar lista (fazendas_ct = []) | `confirmar("Zerar fazendas_ct?", default=False)` |
| 0 | Voltar | H1 |

#### Data State Out

- `cfg["fazendas_ct"]` — updated list

#### Transitions

| Trigger | Destination |
|---|---|
| Select [0] | H1 |

---

### H7 — Abrir Monitor em Janela Separada

| Property | Value |
|---|---|
| **Screen ID** | H7 |
| **Title** | Abrir Monitor Externo |
| **Parent** | H1 |
| **Children** | None |

#### Layout Zones

| Zone | Content |
|---|---|
| **Header** | `subcabecalho("ABRIR MONITOR EXTERNO")` |
| **Selector** | Feed type selection |
| **Result** | Launch confirmation |

#### Interactive Elements

| Element | Type | Default |
|---|---|---|
| Feed type | Radio list | [1] meta |

**Options:**

| # | Label |
|---|---|
| 1 | meta — Operação e metas |
| 2 | rendimentos — HH/ha por atividade |
| 3 | relatórios — Buffer de relatórios |

#### Transitions

| Trigger | Destination |
|---|---|
| Feed selected + launch | H1 (monitor opens in separate window/process) |

---

### S0 — Farm / Mode Selection

| Property | Value |
|---|---|
| **Screen ID** | S0 |
| **Title** | Selecione a Fazenda ou Modo |
| **Parent** | H1 (main menu option [1]) |
| **Children** | S0a (empresa filter), S1 (single farm), B1 (batch), M1 (multi-equipes) |

#### Pre-Condition: Empresa Filter

If the DataFrame has an `equipe` column with multiple values, **S0a** appears first:

**S0a — Filtro por Empresa (Equipe)**

| Element | Type | Items |
|---|---|---|
| Company selector | Radio list | `[TODAS]`, equipe1, equipe2, ... |

After filter: `+ Filtrado por equipe: {name} ({N} registros, {N} atividade(s), {N} fazenda(s))`

#### Farm/Mode Selection (S0)

| Element | Type | Items |
|---|---|---|
| Selection list | Radio list | See below |

**Options:**

| # | Label | Destination |
|---|---|---|
| 1 | TODAS AS FAZENDAS (equipe única) | B1 (batch mode) |
| 2 | MULTI-EQUIPES (carteiras separadas) | M1 (multi-equipes) |
| 3..N | {farm_name} | S1 (single farm scheduler) |
| 0 | Voltar | H1 |

**If only 1 farm exists**: Skip this screen. Auto-select with `+ Fazenda única no escopo: {name}`.

#### Data State

- `df_scope` — filtered DataFrame
- `fazendas` — list of farm names
- `contexto_sessao.atualizar_equipe()` — if empresa filter applied

---

### S1 — Scope by Methodology

| Property | Value |
|---|---|
| **Screen ID** | S1 |
| **Title** | Escopo por Metodologia |
| **Parent** | S0 |
| **Children** | S2 |
| **Condition** | Only if DataFrame has `metodologia` column with 2+ distinct values |

#### Interactive Elements

| Element | Type | Items |
|---|---|---|
| Methodology scope | Radio list | See below |

**Options:**

| # | Label | Sub-prompt |
|---|---|---|
| 1 | TODAS AS METODOLOGIAS | None (select all) |
| 2 | SELECIONAR METODOLOGIAS POR LISTA | `prompt("Metodologias", "")` — type indices like `1,2,4` or `1-3` |
| 3 | SELECIONAR METODOLOGIAS POR NOME | `prompt("Nomes das metodologias (separados por vírgula)", "")` |
| 4 | FILTRAR METODOLOGIAS POR TEXTO | `prompt("Texto para filtrar metodologia", "")` |

---

### S2 — Scope by Talhão

| Property | Value |
|---|---|
| **Screen ID** | S2 |
| **Title** | Escopo por Talhão |
| **Parent** | S1 (or S0 if S1 skipped) |
| **Children** | S3 |
| **Condition** | Only if 2+ talhões exist |

#### Interactive Elements

| Element | Type | Items |
|---|---|---|
| Talhão scope | Radio list | See below |

**Options:**

| # | Label | Sub-prompt |
|---|---|---|
| 1 | TODOS OS TALHÕES | None (select all) |
| 2 | SELECIONAR TALHÕES POR LISTA | `prompt("Talhões", "")` — indices `1,3,7` or `1-4` |
| 3 | FILTRAR TALHÕES POR TEXTO | `prompt("Texto para filtrar talhões", "")` |

---

### S3 — Terrain Evaluation / Declivity

| Property | Value |
|---|---|
| **Screen ID** | S3 |
| **Title** | Refinamento de Declividade |
| **Parent** | S2 |
| **Children** | S4 |

#### Interactive Elements

| Element | Type | Default | Notes |
|---|---|---|---|
| Aplicar penalidade por declive? | S/N toggle | Não (False) | If No: penalty=1.0, skip S3a |
| Declividade (if Yes) | Radio list | — | 3 options |

**Declividade options:**

| # | Label | Multiplier |
|---|---|---|
| 1 | Plano (Base x1.0) | 1.0 |
| 2 | Misto (x1.15) | 1.15 |
| 3 | Inclinado (x1.30) | 1.30 |

#### Data State Out

- `penalidade_declividade` — float multiplier

---

### S4 — Adjust Activity Scope

| Property | Value |
|---|---|
| **Screen ID** | S4 |
| **Title** | Ajuste de Atividades (Apenas Nesta Execução) |
| **Parent** | S3 |
| **Children** | S4a (adjustment menu), S5 |

#### Gate Prompt

`confirmar("Ajustar escopo de atividades (substituir/remover/adicionar) nesta execução?", default=False)`

If No → skip to S5.

#### S4a — Activity Adjustment Menu (Loop)

| Element | Type | Items |
|---|---|---|
| Operation selector | Radio list | 5 options |

**Options:**

| # | Label | Sub-flow |
|---|---|---|
| 1 | Substituir atividade | Choose source(s) by index/selection → choose destination from catalog or `[DIGITAR NOVA ATIVIDADE]` |
| 2 | Remover atividade | Choose by index/selection |
| 3 | Adicionar atividade | Choose from catalog or type new → apply scope → `pedir_float("Área/ha")` → `pedir_float("Penalidade de terreno")` |
| 4 | Ver listas completas (escopo x catálogo) | Display-only + [ENTER] |
| 5 | Concluir ajustes | Exit loop → S5 |

**"Substituir" sub-flow detail:**
1. `prompt("Origens", "")` — type indices or ENTER for `selecionar("ATIVIDADE ORIGEM", atvs)`
2. `selecionar("DESTINO", destinos + ["[DIGITAR NOVA ATIVIDADE]"])` — if `[DIGITAR]`: `prompt("Nova atividade", "")`

**"Adicionar" sub-flow detail:**
1. Select activity from catalog or type new name
2. `selecionar("APLICAR EM", ["Todos os talhões do escopo", "Talhões por lista", "Talhões por texto"])`
3. If "por lista": `prompt("Talhões", "")`
4. If "por texto": `prompt("Texto no talhão", "")`
5. `pedir_float("Área/ha para nova atividade (por talhão)")`
6. `pedir_float("Penalidade de terreno da nova atividade")`

---

### S5 — Toggle Orçamento Estrito

| Property | Value |
|---|---|
| **Screen ID** | S5 |
| **Title** | Orçamento Estrito |
| **Parent** | S4 |
| **Children** | S6 |

#### Display

`Orçamento estrito (sem mediana silenciosa; lacunas pedem input): {True/False}`

#### Interactive Elements

| Element | Type | Default |
|---|---|---|
| Alternar orçamento_estrito? | S/N toggle | Não (False) |

#### Data State Out

- `cfg["orcamento_estrito"]` — toggled boolean, saved to config

---

### S6 — Activities Found (Informational)

| Property | Value |
|---|---|
| **Screen ID** | S6 |
| **Title** | Atividades Encontradas Nesta Fazenda |
| **Parent** | S5 |
| **Children** | S7 |
| **Interactive** | No — display only |

#### Layout Zones

| Zone | Content |
|---|---|
| **Header** | `ATIVIDADES ENCONTRADAS NESTA FAZENDA:` |
| **List** | Numbered list of all activities |
| **Footer** | Talhão count + scope talhões preview (first 8) |
| **Action** | Swipe or tap to continue |

---

### S7 — Comparativo Manual vs Mecanizado (Gate)

| Property | Value |
|---|---|
| **Screen ID** | S7 |
| **Title** | Modo Comparativo Manual vs Mecanizado |
| **Parent** | S6 |
| **Children** | S7a, S7b, S7c, S7d, S8 |

#### Display

- If matches found: `Detectadas {N} atividade(s) com equivalente mecanizado.`
- If none: `Nenhuma sugestão automática encontrada; use modo manual [2] ou recurso externo [3].`

#### Interactive Elements

| Element | Type | Default |
|---|---|---|
| Deseja executar comparativo? | S/N toggle | Não (False) |

If No → skip to S8.

---

### S7a — Comparativo Mode Selection

| Property | Value |
|---|---|
| **Screen ID** | S7a |
| **Title** | Comparativo: Modo de Seleção |
| **Parent** | S7 |
| **Children** | S7a-1, S7a-2, S7a-3, S7d |

#### Interactive Elements

| Element | Type | Default | Items |
|---|---|---|---|
| Mode selector | Radio list | [1] | See below |

**Options:**

| # | Label | Destination |
|---|---|---|
| 1 | Usar sugestões automáticas (detecção por nome) | S7a-1 |
| 2 | Escolher manualmente do catálogo completo | S7a-2 |
| 3 | Cadastrar recurso mecanizado externo | S7a-3 |
| 0 | Cancelar comparativo | S8 |

---

### S7a-1 — Auto Suggestion Mode

| Property | Value |
|---|---|
| **Screen ID** | S7a-1 |
| **Title** | Atividades Detectadas Automaticamente |
| **Parent** | S7a |

#### Layout Zones

| Zone | Content |
|---|---|
| **List** | Numbered pairs: manual → mecanizado (multi-select chips per item) |
| **Action** | `[Selecionar Todas]` chip (equivalent to CLI ENTER=all) |
| **Input** | Multi-select: tap items to toggle, or "Selecionar Todas" chip, or `[Voltar]` |

#### Interactive Elements

| Element | Type | Notes |
|---|---|---|
| Selection | Multi-select chip list | Each pair is toggleable; CLI uses comma-separated numbers |
| "Selecionar Todas" chip | Quick select | Equivalent to CLI ENTER=all — selects all pairs |
| "Voltar" button | Back | Returns to S7a |

#### Data State Out

- `substituicoes_comparativo` — dict of manual→mecanizado mappings

---

### S7a-2 — Manual Catalog Mode

| Property | Value |
|---|---|
| **Screen ID** | S7a-2 |
| **Title** | Catálogo de Atividades Mecanizadas Disponíveis |
| **Parent** | S7a |

#### Layout Zones

| Zone | Content |
|---|---|
| **Catalog** | Paginated list of mecanized activities with HM values |
| **Commands** | [L] List current, [U] Undo, [A] Auto-suggestions |

#### [A] Auto-suggestions Command (inline sub-screen)

Pressing **[A]** during manual catalog mode displays auto-suggestion pairs inline (same content as S7a-1 auto mode), then requires `[ENTER para voltar ao catálogo manual]` — a distinct overlay/modal that the mobile UI must render as a bottom sheet or dialog.
| **Summary** | Current substitutions table |

#### Interactive Elements

| Element | Type | Notes |
|---|---|---|
| Activity selector | Paginated list | Select mecanized activity |
| Manual activity selector | Paginated list | Appears after selecting mecanized — choose which manual to replace |
| Duplicate conflict | S/N toggle | `confirmar("Substituir mapeamento existente?")` |
| Add another? | S/N toggle | After each mapping |

#### Flow

1. User selects a mecanized activity from catalog
2. Screen shows "Atividades MANUAIS na fazenda:" numbered list
3. User selects manual activity to replace
4. If duplicate: `confirmar("Substituir mapeamento existente?", default=True)`
5. `confirmar("Adicionar outra substituição manual?", default=False)`
6. If Yes → loop back to step 1
7. If No → show summary, continue to S7d

---

### S7a-3 — External Resource Mode

| Property | Value |
|---|---|
| **Screen ID** | S7a-3 |
| **Title** | Cadastrar Recurso Mecanizado Externo |
| **Parent** | S7a |

#### Sub-Screen: S7a-3-1 — External Resource Data Entry

| Element | Type | Default | Notes |
|---|---|---|---|
| Manual activity to replace | Paginated list | — | `selecionar_paginado("ATIVIDADE MANUAL A SUBSTITUIR")` |
| Nome do recurso/modelo | Text field | `manual_sugestao` or "Navu" | `prompt("Nome do recurso/modelo externo")` — default is the chosen manual activity name, "Navu" is fallback |
| HM/ha do recurso | Number stepper | 1.0 | `pedir_float("HM/ha do recurso externo")` |
| Custo R$/h | Number stepper | 0.0 | `pedir_float("Custo R$/h do recurso externo", allow_zero=True)` |
| Preço R$/ha (opcional) | Number stepper | 0.0 | `pedir_float("Preço R$/ha (opcional)", allow_zero=True)` |
| Adicionar outro? | S/N toggle | Não | Loop if Yes |

#### Data State Out

- External resource dict: `{atividade_mecanizada, rendimento_hm, custo_h, preco_ha, tipo="Mecanizada", origem="externo"}`

---

### S7d — Comparativo Substitution Summary

| Property | Value |
|---|---|
| **Screen ID** | S7d |
| **Title** | Resumo das Substituições |
| **Parent** | S7a-1, S7a-2, S7a-3 |
| **Children** | S8 |
| **Interactive** | Confirm-only |

#### Layout Zones

| Zone | Content |
|---|---|
| **List** | Pairs: `{manual_activity} → {mecanizado_activity}` |
| **Action** | [ENTER para continuar] button |

---

### S8 — Sequence Selection

| Property | Value |
|---|---|
| **Screen ID** | S8 |
| **Title** | Selecionar Sequência Padrão |
| **Parent** | S7d (or S7 if comparativo skipped) |
| **Children** | S9 |

#### Instruction Text

`Responda S para a sequência desejada (apenas UMA):`

#### Interactive Elements

| Element | Type | Default | Items |
|---|---|---|---|
| Sequence selector | S/N toggle list | Current default | 5 sequences (first-match-wins) |

**Sequences:**

| # | Mode ID | Description |
|---|---|---|
| 1 | `implantacao` | Roçada > Formiga > Coroamento > Coveamento > Adubação > Plantio > Irrigação (cascata) |
| 2 | `manutencao_swg` | Roçada manual > Limpeza de área > Capina de coroa > Formigas > Coveamento > Adubação > Plantio > Irrigação (ordem SWG) |
| 3 | `manutencao_seco` | [EM PROGRESSO] Manutenção período seco — regras ainda não definidas |
| 4 | `manutencao_umido` | [EM PROGRESSO] Manutenção período úmido — regras ainda não definidas |
| 5 | `personalizado` | Ordem livre (sem bloqueio global plantio/irrigação) |

**On mobile**: Radio list with detail cards. Each sequence is a card showing the mode name + description. First "Sim" selection wins. User can only pick one.

**Post-selection**: `confirmar(" Salvar como padrão para próximas execuções?", default=True)`

#### Data State Out

- `modo_seq` — string ("implantacao" | "manutencao_swg" | "manutencao_seco" | "manutencao_umido" | "personalizado")
- `cfg["modo_seq_padrao"]` — saved if user confirms

---

### S9 — Bloqueio global / Reforço / Pelotão

| Property | Value |
|---|---|
| **Screen ID** | S9 |
| **Title** | Bloqueio Global |
| **Parent** | S8 |
| **Children** | S10 |
| **Condition** | Skipped if `modo_seq == "personalizado"` or no `candidatas_bloqueio` |

#### If personalizado mode:

Display: `Modo PERSONALIZADO: bloqueio global plantio/irrigação DESLIGADO.` → skip to S10.

#### Interactive Elements (sequential)

| # | Element | Type | Default | Condition |
|---|---|---|---|---|
| 1 | Aplicar BLOQUEIO GLOBAL (plantio/irrigação só iniciam quando TODO o resto zerar)? | S/N toggle | Sim (True) | If candidate activities exist |
| 2 | Salvar filtros de bloqueio no config? | S/N toggle | Sim (True) | Only if [1]=Yes |
| 3 | Ativar REFORCO AUTOMÁTICO (turma ociosa ajuda outras atividades não bloqueadas)? | S/N toggle | Sim (True) | — |
| 4 | Usar PELOTAO UNIFICADO (todos os executores) só em plantio/irrigação após liberação global? | S/N toggle | Sim (True) | Only if [1]=Yes |

**Blocked activities display** (if [1]=Yes): Shows list of blocked activity names (up to 20, then `+N`)

#### Data State Out

- `usar_bloqueio_global` (bool)
- `atividades_bloqueadas` (set)
- `usar_reforco_automatico` (bool)
- `usar_pool_pos_bloqueio` (bool)

### S10 — Project Configuration (Prazo / Calendário / Equipe)

| Property | Value |
|---|---|
| **Screen ID** | S10 |
| **Title** | Configuração do Projeto |
| **Parent** | S9 |
| **Children** | S10a, S11 |
| **Condition** | Only in single-farm mode (batch uses template) |

#### Instruction Text (before elements 2-4)

`Referência do calendário para DIAS ÚTEIS da meta (meses corridos a partir de):`

#### Interactive Elements (sequential)

| # | Element | Type | Default | Notes |
|---|---|---|---|---|
| 1 | Prazo META para conclusão (meses) | Number stepper | 6.0 | `pedir_float` |
| 2 | Mês inicial (1-12) | Int stepper | current month | `pedir_int` |
| 3 | Ano inicial | Int stepper | current year | `pedir_int` |
| 4 | Dia inicial (1-N) | Int stepper | current day (clamped) | `pedir_int` |
| 5 | Informar dia final manualmente? | S/N toggle | Não | If Yes → sub-prompts 6-8 |
| 6 | Mês final (1-12) | Int stepper | mes_ref | Conditional |
| 7 | Ano final | Int stepper | ano_ref | Conditional |
| 8 | Dia final (1-N) | Int stepper | dia_ref (clamped) | Conditional |
| 9 | Operários totais | Int stepper | 9 | `pedir_int` |
| 10 | Jornada efetiva diária | Dual-mode decimal/time | config default (4.6h) | `pedir_jornada` |
| 11 | Configurar COMPARATIVO MULTI-FATOR agora? | S/N toggle | Não | If Yes → S10a |

#### S10a — Comparativo Multi-Fator Config

| Element | Type | Default |
|---|---|---|
| Jornadas (h/dia) separadas por vírgula | Text field | current jornada |
| Equipes (executores) separadas por vírgula | Text field | current executores |

#### Data State Out

- `prazo_meses`, `mes_ref`, `ano_ref`, `dia_ref`, `data_inicio_txt`, `data_fim_txt`
- `executores`, `jornada`
- `cfg["jornada_horas"]` — saved
- `comparativo_cfg` — if activated

---

### S11 — Etapa 1: Criar Turmas

| Property | Value |
|---|---|
| **Screen ID** | S11 |
| **Title** | ETAPA 1: Criar Turmas / Funções |
| **Parent** | S10 |
| **Children** | S12 |

#### Loop: Create Teams

| # | Element | Type | Default | Notes |
|---|---|---|---|---|
| 1 | Nome da turma (ex: Rocadores) | Text field | "Turma {N}" | `prompt` |
| 2 | Quantos operários na turma '{name}' | Int stepper | min(restantes, restantes//2) | `pedir_int` |
| 3 | Criar outra turma? ({restantes} restantes) | S/N toggle | Sim | If No → remaining go to "Geral" |

#### Display (after creation)

Numbered list of turmas: `{name}: {N} operários`

#### Data State Out

- `turmas` — list of `{nome, operarios, atividades}`

---

### S12 — Etapa 2: Vincular Atividades às Turmas

| Property | Value |
|---|---|
| **Screen ID** | S12 |
| **Title** | ETAPA 2: Vincular Atividades às Turmas |
| **Parent** | S11 |
| **Children** | S12a (percurso S/N), S12b (menu), S13 |

#### S12a — Percurso S/N (Primary Flow)

| Property | Value |
|---|---|
| **Screen ID** | S12a |
| **Title** | TURMA '{name}' — percurso S/N |
| **Parent** | S12 |

**Mobile Layout**: Full-screen activity card. Each activity shown as a card with 4 bottom chips.

| Element | Type | Chips |
|---|---|---|
| Percurso S/N | Activity card per item | Sim / Não / Abortar / OK |

**Card content per activity**: `[{i}/{total}] [{X/ }] '{activity_name}'`

**Chip actions**:
- **Sim** → add to turma
- **Não** → remove from turma
- **Abortar** → stop percurso (don't alter current)
- **OK** → add current + stop percurso (quick exit)

#### S12b — Turma Activity Menu (9 options)

| Property | Value |
|---|---|
| **Screen ID** | S12b |
| **Title** | TURMA: {name} ({N} ops) — {M} atividade(s) vinculadas |
| **Parent** | S12 |

**Options:**

| # | Label | Sub-flow |
|---|---|---|
| 1 | Refazer percurso S/N | S12a |
| 2 | Adicionar por filtro de texto | `prompt("Texto no nome")` → match list → `confirmar("Adicionar TODAS?")` or individual |
| 3 | Adicionar por lista/índices | `prompt("Índices")` or `selecionar_paginado` |
| 4 | Remover por filtro | `prompt("Remover cujo nome contém")` → `confirmar("Remover N?")` |
| 5 | Remover UMA (lista) | `selecionar_paginado("REMOVER ATIVIDADE")` |
| 6 | Ver vinculadas | Display-only + [ENTER] |
| 7 | Trocar atividade (1:1) | `selecionar_paginado("ORIGEM")` → filter/`selecionar("DESTINO")` → `confirmar("Trocar?")` |
| 8 | Assistente inteligente S/N (revisão guiada) | S12c |
| 9 | Ver duas listas (escopo × catálogo) | Display-only + [ENTER] |
| 0 | Concluir esta turma | Exit loop → next turma or S13 |

#### S12c — Assistente Inteligente S/N

| Property | Value |
|---|---|
| **Screen ID** | S12c |
| **Title** | ASSISTENTE S/N — TURMA '{name}' |
| **Parent** | S12b |

**Card content per linked activity**: `[{i}/{total}] '{activity_name}'`

**Chip actions**:
- **ENTER** (tap card background) → manter
- **Não** → remove
- **Trocar** → `selecionar_paginado("DESTINO DA TROCA")`
- **Adicionar** → `selecionar_paginado("ADICIONAR ATIVIDADE")`
- **OK** → encerrar assistente

---

### S12d — Atividades Órfãs

| Property | Value |
|---|---|
| **Screen ID** | S12d |
| **Title** | Atividades sem Turma Vinculada |
| **Parent** | S12 |
| **Condition** | Only if orphan activities exist after linking |

#### Display

Warning banner: `ATENÇÃO: {N} atividades sem turma vinculada:` → numbered list

#### Interactive Elements

**Standard mode:**

| Element | Type | Default |
|---|---|---|
| Vincular todas as órfãs a uma turma existente? | S/N toggle | Sim |
| TURMA PARA ÓRFAS | Radio list | [if Yes] turma names |

**Personalizado mode:**

| Element | Type | Default |
|---|---|---|
| Esta fazenda tem demandas sem turma no modelo. Preencher na turma com mais operários? (N = equipe especializada; HH dessas atividades não entram no cronograma) | S/N toggle | Não |

**Batch mode:** Uses `ctx["preencher_orfas_template"]` — no interactive prompt.

#### Data State Out

- Orphan activities added to selected turma

---

### S13 — Etapa 3: Conflitos e Reatribuição

| Property | Value |
|---|---|
| **Screen ID** | S13 |
| **Title** | ETAPA 3: CONFLITOS E REATRIBUIÇÃO |
| **Parent** | S12 |
| **Children** | S13a (per-conflict), S13b (reattribution) |

#### S13a — Per-Conflict Resolution

For each activity claimed by 2+ turmas:

| Element | Type | Default |
|---|---|---|
| Conflito: '{activity}' | Banner | — |
| Turmas: {list} | Info text | — |
| Várias turmas em PARALELO? | S/N toggle | Sim |
| [If Not parallel] Turma EXCLUSIVA | Radio list | candidate turmas |

#### S13b — Reatribuição (Optional)

| Element | Type | Default |
|---|---|---|
| Reatribuir atividades (reforço)? | S/N toggle | Não |

If Yes → loop:

| Element | Type |
|---|---|
| REATRIBUIR — escolha a ATIVIDADE | `selecionar_paginado` |
| Turma que EXECUTA | `selecionar` from turma names |

#### Data State Out

- `reatribuicao` (dict), `paralelo` (dict), `primaria` (dict)

---

### S14 — Pre-Checkpoint: HH/ha Session Override

| Property | Value |
|---|---|
| **Screen ID** | S14 |
| **Title** | Ajuste de HH/ha — Apenas Esta Execução |
| **Parent** | S13 |
| **Condition** | Single-farm only; `confirmar("Ajustar HH/ha?", default=False)` = Yes |

#### Interactive Elements

Per-activity loop (skips HM-only/mecanizadas):

| Element | Type | Default | Notes |
|---|---|---|---|
| [{activity}] CT:{tarifa} HH/ha [{current}] | Text field | current value | `prompt`; empty = keep; comma→dot auto-fix |

#### Data State Out

- `session_hh` — dict of activity→HH override (memory only, not saved to config)

---

### S15 — CHECKPOINT RETROATIVO (Hub)

| Property | Value |
|---|---|
| **Screen ID** | S15 |
| **Title** | CHECKPOINT RETROATIVO |
| **Parent** | S14 (or S13 if S14 skipped) |
| **Children** | S15a-S15g, S16 |
| **Pattern** | Hub-spoke (loop) — persists until "Continuar para simulação" |

#### Hub Menu

| # | Label | Spoke Destination | Action |
|---|---|---|---|
| 1 | Editar atividades de uma turma | S15a | `selecionar("TURMA")` → S12b menu |
| 2 | Reprocessar conflitos/reatribuição | S15b | Calls `resolver_conflitos_e_reatribuir` |
| 3 | Ajustar HH/ha desta sessão | S15c | Calls `menu_ajustes_hh_apenas_sessao` |
| 4 | Ajustar escopo de atividades desta execução | S15d | Calls `_menu_ajustar_escopo_atividades` → recalculates |
| 5 | Revisar jornada/equipe | S15e | S15e sub-prompts |
| 6 | Voltar ao seletor de fazenda/escopo | — | Returns `{"acao": "retroceder_escopo"}` → restarts at S0 |
| 7 | Continuar para simulação | S16 | Breaks loop |

#### S15a — Edit Turma Activities

Selects a turma by name, then opens S12b menu for that turma.

#### S15b — Reprocess Conflicts

Re-runs S13 (conflict detection + resolution) with current turma state.

#### S15c — Adjust HH/ha (Session)

Same as S14 — per-activity HH override loop.

#### S15d — Adjust Activity Scope

Re-opens S4 (activity scope adjustment), then recalculates:
- `atividades_reais`, `talhoes_ordenados`, `catalogo_global`
- Re-runs conflict resolution

#### S15e — Review Jornada/Equipe

| Element | Type | Default |
|---|---|---|
| Display: `{executores} operários @ {jornada}h/dia` | Info text | — |
| Alterar jornada? | S/N toggle | Não |
| [If Yes] Nova jornada | Dual-mode decimal/time | current jornada |
| Alterar operários? | S/N toggle | Não |
| [If Yes] Operários totais | Int stepper | current executores |

---

### S15f — Validação Orçamento Estrito

| Property | Value |
|---|---|
| **Screen ID** | S15f |
| **Title** | Validação de Orçamento Estrito |
| **Parent** | S15 (after "Continuar") |
| **Condition** | Only if `orcamento_estrito=True` |

For each activity missing from tarifas:

| Element | Type | Default |
|---|---|---|
| Banner: [ESTRITO] Sem tarifa CT para atividade | Warning | — |
| Escolher uma linha existente em tarifas? | S/N toggle | Sim |
| [If Yes] TARIFA CT (orçamento) | `selecionar_paginado` | — |
| [If No] HH/ha (manual) | Number stepper | 8.0 |
| [If No] Preço R$/ha (manual) | Number stepper | 0.0 |
| [If No] Custo R$/h (manual) | Number stepper | `cfg.get("custo_hora_tf")` or 50.0 |
| [If No] Nome da chave a gravar | Text field | current key |

#### S15f-2 — Zero HH/ha Validation (Second Pass)

After all missing-tarifa gaps resolved, a second pass validates tarifas with `rendimento_hh <= 0.01` that are NOT mecanizada:

| Element | Type | Default | Condition |
|---|---|---|---|
| Banner: [ESTRITO] rendimento_hh zero ou inválido na tarifa '{name}' | Warning | — | Per tarifa with HH ≤ 0.01 and not mecanizada |
| Informe HH/ha para esta linha (ou 0 se só máquina) | Number stepper | 0.0 | `pedir_float`, allow_zero=True |
| Aplicar SÓ nesta execução (não gravar em config.json)? | S/N toggle | Sim | If session_hh available |

If "Sim" on session-only: value stored in `session_hh` dict (not persisted). If "Não": value written to `cfg["tarifas"]` and `salvar_config()`.

#### Data State Out

- `cfg["de_para"]` — updated with new mapping
- `cfg["tarifas"]` — updated with manual entry

---

### S16 — Pre-Checagem HH/HM + Sem Executor

| Property | Value |
|---|---|
| **Screen ID** | S16 |
| **Title** | PRÉ-CHECAGEM HH/HM ANTES DO CRONOGRAMA |
| **Parent** | S15 (after checkpoint loop + validation) |
| **Children** | S17 |
| **Interactive** | Partial |

#### Layout Zones

| Zone | Content |
|---|---|
| **Summary** | HH/HM panel: totals by activity, talhão breakdown |
| **Warning** | Missing tariff keys list (if non-strict) |
| **Action 1** | `confirmar("Exibir HH/HM detalhado por talhão?")` |
| **Warning** | Activities with demand but NO executora (red list) |
| **Action 2** | `confirmar("Continuar mesmo assim?")` — if activities have no executora |

#### Interactive Elements

| Element | Type | Default | Condition |
|---|---|---|---|
| Exibir HH/HM detalhado por talhão? | S/N toggle | Não | Single-farm only |
| Continuar mesmo assim (HH não agendadas)? | S/N toggle | Não | Only if sem_executor list exists |

#### Data State Out

- If "Não" on sem_executor: returns to checkpoint
- If "Sim": HH of activities without executora → zeroed in cronograma

---

### S17 — Cronograma Simulação (Non-Interactive)

| Property | Value |
|---|---|
| **Screen ID** | S17 |
| **Title** | GERANDO CRONOGRAMA (talhão a talhão)... |
| **Parent** | S16 |
| **Children** | S18 |
| **Interactive** | No — computation only |

#### Display

Progress indicator during scheduling engine run. Shows Rich table when complete:

| Column | Content |
|---|---|
| Semana | Week number |
| Dias | Day range |
| Talhões / Atividades | Comma-separated activity previews |

---

### S18 — Modo Mecanizado Opcional (Gate)

| Property | Value |
|---|---|
| **Screen ID** | S18 |
| **Title** | ATIVAR MODO MECANIZADO |
| **Parent** | S17 |
| **Children** | S18a, S19 |
| **Condition** | Skipped in batch or comparativo mode |

#### Display

- HM-only activities list (if any)
- Info: "As atividades HM do orçamento já foram contabilizadas automaticamente no cronograma base."

#### Interactive Elements

| Element | Type | Default |
|---|---|---|
| Ativar modo mecanizado opcional? | S/N toggle | Não |

---

### S18a — Cadastrar Recursos Mecanizados (percurso S/N)

| Property | Value |
|---|---|
| **Screen ID** | S18a |
| **Title** | MODO MECANIZADO — recurso #N |
| **Parent** | S18 |

#### Loop: Create Resources

| # | Element | Type | Default |
|---|---|---|---|
| 1 | Mostrar apenas candidatas a mecanizado na pergunta S/N abaixo? | S/N toggle | Sim |
| 2 | Nome do recurso | Text field | "Mecanizado_N" |
| 3 | Produtividade (ha/h) | Number stepper | 0.18 |
| 4 | Custo (R$/h) | Number stepper | 0.0 |
| 5 | Percurso S/N — Vincular '{activity}'? | Activity card (4 chips: s/n/a/ok) | — |
| 6 | Adicionar mais um recurso mecanizado? | S/N toggle | Não |
| 7 | Revisar/editar atividades dos recursos agora? | S/N toggle | Sim |

#### S18a-1 — Editar Recurso Mecanizado (Sub-menu)

If [7]=Sim, opens editing menu per resource:

| # | Label | Action |
|---|---|---|
| 1 | Adicionar atividade | `selecionar_paginado` |
| 2 | Remover atividade | `selecionar_paginado` |
| 3 | Substituir atividade | `selecionar_paginado` (origin) → `selecionar_paginado` (dest) |
| 4 | Alterar produtividade | `pedir_float` |
| 5 | Alterar custo/h | `pedir_float` |
| 6 | Ver lista filtrada (mec/mecanizado/semimec) | Display + [ENTER] |
| 7 | Ver listas completas | Display + [ENTER] |
| 8 | Voltar | Return to resource selector |

#### Post-resource Decision

| Element | Type | Default |
|---|---|---|
| Regra: manter humano em PARALELO nas atividades mecanizadas? | S/N toggle | Não (replace total) |

#### Data State Out

- `recursos_mec` — list of `{nome, prod_ha_h, custo_h, atividades}`
- `cronograma_mec`, `cronograma_com_mec` — if activated
- `regra_implantacao_mec` — "substituir_total" or "paralelo"

---

### S19 — Ocupação por Turma + Comparativo Multi-Fator

| Property | Value |
|---|---|
| **Screen ID** | S19 |
| **Title** | OCUPAÇÃO POR TURMA |
| **Parent** | S18 |
| **Children** | S19a |
| **Interactive** | Display + optional recalc |

#### Display Tables

1. **Ocupação por Turma** (Rich table):
   - Columns: Turma, HH, Cap. max, Uso %
   - Highlight: turma with highest Uso % (caminho crítico)
   - Pelotao_Unificado row (if applicable)

2. **Comparativo de Cenários** (if `comparativo_cfg` exists):
   - Columns: Equipe, Jornada, Dias, Meses, Ganho vs Meta
   - Up to 40 rows

3. **Cronograma Alternativo** (if mecanizado active):
   - Weekly summary table

#### Interactive Elements

| Element | Type | Default | Condition |
|---|---|---|---|
| BASE DO COMPARATIVO MULTI-FATOR | Radio list | — | If mecanizado active |
| Recalcular comparativo com novos valores? | S/N toggle | Não | Single-farm only |

**Base options:**
- "Sem mecanizado (HH total atual)"
- "Com mecanizado (HH humano remanescente)"

#### S19a — Recalcular Cenários (Loop)

| Element | Type | Default |
|---|---|---|
| Jornadas (h/dia) separadas por vírgula | Text field | current |
| Equipes (executores) separadas por vírgula | Text field | current |

---

### S20 — Auditoria do Escopo

| Property | Value |
|---|---|
| **Screen ID** | S20 |
| **Title** | AUDITORIA DO ESCOPO (ANTES DA EXPORTAÇÃO) |
| **Parent** | S19 |
| **Children** | S21 |
| **Interactive** | Display only |

#### Display

- Atividades no escopo: N
- Agendadas no humano: N
- Agendadas no mecanizado: N
- Não agendadas: N
- Per-activity audit: `{activity} → agendada_humana | agendada_mecanizada | nao_agendada`
- Roçada-specific status lines

---

### S21 — Exportação Dossier Excel (Non-Interactive)

| Property | Value |
|---|---|
| **Screen ID** | S21 |
| **Title** | Exportação Dossier |
| **Parent** | S20 |
| **Children** | S22 |
| **Interactive** | No — file generation |

#### Output Files

| File | Sheets |
|---|---|
| `Dossier_{fazenda}__FAZENDA_TODOS_OPERACIONAL.xlsx` | RESUMO_OPERACIONAL, CRONOGRAMA_DETALHADO, CASCATA_EXPLICADA, OCUPACAO_TURMAS_DIA, CRONOGRAMA_MEC_BASE, AUDITORIA_ESCOPO |
| `Dossier_{fazenda}_COMPARATIVO_CENARIOS.xlsx` | COMPARATIVO_CENARIOS |
| `Dossier_{fazenda}__COM_MECANIZADO_OPERACIONAL.xlsx` | (only if mecanizado active) RESUMO_OPERACIONAL, CRONOGRAMA_DETALHADO, CASCATA_EXPLICADA |

#### Success Message

`✓ Dossier operacional exportado: {filename}`

---

### S22 — Diagnóstico de Prazo

| Property | Value |
|---|---|
| **Screen ID** | S22 |
| **Title** | DIAGNÓSTICO DE PRAZO |
| **Parent** | S21 |
| **Children** | S23 |
| **Interactive** | Display only |

#### Display

| Line | Content | Color |
|---|---|---|
| Meta informada | `{prazo_meses} meses ({dias_meta} dias úteis)` | Green |
| Duração simulada | `{dias_simulado} dias ({meses_simulado:.1f} meses)` | Green |
| [If mecanizado] Duração cenário mecanizado | `{d_mc} dias ({m_mc:.1f} meses)` | Cyan |
| [If mecanizado] Ganho operacional estimado | `{ganho:+d} dias` | Cyan |
| **STATUS** | **DENTRO DO PRAZO** or **PRAZO EXCEDIDO** | Green / Yellow |
| [If excedido] Sugestão | `~{exec_teoricos} executores @ {jornada}h/dia cumpririam a meta` | Cyan |
| [If excedido] Dica | `~{ex5} exec @ 5h/dia ou ~{ex6} @ 6h/dia` | Dim |

---

### S23 — Comparativo Manual vs Mecanizado (Result)

| Property | Value |
|---|---|
| **Screen ID** | S23 |
| **Title** | COMPARATIVO: MANUAL vs MECANIZADO |
| **Parent** | S22 |
| **Children** | S24 |
| **Condition** | Only if `modo_comparativo=True` and `substituicoes_comparativo` exists |

#### Display Table

| Column | Content |
|---|---|
| Métrica | Manual / Mecanizado / Diferença |
| Dias necessários | Values + delta |
| HH totais | Values + delta |
| HM totais | Values + delta |
| Dias eq. via HH/cap | Values + delta |

#### Additional Sections

- TURMAS MECANIZADAS NO CENÁRIO (list)
- SUBSTITUIÇÕES APLICADAS (list: manual → mecanizado)
- DESTAQUES: economia de dias, economia de HH, notas

---

### S24 — Result Screen / Return to Menu

| Property | Value |
|---|---|
| **Screen ID** | S24 |
| **Title** | Resultado — Retorno ao Menu |
| **Parent** | S23 (or S22 if no comparativo) |
| **Children** | S25 (methodology loop) or H1 (main menu) |
| **Interactive** | [ENTER para voltar ao menu] |

#### Data State Out

- Monitor state emitted (operacao + lote + rendimentos)
- `resultado_final` dict returned with all simulation data
- If `retroceder_escopo`: special dict `{"acao": "retroceder_escopo"}`

---

### S25 — Post-Simulation Methodology Loop

| Property | Value |
|---|---|
| **Screen ID** | S25 |
| **Title** | PRÓXIMAS METODOLOGIAS DISPONÍVEIS |
| **Parent** | S24 |
| **Children** | S2 (re-scope talhões) or H1 (exit) |
| **Condition** | Only if farm has remaining methodologies not yet executed |

#### Display

- Header: `PRÓXIMAS METODOLOGIAS DISPONÍVEIS`
- Count: `Restantes: {N}`
- List: numbered methodologies (up to 12, then `+N metodologia(s)`)

#### Interactive Elements

| Element | Type | Default |
|---|---|---|
| Executar outra metodologia desta fazenda agora? | S/N toggle | Sim |

#### Flow Logic

- **Sim** → loops back to S2 (talhão scope) with updated `metodologias_executadas` — entire S2→S24 sequence repeats for next methodology
- **Não** → exits to H1 (main menu)

**This makes the single-farm journey cyclical, not linear.** A farm with 3 methodologies will pass through S2→S24 three times, with S25 as the decision gate between iterations.

---

## Batch Flow Screens (B1–B4)

### B1 — Batch Global Configuration

| Property | Value |
|---|---|
| **Screen ID** | B1 |
| **Title** | CONFIGURAÇÃO GLOBAL — TODAS AS FAZENDAS |
| **Parent** | S0 (option "TODAS AS FAZENDAS") |
| **Children** | B2 |

Same prompts as S8–S10 (sequence, bloqueio, prazo, calendário, jornada) but:
- `prazo_absoluto` toggle: `confirmar("{N} meses é o período ABSOLUTO? Se sim, haverá sugestões se necessário")`
- No `comparativo_cfg` prompt
- No per-farm interactive prompts (batch uses template)
- No declivity penalty prompt (batch hardcodes `penalidade: 1.0`)
- No modo mecanizado prompt (batch skips S18)

#### Interactive Elements

| # | Element | Type | Default |
|---|---|---|---|
| 1 | Sequence selection | Radio list | config default |
| 2 | Aplicar BLOQUEIO GLOBAL (plantio/irrigação só iniciam quando TODO o resto zerar)? | S/N toggle | Sim | Same text as single-farm S9 |
| 3 | Ativar REFORCO AUTOMÁTICO (turma ociosa ajuda outras atividades não bloqueadas)? | S/N toggle | Sim | Same text as single-farm S9 |
| 4 | Usar PELOTAO UNIFICADO (todos os executores) só em plantio/irrigação após liberação global? | S/N toggle | Sim (if bloqueio) | Same text as single-farm S9 |
| 5 | Prazo META (meses) | Number stepper | 6.0 |
| 6 | Prazo absoluto? | S/N toggle | Sim |
| 7–10 | Calendário (mês/ano/dia + dia final) | Int steppers | current date |
| 11 | Jornada efetiva diária | Dual-mode | config default |

---

### B2 — Configure Team Template

| Property | Value |
|---|---|
| **Screen ID** | B2 |
| **Title** | CONFIGURAR EQUIPE PADRÃO |
| **Parent** | B1 |
| **Children** | B2a, B3 |

#### Interactive Elements

| Element | Type | Default |
|---|---|---|
| Carregar perfil de equipe salvo? | S/N toggle | Não (if profiles exist) |
| [If Yes] Profile selector | Menu selection | — |
| [If Yes] Editar este perfil antes de usar? | S/N toggle | Não |
| [If No] Operários totais | Int stepper | 9 |
| [If No] Turma creation loop | Same as S11 | — |
| [If No] Vincular atividades (percurso S/N per turma) | Same as S12 | — |
| Salvar este perfil para reusar? | S/N toggle | Não |
| [If Yes] Nome do perfil | Text field | "padrão" |
| Distribuir demandas sem turma automaticamente? | S/N toggle | Não |

#### Data State Out

- `turmas`, `executores` — template team
- `ctx_base` — full context dict for batch processing
- Saved profile (if requested)

---

### B3 — Batch Per-Farm Loop + Checkpoint

| Property | Value |
|---|---|
| **Screen ID** | B3 |
| **Title** | FAZENDA [{i}/{N}]: {name} |
| **Parent** | B2 |
| **Children** | B4 |
| **Pattern** | Repeating per farm |

#### Pre-Farm Display

- Farm name header
- Meta saldo: `{dias_meta} dias | Consumido: {N} dias ({pct}%) | Saldo: {N} dias`
- Warning if 80%+ or 100%+ consumed

#### Inter-farm Checkpoint (B3a)

If `i > 1`: `_checkpoint_editar_template` — allows editing turma template before next farm.

| # | Option | Action | Sub-prompts |
|---|---|---|---|
| 0 | Continuar sem alterar | Proceed to farm | — |
| 1 | Editar operários de uma turma | `selecionar("TURMA PARA EDITAR")` | `pedir_int("Novos operários para '{nm}'", current_ops)` |
| 2 | Adicionar nova turma | `prompt("Nome da nova turma")` | `pedir_int("Quantos operários")` → `menu_vincular_atividades_turma` |
| 3 | Redistribuir atividades (S/N) de uma turma | `selecionar("TURMA PARA REDISTRIBUIR")` | `menu_vincular_atividades_turma` |

Default: `0` (continue without changes).

---

### B4 — Batch Consolidated Report

| Property | Value |
|---|---|
| **Screen ID** | B4 |
| **Title** | CONSOLIDADO FINAL (TODAS AS FAZENDAS) |
| **Parent** | B3 (after all farms) |
| **Children** | H1 |

#### Display Tables

1. **Consolidado** — Rich table:
   - Fazendas processadas, HH total, Dias max isolated, Dias acumulados lote, Meta, Saldo, Status
2. **Análise Equipe Padrão** (if prazo_absoluto):
   - Cascata de execução per farm: Fazenda, HH, Dias, Início, Fim, Meta consumida, Saldo, Status
3. **Excel export**: `_exportar_excel_consolidado_lote`

#### Interactive Elements

| Element | Type |
|---|---|
| [ENTER para voltar ao menu] | Tap/button |

---

## Multi-Equipes Flow Screens (M1–M6)

### M1 — Multi-Equipes Setup

| Property | Value |
|---|---|
| **Screen ID** | M1 |
| **Title** | MODO MULTI-EQUIPES |
| **Parent** | S0 (option "MULTI-EQUIPES") |
| **Children** | M2 |

#### Interactive Elements

| # | Element | Type | Default |
|---|---|---|---|
| 1 | Quantas equipes independentes? | Int stepper | 2 |
| 2 | Sequence selection | Radio list | config default |
| 3 | Mês inicial | Int stepper | current |
| 4 | Ano inicial | Int stepper | current |
| 5 | Dia inicial | Int stepper | current |

---

### M2 — Territory Mode (Gate)

| Property | Value |
|---|---|
| **Screen ID** | M2 |
| **Title** | DISTRIBUIÇÃO POR TERRITÓRIO |
| **Parent** | M1 |
| **Children** | M2a, M3 |

#### Interactive Elements

| Element | Type | Default |
|---|---|---|
| Usar modo automático de distribuição por território/cidade? | S/N toggle | Não |

If Yes → M2a:

#### M2a — Territory Distribution Display

- Per-city breakdown: city name, farm count, N equipes, total operários
- Unidentified farms warning
- Total summary

| Element | Type | Default |
|---|---|---|
| Aceitar esta distribuição automática? | S/N toggle | Sim |

---

### M3 — Per-Equipe Configuration (Loop)

| Property | Value |
|---|---|
| **Screen ID** | M3 |
| **Title** | EQUIPE {i}/{N} |
| **Parent** | M2 (or M1 if territory skipped) |
| **Children** | M4 |

#### Territory Mode (auto-config)

Per-equipe auto-assigned: nome, cidade, operários, fazendas. Only asks:
- `pedir_float("Prazo meta para '{nome}' (meses)", 3.0)`
- `confirmar("Informar dia final manualmente?")` → if Yes, date sub-prompts

#### Manual Mode

| # | Element | Type | Default |
|---|---|---|---|
| 1 | Nome da equipe | Text field | "Equipe N" |
| 2 | Prazo meta (meses) | Number stepper | 3.0 |
| 3 | Jornada diária (horas) | Dual-mode decimal/time | 4.3 | CLI uses `pedir_float` (decimal only); mobile should use Dual-Mode Input (8.4) for consistency |
| 4 | Executores | Int stepper | 10 |
| 5 | Informar dia final manualmente? | S/N toggle | Não |
| 6 | Carregar perfil de equipe? | S/N toggle | Não |
| 7 | [If No] Vincular atividades (percurso S/N) | Same as S12 | — |
| 8 | Fazendas para esta equipe | Index/text selection | All remaining |

**Fazenda assignment**: `prompt("Índices das fazendas (ex: 1,3,5-7) ou ENTER=todas")`

---

### M4 — Multi-Equipes Processing (Non-Interactive)

| Property | Value |
|---|---|
| **Screen ID** | M4 |
| **Title** | PROCESSANDO EQUIPE: {name} ({N} fazendas) |
| **Parent** | M3 |
| **Children** | M5 |
| **Interactive** | No — runs `calcular_cronograma_inteligente` per farm |

---

### M5 — Multi-Equipes Consolidated Report

| Property | Value |
|---|---|
| **Screen ID** | M5 |
| **Title** | CONSOLIDADO MULTI-EQUIPES |
| **Parent** | M4 |
| **Children** | M6 |

#### Display Table

| Column | Content |
|---|---|
| Equipe | Team name |
| Exec. | Executor count |
| Fazendas | Farm count |
| HH | Total HH |
| Dias acum. | Accumulated days |
| Meta (dias) | Target days |
| Saldo | Remaining days |
| Status | DENTRO / EXCEDIDO |

Per-team detail sub-tables + Excel export.

---

### M6 — Multi-Equipes Return

| Property | Value |
|---|---|
| **Screen ID** | M6 |
| **Title** | Retorno ao Menu |
| **Parent** | M5 |
| **Children** | H1 |
| **Interactive** | [ENTER para voltar ao menu] |

---

## 6. Screen Chains — Complete User Journeys

Three primary journeys covering all screens. Decision points show both paths.

---

### 6.1 Journey A: Single Farm — Implantação Mode (Most Complex)

```
H0 (splash)
→ H1 (main menu)
→ [1] S0 (farm select)
→ [S0a] empresa filter (if equipe column)
→ [S1] methodology scope (if metodologia column)
→ [S2] talhão scope (if 2+ talhões)              ←──┐
→ [S3] declivity penalty                             │
→ [S4] adjust activities gate                        │
→ [S4a] activity adjustment loop (optional)          │
→ [S5] toggle orcamento estrito                      │
→ [S6] activities found (info)                       │
→ [S7] comparativo gate                              │
→ [S7a] mode selection                               │
→ [S7a-1] auto suggestions OR                        │
→ [S7a-2] manual catalog OR                          │
→ [S7a-3] external resource                          │
→ [S7d] substitution summary                         │
→ [S8] sequence selection (implantação)              │
→ [S9] bloqueio global / reforço / pelotão           │
→ [S10] project config (prazo/calendário/equipe)     │
→ [S10a] comparativo multi-fator (optional)          │
→ [S11] ETAPA 1: criar turmas                        │
→ [S12] ETAPA 2: vincular atividades                 │
→ [S12a] percurso S/N per turma                      │
→ [S12b] turma menu (9 ops)                          │
→ [S12c] assistente inteligente                      │
→ [S12d] órfãs resolution                            │
→ [S13] ETAPA 3: conflitos                           │
→ [S13a] per-conflict (parallel/exclusive)           │
→ [S13b] reatribuição loop                           │
→ [S14] HH/ha session override (optional)            │
→ [S15] CHECKPOINT RETROATIVO hub ─┐                 │
│ [1] edit turma → S12b │                          │
│ [2] reprocess → S13 │                            │
│ [3] adjust HH → S14 │                            │
│ [4] adjust scope → S4 │                          │
│ [5] review jornada → S15e │                      │
│ [6] retrocede → S0 ←─────┘                       │
│ [7] continue ↓                                    │
↓                                                   │
[S15f] validação orçamento (if estrito)             │
→ [S16] pre-checagem HH/HM                          │
→ [S17] cronograma simulation                        │
→ [S18] modo mecanizado gate                         │
→ [S18a] cadastrar recursos                          │
→ [S19] ocupação + comparativo                       │
→ [S20] auditoria escopo                             │
→ [S21] Excel export                                 │
→ [S22] diagnóstico prazo                            │
→ [S23] comparativo result                           │
→ [S24] result screen                                │
→ [S25] Executar outra metodologia? ─── Yes ────────┘
│
└── No → H1 (main menu)
```

**Key insight:** The single-farm journey is CYCLICAL. After S24, S25 checks if the farm has remaining methodologies. If Yes, the entire S2→S24 sequence repeats for the next methodology (with `metodologias_executadas` tracking which ones are done). Only when all methodologies are exhausted (or user declines) does the flow exit to H1.
H0 (splash)
 → H1 (main menu)
   → [1] S0 (farm select)
     → [S0a] empresa filter (if equipe column)
     → [S1] methodology scope (if metodologia column)
       → [S2] talhão scope (if 2+ talhões)
         → [S3] declivity penalty
           → [S4] adjust activities gate
             → [S4a] activity adjustment loop (optional)
               → [S5] toggle orcamento estrito
                 → [S6] activities found (info)
                   → [S7] comparativo gate
                     → [S7a] mode selection
                       → [S7a-1] auto suggestions OR
                       → [S7a-2] manual catalog OR
                       → [S7a-3] external resource
                     → [S7d] substitution summary
                   → [S8] sequence selection (implantação)
                     → [S9] bloqueio global / reforço / pelotão
                       → [S10] project config (prazo/calendário/equipe)
                         → [S10a] comparativo multi-fator (optional)
                           → [S11] ETAPA 1: criar turmas
                             → [S12] ETAPA 2: vincular atividades
                               → [S12a] percurso S/N per turma
                               → [S12b] turma menu (9 ops)
                               → [S12c] assistente inteligente
                               → [S12d] órfãs resolution
                                 → [S13] ETAPA 3: conflitos
                                   → [S13a] per-conflict (parallel/exclusive)
                                   → [S13b] reatribuição loop
                                     → [S14] HH/ha session override (optional)
                                       → [S15] CHECKPOINT RETROATIVO hub ─┐
                                         │ [1] edit turma      → S12b     │
                                         │ [2] reprocess       → S13      │
                                         │ [3] adjust HH       → S14      │
                                         │ [4] adjust scope    → S4       │
                                         │ [5] review jornada  → S15e     │
                                         │ [6] retrocede       → S0 ←─────┘
                                         │ [7] continue ↓
                                         ↓
                                       [S15f] validação orçamento (if estrito)
                                         → [S16] pre-checagem HH/HM
                                           → [S17] cronograma simulation
                                             → [S18] modo mecanizado gate
                                               → [S18a] cadastrar recursos
                                                 → [S19] ocupação + comparativo
                                                   → [S20] auditoria escopo
                                                     → [S21] Excel export
                                                       → [S22] diagnóstico prazo
                                                         → [S23] comparativo result
                                                           → [S24] return to H1
```

**Total screens touched**: ~35 (including optional sub-screens)
**Minimum path** (all defaults, no optionals): H0→H1→S0→S3→S5→S6→S8→S9→S10→S11→S12→S13→S15→S16→S17→S18→S19→S20→S21→S22→S24 = **21 screens**

---

### 6.2 Journey B: Batch Mode — All Farms

```
H0 → H1 → [1] S0 → [1] "TODAS AS FAZENDAS"
  → B1 (global config: sequence + bloqueio + prazo + calendário + jornada)
    → B2 (team template: profile or manual + percurso S/N)
      → B3 (per-farm loop):
          ├─ Farm 1: [B3a checkpoint] → calcular_cronograma_inteligente(batch)
          ├─ Farm 2: B3a → calcular_cronograma_inteligente(batch)
          └─ Farm N: B3a → calcular_cronograma_inteligente(batch)
        → B4 (consolidated report + Excel)
          → H1
```

**Total screens**: ~8 interactive
**Key difference**: No per-farm interactive prompts; template is reused; checkpoint only between farms

---

### 6.3 Journey C: Multi-Equipes

```
H0 → H1 → [1] S0 → [2] "MULTI-EQUIPES"
  → M1 (N equipes + sequence + calendário)
    → M2 (territory mode gate)
      → [M2a] territory distribution (if Yes)
    → M3 (per-equipe config loop):
        ├─ Equipe 1: nome/prazo/jornada/exec + profile + turma + fazendas
        ├─ Equipe 2: ...
        └─ Equipe N: ...
      → M4 (processing — non-interactive per equipe per farm)
        → M5 (consolidated multi-equipes report + Excel)
          → M6 → H1
```

**Total screens**: ~6 interactive + auto-processing
**Key difference**: Each equipe has independent meta; territory auto-distribution available

---

## 7. Data Flow

### 7.1 Config State (`config.json`)

```
config.json
├── micro_padrao: str              # path to micro .xlsx
├── tarifas: dict                  # {tarifa_name: {rendimento_hh, rendimento_hm, tipo, custo_h, preco_ha}}
├── de_para: dict                  # {micro_name: tarifa_name}
├── fazendas_ct: list              # [farm_name, ...]
├── orcamento_estrito: bool
├── jornada_horas: float
├── custo_hora_tf: float
├── modo_seq_padrao: str           # "implantacao" | "manutencao_swg" | etc.
├── sequencia: dict                # cascade/block rules per mode
├── comparativo: dict              # multi-factor config
└── perfis_equipe: list            # saved team profiles
```

**Lifecycle**:
- Loaded at H0 (splash)
- Saved after: H2 (tarifas), H3 (STG integration), H4 (de_para), H5 (micro), H6 (fazendas_ct), S5 (orcamento_estrito), S8 (sequence default), S10 (jornada), S15f (strict validation), B2 (team profile)
- Never saved during: S14 (session HH), S15 checkpoint edits (except jornada)

### 7.2 Session Context (`contexto_sessao`)

```
SessaoContext
├── fazenda_selecionada: str
├── equipe_selecionada: str
├── talhoes_selecionados: list
├── total_talhoes_fazenda: int
├── area_total_fazenda: float
├── atividades_distribuidas: int
├── total_atividades: int
├── data_inicio: str
├── data_termino: str
├── modo_atual: str
├── tarifas_carregadas: int
├── orcamento_estrito: bool
└── timestamp_atualizacao: datetime
```

**Lifecycle**: Created at H0, updated throughout, drives dashboard_header().

### 7.3 Scheduler-Local State

```
calcular_cronograma_inteligente()
├── Input: cfg, df_faz, fazenda, ctx (batch/multi-equipes), escopo_meta
├── Local: turmas, demanda_global, cronograma, session_hh
├── Output: resultado_final dict
│   ├── fazenda, dias_simulado, meses_simulado
│   ├── total_hh, total_hm
│   ├── dias_mecanizado, ganho_mecanizado_dias
│   ├── cronograma (base), turmas_snapshot
│   └── comparativo_mecanizado (if applicable)
└── Special: {"acao": "retroceder_escopo"} → restarts farm selection
```

### 7.4 Data Flow Diagram

```
┌─────────────┐     load      ┌─────────────┐
│ config.json │──────────────→│    cfg       │
└──────┬──────┘               │ (in-memory)  │
       │                      └──────┬───────┘
       │ save after prompts          │ read by scheduler
       │                             ↓
┌─────────────┐     load      ┌─────────────┐
│  micro.xlsx │──────────────→│    df        │
└─────────────┘               │ (DataFrame)  │
                              └──────┬───────┘
                                     │ filtered by fazenda/talhão/metodologia
                                     ↓
                              ┌─────────────┐
                              │ scheduler   │
                              │ (core)      │
                              │             │
                              │ turmas ← user interaction
                              │ demandas ← df + cfg
                              │ cronograma ← simulation
                              └──────┬───────┘
                                     │ export
                                     ↓
                              ┌─────────────┐
                              │ data/dossies│
                              │  /          │
                              │ *.xlsx      │
                              └─────────────┘
```

### 7.5 Key State Transitions

| From Screen | To Screen | State Change |
|---|---|---|
| H5 → H1 | `cfg["micro_padrao"]` updated, `df` reloaded |
| S0a → S0 | `contexto_sessao.atualizar_equipe()`, `df_scope` filtered |
| S3 → S4 | `penalidade_declividade` set (1.0/1.15/1.30) |
| S4 → S5 | `df_faz` may have added/removed/substituted activities |
| S5 → S6 | `cfg["orcamento_estrito"]` toggled |
| S8 → S9 | `modo_seq` selected, `cfg["modo_seq_padrao"]` maybe saved |
| S10 → S11 | `prazo_meses`, `executores`, `jornada` set; `cfg["jornada_horas"]` saved |
| S12 → S13 | `turmas[*].atividades` populated |
| S13 → S14 | `reatribuicao`, `paralelo`, `primaria` set |
| S14 → S15 | `session_hh` populated with overrides |
| S15[6] → S0 | `{"acao": "retroceder_escopo"}` — full restart |
| S18 → S19 | `recursos_mec`, `cronograma_com_mec` set |
| S21 → S22 | Excel files written to `data/dossies/` |
| B3 → B4 | `resultados[]` accumulated; `dias_acumulados` tracked |

---

## 8. Component Inventory — Reusable Widgets

11 reusable components that map from CLI primitives to mobile UI.

---

### 8.1 S/N Toggle Chip Pair

**Source**: `confirmar()` (ui.py)

| Property | Value |
|---|---|
| **Variant A** | Two flat chips: `[SIM]` (green bg #00FF66/black text) `[NÃO]` (red bg #FF3333/white text) |
| **Variant B** | Two hard-shadow chips: `[Sim]` (primary bg #2D6A4F/white) `[Não]` (white bg, black border, 4px shadow) |
| **Default indicator** | Chip with `•` dot or bold border |
| **Accessibility** | `role="switch"`, `aria-checked` |

---

### 8.2 Text Field

**Source**: `prompt()` (ui.py)

| Property | Value |
|---|---|
| **Label** | Above field, dim text |
| **Default** | Pre-filled, auto-selected on focus |
| **Keyboard** | Varies: text, number, email |
| **Variant A** | No border, green bottom line only, monospace |
| **Variant B** | White card, 4px shadow, Inter font |
| **Enter key** | Submits (maps to ENTER in CLI) |

---

### 8.3 Number Stepper

**Source**: `pedir_float()`, `pedir_int()` (ui.py)

| Property | Value |
|---|---|
| **Label** | Above stepper |
| **Default** | Pre-filled |
| **Controls** | `[−]` `[value]` `[+]` buttons |
| **Step** | 0.1 for `pedir_float`, 1 for `pedir_int` |
| **Allow zero** | Configurable (`allow_zero` parameter) |
| **Min/Max** | Clamp per field (e.g., month 1-12) |
| **Variant A** | Green accent, monospace value |
| **Variant B** | Card with shadow, Inter value |

---

### 8.4 Dual-Mode Decimal/Time Input

**Source**: `pedir_jornada()` (ui.py)

| Property | Value |
|---|---|
| **Label** | "Jornada efetiva diária" |
| **Mode toggle** | `[Decimal]` `[HH:MM]` chip pair |
| **Decimal mode** | Number stepper (step 0.1) |
| **Time mode** | Hour picker + Minute picker (0/15/30/45) |
| **Conversion** | 6.5 ↔ 6:30, 4.3 ↔ 4:18 |
| **Output** | Always stored as float (hours) |

---

### 8.5 Radio List

**Source**: `selecionar()` (ui.py)

| Property | Value |
|---|---|
| **Layout** | Vertical list of radio items |
| **Selection** | Single-select only |
| **Item format** | `{index}. {label}` |
| **Variant A** | Black items, green radio dot, monospace |
| **Variant B** | White cards with 4px shadow, primary radio dot |
| **Scroll** | If >8 items → scrollable area (max 60vh) |

---

### 8.6 Paginated List

**Source**: `selecionar_paginado()` (ui.py)

| Property | Value |
|---|---|
| **Page size** | Default 5 items per page (configurable; some callers pass 8 or 10) |
| **Navigation** | Swipe left/right or `[← Anterior]` `[Próximo →]` chips |
| **Selection** | Single-select tap |
| **Search** | Optional filter bar at top |
| **Item format** | `{index}. {label}` (truncated at 55 chars) |
| **Empty state** | "(vazio)" dim text |
| **Cancel** | Back button or swipe-down |

---

### 8.7 Activity Card (Percurso S/N)

**Source**: Per-turma percurso loop (turmas.py)

| Property | Value |
|---|---|
| **Layout** | Full-screen, one card at a time |
| **Card content** | `[{i}/{total}] [{X/ }] '{activity_name}'` |
| **Chips** | 4 bottom chips in thumb zone: `[Sim]` `[Não]` `[Abortar]` `[OK]` |
| **Progress** | Top progress bar: `i/total` |
| **Swipe** | Right=Sim, Left=Não (optional gesture) |
| **Variant A** | Black card, green/red chips, monospace |
| **Variant B** | White card + shadow, primary/danger chips |

---

### 8.8 Banner / Alert

**Source**: `aviso()`, `erro()`, `ok()` (ui.py)

| Type | Color A | Color B | Icon |
|---|---|---|---|
| **Warning** (`aviso`) | Yellow #FFD600 | Amber #F59E0B | `warning` |
| **Error** (`erro`) | Red #FF3333 | Red #DC2626 | `error` |
| **Success** (`ok`) | Green #00FF66 | Green #2D6A4F | `check_circle` |
| **Duration** | Until dismissed or auto (3s for ok) | Until dismissed | — |
| **Position** | Top snackbar | Top snackbar | — |

---

### 8.9 Dashboard Context Card

**Source**: `dashboard_header()` (context.py)

| Property | Value |
|---|---|
| **Collapsed** | Single row: 4 chips (fazenda, equipe, modo, prazo) |
| **Expanded** | Full detail card: all 10+ fields in grid |
| **Toggle** | Tap to expand/collapse |
| **Position** | Pinned top of scroll area |
| **Variant A** | Dark card, green accent chips, monospace |
| **Variant B** | White card, hard shadow, Inter, colored status dots |

---

### 8.10 Rich Table Viewer

**Source**: `console.print(Table)` throughout scheduler_core.py

| Property | Value |
|---|---|
| **Layout** | Horizontal scroll if needed, fixed first column |
| **Columns** | Auto-width, right-align numbers |
| **Styling** | Header row primary color, data rows alternating |
| **Overflow** | "+N more" for truncated content |
| **Actions** | Pinch-to-zoom, export button |
| **Variant A** | Black bg, green/cyan headers, monospace |
| **Variant B** | White bg, hard shadow, Inter, primary headers |

---

### 8.11 CHECKPOINT FAB

**Source**: CHECKPOINT RETROATIVO hub (scheduler_core.py)

| Property | Value |
|---|---|
| **Position** | Bottom-right, 56dp FAB |
| **Icon** | `edit_note` (Material Symbols) |
| **Color A** | Green #00FF66 on black |
| **Color B** | Primary #2D6A4F with 4px shadow |
| **Tap** | Opens bottom sheet with 7 options |
| **Visibility** | Shown only during S11–S15 flow (turmas through checkpoint) |
| **Badge** | Orange dot if unsaved changes exist |

---

## 9. Iconography — Material Symbols Mapping

Full mapping of all icons used in the application.

### 9.1 Navigation & Menu

| Icon | Name | Used In |
|---|---|---|
| `event_note` | Smart Scheduler | H1 option [1] |
| `upload_file` | Importar Tarifas | H1 option [2] |
| `transform` | Normalizar CT | H1 option [3] |
| `swap_horiz` | Mapeamentos de/para | H1 option [4] |
| `folder_open` | Trocar Micro | H1 option [5] |
| `domain` | Fazendas CT | H1 option [6] |
| `dashboard` | Monitor Externo | H1 option [M] |
| `exit_to_app` | Sair | H1 option [0] |

### 9.2 Scheduler Flow

| Icon | Name | Used In |
|---|---|---|
| `landscape` | Declividade | S3 |
| `filter_list` | Scope adjustments | S1, S2, S4 |
| `toggle_on` / `toggle_off` | Orçamento Estrito | S5 |
| `list_alt` | Activities Found | S6 |
| `compare_arrows` | Comparativo Manual vs Mec | S7 |
| `auto_fix` | Auto suggestions | S7a-1 |
| `search` | Manual catalog | S7a-2 |
| `add_circle` | External resource | S7a-3 |
| `account_tree` | Sequence selection | S8 |
| `block` | Bloqueio global | S9 |
| `group_work` | Reforço / Pelotão | S9 |
| `calendar_today` | Prazo / Calendário | S10 |
| `people` | Operários / Equipe | S10 |
| `schedule` | Jornada | S10 |
| `groups` | Criar Turmas | S11 |
| `link` | Vincular Atividades | S12 |
| `checklist` | Percurso S/N | S12a |
| `warning` | Conflitos | S13 |
| `swap_horiz` | Reatribuição | S13b |
| `edit_note` | CHECKPOINT FAB | S15 |
| `trending_up` | HH/HM pre-checagem | S16 |
| `play_arrow` | Simulação | S17 |
| `precision_manufacturing` | Modo Mecanizado | S18 |
| `bar_chart` | Ocupação / Comparativo | S19 |
| `fact_check` | Auditoria Escopo | S20 |
| `file_download` | Excel Export | S21 |
| `timer` | Diagnóstico Prazo | S22 |
| `compare` | Comparativo Result | S23 |

### 9.3 Status & Feedback

| Icon | Name | Used In |
|---|---|---|
| `check_circle` | Success (ok) | Banners |
| `error` | Error (erro) | Banners |
| `warning` | Warning (aviso) | Banners |
| `info` | Informational | Banners |
| `schedule` | Prazo OK | S22 |
| `event_busy` | Prazo Excedido | S22 |
| `speed` | HM-only activity | S16, S18 |

### 9.4 Actions

| Icon | Name | Used In |
|---|---|---|
| `add` | Add activity/turma | S4, S11, S12b |
| `remove` | Remove activity | S12b |
| `edit` | Edit resource | S18a-1 |
| `undo` | Undo last change | S7a-2 |
| `save` | Save profile | B2 |
| `folder` | File picker | H2, H3, H5 |
| `description` | Sheet selector | H2b |
| `map` | Territory mode | M2 |
| `pie_chart` | Consolidated report | B4, M5 |

---

## 10. Appendix

### 10.1 CLI Prompt → Mobile Traceability Table

| CLI Function | Source File:Line | Mobile Component | Screen(s) |
|---|---|---|---|
| `prompt()` | ui.py:89 | Text Field (8.2) | S10, S11, S12, H4, M3 |
| `confirmar()` | ui.py:95 | S/N Toggle (8.1) | S3, S4, S5, S7, S8, S9, S10, S12, S13, S15, S15f, S15f-2, S16, S18, S25, B1, B2, M2 |
| `pedir_float()` | ui.py:101 | Number Stepper (8.3) | S10, S18a, S15f |
| `pedir_int()` | ui.py:107 | Number Stepper (8.3) | S10, S11, B2, M3 |
| `pedir_jornada()` | ui.py:113 | Dual-Mode Input (8.4) | S10, S15e, B1 |
| `selecionar()` | ui.py:119 | Radio List (8.5) | S3, S7a, S8, S9, S12b, S13, H2b, H4, M3 |
| `selecionar_paginado()` | ui.py:125 | Paginated List (8.6) | S4, S7a-2, S12b, S13b, S15f, H2c, H4 |
| `aviso()` | ui.py:131 | Warning Banner (8.8) | Throughout |
| `erro()` | ui.py:137 | Error Banner (8.8) | S10, S15f, B2 |
| `ok()` | ui.py:143 | Success Banner (8.8) | Throughout |
| `linha()` | ui.py:149 | Divider | Between sections |
| `sub()` | ui.py:155 | Sub-Divider | Between sub-sections |
| `cabecalho()` | ui.py:161 | Screen Header (4.3) | H0, H1 |
| `subcabecalho()` | ui.py:167 | Section Header | H2-H7, B1-B4, M1-M5 |
| `dashboard_header()` | context.py:45 | Dashboard Card (8.9) | Persistent top |

### 10.2 Color Token Cross-Reference

| CLI Constant | Meaning | Variant A (Raw) | Variant B (Neo-Brutalist) |
|---|---|---|---|
| `G` (Green) | Success/primary | #00FF66 | #2D6A4F |
| `Y` (Yellow) | Warning | #FFD600 | #F59E0B |
| `C` (Cyan) | Info/secondary | #00E5FF | #0EA5E9 |
| `R` (Red) | Error/danger | #FF3333 | #DC2626 |
| `DM` (Dim) | Muted text | #666666 | #9CA3AF |
| `BL` (Bold) | Emphasis | font-weight:700 | font-weight:700 |
| `RS` (Reset) | Default | #CCCCCC | #1F2937 |
| bg | Background | #0A0A0A | #FAFAFA |
| surface | Card/panel | #141414 | #FFFFFF |
| border | Border | #00FF66 1px | #1F2937 2px |

### 10.3 Screen Count Summary

| Flow | Interactive Screens | Sub-screens | Total |
|---|---|---|---|
| Home/Menu (H0–H7) | 8 | 5 | 13 |
| Single Farm (S0–S25) | 26 | 14 | 40 |
| Batch (B1–B4) | 4 | 2 | 6 |
| Multi-Equipes (M1–M6) | 6 | 1 | 7 |
| **Total** | **44** | **22** | **66** |

### 10.4 Keyboard → Mobile Input Mapping

| CLI Input | Mobile Input | Notes |
|---|---|---|
| ENTER (empty) | Tap card background / "Manter" chip | Keep default |
| `s`/`sim`/`y`/`yes` | `[Sim]` chip | Green accent |
| `n`/`não`/`no` | `[Não]` chip | Red/danger accent |
| `a` (abortar) | `[Abortar]` chip | Orange accent |
| `ok` | `[OK]` chip | Blue accent — quick exit |
| `t` (trocar) | `[Trocar]` chip | Purple accent |
| Number (`1,3,5-7`) | Multi-select + range chips | Or swipe-select |
| Decimal (`6.5` or `6:30`) | Dual-mode stepper (8.4) | Auto-converts comma→dot |
| Text filter | Search bar | Real-time filter |
| `0` (voltar/concluir) | Back arrow / "Concluir" button | Always in thumb zone |

### 10.5 Error States & Edge Cases

| Condition | CLI Behavior | Mobile Behavior |
|---|---|---|
| No micro file found | Auto-prompt file picker | Redirect to H5 with empty state |
| Single farm in scope | Auto-select with message | Skip S0, toast "Fazenda única" |
| No methodology column | Skip S1 | Hide methodology section entirely |
| No `equipe` column | Skip S0a | Hide empresa filter |
| Orphan activities after linking | Warning + confirm dialog | Warning banner + S/N toggle |
| Activities without executora | Red list + confirm "continuar?" | Danger banner + S/N toggle |
| Orçamento estrito validation failure | Per-gap prompt loop | Full-screen modal per gap |
| Retrocede (checkpoint [6]) | `return {"acao": "retroceder_escopo"}` | Pop to S0 with slide animation |
| Batch: 80%+ meta consumed | Yellow warning per farm | Amber banner + progress bar |
| Batch: 100%+ meta consumed | Red "JA EXCEDIDA" | Red banner + progress bar |
| Invalid number input | "Valor inválido." (`pedir_float/int`), "Valor inválido, ignorado." (scheduler) | Shake animation + red border |
| Zero operários | "Precisa de pelo menos 1" | Error banner, block continue |
| No tariff data | "Nenhuma tarifa em config" | Error dialog, redirect to H2/H3 |
| Remaining methodologies after simulation | S25 loop gate | Methodology list + S/N toggle, loops to S2 |

### 10.6 Animation & Motion

| Variant | Transition | Duration | Curve |
|---|---|---|---|
| A (Raw) | Cut/hard swap | 0ms | None |
| B (Neo-Brutalist) | Slide-up (sheets), fade (screens) | 150-200ms | ease-out |
| Both | Banner entry | 200ms | ease-in-out |
| Both | Percurso card swap | 150ms | ease-out |

### 10.7 Responsive Breakpoints

| Breakpoint | Layout |
|---|---|
| < 360dp (small phone) | Single column, full-screen cards, bottom chips |
| 360–599dp (phone) | Single column, card with side padding |
| 600–839dp (tablet portrait) | Two-column where applicable (e.g., turma list + detail) |
| 840dp+ (tablet landscape / web) | Master-detail, sidebar nav possible |

### 10.8 CLI→Mobile Component Conversion Table

The CLI uses three input mechanisms that do NOT map 1:1 to the mobile components in §8. This table documents every conversion so Google Stitch generates the correct mobile component for each CLI input source.

#### 10.8.1 Raw `input()` Calls → Mobile Component

The CLI uses `input()` directly (not via `ui.py` wrappers) in several places. These must be converted to structured mobile components:

| Screen | Code Location | CLI `input()` prompt | Mobile Component | Notes |
|---|---|---|---|---|
| S7a | scheduler_core.py:245 | `>> Opção [1/2/3/0]:` | Radio List (8.5) | 3 options + "Voltar" |
| S7a-1 | scheduler_core.py:271 | `>> Escolha:` | Multi-select chips (8.7) | Comma-separated numbers → toggle chips; ENTER → "Selecionar Todas" |
| S7a-2 | scheduler_core.py:329 | `>> Número (0 para voltar ao menu):` | Paginated List (8.6) + command chips | Dual-use: number OR [L]/[U]/[A] command. Split into: paginated list for activity selection + separate chip row for L/U/A |
| S7a-2 | scheduler_core.py:380 | `[ENTER para voltar ao catálogo manual]` | Dismiss button / back | Overlay dismissal |
| S7a-2 | scheduler_core.py:398 | `>> Número da atividade manual (0 para cancelar):` | Paginated List (8.6) | Single-select |
| S7a-3-1 | scheduler_core.py:459 | `[ENTER para continuar]` | Continue button | Non-interactive acknowledgment |

#### 10.8.2 `prompt("Opcao")` Used as Menu Selector → Radio List

Several screens use `prompt("Opcao", "0")` for menu selection instead of `selecionar()`. These must render as Radio Lists or Bottom Sheets on mobile:

| Screen | Code Location | CLI Pattern | Mobile Component |
|---|---|---|---|
| S12b | turmas.py:424 | `prompt("Opcao", "0")` | 10-option Radio List (9 + Voltar) |
| B3a | excel_export.py:544 | `prompt("Opcao", "0")` | 4-option Radio List (0-3) |
| H6 | territorio.py:98 | `prompt("Opcao")` | 7-option Radio List |
| H4c | tarifas.py:788 | `prompt("Opcao")` | Menu Radio List |

#### 10.8.3 `prompt()` Used as S/N Chip Input → Keep as Chip Bar

These `prompt()` calls are the **correct** mechanism for percurso S/N flows and should map to the 4-chip Activity Card (8.7):

| Screen | Code Location | CLI Pattern | Mobile Component |
|---|---|---|---|
| S12a | turmas.py:205 | `prompt("[i/N] Vincular '{a}'? (s/n/a/ok)")` | Activity Card (4 chips: s/n/a/ok) |
| S12c | turmas.py:368 | `prompt("[i/N] '{a}' (ENTER/n/t/a/ok)")` | Activity Card (5 chips: enter/n/t/a/ok) |
| S18a | turmas.py:326 | `prompt("[i/N] [{mk}] '{a}' (s/n/a/ok)")` | Activity Card (4 chips: s/n/a/ok) |

#### 10.8.4 `prompt()` Used as Search/Filter → Search Bar

| Screen | Code Location | CLI Pattern | Mobile Component |
|---|---|---|---|
| S12b [3] | turmas.py:431 | `prompt("Texto no nome (ex: roçada)")` | Search bar with real-time filter |
| S12b [5] | turmas.py:477 | `prompt("Remover cujo nome contém")` | Search bar |
| S12b [7] | turmas.py:524 | `prompt("Filtro do destino (opcional)")` | Search bar |
| H4b | territorio.py:109 | `prompt("Nome EXATO como no micro ou na CT")` | Text field with autocomplete |
| H4b | territorio.py:138 | `prompt("Nomes separados por vírgula ou ;")` | Tag input field |
| M3 | scheduler_core.py:3103 | `prompt("Índices das fazendas (ex: 1,3,5-7)")` | Multi-select + range chips |

### 10.9 ASCII→Accented Portuguese Conversion Rules

**CRITICAL for Google Stitch**: The CLI codebase uses ASCII-only Portuguese (no cedillas, no accents) for ALL UI strings except `scheduler_core.py` lines 239–241 (comparativo mode labels). The mobile app must display proper accented Portuguese for user-facing text.

#### Conversion Rules (apply to ALL prompt labels, banners, titles, and display text)

| ASCII Pattern | Accented Form | Examples |
|---|---|---|
| `cao` (end of word) | `ção` | `conclusao` → `conclusão`, `implantacao` → `implantação` |
| `coes` | `ções` | `ações`, `exceções` |
| `oes` | `ões` | `informações`, `sugestões` |
| `acao` | `ação` | `configuracao` → `configuração`, `validacao` → `validação` |
| `ecao` | `eção` | `selecao` → `seleção` |
| `operario(s)` | `operário(s)` | — |
| `orcamento` | `orçamento` | — |
| `inicio` | `início` | — |
| `termino` | `término` | — |
| `periodo` | `período` | — |
| `numero` | `número` | — |
| `cenario` | `cenário` | — |
| `catalogo` | `catálogo` | — |
| `reforco` | `reforço` | — |
| `pelotao` | `pelotão` | — |
| `proximas` | `próximas` | — |
| `logica` | `lógica` | — |
| `teorico/a` | `teórico/a` | — |
| `pratico/a` | `prático/a` | — |
| `unico/a` | `único/a` | — |
| `disponivel` | `disponível` | — |
| `possivel` | `possível` | — |
| `responsavel` | `responsável` | — |
| `automatico/a` | `automático/a` | — |
| `diario/a` | `diário/a` | — |
| `substituicao` | `substituição` | — |
| `distribuicao` | `distribuição` | — |
| `vinculacao` | `vinculação` | — |
| `liberacao` | `liberação` | — |
| `atribuicao` | `atribuição` | — |
| `execucao` | `execução` | — |
| `geracao` | `geração` | — |
| `exibicao` | `exibição` | — |
| `restauracao` | `restauração` | — |

#### Exceptions (DO NOT accent)

| Word | Reason |
|---|---|
| `bloqueio` | Correct without accent |
| `fazenda` | Correct without accent |
| `equipe(s)` | Correct without accent |
| `turma` | Correct without accent |
| `cronograma` | Correct without accent |
| `metodologia` | Correct without accent |
| `jornada` | Correct without accent |
| `tarifa` | Correct without accent |
| `comparativo` | Correct without accent |
| `mecanizado` | Correct without accent |
| `template` | English loanword |

#### Implementation Note

When tracing prompt strings from code to mobile, ALWAYS apply these conversion rules. The report already uses accented Portuguese throughout — this table serves as the authoritative reference for any string that appears differently between code and report.

---

*End of LAYOUT_REPORT.md — SRF v6.3 Mobile Android Layout Specification for Google Stitch*

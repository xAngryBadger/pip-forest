# SRF Mobile – Layout & Interaction Improvement Plan

This document provides a complete, detailed guide for revising the layout and interaction patterns of the SRF mobile application (Kivy‑based) to make it simpler, more affordable to develop, and practical for daily use. All suggested changes preserve the existing functionality (matching desktop CLI v6.2) while reducing visual clutter, tap count, and scrolling effort.

---  

## Table of Contents
1. [Guiding Principles](#guiding-principles)  
2. [Screen‑by‑Screen Recommendations](#screen-by-screen-recommendations)  
   2.1 Dashboard  
   2.2 Step 1 – Empresa  
   2.3 Step 2 – Fazenda  
   2.4 Steps 3‑4 – Metodologias & Talhōes  
   2.5 Step 5 – Sequência  
   2.6 Step 6 – Bloqueios  
   2.7 Step 7 – Projeto  
   2.8 Step 8 – Turmas (Team Assignment)  
   2.9 Step 9 – Atividades (Link Activities)  
   2.10 Step 10 – Conflitos (Parallel/Exclusive & Reatribuição)  
   2.11 Step 11 – Comparativo  
   2.12 Step 12 – HH/ha (Tarifa Adjustment)  
   2.13 Step 13 – Escopo (Add/Remove/Substituir)  
3. [Widget‑Level Tweaks](#widget-level-tweaks)  
4. [Interaction Flow Recommendations](#interaction-flow-recommendations)  
5. [Visual & Accessibility Notes](#visual--accessibility-notes)  
6. [Implementation Roadmap](#implementation-roadmap)  
7. [Expected Impact](#expected-impact)  
8. [Risks & Mitigations](#risks--mitigations)  
9. [Appendix – File‑wise Change Summary](#appendix--file-wise-change-summary)  

---  

<a name="guiding-principles"></a>
## 1. Guiding Principles
| Principle | Rationale | Application |
|-----------|-----------|-------------|
| **Single source of truth for selections** | Users should see what is chosen without scanning many boxes. | Replace long checkbox lists with searchable multi‑select spinners or chip‑based pickers that display selected items inline. |
| **Minimize vertical scrolling** | Scrolling hides context and increases effort. | Collapse optional sections into expandable cards; keep primary actions visible without scroll. |
| **Uniform input affordance** | Inconsistent tap targets cause errors. | Standardize height (44 dp) for all touchable widgets (buttons, spinners, checkboxes, switches). Use same visual feedback (border change on focus). |
| **Progressive disclosure** | Show only what is needed at each wizard step. | Hide secondary options behind a “More▼” toggle or move them to a secondary screen accessible via a button. |
| **Clear feedback for state changes** | Users must know when a toggle or selection took effect. | Update labels/counters instantly; use chip badges or counters (e.g., “3 de 12 selecionados”). |
| **Leverage existing theme** | The brutalist look is already appreciated; we only adjust layout, not colors. | Keep the same `Colors`, `RADIUS`, and line‑based graphics; only change widget composition and container sizing. |

---  

<a name="screen-by-screen-recommendations"></a>
## 2. Screen‑by‑Screen Recommendations

### 2.1 Dashboard (`dashboard.py`)
- **Current**: Four `_DataBadge` widgets + two action buttons.
- **Improvement**:
  - Keep the badge grid (compact and informative).
  - Replace the two action boxes with a single horizontal row:
    - **Primary** button (“INICIAR SCHEDULER”) stays primary.
    - **Secondary** button (“IMPORTAR CT 317”) becomes an outlined flat button (same height).
  - Add a small **info icon** (ⓘ) next to the version text that opens a tooltip with build‑date/commit hash (helps users confirm version without clutter).

### 2.2 Step 1 – Empresa (`scheduler.py:_build_step_1`)
- **Current**: `SRFSpinner` with a hint box below.
- **Improvement**:
  - Keep the spinner (good single‑choice control).
  - Move the hint box **inside** the spinner’s dropdown as a disabled first item (“TODAS = roda todas as fazendas da equipe.”) or show it as helper text below the spinner (smaller font, dim colour).
  - Ensure the spinner displays “Selecione…” when empty.

### 2.3 Step 2 – Fazenda (`scheduler.py:_build_step_2`)
- **Current**: Spinner + hint box (same as Step 1).
- **Improvement**: Apply the same changes as Step 1.
  - Additionally, when “TODAS AS FAZENDAS” or “MULTI‑EQUIPES” is selected, automatically advance to Step 4 (already done) – keep this behaviour but add a brief toast (“Pulando para Sequência…”) to reassure the user.

### 2.4 Steps 3‑4 – Metodologias & Talhōes (`scheduler.py:_build_step_3`, `_build_step_4`)
- **Current**: Searchable list of checkboxes with “TODAS/NENHUMA” buttons.
- **Pain**: Long list; many taps to select/deselect; scrollbar appears on many devices.
- **Improvement Options** (pick one; both compatible):
  1. **Chip‑based Multi‑Select Spinner**  
     - Replace the vertical list with a single `SRFSpinner` whose popup contains a searchable list of checkboxes.  
     - The spinner’s displayed text shows selected items as chips (e.g., “Metodologia A, Metodologia B …”) or “X de Y selecionados”.  
     - Keep the “TODAS/NENHUMA” actions as **menu items** inside the popup (top‑right buttons).  
     - The search box stays at the top of the popup.
  2. **Expandable Card with Toggle All**  
     - Keep the list but wrap it in an `SRFCard` that can be collapsed/expanded via a header toggle.  
     - Add a **“Select All”** and **“Select None”** as **toggle switches** in the card header (right‑aligned).  
     - This reduces height when collapsed and still gives quick bulk actions.
- Both approaches keep the existing `_step3_checkboxes` / `_step4_checkboxes` lists internally; only the view changes.

### 2.5 Step 5 – Sequência (`scheduler.py:_build_step_5`)
- **Current**: Three `SRFRadio` widgets stacked vertically.
- **Improvement**:
  - Replace with a single `SRFSpinner` (dropdown) showing the three options.
  - Show the description of the selected option in a **helper label** below the spinner (updated on change).
  - This saves vertical space and provides a clearer tap target.

### 2.6 Step 6 – Bloqueios (`scheduler.py:_build_step_6`)
- **Current**: Three `SRFSwitch` widgets with labels.
- **Improvement**:
  - Keep switches (appropriate for binary flags).
  - Group them inside an `SRFCard` titled “Bloqueios” with a thin divider between each switch for visual separation.
  - Add a short **summary line** at the bottom: “Bloqueio: OFF | Reforço: ON | Pool: OFF” that updates live.

### 2.7 Step 7 – Projeto (`scheduler.py:_build_step_7`)
- **Current**: Mix of steppers, inputs, switches, spinners.
- **Improvement**:
  - Ensure all `SRFStepperInput` and `SRFInput` have explicit `input_type='text'` (verify any missing).
  - Collapse the “DATA DE FIM” section into the same row as “DATA DE INÍCIO” when the toggle is off (height = 0).
  - Replace the terrain spinner with a **segmented control** (three small buttons) if desired, but keep spinner for simplicity.
  - Keep the penalty stepper as is; it is already compact.

### 2.8 Step 8 – Turmas (Team Assignment) (`scheduler.py:_build_step_8`)
- **Current**: Top bar with “SUGERIR EQUIPES” / “+ ADICIONAR TURMA”; dynamic turma cards; bottom “ATIVIDADES PENDENTES” panel with per‑activity assign buttons.
- **Pain**: Many nested BoxLayouts; adding/removing turmas causes layout jumps; assigning an activity requires tapping a small “+” button inside each pending item.
- **Improvement Plan** (modular, can be done stepwise):
  1. **Two‑Panel Layout** (replaces current “turmas list + pending list”):
     - **Left panel**: Turmas (compact cards, show name + operários).
     - **Right panel**: Atividades (simple list, each row shows activity name).
     - Between panels, place **arrow buttons** (`>` to assign selected activity to selected turma, `<` to remove).
     - Mirrors classic “available ↔ selected” pickers and reduces nested scrolling.
  2. **Turma Card Simplification**:
     - Keep the card but reduce internal padding (use `dp(6)` instead of `dp(10)` for inner spacing).
     - Show assigned activities as **chips** (small rounded labels) wrapping horizontally; if >3 chips, show “+ N more”.
     - Remove the internal “stats row” (operários + especialidade) and move that info to the card header as a subtitle.
  3. **Add/Remove Turma Controls**:
     - Place a **Floating Action Button (FAB)**‑style circle (or a small `SRFButton` with “+”) at the bottom‑right of the left panel.
     - Tapping it opens a small dialog (`Popup`) with fields for name and quantity (stepper).
     - Keeps the main UI uncluttered.
  4. **Pending Activities List**:
     - Show as a simple list; each row has a **checkbox** (instead of a button) to mark for assignment.
     - A “Assign Checked → Turma” button appears at the bottom of the right panel when any checkbox is checked.
  5. **Sugerir Equipes / Território**:
     - Keep the log panel but make it collapsible (header with toggle).

### 2.9 Step 9 – Atividades (Link Activities) (`scheduler.py:_build_step_9`)
- **Current**: Similar to Step 8 but with per‑turma cards containing checkboxes.
- **Improvement**: Mirror the **Two‑Panel** approach from Step 8:
  - Left: Turmas (read‑only chips showing assigned activities).
  - Right: Activities list with checkboxes.
  - Arrow buttons to move checked activities between turmas.
  - Keep the “AUTO‑DISTRIBUIR” button at the bottom.

### 2.10 Step 10 – Conflitos (Parallel/Exclusive & Reatribuição) (`scheduler.py:_build_step_10`)
- **Current**: Lists of conflicted activity rows with a switch per row + separate reatribuição spinners.
- **Improvement**:
  - Combine the two concepts into a **single table‑like row**:
    - Activity name (left).
    - Toggle for “Exclusivo” (switch).
    - Button “Reatribuir →” that opens a small popup to choose destination turma (spinner).
    - Show the current destino as a label next to the button (or “—” if none).
  - Reduces vertical height per conflict and keeps related controls together.

### 2.11 Step 11 – Comparativo (`scheduler.py:_build_step_11`)
- **Current**: Switch to activate, then a list of manual→mec pairs, plus multi‑factor inputs.
- **Improvement**:
  - Keep the master switch.
  - Replace the manual→mec list with a **two‑column Spinner** (or a simple `SRFDataTable` with two columns) where each row shows the pair.
  - Provide “+” and “‑” buttons above the table to add/remove pairs (opens a dialog with two spinners).
  - Keep multi‑factor inputs as is but place them in an `SRFCard` titled “Multi‑Fator (Opcional)” that collapses when the master switch is off.

### 2.12 Step 12 – HH/ha (`scheduler.py:_build_step_12`)
- **Current**: Table‑like rows with labels and an `SRFInput` for adjustment.
- **Improvement**:
  - Keep the table layout but **reduce row height** to `dp(30)` and tighten padding (`dp(4)`).
  - Make the adjustment field **always visible** (no need for a separate cell; just an input that fills its column).
  - Add a **“Reset All”** button at the bottom that clears all inputs.
  - Ensure the header remains sticky (use a `ScrollView` with the header outside the scroll area if needed).

### 2.13 Step 13 – Escopo (`scheduler.py:_build_step_13`)
- **Current**: Buttons at top, then a list of operations as plain labels.
- **Improvement**:
  - Keep the three top buttons.
  - Render each operation as a **colored chip** (e.g., Add = green background, Remove = red, Substituir = blue) with the text inside.
  - Chips wrap horizontally; when they exceed width, they flow to the next line (use a `BoxLayout` with `orientation: 'horizontal'` and `size_hint_y: None`).
  - Provides instant visual scanning of queued changes.

---  

<a name="widget-level-tweaks"></a>
## 3. Widget‑Level Tweaks
| Widget | Current | Suggested tweak (no new assets) |
|--------|---------|---------------------------------|
| `SRFCheckbox` | 22 dp box + label | Increase hit‑area to full height (`size_hint_y: None, height: dp(44)`) and vertically center label. |
| `SRFRadio` | Same as checkbox | Same as checkbox. |
| `SRFSwitch` | 36 dp track + thumb | Ensure entire row height is `dp(44)` for consistent tap target. |
| `SRFSpinner` | Dropdown with default text | Add clear placeholder “Selecione…” when no value; ensure dropdown width matches spinner width. |
| `SRFInput` | TextInput with hint | Always set `multiline=False` for single‑line fields; set `input_type='text'` to force keyboard on Android. |
| `SRFButton` | Flat / Primary / Danger | Enforce minimum width `dp(64)` for icon‑only buttons (e.g., “+”, “x”) so they are easier to tap. |
| `SRFLabel` | Used for hints/titles | Add utility style `Caption` (size `sp(10)`, dim colour) for helper text; reuse across screens. |
| Pop‑ups / Dialogs | Various sizes | Standardise modal width `0.92` and height `0.8` (as used elsewhere); add subtle semi‑transparent backdrop (`rgba(0,0,0,0.3)`) to focus attention. |

---  

<a name="interaction-flow-recommendations"></a>
## 4. Interaction Flow Recommendations
1. **Preserve Wizard Linear Flow** – Keep the “Back / Next” buttons at the bottom of every step; they are already large and easy to thumb‑reach.  
2. **Immediate Validation** – When a user changes a value (spinner toggle, switch), update any dependent counters or helper labels **instantly** (no need to wait for “Next”).  
3. **Undo / Reset** – Provide a subtle “Reset” (circular arrow) icon in the app bar for steps where bulk selection is possible (Metodologias, Talhōes, Atividades). Tapping it clears selections and returns to default (usually “All selected”).  
4. **Toast‑style Feedback** – For actions that navigate automatically (e.g., selecting “TODAS AS FAZENDAS” jumps to Step 4), show a brief toast at the bottom (“Pulando para Sequência…”) for ~1 second, then proceed.  
5. **Error Handling** – Keep existing pop‑ups for validation errors but ensure they appear **centered** and have a primary “OK” button that dismisses them.  

---  

<a name="visual--accessibility-notes"></a>
## 5. Visual & Accessibility Notes
- **Touch Target Size**: All interactive elements should be at least `48 dp` (≈9 mm) high; adjust heights/paddings where needed (e.g., checkboxes, radio dots).  
- **Contrast**: The brutalist theme already uses high‑contrast borders; ensure text inside chips or spinner selections meets WCAG AA (≥4.5:1).  
- **Screen Reader (TalkBack)**:  
  - Provide meaningful `accessibility_label` (Kivy’s `accessibility` property) for custom widgets (e.g., checkbox: “Metodologia A, checkbox, unchecked”).  
  - Ensure spinner announcements read the selected value.  
- **Orientation**: Lock to portrait (as current), but verify that layouts do not break if forced to landscape (use `size_hint` and `dp` units).  

---  

<a name="implementation-roadmap"></a>
## 6. Implementation Roadmap (High‑Level, No Code Yet)

| Phase | Goal | Key Changes |
|-------|------|-------------|
| **0 – Preparation** | Extract reusable helper classes (e.g., `MultiSelectSpinner`, `ChipList`, `TwoPanelSelector`). | Create new Python modules in `srf_mobile/widgets/` that encapsulate the patterns above. |
| **1 – Dashboard & Steps 1‑2** | Refine header, action buttons, hint placement. | Edit `dashboard.py` and `scheduler.py` (steps 1‑2). |
| **2 – Steps 3‑4** | Replace long checkbox lists with searchable multi‑select spinner or collapsible card. | Modify `_build_step_3`/`_build_step_4` and related update methods. |
| **3 – Step 5** | Switch radio group to spinner + description label. | Edit `_build_step_5` and `_apply_sequencia`. |
| **4 – Step 6** | Group switches in a card with live summary. | Edit `_build_step_6` and `_apply_bloqueios`. |
| **5 – Step 7** | Ensure consistent input types, collapse optional sections. | Edit `_build_step_7`. |
| **6 – Step 8‑9** | Implement two‑panel selector (activities ↔ turmas). | Replace current turma‑card + pending‑list logic with left/right panels and arrow buttons. |
| **7 – Step 10** | Consolidate conflict rows into single‑line controls. | Edit `_build_step_10` and `_apply_conflitos`. |
| **8 – Step 11** | Replace manual/mec list with a two‑column table/spinner; keep multi‑factor in collapsible card. | Edit `_build_step_11`. |
| **9 – Step 12** | Tighten HH/ha table rows, add reset button. | Edit `_build_step_12`. |
| **10 – Step 13** | Show escopo operations as colored chips. | Edit `_build_step_13` and `_refresh_escopo_display`. |
| **11 – Polish** | Run through the whole wizard on device, verify touch targets, run accessibility checks, adjust paddings. | No structural changes, only visual tweaks. |
| **12 – Documentation** | Update any internal comments / README to reflect new widget usage. | - |  

Each phase can be delivered as a separate Git commit, allowing easy rollback if a particular change introduces regressions.

---  

<a name="expected-impact"></a>
## 7. Expected Impact (Qualitative)

| Metric | Before | After (estimated) |
|--------|--------|-------------------|
| **Average taps per wizard completion** | ~120 (lots of checkbox toggles) | ~70–80 (bulk selects, spinners) |
| **Maximum scroll depth encountered** | 3‑4 full screens (long lists) | 1‑2 screens (collapsed panels) |
| **User error rate (mis‑taps)** | Higher due to small touch targets | Lower with uniform 44 dp+ targets |
| **Perceived simplicity** (subjective) | “Powerful but dense” | “Straightforward, guided” |
| **Development effort** | N/A (baseline) | Moderate – mainly layout refactor, no logic changes. |

---  

<a name="risks--mitigations"></a>
## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Regression in selection logic** (e.g., missing a checkbox) | Medium | High (core functionality broken) | Keep underlying data structures (`_step3_checkboxes`, `_step4_checkboxes`, etc.) unchanged; only replace view layer. Write unit tests for helper methods (`_selected_from_checkboxes`, `_update_selection_counter`). |
| **Performance hit from spinners with large lists** | Low (lists are modest) | Medium | If needed, use Kivy’s `RecyclerView`‑like approach; but current lists (<200 items) are fine. |
| **User resistance to new interaction pattern** | Low‑Medium | Medium | Provide short tooltip or help text on first launch (e.g., “Tap to open list, select items, press OK”). |
| **Inconsistent look if custom widgets diverge from theme** | Low | Low | Reuse existing colour and line‑drawing functions; keep same `_hex_a` and `KivyColor` usage. |
| **Buildozer / Python 3.14 blocker** (already known) | High (blocks APK) | High | Address separately (patch or shim for `FancyURLopener`). This plan assumes the block will be resolved before attempting a new APK. |  

---  

<a name="appendix--file-wise-change-summary"></a>
## 9. Appendix – File‑wise Change Summary

| File | Primary Changes |
|------|-----------------|
| `main.py` | Update app title if desired (optional). |
| `dashboard.py` | Replace action buttons with horizontal row; add info tooltip. |
| `scheduler.py` | - Step 1: move hint into spinner or as helper text.<br>- Step 2: same as step 1 + toast on auto‑advance.<br>- Steps 3‑4: replace checkbox list with multi‑select spinner or expandable card.<br>- Step 5: replace radio group with spinner + description label.<br>- Step 6: group switches in card with live summary.<br>- Step 7: ensure `input_type='text'`; collapse optional sections.<br>- Steps 8‑9: implement two‑panel selector layout with arrow buttons.<br>- Step 10: consolidate conflict rows into single‑line controls.<br>- Step 11: replace manual/mec list with two‑column spinner/table; keep multi‑factor in collapsible card.<br>- Step 12: tighten HH/ha table rows; add reset button.<br>- Step 13: render escopo ops as colored chips.<br>- Widget tweaks: adjust hit‑areas, heights, placeholders, min widths. |
| `widgets.py` | - Add/reuse helper classes: `MultiSelectSpinner`, `ChipList`, `TwoPanelSelector` (optional).<br>- Adjust existing widget constructors to accept new parameters (e.g., `height=dp(44)`, `placeholder` text).<br>- Ensure all touchable widgets expose a consistent `height` of `dp(44)` where applicable.<br>- Add utility `Caption` label style if not present. |
| `theme.py` (optional) | No changes required; reuse existing colours and radii. |
| `buildozer.spec` | Update version name to differentiate from old glitchy version (e.g., `version = 7.1.0`). |
| `assets / icons` (if any) | No new assets needed; rely on Unicode symbols already used. |

---  

*End of Plan*  
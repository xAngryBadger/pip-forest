# Changes to atm_v6.py - Real Dates Implementation

## Stabilization Patch (2026-04-08)

### Scope

- Fixed critical breakages introduced by recent edits in `atm_v6.py` to restore executable state.
- Kept behavior and data contracts intact (no large refactor).

### Fixes Applied

1. **Mechanized dossier export block repaired**
   - Rebuilt broken `try/except` / `with` boundaries in the mechanized export path.
   - Re-indented the block so `df_cascata_mec`, `df_mec_op`, and both mechanized Excel writers execute only inside the mechanized scenario branch.
   - Restored the corresponding success messages to the correct scope.

2. **`_executar_multi_equipes()` flow repaired**
   - Fixed malformed indentation in the team setup loop (`for ie in range(...)`).
   - Fixed nested `if/else` blocks for manual end-date input in territory mode.
   - Fixed profile-loading branch indentation (`perfil_carregado`) so turma setup is deterministic.
   - Fixed context/monitor update placement inside the per-team processing loop.
   - Fixed `all_eq_results.append(...)` scope to avoid leaking/duplicating state.
   - Moved `console.print(t_meq)` outside row-building loop to print consolidated table once.

3. **Console stability in Windows legacy encoding**
   - Replaced emoji labels in dashboard table headers with ASCII labels (`Fazenda`, `Equipe`, `Talhoes`, `Atividades`, `Datas`) to avoid `UnicodeEncodeError` in cp1252 terminals.

### Validation Run

- `python -m py_compile E:\cli_planilhas\atm_v6.py` -> **OK**
- `python -c "import atm_v6"` (with project path injected) -> **OK**
- Quick startup smoke (`python atm_v6.py` with piped input) under UTF-8 mode -> **OK**
  - Note: this confirms startup/menu path; full interactive `single` / `lote` / `multi_equipes` end-to-end still depends on manual operator inputs and data decisions.

## Summary

Implemented real calendar dates (DD/MM/AAAA) with Brazilian day-of-week abbreviations (Seg, Ter, Qua, Qui, Sex, Sáb, Dom) in all Excel exports.

## Changes Made

### 1. Added Date Conversion Functions (Lines 326-370)

**New helper functions:**

```python
_DIAS_SEMANA_CURTO = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
_DIAS_SEMANA_COMPLETO = [
    "Segunda-feira", "Terça-feira", "Quarta-feira",
    "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"
]

def _converter_dia_simulado_para_data(dia_simulado, dia_ref, mes_ref, ano_ref):
    """Converte dia simulado (1, 2, 3...) para data real.
    Retorna: (data_str, dia_semana_curto, dia_semana_completo, data_obj)
    Ex: (1, 20, 4, 2025) -> ("20/04/2025", "Seg", "Segunda-feira", date_obj)
    """
```

### 2. Updated `_gerar_aba_timeline()` (Lines 6044-6117)

**Added parameters:** `dia_ref`, `mes_ref`, `ano_ref` (optional)

**New columns in export:**

- `Data` - Real date in DD/MM/AAAA format
- `Dia_Semana` - Abbreviated day of week (Seg, Ter, Qua, etc.)
- `Dia_Simulado` - Original day number (for reference)

**Column order:** Data, Dia_Semana, Dia_Simulado, Fazenda, Talhao, ...

### 3. Updated `_gerar_aba_cascata_explicada()` (Lines 6120-6285)

**Added parameters:** `dia_ref`, `mes_ref`, `ano_ref` (optional)

**New columns in export:**

- `Data` - Real date
- `Dia_Semana` - Day of week abbreviation

**Applied to both:**

- ATIVIDADE rows (individual activities)
- RESUMO_DIA rows (daily summaries)

### 4. Updated `_gerar_aba_ocupacao_turmas()` (Lines 6288-6320)

**Added parameters:** `dia_ref`, `mes_ref`, `ano_ref` (optional)

**New columns in export:**

- `Data` - Real date
- `Dia_Semana` - Day of week abbreviation

**Note:** Adds data to each row for daily team occupancy tracking.

### 5. Updated `_df_crono_operacional()` (Lines 6323-6350)

**Added parameters:** `dia_ref`, `mes_ref`, `ano_ref` (optional)

**New columns inserted at beginning:**

- `Data` - Real date
- `Dia_Semana` - Day of week abbreviation

**Calculation:** Converts each `Dia` value to real date based on start date.

### 6. Updated Function Calls (Lines 5683-5688, 5828-5831)

**Modified calls to pass date parameters:**

```python
# Main cronograma export
df_cascata = _gerar_aba_cascata_explicada(cronograma, jornada, dia_ref, mes_ref, ano_ref)
df_ocupacao = _gerar_aba_ocupacao_turmas(cronograma, turmas, jornada, dias_simulado, dia_ref, mes_ref, ano_ref)
df_crono_op = _df_crono_operacional(df_crono, dia_ref, mes_ref, ano_ref)
df_timeline = _gerar_aba_timeline(cronograma, seq_cfg, modo_seq, atividades_reais, fazenda, dia_ref, mes_ref, ano_ref)

# Mechanized scenario export
df_cascata_mec = _gerar_aba_cascata_explicada(cronograma_com_mec, jornada, dia_ref, mes_ref, ano_ref)
df_mec_op = _df_crono_operacional(df_mec_full, dia_ref, mes_ref, ano_ref)
```

## Excel Export Changes

### CRONOGRAMA_DETALHADO Sheet

| Before | After |
|--------|-------|
| Dia | **Data** |
| Semana | **Dia_Semana** |
| Fazenda | Dia_Simulado |
| ... | Fazenda |
| | ... |

**Example:**

```
Data        | Dia_Semana | Dia_Simulado | Fazenda   | Talhao | Atividade
20/04/2025  | Seg        | 1            | Fazenda A | T001   | Rocada
21/04/2025  | Ter        | 2            | Fazenda A | T001   | Formiga
26/04/2025  | Sáb        | 7            | Fazenda A | T001   | Coroamento
```

### CASCATA_EXPLICADA Sheet

- Added `Data` and `Dia_Semana` columns
- Shows real dates for each activity and daily summary

### OCUPACAO_TURMAS_DIA Sheet

- Added `Data` and `Dia_Semana` columns
- Shows real dates for team occupancy tracking

### TIMELINE_CASCATA Sheet

- Added `Data` and `Dia_Semana` columns
- Shows real dates with color-coded phases

### CRONOGRAMA_MECANIZADO & CRONOGRAMA_COMBINADO Sheets

- Also include `Data` and `Dia_Semana` columns
- Mechanized scenarios use same date calculation

## Testing

To verify the implementation:

1. Run the scheduler with start date 20/04/2025
2. Check that Day 1 shows "20/04/2025 (Seg)"
3. Check that Day 2 shows "21/04/2025 (Ter)"
4. Check that Day 7 shows "26/04/2025 (Sáb)"
5. Check that Day 8 shows "27/04/2025 (Dom)"

## Benefits

- **Clear visualization:** Users see actual calendar dates instead of abstract day numbers
- **Weekend awareness:** Saturdays and Sundays are clearly marked
- **Better planning:** Easier to correlate with real-world calendars
- **Backward compatible:** If dates not provided, falls back to original behavior

## Future Enhancements (Phase 2)

1. **Team Coordinator Deduction** - Account for 1 non-working coordinator per team
2. **SWG Overflow Detection** - Export showing if SWG can take extra work before June
3. **Territory Filters** - Pattern-based area assignment to teams

# ATM Automated Tests — Strategy & Horizon

## Purpose

Every change to ATM (path reorg, column mapping, scheduler logic, comparative mode)
must be validated before promoting to production. This document defines the test
strategy, the standard test scenarios, and the acceptance criteria.

---

## Test Environment

| Item | Value |
|------|-------|
| Working copy | `src/atm_v6_3/atm_v6_2.py` |
| Production | `src/atm/atm_v6_2.py` |
| Input dir | `data/planilhas/` |
| Output dir | `data/dossiês/` |
| Config | `src/atm_v6_3/config.json` (per-copy) |
| Command | `python src/atm_v6_3/atm_v6_2.py` |

### Before each test session

```bash
# Reset config to clean state (optional)
cp src/atm_v6_3/config.json.bak src/atm_v6_3/config.json

# Remove old dossiers from test runs
rm -f data/dossiês/Dossier_FORMOSA* data/dossiês/Dossier_TEST*
```

---

## Standard Test Scenarios

### T1 — Cold Boot (Auto-Detect)

**What**: Start ATM, verify it auto-finds CT and micro without user navigation.

**Steps**:
1. `python src/atm_v6_3/atm_v6_2.py`
2. Press ENTER at mapping screen
3. Observe dashboard

**Pass criteria**:
- [ ] Version shows `v6.3`
- [ ] `CT auto: ct317real.xlsx -> N atividades (modo operacional)` appears
- [ ] `Carregadas N atividades validas` appears
- [ ] `Microplanejamento: <filename>.xlsx` shows correct file
- [ ] `STG: Sim` in dashboard
- [ ] File browser opens in `data/planilhas/` (not `src/atm/`)

### T2 — Single Fazenda, Single Equipe

**What**: Run Smart Scheduler on one fazenda with one team.

**Steps**:
1. Main menu → `[1]` Smart Scheduler
2. Select empresa (if prompted)
3. Select fazenda: FORMOSA
4. Metodologia: All (ENTER)
5. No activity scope adjustment
6. No orcamento estrito toggle
7. No comparativo (n)
8. Sequence: implantacao (s)
9. Global block: No
10. Prazo META: 6 months
11. Calendar: defaults (ENTER through)
12. Operarios: 10
13. Jornada: 4.6
14. No multifator
15. Single turma "Geral" with all 10 operators
16. Accept default activity assignments
17. Continue to simulation (6)

**Pass criteria**:
- [ ] Schedule completes without errors
- [ ] Dossier xlsx written to `data/dossiês/Dossier_FORMOSA*.xlsx`
- [ ] Dossier contains sheets: RESUMO_OPERACIONAL, CRONOGRAMA_DETALHADO
- [ ] Total HH > 0
- [ ] Dias necessarios > 0

### T3 — Comparative Mode with Navu (External Mecanizado)

**What**: Run FORMOSA with a manual team + Navu resource for roçada comparison.

**Steps**:
1. Same as T2 through step 6
2. Comparativo MANUAL vs MECANIZADO: **s** (yes)
3. Comparativo menu → `[3]` Cadastrar recurso mecanizado externo
4. Select activity: ROÇADA MANUAL...
5. Resource name: `Navu` (default)
6. HM/ha: `2.5` (= 0.4 ha/h productivity)
7. Custo R$/h: `0`
8. Preco R$/ha: `0`
9. Add another: `n`
10. Continue with single turma, 10 operators, jornada 4.6
11. Continue to simulation

**Pass criteria**:
- [ ] Manual scenario completes
- [ ] Mecanizado scenario completes
- [ ] Comparative display shows side-by-side: MANUAL vs MECANIZADO
- [ ] Dias and HH differ between scenarios
- [ ] Navu substitution shown in output: `ROÇADA MANUAL... → Navu [HM=2.50]`
- [ ] Dossier `Dossier_FORMOSA*_COMPARATIVO_CENARIOS.xlsx` written to `data/dossiês/`
- [ ] Mecanizado scenario has fewer or equal days than manual

### T4 — Multi-Turma with Activity Assignment

**What**: Configure 2 turmas with explicit activity assignments.

**Steps**:
1. Same as T2 through operadores
2. Turma 1: "Rocadores", 5 operators
3. Turma 2: "Plantio", 5 operators
4. Link roçada/coroamento to Rocadores (s), plantio to Plantio (s)
5. Continue to simulation

**Pass criteria**:
- [ ] Each turma has assigned activities
- [ ] Schedule distributes work per turma
- [ ] No orphan activities remain
- [ ] Dossier shows per-turma breakdown

### T5 — Dossier Output Path Validation

**What**: Verify all output files land in correct directories.

**Steps**:
1. Run T2 or T3
2. After completion, check file locations

**Pass criteria**:
- [ ] `data/dossiês/` contains new Dossier xlsx files
- [ ] `src/atm_v6_3/` does NOT contain any new xlsx files
- [ ] `data/planilhas/CT_317_NORMALIZADA.xlsx` exists (if CT normalization ran)
- [ ] `data/perfis_equipe/` is target for profile saves (if tested)
- [ ] `config.json` remains in `src/atm_v6_3/` (code-adjacent, correct)

### T6 — File Browser Navigation

**What**: Verify file browser starts in `data/planilhas/` and can navigate.

**Steps**:
1. Main menu → `[5]` Trocar planilha
2. Observe starting directory
3. Navigate up one level, then back into planilhas

**Pass criteria**:
- [ ] Browser opens in `data/planilhas/`
- [ ] Can navigate to parent directory (..)
- [ ] Can enter subdirectories
- [ ] Can select an xlsx file and load it
- [ ] Cancel returns to main menu without crash

### T7 — Batch Mode (All Fazendas)

**What**: Run Smart Scheduler for all fazendas in a single batch.

**Steps**:
1. Main menu → `[1]`
2. Select `[1]` TODAS AS FAZENDAS
3. Configure team defaults
4. Run

**Pass criteria**:
- [ ] All fazendas processed sequentially
- [ ] Consolidado_SmartScheduler xlsx written to `data/dossiês/`
- [ ] No crash on any fazenda
- [ ] Summary table shows per-fazenda results

---

## Rev.0 Compatibility Tests (NEW — Critical)

### T-REV0-1 — Sheet Detection with Rev.0

**What**: Verify ATM correctly selects a sheet from the new Rev.0 file.

**Context**: The new `SUZANO_MICROPLANEJAMENTO_CONSOLIDADO_INOVESA.Rev.0.xlsx`
has these sheets:
- `MICROPLANEJAMENTO_ABR_JUN_V1` (797 rows, closest to old format)
- `MICROPLANEJAMENTO_ABR_JUN_V2` (Nucleação variant)
- `MICROPL_IMPL_ABR_JUN_V3/V4/V5` (Implantação only)
- `MICROPL_MANUT_ABR_JUN_V1` (Manutenção only, 55 rows)
- `previsão_chuva`, `Planilha1-5`, `Planilha7`

**Risk**: ATM's `_prefer_micro_sheet()` looks for:
1. `microplanejamento_abril_junho` — NO MATCH (old name gone)
2. `microplanejamento` — **MATCHES V1, V2** (both contain "microplanejamento")
3. `inovesa` or `consolidado` — might match filename but not sheet names
4. Fallback: first sheet

**Steps**:
1. Load Rev.0 file (should auto-detect)
2. Observe which sheet ATM selects
3. Verify column mapping (below)

**Pass criteria**:
- [ ] ATM selects `MICROPLANEJAMENTO_ABR_JUN_V1` (most complete sheet)
- [ ] ATM does NOT select `MICROPL_MANUT_ABR_JUN_V1` (only 55 rows)
- [ ] If wrong sheet selected, user can manually choose via option [5]

### T-REV0-2 — Column Mapping with Rev.0

**What**: Verify ATM's 4 required columns are found in the new Rev.0 sheets.

**Required columns vs Rev.0 availability**:

| ATM Required | Rev.0 V1 | Rev.0 V3-V5 | Rev.0 MANUT | Status |
|---|---|---|---|---|
| `NOME FAZENDA` | YES | YES | YES | OK |
| `CHAVE POLÍGONO` | YES | YES | YES | OK |
| `ÁREA TRABALHADA ESTIMADA (HECTARE)` | YES | YES | YES | OK |
| `ATIVIDADES` | YES | YES | YES | OK |
| `METODOLOGIA PROPOSTA` (optional) | YES | YES | NO (renamed to `METODOLOGIA IMPLANTADA`) | OK for V1-V5, MANUT needs mapping |
| `EQUIPE` (optional) | NO (removed) | NO (V5 has it, empty) | NO | OK (optional) |

**Steps**:
1. Load Rev.0 with V1 sheet
2. Check column auto-detection log
3. Load Rev.0 with V5 sheet
4. Check column auto-detection log

**Pass criteria**:
- [ ] V1 sheet: all 4 required columns auto-detected
- [ ] V5 sheet: all 4 required columns auto-detected
- [ ] METODOLOGIA PROPOSTA detected in V1-V5 (optional, but needed for scope filtering)
- [ ] MANUT sheet: NOME FAZENDA, CHAVE, AREA, ATIVIDADES detected
- [ ] MANUT sheet: `METODOLOGIA IMPLANTADA` may NOT auto-detect as `metodologia` — verify

### T-REV0-3 — Full Schedule with Rev.0

**What**: Run T2-equivalent on Rev.0 and verify output is sensible.

**Steps**:
1. Load Rev.0 (V1 sheet auto-selected)
2. Run FORMOSA with 10 operators, 4.6h jornada
3. Compare results with old `PLANEJAMENTO_ABR_MAI_JUN 1 (1).xlsx`

**Pass criteria**:
- [ ] Same fazendas appear (16 expected)
- [ ] Same talhão count (114 expected)
- [ ] Activity count comparable (may differ due to methodology variants)
- [ ] Schedule completes without crash
- [ ] Dossier output in `data/dossiês/`

---

## Known Risks — Rev.0

### HIGH — Sheet Selection May Pick Wrong Sheet

`_prefer_micro_sheet()` uses substring matching. Both `MICROPLANEJAMENTO_ABR_JUN_V1`
and `MICROPLANEJAMENTO_ABR_JUN_V2` match priority 2 (`microplanejamento`).
ATM picks the **first** match in `abas` list, which depends on Excel tab order.
If V2 comes before V1, ATM loads Nucleação variant instead of Plantio Total.

**Mitigation**: Check tab order in Rev.0. If V1 is first tab matching "microplanejamento",
it works. Otherwise, add `MICROPLANEJAMENTO_ABR_JUN_V1` to the priority list or
add logic to prefer sheets containing `_V1`.

### MEDIUM — METODOLOGIA IMPLANTADA in MANUT Sheet

The MANUT sheet uses `METODOLOGIA IMPLANTADA` instead of `METODOLOGIA PROPOSTA`.
ATM's `encontrar_coluna()` heuristic checks for `metodolog` as a partial match,
so `METODOLOGIA IMPLANTADA` WOULD be detected (it contains `metodolog`).
However, the semantic meaning differs (implanted vs proposed).

**Impact**: Low for scheduling. ATM uses `metodologia` only for filtering/sorting,
not for tariff calculations. The column content may differ (implanted methodology
may not match proposed methodology for future planning).

### LOW — EQUIPE Column Removed from V1-V4

V1-V4 don't have `EQUIPE`. V5 has it but empty. This is fine — `equipe` is optional.
ATM will skip the empresa filter step. If the user needs empresa-scoped scheduling,
they must use a sheet that has the column populated.

### INFO — Financial Sheets Removed (INOVESA/SWG/CULTIVAR)

ATM never reads INOVESA, SWG, or CULTIVAR sheets from the microplanejamento.
These were purely for financial reporting in Excel. Their removal has **zero impact**
on ATM scheduling logic.

### INFO — New Sheets (previsão_chuva, Planilha1-7)

ATM ignores sheets that don't match its name patterns. These new auxiliary sheets
have **zero impact** on ATM.

---

## Test Execution Template

```
Date: ____
Tester: ____
ATM version: ____
Input file: ____
Sheet selected: ____

T1 Cold Boot:        [PASS/FAIL]  Notes: ____
T2 Single Fazenda:   [PASS/FAIL]  Notes: ____
T3 Comparative Navu:  [PASS/FAIL]  Notes: ____
T4 Multi-Turma:      [PASS/FAIL]  Notes: ____
T5 Output Paths:     [PASS/FAIL]  Notes: ____
T6 File Browser:     [PASS/FAIL]  Notes: ____
T7 Batch Mode:       [PASS/FAIL]  Notes: ____

T-REV0-1 Sheet Detect:  [PASS/FAIL]  Notes: ____
T-REV0-2 Column Map:    [PASS/FAIL]  Notes: ____
T-REV0-3 Full Schedule: [PASS/FAIL]  Notes: ____

Dossier output verified:  [Y/N]
data/dossiês/ path:       [Y/N]
No stray files in src/:   [Y/N]
```

---

## Future Horizon

### Short-term (next session)
- [ ] Run T1-T7 against v6.3 with old `PLANEJAMENTO_ABR_MAI_JUN 1 (1).xlsx`
- [ ] Run T-REV0-1 through T-REV0-3 against new Rev.0 file
- [ ] Fix sheet selection if Rev.0 picks wrong sheet

### Medium-term
- [ ] Add automated CLI test script (pipe inputs to ATM, check exit code)
- [ ] Add regression test: compare dossier output row counts between versions
- [ ] Add `_V1` suffix preference to `_prefer_micro_sheet()` for Rev.0 compat

### Long-term
- [ ] Unit tests for `encontrar_coluna()`, `normalizar_chave()`, `_prefer_micro_sheet()`
- [ ] Integration test: load xlsx → verify DataFrame shape and columns
- [ ] Smoke test in CI (if applicable)
- [ ] Config-driven test matrix (multiple input files, multiple sheet variants)

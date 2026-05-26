# Deep Investigation Report: SE-4 (Path Traversal) & EH-1/EH-2 (Silent Exceptions)

## Part 1: Path Traversal Analysis

### File Upload Endpoints

| Endpoint | Method | Line | Filename Source | Write Path | Sanitization | Risk |
|----------|--------|------|-----------------|------------|--------------|------|
| `POST /upload` | POST | 259-273 | `file.filename` (user-controlled, from multipart form) | `_DATA_DIR / "planilhas" / file.filename` | **NONE** — no sanitization, no `secure_filename`, no extension check | **CRITICAL** |
| `POST /term/upload/{session_id}` | POST | 276-291 | `file.filename` (user-controlled, from multipart form) | `ts.data_dir / "planilhas" / file.filename` | **NONE** — no sanitization, no `secure_filename`, no extension check | **CRITICAL** |

### File Download/Read Endpoints

| Endpoint | Method | Line | File Path Source | Read Path | Sanitization | Risk |
|-----------|--------|------|------------------|-----------|--------------|------|
| `GET /download/{session_id}/{filename}` | GET | 244-256 | `filename` URL param, but checked against `session.result_files` whitelist | `Path(OUTPUT_DIR) / filename` | **Partial** — `filename` must be in `session.result_files` list, but `Path(OUTPUT_DIR) / filename` with `../` could escape OUTPUT_DIR; also `OUTPUT_DIR` is global, not session-scoped | **HIGH** |
| `GET /term/download/{session_id}/{filename}` | GET | 380-391 | `filename` URL param, but checked against `ts.result_files` whitelist | `ts.data_dir / "dossiês" / filename` | **Partial** — same whitelist check, but path traversal in `filename` could escape the dossiês directory | **HIGH** |

### Session Directory Construction

**Session ID generation** (`session.py:22`):
```python
self.session_id = str(uuid.uuid4())[:8]
```

- The session ID is a truncated UUID4 (8 hex chars = 32 bits of entropy). This is **not cryptographically strong** for resisting brute-force: only ~4 billion possibilities. An attacker who can enumerate session IDs could potentially access other users' sessions.
- The session ID is **not user-controlled** — it's server-generated. This means the session directory path `_SESSIONS_DIR / self.session_id` cannot be directly manipulated via path traversal through the session_id itself.
- However, the short ID space (32 bits) makes session hijacking feasible if the auth cookie is missing or weak.

**TermSession** (`term.py:24`):
```python
self.session_id = session_id  # passed from create_session()
```
In `create_session()` (`term.py:74`):
```python
sid = str(uuid.uuid4())[:8]
```
Same pattern — server-generated, 8-hex truncation.

**Data directory** (`session.py:36`):
```python
self.data_dir = _SESSIONS_DIR / self.session_id
```
Where `_SESSIONS_DIR = _BASE_DATA_DIR / "sessions"`, and `_BASE_DATA_DIR = Path(os.environ.get("ORCA_DATA_DIR", "data"))`.

### Exploit Scenarios

#### Scenario 1: Write Arbitary File via `POST /upload` (CRITICAL)

**Endpoint**: `POST /upload` (`api.py:259-273`)

**Payload**:
```
filename = "../../../etc/cron.d/malicious"
```
or
```
filename = "../../config.json"
```

**What happens**:
```python
dest_dir = _DATA_DIR / "planilhas"            # e.g., data/planilhas
dest_path = dest_dir / file.filename           # e.g., data/planilhas/../../../etc/cron.d/malicious
# Path resolves to: /etc/cron.d/malicious
dest_dir.mkdir(parents=True, exist_ok=True)
with open(dest_path, "wb") as f:
    f.write(content)
```

`Path` objects in Python do **not** resolve `..` at construction time — `Path("data/planilhas") / "../../../etc/passwd"` creates a path that **resolves** to `/etc/passwd` when used in `open()`. The OS follows the `..` traversal.

**Impact**: Overwrite `config.json` (inject malicious tarifas/de_para), overwrite Python source files (RCE), write to `/etc/cron.d/` (if process has root), overwrite any file the process has write access to.

#### Scenario 2: Write Arbitrary File via `POST /term/upload/{session_id}` (CRITICAL)

**Endpoint**: `POST /term/upload/{session_id}` (`api.py:276-291`)

**Payload**:
```
filename = "../../../../home/badger/.ssh/authorized_keys"
```

**What happens**:
```python
session_dir = ts.data_dir / "planilhas"        # e.g., data/sessions/abc12345/planilhas
content = await file.read()
with open(session_dir / file.filename, "wb") as f:
    f.write(content)
```

Same traversal vulnerability. The deeper directory nesting gives even more `../` room.

#### Scenario 3: Read Arbitrary File via `GET /download/{session_id}/{filename}` (HIGH)

**Endpoint**: `GET /download/{session_id}/{filename}` (`api.py:244-256`)

**Gating check**: `filename not in session.result_files` → 404.

**Bypass**: The `result_files` list is populated by `_collect_result_files()` (`bridge.py:540-551`):
```python
for f in sorted(dossier_dir.glob("*.xlsx")):
    if f.name not in existing:
        if f.stat().st_mtime > created_ts:
            session.result_files.append(f.name)
```

This only adds filenames from the dossiês directory, so a path traversal string like `../../etc/passwd` will **never** be in `result_files` unless an attacker can create a file with that literal name in the dossiês directory.

**Assessment**: The whitelist makes direct exploitation difficult, BUT:
1. If `OUTPUT_DIR` is shared across sessions, a malicious filename placed via upload could appear in another session's results.
2. The `FileResponse(str(file_path), filename=filename)` at line 256 uses `Path(OUTPUT_DIR) / filename` — if `filename` contained `..` and somehow passed the whitelist, it would escape `OUTPUT_DIR`.
3. **No path resolution check** (e.g., `file_path.resolve().parent == OUTPUT_DIR.resolve()`) is performed.

#### Scenario 4: Null Byte Injection

On modern Python (3.10+), null bytes in filenames raise `ValueError` in `open()`. This is not exploitable on the target Python version.

### Additional Filesystem-Accessing Code (Non-Endpoint)

| Code | Location | Type | Risk |
|------|----------|------|------|
| `shutil.copy2(cfg_src, cfg_dst)` | `session.py:48` | Copies config into session dir | NONE — src/dst are server-controlled |
| `shutil.copytree(planilhas_src, planilhas_dst)` | `session.py:60` | Copies planilhas into session dir | NONE — src/dst are server-controlled |
| `shutil.copy2(cfg_src, session.data_dir / "config.json")` | `term.py:113` | Copies config into term session dir | NONE |
| `shutil.copytree(planilhas_src, planilhas_dst)` | `term.py:117` | Copies planilhas into term session dir | NONE |
| `session_dir.mkdir(parents=True, exist_ok=True)` | `api.py:266` | Creates upload dir | NONE |
| `_collect_result_files` glob | `bridge.py:540-551` | Reads dossiês dir | NONE — only reads |
| `_collect_result_files` glob | `term.py:224-230` | Reads dossiês dir | NONE — only reads |
| `salvar_config(cfg)` → `open(CFGP, "w")` | `config.py:329` | Writes config.json | NONE — CFGP is server-controlled |
| `_salvar_perfil_equipe` | `excel_export.py:361` | Writes profile JSON | NONE — name is slug-secured |
| `gravar_atomico` | `orca_monitor_state.py:58-60` | Writes state JSON | NONE — path is server-controlled |

### Recommended Fixes

1. **CRITICAL — `api.py:267` (POST /upload)**: Add filename sanitization:
   ```python
   from werkzeug.utils import secure_filename  # or implement equivalent
   safe_name = secure_filename(file.filename)  # strips path separators, ..
   if not safe_name:
       raise HTTPException(status_code=400, detail="Invalid filename")
   dest_path = dest_dir / safe_name
   if dest_path.resolve().parent != dest_dir.resolve():
       raise HTTPException(status_code=400, detail="Path traversal detected")
   ```

2. **CRITICAL — `api.py:288` (POST /term/upload/{session_id})**: Same fix as above.

3. **HIGH — `api.py:253` (GET /download/{session_id}/{filename})**: Add resolved path check:
   ```python
   file_path = Path(OUTPUT_DIR) / filename
   if file_path.resolve().parent != Path(OUTPUT_DIR).resolve():
       raise HTTPException(status_code=403, detail="Path traversal detected")
   ```

4. **HIGH — `api.py:388` (GET /term/download/{session_id}/{filename})**: Same resolved path check:
   ```python
   file_path = ts.data_dir / "dossiês" / filename
   if file_path.resolve().parent != (ts.data_dir / "dossiês").resolve():
       raise HTTPException(status_code=403, detail="Path traversal detected")
   ```

5. **MEDIUM — Session ID entropy** (`session.py:22`, `term.py:74`): Use full UUID (32 hex chars) instead of truncated 8-char UUID to increase brute-force resistance.

6. **LOW — Import `secure_filename`**: Neither `werkzeug.utils.secure_filename` nor any equivalent is imported or used anywhere in the codebase. A custom sanitizer could be implemented since werkzeug may not be in dependencies.

---

## Part 2: Silent Exception Handling Analysis

### Summary Statistics

| Category | Count | Files |
|----------|-------|-------|
| Dangerous | 3 | `tarifas.py`, `datas.py`, `config.py` |
| Risky | 8 | `tarifas.py`, `config.py`, `excel_export.py`, `io.py`, `monitor.py` |
| Acceptable | 12 | `monitor.py`, `term.py`, `context.py`, `ui.py`, `orca_monitor.py` |
| Intentional | 99 | `tarifas.py`, `scheduler_core.py`, `scheduler.py`, `ui.py`, `api.py`, etc. |

### Dangerous Findings (Detailed)

| File:Line | Try Block | Exception | Handler | Consequence | Fix |
|-----------|-----------|-----------|---------|-------------|-----|
| `tarifas.py:209-222` (`_to_float_json`) | `float(s)` conversion of user-supplied JSON values | `except Exception:` | `return float(default)` | When a JSON tariff value like `"preco_ha"` is malformed (e.g., `"R$ 1.234,56abc"`), the function silently returns `0.0`. This is called from `_carregar_mapa_preco_final_json` and then `_aplicar_mapa_preco_final_em_rows_by_name`. If all `preco_ha` values fail parsing, ALL tariffs get `preco_ha=0.0`. The scheduler then produces schedules with **zero-cost activities**. No downstream validation catches `preco_ha=0.0` as an error. | Log warning with the value and field name; return `None` and propagate to caller; add downstream check for zero tariffs |
| `datas.py:59-60` (`_converter_dia_simulado_para_data`) | Full date computation from simulated day to real date | `except Exception:` | `return (f"Dia_{dia_simulado}", "-", "-", None)` | Returns a sentinel tuple `("Dia_N", "-", "-", None)`. **No downstream code checks for this sentinel.** In `excel_export.py:132-137`, the code checks `if data_tuple:` — which is **always truthy** (non-empty tuple), so the sentinel is used as valid data. The Excel export will show `"Dia_5"` instead of a real date, and `"-"` for day-of-week. The `None` 4th element is never consumed directly. | Narrow exception to `(ValueError, OverflowError)`; add sentinel check in all 3 consumers (`excel_export.py:132, 236, 290`) |
| `datas.py:73-74` (`_calcular_data_fim_por_meses`) | Date arithmetic for deadline calculation | `except Exception:` | `return None` | If the conversion of `prazo_meses` to int fails, returns `None`. The caller (`scheduler_core.py` line where `_calcular_data_fim_por_meses` is used) checks for `None`, so this is less dangerous but still hides input errors. | Narrow to `(ValueError, TypeError)` |

### Risky Findings (Detailed)

| File:Line | Try Block | Exception | Handler | Consequence | Fix |
|-----------|-----------|-----------|---------|-------------|-----|
| `config.py:327-328` (`salvar_config`) | `shutil.copy2(CFGP, CFGP + ".bak")` — creating backup before overwrite | `except Exception:` | `pass` | If the backup fails, the old config is not preserved. Then if the subsequent `json.dump()` also fails (e.g., disk full), the config file is **truncated or corrupted with no backup to restore**. Next `carregar_config()` falls back to empty config → **all tariffs, de_para, and settings lost**. | Raise or at minimum log the error; consider write-to-temp-then-rename pattern |
| `tarifas.py:264-265` (`_carregar_mapa_preco_final_json`) | `os.path.getmtime(caminho)` — check file modification time | `except Exception:` | `return {}` | If mtime check fails (permissions, etc.), the entire price map is skipped. All downstream tariff lookups then use only the in-memory tarifas dict, missing any JSON overrides. **No warning emitted.** | Narrow to `OSError`; log warning |
| `tarifas.py:278-279` (`_carregar_mapa_preco_final_json`) | `open(caminho)` + `json.load(f)` — reading price JSON | `except Exception:` | `return {}` | If the JSON file exists but is malformed, the entire price map is silently discarded. Same consequence as above — missing price overrides. | Narrow to `(json.JSONDecodeError, OSError)`; log warning |
| `tarifas.py:839-840` (`modulo_importar_precos_contrato`) | `normalizar_ct313(ct_path)` — CT normalization during import | `except Exception:` | `tarifas_ct_ref = {}` | If CT normalization fails, reference tariffs are empty. The import then proceeds without baseline CT data, potentially creating tariff entries with zero HH/HM. | Log the specific error; at minimum warn the user |
| `excel_export.py:376-377` (`_listar_perfis_equipe`) | `json.load(f)` — reading profile files | `except Exception:` | `pass` | Malformed profile files are silently skipped. User saves a profile, it gets corrupted, and next load it vanishes with no error. | Narrow to `(json.JSONDecodeError, OSError)`; log filename |
| `excel_export.py:646-647` (`_exportar_excel_consolidado_lote`) | openpyxl color styling | `except Exception:` | `pass` | If color styling fails, the Excel file is still written but without visual cues. User may not notice missing color-coding for status columns (OK/RISCO/EXCEDIDO). | Narrow to specific openpyxl exceptions |
| `io.py:484-485` (`carregar_planilha_microplanejamento`) | EQUIPE enrichment from secondary sheet | `except Exception:` | `pass` | If the equipe-mapping logic fails, the spreadsheet is loaded without equipe assignments. The scheduler then operates without team assignments, potentially producing a single-team schedule instead of multi-team. | Narrow exception scope; log warning |
| `monitor.py:152-153` (`_emitir_monitor_rendimentos`) | `json.load(f)` reading monitor state | `except Exception:` | `rendimentos_existentes = []` | Corrupted monitor state causes rendimentos to be silently reset to empty list, then overwritten. All prior rendimentos data lost without warning. | Narrow to `(json.JSONDecodeError, OSError)` |

### Acceptable Findings (Summary)

These are silent catches for truly optional/defensive features where failure should not block the main flow:

| File:Line | Handler | Rationale |
|-----------|---------|-----------|
| `context.py:17` | `except ImportError:` → set Console/Table to None | Rich library optional for dashboard |
| `ui.py:37` | `except ImportError:` → exit with install instructions | Rich is required; early exit is correct |
| `ui.py:55` | `except ImportError:` → empty color strings | Colorama optional; graceful degradation |
| `monitor.py:28` | `except Exception:` → set all monitor funcs to None | Optional monitor subsystem; graceful no-op |
| `monitor.py:63` | `except Exception:` → `pass` | Monitor state emit failure should not crash scheduler |
| `monitor.py:71` | `except Exception:` → `pass` | Monitor relatorio emit failure should not crash scheduler |
| `monitor.py:126` | `except Exception:` → `pass` | Monitor atual emit failure should not crash scheduler |
| `monitor.py:223` | `except Exception:` → `pass` | Monitor rendimentos emit failure should not crash scheduler |
| `monitor.py:279` | `except FileNotFoundError:` → `continue` | Terminal emulator not found; try next |
| `term.py:50` | `except Exception:` → `dead.append(ws)` | WebSocket send failure; disconnect client |
| `term.py:60` | `except Exception:` → `pass` | PTY resize failure; non-critical |
| `term.py:67` | `except Exception:` → `pass` | Process kill failure; non-critical |
| `orca_monitor.py:345` | `except Exception as ex:` → print error | Monitor render error; printed to stderr |
| `orca_monitor_state.py:51` | `except (json.JSONDecodeError, OSError):` → `return {}` | Properly narrowed; monitor state read failure |

### Intentional Findings (Summary — 99 blocks)

These are properly narrowed exception handlers or deliberate fallback logic:

**Type-conversion fallbacks in `tarifas.py`** (lines 51, 76, 91, 102, 121, 131, 144, 160, 170, 187, 197, 549, 553, 557): All `except (TypeError, ValueError): pass` — these are in `try: float(x)` blocks that fall through to a default value. The pattern is intentional: if a tariff field cannot be parsed as a number, skip it and use fallback. **However**, the fallback chain in `resolver_rendimento_hh` (line 96-107) goes: tarifas → config fallback → median → hardcoded 8.0. This means a completely broken tariff entry still gets `hh=8.0`, which could produce **wildly incorrect schedules** with no warning.

**Input parsing in `ui.py`** (lines 163, 172, 182, 207): `except ValueError:` in `pedir_float/pedir_int/_parse_jornada` — these are in `while True` retry loops. Intentional and correct.

**WebSocket parsing in `api.py`** (lines 440, 451): `except Exception:` after `json.loads(text)` — if the message isn't JSON, it's treated as raw terminal input. Intentional.

**Value parsing in `scheduler.py`** (lines 94, 509, 528, 604, 763): All `except (TypeError, ValueError):` — properly narrowed, fallback to default values.

**tarifas.py** (lines 899, 911, 921, 927, 931, 939, 943, 958): All `except Exception:` in `modulo_importar_precos_contrato` — these are in `float(str(r.get(col_xxx, 0)).replace(",", "."))` blocks inside a row iteration. If a single cell value fails to parse, it defaults to 0.0. This is **risky in aggregate** — if the column mapping is wrong, ALL values default to 0.0 with no indication.

### Tariff Chain Analysis

**Trace: What happens when tariff lookup fails silently?**

1. **Entry point**: `scheduler_core.py:1083-1119` — `calcular_cronograma_inteligente`
2. **Tariff key resolution**: `resolver_chave_tarifa(cfg, tarifas, atv)` (`tarifas.py:1050-1100`)
   - Always returns a string key (never raises). If no match found, returns the raw `atv` name.
3. **HH resolution**: `resolver_rendimento_hh(cfg, tarifas, t_nome, strict=strict)` (`tarifas.py:61-107`)
   - If `strict=True` (orcamento_estrito mode) and `rendimento_hh` is invalid: returns `None`
   - If `strict=False`: tries tarifas → config fallback → median → hardcoded **8.0**
4. **When `resolver_rendimento_hh` returns `None` in strict mode** (`scheduler_core.py:1093-1112`):
   ```python
   if rend_base is None:
       if float(hm_base or 0) > 0.0:
           rend_base = 0.0  # HM-only activity
       else:
           rend_fb = resolver_rendimento_hh(cfg, tarifas, t_nome, strict=False)
           if rend_fb is None:
               rend_fb = 0.0
           rend_base = float(rend_fb)  # Falls back to non-strict: likely 8.0
   ```
5. **Critical consequence**: When strict mode fails, the code **immediately falls back to non-strict**, which returns the hardcoded 8.0 h/ha. This means:
   - An activity with no tariff match gets `hh=8.0` (the hardcoded default).
   - This value is used for `horas = area * rend_hh_ha * pen`.
   - The scheduler produces a **valid-looking schedule with potentially wrong HH values**.
   - No error is raised, no warning is logged for the specific activity.
   - The only indication is in `fallback_hh_items` list which is printed as a warning, but only in terminal mode — **not propagated to the web UI**.

6. **Price resolution**: `resolver_preco_ha(cfg, tarifas, t_nome)` (`tarifas.py:149-173`)
   - In `modo_somente_hh` (default=True): returns `0.0` immediately.
   - Otherwise: tarifas → config fallback → median → `0.0`.
   - **Result**: Even when `modo_somente_hh=False`, a missing price defaults to **0.0**, producing schedules with zero-cost activities. No downstream check validates `preco_ha > 0`.

7. **Does the scheduler produce zero-cost results?** **Yes.** When `modo_somente_hh` is False (R$ mode) and a tariff has no price, `resolver_preco_ha` returns `0.0`. The scheduler's cost calculation (`custo_h = resolver_custo_hora(...) or 0.0`) also silently returns 0.0. The Excel export shows `Custo_MO = 0.0` with no visual warning.

### Date Conversion Analysis

**`_converter_dia_simulado_para_data`** (`datas.py:25-60`):

**Error sentinel**: `(f"Dia_{dia_simulado}", "-", "-", None)`

**Consumers** (all in `excel_export.py`):

1. **`_gerar_aba_cascata_explicada`** (line 132-137):
   ```python
   data_tuple = _converter_dia_simulado_para_data(dia, dia_ref, mes_ref, ano_ref)
   if data_tuple:  # ← ALWAYS TRUE (non-empty tuple)
       data_real = data_tuple[0]  # "Dia_5" instead of "20/04/2025"
       dia_semana = data_tuple[1]  # "-" instead of "Seg"
   ```
   The `if data_tuple:` check is **broken** — it's meant to detect `None` but the function always returns a tuple (never `None`). The sentinel passes through as valid data. The Excel export will show `"Dia_5"` as a date column and `"-"` as day of week.

2. **`_gerar_aba_ocupacao_turmas`** (line 236-241): Same broken check.

3. **`_df_crono_operacional`** (line 290-298):
   ```python
   data_tuple = _converter_dia_simulado_para_data(dia_simulado, dia_ref, mes_ref, ano_ref)
   if data_tuple:  # ← ALWAYS TRUE
       datas_reais.append(data_tuple[0])  # "Dia_5"
       dias_semana.append(data_tuple[1])  # "-"
   else:
       datas_reais.append(f"Dia_{dia_simulado}")  # never reached
       dias_semana.append("")
   ```
   The `else` branch is dead code — it was probably the intended fallback but is never executed because the sentinel is truthy.

**Impact**: When date conversion fails (invalid reference date, corrupted inputs), the Excel output shows opaque `"Dia_N"` labels instead of real dates, with no indication of error. Users may not realize the dates are simulated-day labels, not real calendar dates.

**Fix**: Change the function to return `None` on error, and update all consumers to check `if data_tuple is not None:`.

### Config Save Analysis

**`salvar_config`** (`config.py:321-330`):

```python
def salvar_config(cfg):
    cfg = _normalize_for_json(cfg)
    if os.path.exists(CFGP):
        try:
            shutil.copy2(CFGP, CFGP + ".bak")
        except Exception:
            pass  # ← Backup failure silently ignored
    with open(CFGP, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
```

**What happens if save fails silently?**

1. **Backup fails** (line 327): `pass` — no `.bak` file is created. The subsequent `json.dump()` overwrites `config.json`.
2. **`json.dump()` fails** (e.g., disk full, permissions): This is **NOT** caught — it would raise an unhandled exception. But the exception propagates differently depending on the caller:
   - In `entry.py:322` (`main()`): `salvar_config(cfg)` — unhandled, would crash the app.
   - In `tarifas.py:805` (`modulo_importar_custos_globais_brutos`): Inside a `try/except Exception as ex` block, so the error is caught and displayed to the user.
   - In `tarifas.py:993` (`modulo_importar_precos_contrato`): Same — caught and displayed.
   - In web mode (`bridge.py`): The entire scheduler run is in a `try/except Exception as e` → `session.mark_finished(str(e))`.

3. **Partial write scenario**: `json.dump()` opens the file with `"w"` (truncate then write). If the process is killed mid-write, `config.json` is **truncated**. No `.bak` exists if the backup step failed. Next `carregar_config()` would:
   - Get `json.JSONDecodeError` on the truncated file
   - Try `.bak` → if `.bak` doesn't exist → `cfg = {}`
   - **All tariffs, de_para, fazendas_ct, sequencia settings lost**

4. **Stale data scenario**: If `salvar_config` succeeds but the caller then modifies `cfg` in memory without calling `salvar_config` again, the in-memory state diverges from disk. This is a design issue, not a bug — the codebase consistently calls `salvar_config` after modifications.

**Critical scenario**: Backup creation fails → config.json gets partially overwritten → next load gets empty config → **all user settings, tariff mappings, and de_para are lost**. The user sees a fresh app state with no indication of what happened.

**Fix**: Use atomic write (write to `.tmp`, then `os.replace()`). Ensure backup exists before overwriting. Return success/failure status.

### Recommended Priority Fixes

1. **`tarifas.py:209,221` — `_to_float_json` silently returns 0.0** (DANGEROUS)
   - **Rationale**: This single function feeds all JSON price/tariff parsing. A malformed JSON file can set ALL tariffs to zero with no warning. This is the highest-impact silent handler.
   - **Fix**: Return `None` on failure; propagate to callers with logging.

2. **`config.py:327` — `salvar_config` backup failure** (RISKY)
   - **Rationale**: Config loss is catastrophic — all user settings vanish. Atomic write + mandatory backup is essential.
   - **Fix**: Raise on backup failure; use `os.replace()` pattern.

3. **`datas.py:59` — sentinel tuple bypasses truthiness check** (DANGEROUS)
   - **Rationale**: The sentinel is used as valid data in 3 Excel export functions. Dead `else` branches never execute.
   - **Fix**: Return `None` on error; fix `if data_tuple is not None:` checks in all consumers.

4. **`tarifas.py:264,278` — price JSON loading silently returns `{}`** (RISKY)
   - **Rationale**: Entire price override map is discarded on any I/O or parse error.
   - **Fix**: Narrow exceptions; log warnings with file path.

5. **`tarifas.py:839` — CT normalization failure during import** (RISKY)
   - **Rationale**: Import proceeds without baseline data, creating zero-value tariffs.
   - **Fix**: Surface the error to the user; abort import if CT data is required.

6. **`tarifas.py:899-958` — cell parsing in import loop** (RISKY in aggregate)
   - **Rationale**: Individual cell failures are acceptable, but systematic failures (wrong column mapping) produce all-zero tariffs with no warning.
   - **Fix**: Count parse failures; warn if > 50% of values failed.

7. **`io.py:484` — EQUIPE enrichment failure** (RISKY)
   - **Rationale**: Missing equipe assignments change scheduling behavior.
   - **Fix**: Log the error; inform user that equipe data is missing.

8. **`scheduler_core.py:1093-1112` — strict→non-strict HH fallback** (DANGEROUS by design)
   - **Rationale**: Strict mode is immediately bypassed, defeating its purpose. Hardcoded 8.0 h/ha is applied with no logging.
   - **Fix**: Log the fallback with the activity name and tariff key; add a summary warning at schedule completion.

---

## Appendix: Full Exception Block Inventory

| File | Line | Exception Type | Handler Action | Category |
|------|------|----------------|----------------|----------|
| context.py | 17 | `ImportError` | Set Console/Table to None | Acceptable |
| config.py | 273 | `json.JSONDecodeError` | Try .bak file | Intentional |
| config.py | 279 | `json.JSONDecodeError` | Return empty config | Intentional |
| config.py | 327 | `Exception` | `pass` | **Risky** |
| ui.py | 37 | `ImportError` | `sys.exit(1)` | Intentional |
| ui.py | 55 | `ImportError` | Set colors to empty strings | Acceptable |
| ui.py | 148 | `(EOFError, KeyboardInterrupt)` | `sys.exit(0)` | Intentional |
| ui.py | 163 | `ValueError` | `pass` (retry loop) | Intentional |
| ui.py | 172 | `ValueError` | `pass` (retry loop) | Intentional |
| ui.py | 182 | `(ValueError, IndexError)` | `pass` (retry loop) | Intentional |
| ui.py | 207 | `ValueError` | `pass` (retry loop) | Intentional |
| ui.py | 282 | `(EOFError, KeyboardInterrupt)` | `sys.exit(0)` | Intentional |
| ui.py | 292 | `(EOFError, KeyboardInterrupt)` | `sys.exit(0)` | Intentional |
| api.py | 35 | `TypeError` | Parse template manually | Intentional |
| api.py | 165 | `(ValueError, TypeError)` | Use default value | Intentional |
| api.py | 170 | `(ValueError, TypeError)` | Use default value | Intentional |
| api.py | 173 | `(ValueError, TypeError)` | `value = 0` | Intentional |
| api.py | 187 | `(ValueError, TypeError)` | `value = 0` | Intentional |
| api.py | 359 | `Exception` | `pass` | Acceptable |
| api.py | 440 | `Exception` | `pass` | Acceptable |
| api.py | 451 | `Exception` | `pass` | Acceptable |
| api.py | 454 | `WebSocketDisconnect` | `pass` | Intentional |
| api.py | 456 | `Exception` | `pass` | Acceptable |
| session.py | 50 | `Exception` | Unlink cfg_dst, re-raise | Intentional |
| session.py | 88 | `queue.Empty` | `answer = None` | Intentional |
| bridge.py | 246 | `(ValueError, IndexError)` | `pass` | Intentional |
| bridge.py | 274 | `(ValueError, TypeError)` | `return -1` | Intentional |
| bridge.py | 374 | `Exception` | `continue` | Acceptable |
| bridge.py | 441 | `Exception as e` | `session.mark_finished(str(e))` | Intentional |
| bridge.py | 487 | `Exception as e` | `session.mark_finished(str(e))` | Intentional |
| bridge.py | 532 | `Exception as e` | `session.mark_finished(str(e))` | Intentional |
| scheduler_core.py | 337 | `ValueError` | Use all activities | Intentional |
| scheduler_core.py | 492 | `ValueError` | `aviso("Entrada inválida")` | Intentional |
| scheduler_core.py | 500 | `ValueError` | `aviso("Entrada inválida")` | Intentional |
| scheduler_core.py | 1070 | `(ValueError, TypeError) as exc` | `raise ValueError(...) from exc` | Intentional |
| scheduler_core.py | 1077 | `(ValueError, TypeError) as exc` | `raise ValueError(...) from exc` | Intentional |
| scheduler_core.py | 2188 | `Exception as _fmt_err` | `aviso(...)` | Acceptable |
| scheduler_core.py | 2263 | `Exception as _fmt_err` | `aviso(...)` | Acceptable |
| scheduler_core.py | 2267 | `Exception as ex` | `aviso(...)` | Intentional |
| scheduler_core.py | 2389 | `Exception as e` | `aviso(...)`, `resultado_mecanizado = None` | Intentional |
| scheduler_core.py | 2516 | `Exception` | `rendimentos_feed = []` | Acceptable |
| scheduler_core.py | 2811 | `Exception as _err_faz` | `erro(...)`, `r = None` | Intentional |
| scheduler_core.py | 3528 | `Exception as ex` | `aviso(...)` | Intentional |
| tarifas.py | 51 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 76 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 91 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 102 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 121 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 131 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 144 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 160 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 170 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 187 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 197 | `(TypeError, ValueError)` | `pass` → skip value | Intentional |
| tarifas.py | 209 | `Exception` | `return float(default)` | **Dangerous** |
| tarifas.py | 221 | `Exception` | `return float(default)` | **Dangerous** |
| tarifas.py | 264 | `Exception` | `return {}` | **Risky** |
| tarifas.py | 278 | `Exception` | `return {}` | **Risky** |
| tarifas.py | 549 | `(TypeError, ValueError)` | `hh = 0.0` | Intentional |
| tarifas.py | 553 | `(TypeError, ValueError)` | `hm = 0.0` | Intentional |
| tarifas.py | 557 | `(TypeError, ValueError)` | `preco = 0.0` | Intentional |
| tarifas.py | 816 | `Exception as ex` | `erro(...)` | Intentional |
| tarifas.py | 839 | `Exception` | `tarifas_ct_ref = {}` | **Risky** |
| tarifas.py | 899 | `Exception` | `pass` | **Risky** |
| tarifas.py | 911 | `Exception` | `pass` | **Risky** |
| tarifas.py | 921 | `Exception` | `preco = 0.0` | **Risky** |
| tarifas.py | 927 | `Exception` | `hh_pf = 0.0` | **Risky** |
| tarifas.py | 931 | `Exception` | `hm = 0.0` | **Risky** |
| tarifas.py | 939 | `Exception` | `hh_ct = 0.0` | **Risky** |
| tarifas.py | 943 | `Exception` | `hm_ct = 0.0` | **Risky** |
| tarifas.py | 958 | `Exception` | `c_h = 0.0` | **Risky** |
| tarifas.py | 1025 | `Exception as ex` | `erro(...)` | Intentional |
| tarifas.py | 1046 | `Exception` | `return None` | Intentional |
| excel_export.py | 89 | `(TypeError, ValueError)` | `continue` | Intentional |
| excel_export.py | 311 | `ImportError` | `return` | Acceptable |
| excel_export.py | 376 | `Exception` | `pass` | **Risky** |
| excel_export.py | 646 | `Exception` | `pass` | Acceptable |
| excel_export.py | 649 | `Exception as ex` | `aviso(...)` | Intentional |
| monitor.py | 28 | `Exception` | Set funcs to None | Acceptable |
| monitor.py | 63 | `Exception` | `pass` | Acceptable |
| monitor.py | 71 | `Exception` | `pass` | Acceptable |
| monitor.py | 126 | `Exception` | `pass` | Acceptable |
| monitor.py | 152 | `Exception` | `rendimentos_existentes = []` | **Risky** |
| monitor.py | 223 | `Exception` | `pass` | Acceptable |
| monitor.py | 279 | `FileNotFoundError` | `continue` | Intentional |
| monitor.py | 287 | `Exception as e` | `aviso(...)` | Intentional |
| term.py | 50 | `Exception` | `dead.append(ws)` | Acceptable |
| term.py | 60 | `Exception` | `pass` | Acceptable |
| term.py | 67 | `Exception` | `pass` | Acceptable |
| term.py | 165 | `Exception as e` | Set error on session | Intentional |
| term.py | 184 | `OSError` | `break` | Intentional |
| term.py | 186 | `Exception` | `break` | Acceptable |
| term.py | 196 | `Exception` | `rc = -1` | Acceptable |
| term.py | 208 | `Exception` | `return False` | Acceptable |
| term.py | 216 | `Exception` | `pass` | Acceptable |
| entry.py | 265 | `Exception as ex` | `aviso(...)` | Intentional |
| entry.py | 336 | `Exception as ex` | `aviso(...)` | Intentional |
| entry.py | 390 | `Exception` | `pass` | Acceptable |
| entry.py | 394 | `Exception` | `pass` | Acceptable |
| orca_monitor.py | 35 | `ImportError` | Set colors to empty | Acceptable |
| orca_monitor.py | 81 | `ValueError` | `return None` | Intentional |
| orca_monitor.py | 345 | `Exception as ex` | Print error to stderr | Intentional |
| orca_monitor_state.py | 51 | `(json.JSONDecodeError, OSError)` | `return {}` | Acceptable |
| io.py | 172 | `Exception as ex` | `erro(...)` | Intentional |
| io.py | 484 | `Exception` | `pass` | **Risky** |
| io.py | 489 | `Exception as e` | `erro(...)` | Intentional |
| io.py | 511 | `Exception` | `return float(default)` | Intentional |
| text_utils.py | 88 | `(TypeError, ValueError)` | `pass` | Intentional |
| text_utils.py | 122 | `ValueError` | `continue` | Intentional |
| text_utils.py | 129 | `ValueError` | `continue` | Intentional |
| turmas.py | 687 | `(TypeError, ValueError)` | `hm = 0.0` | Intentional |
| comparativo_mec.py | 151 | `Exception` | `pass` | Acceptable |
| scheduler.py | 94 | `(TypeError, ValueError)` | `return 5.5` | Intentional |
| scheduler.py | 509 | `(TypeError, ValueError)` | `hm = 0.0` | Intentional |
| scheduler.py | 528 | `(TypeError, ValueError)` | `aviso(...)` | Intentional |
| scheduler.py | 604 | `(TypeError, ValueError)` | `rh = 0.0` | Intentional |
| scheduler.py | 763 | `(ValueError, IndexError)` | `return []` | Intentional |
| app.py | 188 | `Exception as e` | `erro(...)` | Intentional |
| datas.py | 59 | `Exception` | `return (f"Dia_{N}", "-", "-", None)` | **Dangerous** |
| datas.py | 73 | `Exception` | `return None` | **Dangerous** |

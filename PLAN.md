# Orca v7 — Refactoring Plan
# Data: 10/06/2026
# Foco: error handling, SRP, maintainabilidade
# Low-priority: security (hardcoded password OK por enquanto), testing, web layer
# Última auditoria + fixes: 09–10/06/2026

---

## Current Progress (Após Correções)

### ✅ Completado
1. **Logging Infrastructure** — `logging_config.py` criado, `get_logger` importado em 31 módulos, `ORCA_LOG_LEVEL` funciona
2. **Scheduler Core Decomposition** — Monolito eliminado, 19 módulos no package, `__init__.py` re-exporta, consumers atualizados
3. **Tarifas Decomposition** — 7/7 módulos criados com implementações reais (import_ct.py agora existe)
4. **Error Handling** — 21 bare `except Exception` blocks: 7 aceitáveis, 14 fixados com logger (zero sem logger agora)
5. **Type Hints** — `tarifas/resolvers.py` + `scheduler_core/` 3 public functions tipados
6. **Config Schema Validation** — `config_schema.py` criado (dataclass + `__post_init__`), `carregar_config()` valida no load
7. **Pipeline modules limpos** — `demand.py`, `scheduler_loop.py`, `merge.py`, `validation.py` sem `print()` ou `ui.*` direto (merge usa callback opcional)
8. **Dependency rule fix** — Zero imports de `app.py` em `scheduler_core/` (funções extraídas pra callbacks + `config.py`)
9. **Print → logger migration** — ~200+ `print()` substituídos por `logger.*` em módulos não-interativos
10. **Cell parse failure counting** — `ct_parser.py` + `import_contrato.py` com >50% warning
11. **`_to_float_json` retorna None** — semântica de erro corrigida, callers tratam None
12. **Raw `input()` elimination** — Zero `input()` cru fora de `ui.py`
13. **Test suite** — 64/64 core unit tests passam (36 imports broken — fixed on branch `ultima`) + 88 em outros (152 total)

### ❌ Ainda Pendente (baixo impacto)
- [x] `%(funcName)s` no log format (P1)
- [ ] mypy config + pre-commit (P5)
- [ ] `batch/multi_equipe.py` (538→<400 linhas) (P3)
- [ ] `pyproject.toml` com dependências pinadas (P7)
- [ ] Consolidar `_to_float_br`/`_to_float_json`/`_to_float_any` (P7)
- [ ] `col_by_tokens` local function → module-level (P4)
- [x] AGENTS.md: 41→66 tests

---

## Phase 1: Logging Framework — ✅ COMPLETO (infra OK, migração OK)

### Logging Infrastructure
- `logging_config.py` existe, `get_logger(__name__)` importado em 31+ módulos
- `ORCA_LOG_LEVEL=DEBUG` funciona
- Módulos com zero prints (logs puros): `cronograma.py`, `datas.py`, `config.py`, `tarifas/*.py`, `scheduler_core/*.py`, `monitor.py`, `io.py`, `territorio.py`, `excel_export.py`, `comparativo_mec.py`, `scheduler.py`, `context.py`

### Print calls restantes (187 total, todos em módulos interativos de UI)
| Arquivo | Prints | Motivo |
|---------|--------|--------|
| `turmas.py` | 49 | Menus interativos S/N, listas, opções |
| `comparativo_config.py` | 47 | Menu modo comparativo (seleção 1/2/3/0) |
| `app.py` | 31 | Menus de escopo, filtros, metodologias |
| `scheduler_core/display.py` | 24 | Saída de tabelas visuais (Rich console.print) |
| `ui.py` | 23 | Helpers visuais, separadores, cabeçalhos |
| `entry.py` | 13 | Dashboard, menu principal |

**Nenhum `traceback.print_exc()` restante** (último em `batch/run.py:70` foi substituído por `logger.exception`).

---

## Phase 2: Error Handling — ✅ COMPLETO

### 2.1 High-impact patches (9/9)
- [x] 2.1.1: `_to_float_json` — log warning + return `None` (callers usam `or 0.0`)
- [x] 2.1.2: `datas.py` sentinel → `return None` + consumers `is not None`
- [x] 2.1.3: `_calcular_data_fim_por_meses` narrow `(TypeError, ValueError)` + logger.exception
- [x] 2.1.4: `config.py` — atomic write (mkstemp + os.replace) + backup failure logged
- [x] 2.1.5: Price JSON load narrow `(json.JSONDecodeError, OSError)` + logger.exception
- [x] 2.1.6: CT normalize failure narrowed + `logger.warning` em import_contrato + entry.py
- [x] 2.1.7: Cell parse loop — failure counting + >50% warning em `ct_parser.py` e `import_contrato.py`
- [x] 2.1.8: `io.py` EQUIPE enrichment — narrowed + `logger.warning`
- [x] 2.1.9: `monitor.py` corrupted state — narrowed + `logger.warning`

### 2.2 Exception audit
- [x] 21 `except Exception` blocks: 7 aceitáveis (monitor defensivo, UI guards), 14 fixados com `logger.exception`/`logger.warning`

### 2.3 Strict→non-strict fallback
- [x] `demand.py` transition logged, 8.0 hardcoded fallback logged com tariff key

### 2.4 Raw `input()`
- [x] Zero raw `input()` fora de `ui.py`

---

## Phase 3: Scheduler Core Decomposition — ✅ COMPLETO

### Estrutura atual
```
src/atm/srf/scheduler_core/
├── __init__.py           (65 linhas)
├── orchestrator.py       (434 linhas)  [excede 400]
├── validation.py         (107 linhas)  ✅ pipeline, sem ui.*
├── demand.py             (242 linhas)  ✅ pipeline, sem ui.*
├── scheduler_loop.py     (233 linhas)  ✅ pipeline, sem ui.*
├── linking.py            (142 linhas)
├── setup.py              (266 linhas)
├── checkpoint.py         (124 linhas)
├── merge.py (52 linhas) ✅ pipeline, sem ui.* (callback opcional)
├── mechanizado.py        (147 linhas)
├── comparativo.py        (144 linhas)
├── multi_fator.py        (88 linhas)
├── diagnostics.py        (166 linhas)
├── resultados.py         (94 linhas)
├── display.py            (389 linhas)
└── batch/
    ├── __init__.py
    ├── setup.py           (183 linhas)
    ├── run.py             (291 linhas)
    └── multi_equipe.py    (538 linhas)  [excede 400]
```

### Done
- [x] 3.1: Monolito eliminado, 19 módulos, imports atualizados
- [x] 3.2: Pipeline modules (validation, demand, scheduler_loop, merge) — zero `ui.*`/zero `print()`
- [x] 3.3: `atm_v6_3.py` funciona
- [x] **Dependency rule fix:** Zero `from ..app import` em scheduler_core/
  - `_proximo_caminho_livre` movido de `app.py` → `config.py`
  - `calcular_cronograma_inteligente` usa callbacks opcionais (`avaliar_terreno_fn`, `ajustar_escopo_fn`)
  - `_executar_checkpoint_retroativo` usa callback opcional (`ajustar_escopo_fn`)

---

## Phase 4: Tarifas Decomposition — ✅ COMPLETO

### Estrutura atual
```
src/atm/srf/tarifas/
├── __init__.py           (22 linhas)   ✅ re-exports todos os públicos
├── resolvers.py          (244 linhas)  ✅ sem pandas/openpyxl
├── ct_parser.py          (345 linhas)  ✅ normalizar_ct313 + helpers
├── preco_final_json.py   (255 linhas)  
├── import_ct.py (155 linhas) ✅ NOVO — modulo_importar_tarifas + modulo_normalizar_ct
├── import_contrato.py    (229 linhas)  ✅ modulo_importar_precos_contrato
├── import_custos.py      (71 linhas)   ✅ modulo_importar_custos_globais_brutos
└── de_para_crud.py       (138 linhas)  ✅ modulo_mapeamentos_de_para
```

### Done
- [x] 7/7 módulos com implementações reais (não stubs)
- [x] `import_ct.py` criado com `modulo_importar_tarifas` e `modulo_normalizar_ct` extraídos de `app.py`
- [x] `__init__.py` re-exporta todos os públicos
- [x] `entry.py` importa de `tarifas/` (não mais de `app.py`)
- [x] Dead code removido de `app.py` (+ imports não usados)
- [x] Stale `__pycache__/import_ct.cpython-314.pyc` deletado

---

## Phase 5: Type Hints — ✅ COMPLETO (mypy pendente)

### Done
- [x] 5.1: `tarifas/resolvers.py` — 4 funções tipadas com type aliases
- [x] 5.2: scheduler_core public functions tipadas:
  - `calcular_cronograma_inteligente(...) -> Dict[str, Any]` (9 params tipados)
  - `_executar_lote_fazendas(...) -> None` (5 params tipados)
  - `_executar_multi_equipes(...) -> None` (5 params tipados)

### Pendente
- [ ] 5.3: mypy config + pre-commit

---

## Phase 6: Config Schema Validation — ✅ COMPLETO

### Done
- [x] 6.1: `config_schema.py` criado com:
  - `ConfigSchema` dataclass com 24 campos, defaults e `__post_init__` validation
  - `validate_config(cfg)` — lenient (=warn+correct) para load
  - `validate_config_strict(cfg)` — strict (=raise) para save
- [x] 6.2: `carregar_config()` chama `validate_config(cfg)` após load
  - Log warnings pra campos com tipo errado
  - Corrige valores (ex: `"tarifas": "string"` → `{}`)
- [x] `salvar_config()` usa `validate_config_strict(cfg)` (raise on invalid)
- [x] Inline `_validate_config()` removida de `config.py`

---

## Phase 7: Manutenibilidade (bônus) — ❌ Não iniciado

- [ ] Criar `pyproject.toml` com dependências pinadas (MT-3)
- [ ] Remover `duplicate float-parsing` — `_to_float_br`, `_to_float_json`, `_to_float_any` → consolidar em `tarifas/resolvers.py` (CQ-5)
- [ ] Subir `constants.py` para `constants.yaml` + loader lazy (CQ-9)
- [ ] Documentar invariantes no topo de cada módulo movido
- [ ] `col_by_tokens` local function → module-level (baixa prioridade)

---

## Test Suite Status

### Core (fixed on `ultima` branch): 64/64 ✅ PASS (was 25/25 srf + 36 broken imports)
| File | Tests | Content |
|------|-------|---------|
| `test_srf_helpers.py` | 25 | mediana, resolver, stg_tarifas, chave_tarifa, _to_float_any, preco_final_json |
| `test_srf_strict.py` | 0 | strict mode (merged into helpers) |
| `test_scheduler_config.py` | 17 | SchedulerConfig, TurmaSpec, ScheduleResult, EquipeSpec |
| `test_scheduler_runner.py` | 9 | run_scheduler integration |
| `test_headless_api.py` | 10 | FastAPI web endpoints |
| `test_e2e_web.py` | 3 | E2E web session flows |

### Extended (NOT in AGENTS.md): 88 tests
| File | Tests | Content |
|------|-------|---------|
| `test_scheduler_config.py` | 17 | SchedulerConfig, TurmaSpec, ScheduleResult, EquipeSpec |
| `test_scheduler_runner.py` | 9 | run_scheduler integration |
| `test_headless_api.py` | 10 | FastAPI web endpoints |
| `test_cascata_global.py` | 3 | Cascata GLOBAL |
| 11 E2E files | 49 | happy path, batch, completo, cascata, dossier, real data |
| **Total** | **154** | |

### Gaps
- [x] AGENTS.md diz "41 tests" mas são 66 — atualizar docs
- [ ] Zero test coverage para logging
- [ ] `calcular_cronograma_inteligente` sem unit tests (apenas E2E/integration)
- [ ] Vários E2E tests são `self.assertTrue(True)` placeholders

---

## Estado Atual (Original → Final)

| Métrica | Antes | Depois |
|---------|-------|--------|
| `scheduler_core.py` | 3,376 linhas monólito | 19 módulos, <400 linhas (exceção: 2 módulos) |
| `tarifas.py` | 1,225 linhas monólito | 7 módulos no package |
| `print()` em non-UI | ~400+ | 187 (todos em módulos interativos de UI) |
| `input()` cru | 9 | 0 (só em `ui.py`) |
| `traceback.print_exc()` | múltiplos | 0 |
| `except Exception: pass` | 64 | 21 (7 aceitáveis, 14 com logger) |
| Type hints | só scheduler_config.py | resolvers.py + 3 scheduler_core functions |
| Config validation | nenhuma | `config_schema.py` with dataclass validation |
| Testes | 41 | 66 (154 com extended) |

# SRF v5.x — Review: o que está feito vs o que falta

Última passagem alinhada ao código `atm_v5.py` **v5.9** (março/2026).

---

## Implementado nesta versão (checklist)

| Área | Situação |
|------|----------|
| Microplanejamento Excel + mapeamento de colunas | OK |
| Import CT_313 → `config.tarifas` (manual, menu [2]) | OK |
| Normalizar CT_313 → STG (menu [3]) | OK |
| Pipeline RAW→STG (`STG_TARIFAS`, `STG_METADATA`) | OK |
| CRUD `de_para` (menu [4]) | OK |
| Smart Scheduler: turmas, reforço, bloqueio global plantio/irrigação | OK |
| **Pelotao_Unificado** após liberação global (pool de executores) | OK v5.9 |
| **`orcamento_estrito`** em `config.json`: validação micro→tarifa; resolvers `strict` sem mediana silenciosa | OK v5.9 |
| Heurística `auto_mapear_de_para` **desligada** quando `orcamento_estrito` é true | OK v5.9 |
| Fallback de rendimento (modo compat: mediana → 8) | OK |
| Dossier Excel: **DASHBOARD** KPI, **GANTT_SIMPLES** semanal, cabeçalhos navy, zebra no cronograma | OK v5.9 |
| Coluna **Semana** no `CRONOGRAMA_DETALHADO` exportado | OK v5.9 |
| Texto de diagnóstico: Uso %, reforço, bloqueio; turma caminho crítico; **dica jornada 5h/6h** se prazo excedido | OK v5.9 |
| Testes: `test_srf_helpers.py` + `test_srf_strict.py` (28 testes) | OK v5.9 |

---

## Backlog / ainda não implementado

### 1. Calendário e feriados

- Dias úteis genéricos; simulação em "Dia" 1..N sem data civil no Excel.

### 2. Curva S financeira

- Aba dedicada com custo acumulado dia a dia.

### 3. Viabilidade máquina vs manual

- `criterios_mecanizacao` (v4) não integrado ao v5.

### 4. Persistência de cenários

- Guardar turmas/último run em JSON.

### 5. UX enterprise

- PDF, e-mail, logs de auditoria.

### 6. Legado

- `atm43.py` não portado.

---

## Priorização sugerida

1. Datas reais + feriados (CSV).
2. Curva S no Dossier.
3. Persistir cenário.
4. Mecanização opcional.

---

*Este ficheiro é atualizado a cada release relevante.*

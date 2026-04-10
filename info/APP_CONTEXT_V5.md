# SRF / ATM — Contexto técnico para assistentes (v5.x)

Este documento descreve o **estado atual** do projeto em `e:\cli_planilhas`. Documentos antigos (`GUIA_RAPIDO_V4_1.md`, `ANALISE_ATM_V4.md`, `CHANGELOG_V4_1.md`) referem o **ATM v3/v4** com menu extenso e script `atm3.py` — **não** refletem o fluxo do **v5**.

**Lista do que falta / backlog:** `REVIEW_FALTANTES.md`.

---

## O que é o aplicativo

- **Nome no código:** `SRF - Sistema de Restauracao Florestal` (linhagem "ATM" do Isaac/Zaza).
- **Versão atual (script principal):** **5.11** — ficheiro `atm_v5.py` *(aviso declividade / roçada Classe I padrao; exemplo FORMOSA em markdown)*.
- **Propósito:** Microplanejamento + CT_313; simulação por **turmas** com **reforço automático**, **bloqueio global** de plantio/irrigação e opcional **pelotão unificado** após liberação; **orçamento estrito** (sem mediana silenciosa); bootstrap automático que carrega exame.xlsx + CT_313 e aplica 21 de_para hardcoded; suporte a atividades mecanizadas (HH=0, HM>0); export **Dossier Excel** com formatação executiva (**DASHBOARD**, **GANTT_SIMPLES**).

É uma **CLI interativa** (terminal), não uma aplicação web.

---

## Como executar

```bash
cd e:\cli_planilhas
pip install -r requirements.txt
python atm_v5.py
```

**Dependências:** ver `requirements.txt` (`pandas`, `openpyxl`, `rich`, `colorama`).

---

## Ficheiros importantes

| Ficheiro | Papel |
|----------|--------|
| **`atm_v5.py`** | v5.10: bootstrap auto (CT + micro), `normalizar_chave`, scheduler com reforço/bloqueio/pool, mecanizadas, Dossier. |
| **`srf_excel_format.py`** | Formatação openpyxl: cabeçalhos navy, zebra, `DASHBOARD`, `GANTT_SIMPLES`. |
| **`config.json`** | 21 `de_para` hardcoded (EXAME→CT), 81 `tarifas`, `orcamento_estrito=true`, `filtros_bloqueio_global`, `custo_hora_tf`. |
| **`CT_313_NORMALIZADA.xlsx`** | STG gerado automaticamente a partir da CT bruta no bootstrap. |
| **`tests/test_srf_helpers.py`** | Testes helpers e resolvers (28 tests). |
| **`tests/test_srf_strict.py`** | Testes modo estrito, mecanizadas e `normalizar_chave` (6 tests). |
| **`Dossier_<Fazenda>.xlsx`** | Abas: `DASHBOARD`, `RESUMO_FINANCEIRO`, `CRONOGRAMA_DETALHADO`, `CUSTO_POR_ATIVIDADE`, `GANTT_SIMPLES`. |

---

## Métricas e logística (v5.10)

- **Uso % (por turma):** HH agendadas com o **nome dessa turma** no cronograma ÷ (dias simulados × operários da turma × jornada). Reforço **não** aumenta `n_ops`; aparece como HH extra na mesma turma.
- **Bloqueio global:** plantio/irrigação só quando o resto da fazenda zerou; **reforço não consome** atividades bloqueadas até lá.
- **Pelotao_Unificado:** se ativado, após só restar demanda bloqueada, o simulador usa **todos os executores** num único pelotão para plantio/irrigação (linhas `Modo=PoolPosBloqueio`).
- **`orcamento_estrito`:** sem mediana/8 silenciosos; lacunas exigem escolher tarifa CT ou entrada manual antes das demandas.
- **Atividades mecanizadas:** HH=0 e HM>0 — não geram demanda humana no scheduler mas contribuem receita no Dossier financeiro.

---

## Mudanças chave na v5.10

1. **`normalizar_chave()`:** nova função que remove acentos + pontuação + colapsa espaços. Resolve bug crítico em que `remover_acentos` mantinha `/`, `.`, `-` etc., fazendo com que nenhum dos 21 `DEFAULT_DEPARA_EXAME_CT313` batesse.
2. **Bootstrap automático em `main()`:** carrega CT bruta → STG → tarifas → micro → aplica `DEFAULT_DEPARA` (21 mapeamentos) → salva config. Resultado: **100% CT, 0% fallback** na inicialização.
3. **`_find_default_ct_path` exclui `STG_FILENAME`:** evita confundir `CT_313_NORMALIZADA.xlsx` com a CT bruta.
4. **Mecanizadas em strict mode:** `resolver_rendimento_hh` retorna `0.0` (não `None`) para atividades com `tipo=Mecanizada` ou `rendimento_hm > 0`.
5. **`rendimento_hm` incluído em `carregar_stg_tarifas`:** disponível para checagem de mecanizada nos resolvers.
6. **Dossier financeiro separado:** receita MO vs mecanizada; tipo no pivot CUSTO_POR_ATIVIDADE.

---

## `config.json` (v5.10)

- **`orcamento_estrito`:** `true` — validação obrigatória micro→tarifa; `false` — compatível com heurística `auto_mapear_de_para` e fallbacks.
- **`filtros_bloqueio_global`:** lista de substrings para identificar plantio/irrigação no nome da atividade.
- **`de_para`:** 21 entradas fixas (protótipo EXAME→CT_313), aplicadas automaticamente no bootstrap.
- **`custo_hora_tf`:** R$ 52,86 (extraído da aba Diária_TF da CT_313).

---

## Resumo

**v5.10** = bootstrap inteligente com 100% dados CT; `normalizar_chave` para lookup robusto; mecanizadas tratadas; simulador com reforço/bloqueio/pelotão; Dossier Excel executivo com Dashboard e Gantt.

---

*Documento alinhado a `atm_v5.py` v5.10.*

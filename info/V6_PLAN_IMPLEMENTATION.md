# V6 Plan Implementation (SRF / Smart Scheduler)

## 1) Objetivo do V6

Evoluir o SRF de um simulador robusto por fazenda para um planejador operacional multi-fazenda com:

- visualização clara do efeito cascata entre atividades e turmas;
- noção de timeline única de execução (meta sendo consumida dia a dia no lote);
- cenários avançados com múltiplas equipes independentes;
- saídas executivas mais intuitivas (Excel + opcional UI).

---

## 2) Estado Atual (V5) - leitura funcional

### O que já existe e funciona bem

- fluxo completo: micro -> de_para -> tarifa -> HH -> cronograma -> financeiro;
- regras de sequência (implantação/cascata, personalizado etc.);
- lote de fazendas com equipe padrão e checkpoint;
- comparativo com modo mecanizado;
- exportações de dossier por fazenda e consolidado.

### Limitações percebidas pelo negócio

- Excel exportado não evidencia visualmente o entrelaçamento de turmas e fases;
- a meta de prazo no lote é avaliada por fazenda (ou consolidada por agregação), não como "calendário contínuo único";
- falta modo nativo para planejamento "N equipes paralelas com carteiras de fazendas e metas próprias".

---

## 3) Escopo V6 (Macro)

### Pilar A - Visual operacional (cascata real no Excel/relatório)

Entregar uma leitura visual de:

- sequência por fase (roçada -> formiga -> ... -> irrigação);
- ocupação por turma ao longo dos dias;
- conflitos, espera e sobreposição;
- caminho crítico por fazenda e no lote.

### Pilar B - Meta contínua no lote (budget de dias)

Tratar o lote como uma operação única:

- mesma equipe executa fazendas em sequência;
- cada dia gasto reduz o saldo da meta global;
- cada fazenda entra com "data de início acumulada" e "data fim acumulada";
- alerta de estouro passa a ser progressivo (não só no final).

### Pilar C - Modo avançado multi-equipes

Permitir simular:

- várias equipes (A/B/C), com capacidades diferentes;
- alocação de fazendas por equipe;
- metas por equipe e meta global;
- cronograma combinado com paralelismo real.

### Pilar D - Usabilidade

- reduzir fricção de prompts;
- padronizar templates de equipe;
- preparar caminho para UI (sem perder CLI).

---

## 4) Backlog proposto (épicos e entregas)

## EPIC 1 - Linha do tempo e cascata visual

### E1.1 - Aba "TIMELINE_CASCATA" no Excel por fazenda

- dataset: dia, semana, talhão, atividade, fase, turma, HH, duração;
- layout tipo Gantt simplificado (barras por dia e cor por fase);
- legenda de cores por fase;
- destaque de blocos com bloqueio/restrição.

### E1.2 - Aba "OCUPACAO_TURMAS_DIA"

- matriz dia x turma (HH e % de uso);
- heatmap (alto/médio/baixo uso);
- identificação do gargalo diário.

### E1.3 - Aba "REDE_CASCATA"

- visão por fase: HH total, início, fim, dependências;
- campo "espera por bloqueio" para explicar ociosidade.

## EPIC 2 - Meta contínua do lote

### E2.1 - Novo modo de simulação: `lote_continuo`

- hoje: fazendas simuladas separadamente;
- V6: timeline única acumulada.

Campos novos por fazenda:

- `dia_inicio_acumulado`;
- `dia_fim_acumulado`;
- `dias_consumidos_no_lote`;
- `saldo_meta_apos_fazenda`;
- `status_meta_ate_agora` (ok / risco / excedido).

### E2.2 - Diagnóstico incremental da meta

- a cada fazenda no lote:
  - meta total em dias úteis;
  - consumido até agora;
  - saldo restante;
  - projeção de término.

### E2.3 - Consolidado com curva de consumo

- gráfico linha: dia acumulado vs meta;
- pontos por fazenda (marcos de avanço);
- alerta automático quando cruza 80/90/100% da meta.

## EPIC 3 - Modo avançado multi-equipes

### E3.1 - Entidade `EquipeOperacional`

Estrutura sugerida:

- nome da equipe;
- executores;
- jornada;
- turmas internas;
- especialização;
- calendário/disponibilidade.

### E3.2 - Estratégias de alocação de fazendas

- manual (usuário escolhe equipe por fazenda);
- automática (heurística por HH/caminho crítico/especialização);
- híbrida (sugestão + confirmação).

### E3.3 - Metas por equipe

- prazo absoluto por equipe;
- SLA por fazenda;
- painel de aderência por equipe e global.

### E3.4 - Consolidado multi-equipes

- tabela e gráfico de carga por equipe;
- comparação produtividade, custo, atraso e ociosidade.

## EPIC 4 - UX e arquitetura

### E4.1 - Refatoração modular

Separar `atm_v5.py` em módulos:

- `scheduler_core.py`;
- `batch_planner.py`;
- `finance_engine.py`;
- `excel_exporter.py`;
- `ui_cli.py`.

### E4.2 - Configuração declarativa

- perfis de equipe versionados em JSON;
- presets de sequência;
- presets de export.

### E4.3 - Base para UI

- camada de serviço comum (funções puras);
- CLI e UI chamando o mesmo núcleo;
- evitar regra de negócio dentro da camada visual.

---

## 5) Foco solicitado pelo supervisor (prioridade máxima)

## P0 - "Excel sem cascata visual"

Implementar primeiro:

1. aba timeline (Gantt simplificado);
2. aba ocupação diária por turma;
3. legenda de fases e bloqueios.

Resultado esperado: qualquer supervisor entende visualmente "quem trabalhou em quê e quando".

## P0 - "Meta 3 meses não é subtraída no lote"

Implementar `lote_continuo` como modo padrão opcional:

- cada fazenda começa no dia seguinte ao final acumulado da anterior (ou regra definida);
- meta global decresce a cada fazenda;
- relatório mostra saldo de dias restante em tempo real.

Resultado esperado: refletir operação real de equipe única percorrendo várias fazendas.

## P1 - "Modo complexo com várias equipes e prazos"

Sim, é possível.

Não está pronto hoje de forma completa. O sistema atual já tem peças úteis (turmas, capacidade, lote), mas falta:

- abstração de equipes múltiplas concorrentes;
- motor de alocação por equipe;
- relatório consolidado multi-equipe.

---

## 6) Proposta de fases de implementação

### Fase 1 (rápida, alto impacto)

- adicionar `lote_continuo` com saldo de meta acumulado;
- exportar abas de timeline e ocupação diária;
- manter compatibilidade com modo atual.

Prazo sugerido: 1-2 sprints.

### Fase 2 (robustez operacional)

- modo multi-equipes manual;
- metas por equipe;
- consolidado multi-equipes.

Prazo sugerido: 2-3 sprints.

### Fase 3 (produto)

- UI web leve (dashboard e configuração assistida);
- filtros e visual interativo;
- histórico de simulações.

Prazo sugerido: 2+ sprints (dependendo do escopo de frontend).

---

## 7) UI: vale a pena?

### Resposta curta

Sim, para esse tipo de necessidade (timeline, consumo de meta, múltiplas equipes), UI tende a ser mais intuitiva e escalável.

### Porém

Não precisa abandonar CLI. Melhor estratégia:

- preservar CLI como motor operacional e fallback;
- criar UI gradual em cima do mesmo core;
- começar por visualização (dashboard), depois edição.

---

## 8) Critérios de sucesso V6 (KPIs)

- redução de tempo para leitura do planejamento por fazenda;
- taxa de entendimento do efeito cascata por supervisores;
- precisão de previsão de prazo no lote contínuo;
- redução de retrabalho no ajuste de equipe;
- adoção do modo multi-equipe.

---

## 9) Riscos e mitigação

- risco: complexidade explode no arquivo monolítico;
  - mitigação: modularizar antes dos épicos mais pesados.
- risco: UI divergir da lógica CLI;
  - mitigação: uma camada de core única e testada.
- risco: dados de entrada inconsistentes (de_para, HM, tipos);
  - mitigação: auditoria de cadeia mais visível e bloqueios opcionais.

---

## 10) Próximos passos recomendados (ordem prática)

## Status de implementação

### Fase 1 - IMPLEMENTADA (v6.0)

- [x] `lote_continuo` com saldo de meta acumulado entre fazendas
- [x] Diagnóstico incremental no console (saldo/% consumido a cada fazenda)
- [x] Aba `TIMELINE_CASCATA` no Excel (dia, semana, talhão, atividade, fase, turma, cor)
- [x] Aba `OCUPACAO_TURMAS_DIA` no Excel (dia x turma com HH, cap, uso%, status colorido)
- [x] Cores de fases e status aplicadas nas abas Excel
- [x] Tabela "Cascata de execução" com Início/Fim acumulado + saldo + status
- [x] Consolidado Excel com abas: METADADOS, RESUMO, CASCATA_FAZENDAS, CURVA_CONSUMO_META, CRONOGRAMA_LOTE

### Fase 2 - IMPLEMENTADA (v6.0)

- [x] Modo MULTI-EQUIPES (N equipes com carteiras de fazendas e prazos próprios)
- [x] Alocação manual de fazendas por equipe (índices/intervalos)
- [x] Metas por equipe (prazo, jornada, executores independentes)
- [x] Consolidado comparativo entre equipes (console Rich + Excel)
- [x] Export `MultiEquipes_<empresa>.xlsx`
- [x] Lote contínuo e multi-equipes: escolha **todos os talhões** ou **definir por fazenda** (reutiliza o mesmo fluxo que “uma fazenda”) antes de processar cada fazenda
- [x] Listas paginadas no menu vínculos/assistente: **10 itens por página** por defeito em `selecionar_paginado`

### Extras implementados

- [x] Perfis de equipe salvos em JSON (`perfis_equipe/`)
- [x] Carregamento de perfil no setup do lote e multi-equipes
- [x] Opção "salvar perfil" após configuração

### Fase 3 - PENDENTE

- [ ] UI web leve (dashboard + configuração assistida)
- [ ] Filtros e visual interativo
- [ ] Histórico de simulações

---

## 11) Monitores auxiliares CLI (três processos)

- **Principal:** `python atm_v5.py` grava `estado_sessao_<PID>.json` na pasta do projeto (overwrite atómico).
- **Auxiliares (modo predefinido — manual):** abrir dois terminais na pasta do projeto e executar `python srf_monitor.py --feed meta --pid <PID>` e `python srf_monitor.py --feed rendimentos --pid <PID>` (o `<PID>` é o do processo onde corre o `atm_v5.py`). Sem estes passos **não** aparecem janelas extra por magia.
- **Abrir consolas automaticamente (Windows):** `python atm_v5.py --spawn-monitors` ou `SRF_SPAWN_MONITORS=1` — tenta lançar dois processos `srf_monitor.py` em **novas** janelas de consola (`CREATE_NEW_CONSOLE`), com pequeno atraso entre o primeiro e o segundo e mensagem no principal (“Janela 1 — meta”, “Janela 2 — rendimentos”). Requer `SRF_MONITOR` diferente de `0`. Em Linux/macOS os processos são criados sem consola dedicada (comportamento depende do ambiente).
- **Só vejo uma janela:** no Windows as duas consolas podem **sobrepor-se** no mesmo sítio (Alt+Tab / barra de tarefas). O spawn **não** abre o terceiro feed (`relatorios`) — esse continua manual.
- **Visual dos monitores:** `srf_monitor.py` usa o mesmo ASCII/cores do principal e tabelas **Rich** para `meta` e `rendimentos` (dependências: `rich`, `colorama` — ver [info/requirements.txt](info/requirements.txt)).
- **Variáveis de ambiente:**
  - `SRF_MONITOR=0` — desliga gravação de estado e append ao buffer de relatórios no processo principal.
  - `SRF_MONITOR_QUIET=1` — no lote contínuo, omite o bloco repetido “LOTE CONTÍNUO — após …” no console (o feed `meta` continua a mostrar o mesmo).
  - `SRF_MONITOR_PID` — PID alvo para `srf_monitor.py` / `srf_local_api.py` quando não se passa `--pid`.
- **Semântica dos feeds:** `meta` — `operacao` + `lote`; `rendimentos` — `rendimentos_sessao`; `relatorios` — `buffer_relatorios` (resumos/diagnósticos).
- **HTTP local (protótipo):** `python srf_local_api.py --port 8765 --pid <PID>` → `http://127.0.0.1:8765/api/state`.

**Comparativo multi-fator (Excel):** a configuração do cenário corre **depois** de criar as turmas (ETAPA 1), com **menu incremental** (adicionar/remover jornadas e tamanhos de equipe, reset, modo rápido por vírgulas, preset “operários de cada turma”). O fluxo interactivo duplicado em `simular_cenarios_multifator` reutiliza o mesmo menu.

**Mecanizado:** ao vincular atividades a um recurso mecanizado, além do percurso S/N há **filtro por texto** e **lista paginada / índices**, alinhados ao menu de vínculos de turma.

## 12) Camada de serviço e Excel in-app

- **Serviço importável:** [`srf_scheduler_service.py`](../srf_scheduler_service.py) expõe `load_config`, `load_monitor_state`, `run_cronograma_single` para UI ou API futura sem duplicar regras.
- **Estratégia Excel (produto):** manter o motor e os ficheiros `.xlsx` gerados como **artefacto de exportação**; qualquer UI deve priorizar **tabelas in-app** (mesmas colunas que o dossier) + botão “Exportar .xlsx”. Evitar duplicar o Excel como fonte de verdade; *viewer* embutido de Excel completo não é objetivo — preview tabular + export é suficiente para a maioria dos casos.

## 13) Épico futuro — várias estruturas de equipe na mesma fazenda

Planeamento separado: permitir que a mesma fazenda tenha **carteiras/equipes paralelas** (ex.: turnos, carteiras de serviço) com metas distintas e consolidação — base para UI e para extensão do modo multi-equipe. Não faz parte do núcleo atual; depende de modelo de dados de alocação por talhão/atividade mais rico.

## 14) Menu vínculos turma — melhorias opcionais (backlog)

- Resumo **N atividades reais / M já vinculadas** no topo do menu (implementado como linha de contexto).
- Opcional futuro: modo inicial (percurso vs menu primeiro), atalho `?`, log de vínculos em ficheiro no workspace para revisão externa.

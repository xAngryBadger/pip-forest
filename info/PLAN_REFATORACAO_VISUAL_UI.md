# Plano reserva — Refatoração visual completa (SRF / Smart Scheduler)

**Status:** reserva estratégica — não substitui o núcleo Python; define camada de apresentação e rollout.  
**Objetivo:** transformar a experiência de uso em produto **empresarial**, **intuitivo** e **visualmente coerente**, sem reinventar a lógica de negócio no frontend.

**Guia visual (ordem de autoridade):**

1. **Primário:** o protótipo HTML versionado em [`aparencia/prototipos/app_srf_5_telas.html`](aparencia/prototipos/app_srf_5_telas.html) — layout, fluxo entre **sete** vistas (inclui **Análise / Gráficos**), tokens CSS no `:root`, componentes visíveis. Não existe um “segundo código” a extrair das imagens: as imagens **não** são o desenho-canónico.
2. **Secundário:** ficheiros PNG em [`aparencia/`](aparencia/) — consulta opcional para **acrescentar ou remover** pormenores (densidade, labels, ideias) quando útil; não substituem o HTML nem obrigam a replicar pixel a pixel salvo decisão explícita de produto.

---

## 1) Princípios de produto

- **Uma fonte de verdade:** motor em Python (API ou biblioteca); UI só consome e dispara ações.
- **Configuração vs resultado:** telas de setup (wizard) separadas de telas de leitura (dashboards, relatórios).
- **Menos Excel como interface:** Excel permanece como export e arquivo; a app é o lugar de operar e entender.
- **Acessibilidade básica:** contraste, foco visível, labels explícitos (empresas exigem auditoria e treinamento).

---

## 2) Direção estética sugerida: brutalista corporativo

Inspirado em brutalismo digital **mas** domesticado para escritório:

| Elemento | Orientação |
|----------|------------|
| **Grid** | Forte: colunas claras, bordas visíveis ou sombras duras leves |
| **Tipografia** | Uma fonte display condensada para títulos + uma sans para corpo (evitar genérico “Inter-only” em tudo) |
| **Cor** | Fundo neutro frio ou off-white; **um** acento saturado (ex.: laranja queimado, verde floresta) só para CTAs e estados |
| **Componentes** | Caixas com borda explícita (`1–2px`), cantos **não** ultra-arredondados (4–8px) |
| **Densidade** | Dados densos em tabelas; respiração nas telas de decisão (wizard) |

Evitar: gradientes genéricos roxo/azul “startup”; excesso de sombras e glassmorphism em telas operacionais.

**Tema aprovado para o MVP visual:** o protótipo HTML (**modo escuro**, **acentos vermelhos**, tipografia `DM Mono`) define paleta e ritmo. Os PNG em [`aparencia/`](aparencia/) podem sugerir ajustes pontuais, mas o **tema de referência** é o CSS do protótipo (variante clara “brutalista papel” pode vir depois como `light`).

---

## 3) Stack técnica recomendada (referência)

| Camada | Opção A (rápida) | Opção B (empacotado) |
|--------|------------------|----------------------|
| UI | SPA (React ou Vue ou Svelte) | Mesma SPA dentro de **Tauri** ou **Electron** |
| API local | **FastAPI** — JSON, CORS localhost | Idem |
| Estado | TanStack Query / fetch + cache de sessão | Idem |
| Tabelas grandes | TanStack Table ou AG Grid Community | Idem |
| Gráficos | ECharts ou Chart.js | Idem |
| Build | Vite | Vite + Tauri |

O CLI (`atm_v5.py`) pode coexistir indefinidamente; a UI chama os mesmos serviços.

### 3.1 Prioridade explícita: **aplicação local primeiro** (secretária / pasta do projeto)

A virtualização na nuvem (VM, container, SaaS) é **fase posterior**. O objetivo imediato é um produto que:

1. **Funcione como app** — janela própria ou browser em `localhost`, com arranque previsível (script ou instalador), **sem** dependência de login remoto ou deploy para operar.
2. **Persista no disco** — SQLite e/ou pastas de projeto (`dossiês/`, micro Excel, estado de jobs) no filesystem local; o mesmo modelo de dados serve depois na nuvem, mas **não** bloqueia o MVP.
3. **Exponha API local** — FastAPI (ou equivalente) em `127.0.0.1`; a SPA é o cliente; o motor Python continua a ser a fonte de verdade.
4. **Opcional de empacotamento** — Tauri ou Electron **depois** de a UI + API estarem estáveis em dev; não antecipar complexidade de build antes do fluxo feliz local.

**Implicações de engenharia:** contratos JSON estáveis (secção 6); CORS só para origem local; paths de ficheiro resolvidos no backend (nunca `file://` direto a partir da SPA sem canal seguro). Documentar “modo portátil” (pasta com `.exe` + dados) como alvo de release antes de “modo servidor”.

### 3.2 Fase posterior: **nuvem / acesso remoto** (sem redesenhar o produto)

Quando o app local estiver maduro:

- Reutilizar a **mesma** API e os mesmos modelos; empacotar backend + frontend em imagem ou PaaS, ou expor apenas a API atrás de reverse proxy.
- Adicionar autenticação, multi-instância e backup **só** quando o caso de uso o exigir; não misturar esses requisitos com o MVP visual.

---

## 4) Inventário de telas (mapa do produto)

Cada linha vira um “épico de tela” com o prompt da secção 7.

| # | ID tela | Finalidade |
|---|---------|------------|
| T01 | `SplashAuth` | (Futuro) Login / modo offline local — opcional na fase 1 |
| T02 | `HomeProjeto` | Abrir micro, ver resumo (N fazendas, N atividades), atalhos |
| T03 | `ConfigGlobal` | Tarifas, de_para, custos globais — links para fluxos existentes do menu |
| T04 | `WizardModo` | **Passo 1:** escolher modo — uma fazenda \| lote equipe única \| multi-equipes |
| T05 | `WizardFiltroEquipe` | **Passo 2:** dropdown `EQUIPE` (valores únicos do micro) + opção “todas” |
| T06 | `WizardFazendas` | **Passo 3:** checkboxes ou lista com seleção múltipla — **ecrã 2 do protótipo HTML** (grelha de cartões); PNG `programação fazendas.PNG` só como referência secundária |
| T07 | `ParametrosScheduler` | Prazo, jornada, sequência, bloqueio global, reforço — cartões agrupados |
| T08 | `EquipeTurmas` | CRUD leve de turmas + vínculo de atividades (equivalente ao menu atual) |
| T09 | `RunProgress` | Execução longa: barra, fazenda atual, saldo de meta (lote contínuo) |
| T10 | `ResultadoCronograma` | Tabela + mini-Gantt / timeline por fase |
| T11 | `ResultadoFinanceiro` | Painel dossier (receita, MO, margem, globais) |
| T12 | `ExportCenter` | Botões: Excel dossier, consolidado, PDF/HTML futuro; lista de relatórios (`ReportRow`) — o PNG `relatórios feitos.PNG` é só referência secundária |
| T13 | `MonitorSessao` | Réplica dos “monitores auxiliares”: operação + relatório limpo (opcional) |
| T14 | `AjudaAtalhos` | Atalhos de teclado, glossário (rocada, cascata, etc.) |

Fases de entrega sugeridas:

- **MVP visual:** prioridade **P0** = programação em cartões **e** lista **Relatórios gerados** (`ReportRow`, ecrã 6 do protótipo); os PNG com esses nomes são **apoio**, não critério de aceitação em detrimento do protótipo; em seguida T02, T04–T07, T09–T11 (fluxo “rodar scheduler”).
- **Infra do MVP:** **aplicação local** (API + UI em `localhost` ou app empacotada) — **sem** requisito de nuvem; ver §3.1.
- **V2:** T08 completo (paridade com CLI de turmas).
- **V3:** T01, permissões, auditoria; **opcional** virtualização na nuvem (§3.2) quando o produto local estiver estável.

---

## 5) Biblioteca de componentes (padrões UI)

- **WizardStepper** — indica passo atual (Modo → Equipe → Fazendas → Parâmetros → Executar).
- **SelectSearchable** — dropdown com busca para listas longas (fazendas, atividades).
- **CheckboxGroup** — seleção múltipla com “selecionar todas” / “limpar”.
- **MetricCard** — HH total, dias simulados, saldo meta (número grande + label).
- **DataTable** — ordenação, pin de colunas, export CSV da vista.
- **AlertBanner** — avisos de de_para, orçamento estrito, meta excedida.
- **EmptyState** — quando não há micro carregado ou filtro zerou tudo.

---

## 6) Contrato com o backend (independente do visual)

Antes de desenhar pixels finos, estabilizar:

- `GET /api/micro/summary` — contagens e lista de equipes/fazendas.
- `POST /api/scheduler/run` — body com modo, filtros, parâmetros; retorna job id ou resultado síncrono.
- `GET /api/scheduler/status/:id` — se jobs forem assíncronos.

O plano de **refatoração visual** assume que esses contratos existem ou serão mockados com JSON fixo no início.

---

## 7) Prompt mestre para gerar cada tela com IA

Copie o bloco abaixo para uma conversa de design/implementação (Cursor, ChatGPT, Claude, etc.). **Substitua** os campos entre `« »`.

```
Contexto do produto:
- Nome: SRF — Sistema de Restauração Florestal / Smart Scheduler.
- Público: equipes operacionais e supervisão; uso em escritório e campo (notebook).
- Estética: brutalista corporativo — grid forte, bordas visíveis, poucos arredondamentos,
  fundo neutro, um acento de cor para ações primárias. Sem visual genérico “IA startup”.
- Stack alvo da UI: «React | Vue | Svelte» + CSS modules ou Tailwind (especificar).

Tela a descrever/implementar:
- ID: «Txx_nome_curto»
- Nome amigável: «…»
- Objetivo do utilizador nesta tela: «…»
- Dados de entrada (props / API): «lista de campos»
- Ações principais (botões): «…»
- Estados vazios / erro / carregamento: «…»
- Requisitos de acessibilidade: contraste AA, foco visível, labels em todos os controlos.

Entregáveis pedidos:
1) Wireframe em texto (secções de cima a baixo).
2) Lista de componentes reutilizáveis usados.
3) Mockup em HTML+CSS único (um ficheiro) OU componentes «framework» prontos a colar,
   responsivo min-width 1280px e colapso para tablet.
4) Textos de UI em português (PT-BR), curtos e diretos.
5) Não inventar regras de negócio — apenas apresentação; onde faltar dado, usar placeholder.

Restrições:
- Não usar «biblioteca X» se for pesada demais para MVP (ajustar conforme stack escolhida).
- Evitar gráficos nesta tela se não forem essenciais (especificar sim/não).
```

### Variante só wireframe (rápido)

```
Gera um wireframe textual + lista de componentes para a tela «Txx» do SRF
(brutalista corporativo, PT-BR). Sem código. Foco em hierarquia e fluxo do utilizador.
```

### Variante só HTML estático (prototipo visual)

```
Gera um único ficheiro HTML com CSS embutido para a tela «Txx» do SRF.
Estilo brutalista corporativo. Dados mock em JSON no próprio script.
Largura máxima 1200px centrada. Sem dependências externas obrigatórias.
```

---

## 8) Riscos e mitigação

| Risco | Mitigação |
|-------|-----------|
| UI diverge da lógica Python | API única; testes de contrato JSON |
| Escopo infinito | MVP por fases na secção 4 |
| Excel como “segunda UI” | Export explícito; tabela na app como principal |

---

## 9) Ponte de leitura (estrutura deste documento)

- **Guia visual primário vs PNG** — cabeçalho deste documento + **secção 12**.
- **App local vs nuvem:** prioridade e implicações técnicas — **secções 3.1 e 3.2**.
- **PNG em `aparencia/` (secundários) e tokens alinhados ao HTML** — **secção 10**.
- **Protótipo HTML** (sete vistas; análise e mapeamento) — **secção 12**.
- **Passos ordenados de adaptação** (tokens → HTML válido → rotas → API → empacotamento) — **secção 13**.
- **Ligação com outros planos** — **secção 14**.

---

## 10) Pasta `aparencia/` — PNG de apoio (secundários ao protótipo HTML)

Os PNG **não** são o guia primário de implementação (ver cabeçalho do documento). Servem para inspirar ou validar detalhes que ainda não existam no HTML; divergências resolvem-se a favor do ficheiro [`aparencia/prototipos/app_srf_5_telas.html`](aparencia/prototipos/app_srf_5_telas.html) salvo decisão explícita.

Colocar os PNG em `cli_planilhas/aparencia/` (se ainda não versionados, confirmar sincronização do explorador de ficheiros com o repositório). A coluna **Prioridade** indica utilidade como inspiração; o **critério de implementação** continua a ser o protótipo HTML.

| Ficheiro | Prioridade | Mapeamento funcional (SRF) |
|----------|------------|----------------------------|
| `programação fazendas.PNG` | **P0** | Lista/carteiras de fazendas do micro: seleção, filtros, atalho para agendar ou abrir detalhe |
| `relatórios feitos.PNG` | **P0** | Histórico de relatórios gerados (dossier, consolidado): estado, download, reabrir |
| `inicial.PNG` | P1 | Entrada / escolha de modo (dois grandes cartões + CTAs) |
| `detalhes operação.PNG` | P1 | Dashboard de operação: KPIs, gráfico de linha, lista de itens com miniatura |
| `secundaria.PNG` | P2 | Vista longa “relatório único”: secções com texto + mini-gráficos + tabelas (substitui cópia bagunçada do console) |

### 10.1 Tema visual inferido (tokens de partida)

| Token | Uso | Valor inicial sugerido |
|-------|-----|-------------------------|
| `--bg-app` | fundo geral | `#0c0c0e` – `#141418` |
| `--bg-elevated` | cartões, linhas | `#1a1a20` |
| `--border` | separadores | `#2e2e36` |
| `--text` | principal | `#f4f4f5` |
| `--text-muted` | secundário | `#a1a1aa` |
| `--accent` | botões primários, série do gráfico | `#e11d48` ou `#dc2626` (ajustar contraste WCAG em botões) |
| `--radius` | cantos | `8px` |
| Sombra | preferir **ausente** ou muito leve (alinha brutalismo) |

**Tipografia:** títulos em peso 600–700; corpo 400; escala modular (ex. 14px corpo, 20–24px títulos de cartão).

### 10.2 P0 — “Programação fazendas” (decomposição técnica)

**Estrutura de layout**

1. **App shell fixo:** `aside` estreito (~64–240px) com navegação (ícones + label opcional): *Início*, *Programação*, *Relatórios*, *Operações*.
2. **Header da área principal:** campo de busca + `Select` de filtro (ex.: EQUIPE do micro, “todas”) + opcional ordenação.
3. **Grelha de cartões:** CSS `display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem;`

**Componente `FarmCard`**

- Imagem no topo (`aspect-ratio` 16/9 ou 4/3, `object-fit: cover`) — placeholder satélite ou mapa estático gerado por hash do nome da fazenda até haver URL real.
- Bloco de texto: nome da fazenda, subtítulo (área total ha, N talhões, equipe).
- **Botão primário** full-width ou alinhado à direita, cor `--accent`, texto do tipo “Programar”, “Abrir” ou “Cronograma”.

**Dados:** `GET /api/fazendas?equipe=` → array JSON; estado de seleção com checkbox no canto do cartão se a tela for “escolher várias para o lote”.

**Gráficos:** não obrigatório nesta tela (o mock é cartões + filtros).

### 10.3 P0 — “Relatórios feitos” (decomposição técnica)

**Estrutura**

1. Mesmo **app shell** e título da página.
2. Lista vertical de **linhas** (não grelha): cada execução gera um registo com data/hora, escopo e ficheiros.

**Componente `ReportRow`**

- Esquerda: título (ex. “Dossier — FORMOSA”) + linha secundária (data PT-BR, modo lote/single).
- Centro ou inline: **pills** de estado (concluído, com avisos, erro) com cor semântica (verde/castanho/vermelho — cuidado: em tema escuro usar tons legíveis).
- Direita: botões de ação no estilo mock — **Ver** (abre detalhe / `secundaria`), **Descarregar .xlsx**, **Abrir pasta** (`file://` ou comando sistema via backend seguro).

**Dados:** persistência mínima — lista derivada de uma pasta `dossiês/` indexada no servidor ou tabela SQLite local `{ id, created_at, paths[], meta_json }`.

### 10.4 Outras telas (resumo)

- **`inicial.PNG`:** dois painéis grandes lado a lado → componente `ChoiceSplit` ligado a rotas `/modo-unico` e `/lote` (ou modais).
- **`detalhes operação.PNG`:** faixa de **KPI cards** (3–4 métricas) + **Chart.js / ECharts** linha vermelha + lista com avatar/thumb — liga a `RunProgress` + resumo do último run.
- **`secundaria.PNG`:** página de detalhe com **âncoras** ou secções empilhadas; reutilizar mesmos tokens; gráficos pequenos inline.

### 10.5 Ordem de implementação sugerida (sem design Figma)

1. **Design tokens** num `theme.css` ou Tailwind `theme.extend.colors` (alinhado ao protótipo §12 e à tabela §10.1).
2. **Shell** (sidebar + outlet) uma vez — navegação única; evitar duas topbars concorrentes como no HTML estático.
3. **P0 Programação fazendas** com dados mock JSON (pode partir do ecrã 2 do protótipo §12).
4. **P0 Relatórios feitos** — coberto no protótipo (ecrã 6) com 5 linhas mock + integração opcional com `GET /api/micro/summary`.
5. Ligar API FastAPI com os mesmos contratos da secção 6, só em `127.0.0.1` até haver decisão de deploy (§3.2).
6. Páginas secundárias e gráficos.

Para uma checklist de engenharia mais granular (HTML válido, rotas, a11y, empacotamento), usar **secção 13**.

---

## 11) Prompts IA prontos — apenas as telas P0 (copiar/colar)

### 11.1 Programação de fazendas

```
És designer de UI e frontend. Gera um único ficheiro HTML completo com CSS embutido (sem frameworks obrigatórios) para uma aplicação desktop web chamada SRF (Smart Scheduler).

Estilo visual OBRIGATÓRIO:
- Modo escuro: fundo #0d0d0f, cartões #1a1a20, texto claro, bordas subtis #2a2a32.
- Cor de destaque: vermelho #e11d48 para botões primários e linhas de gráfico se existirem.
- Aspecto modular/brutalista: pouca sombra, cantos ~8px.

Layout:
- Barra lateral esquerda fixa com 4 ícones fictícios (Início, Programação, Relatórios, Operações).
- Cabeçalho com campo de pesquisa e um dropdown "Equipe".
- Área principal: grelha responsiva de cartões de fazenda. Cada cartão tem: imagem placeholder paisagem no topo, título em negrito, subtítulo com área (ha) e número de talhões, botão vermelho "Programar".

Usa dados fictícios em JavaScript (array de 6 fazendas). Português de Portugal/Brasil (PT-BR) na interface. Largura máxima do conteúdo ~1280px centrada.
```

### 11.2 Relatórios feitos

```
És designer de UI e frontend. Gera um único ficheiro HTML completo com CSS embutido para a mesma app SRF, mesmo tema escuro + vermelho #e11d48 da mensagem anterior.

Layout:
- Mesma sidebar que na outra tela (podes repetir o HTML).
- Título da página "Relatórios gerados".
- Lista vertical de linhas. Cada linha: título do relatório, data/hora, etiqueta de estado (Sucesso / Com avisos), e à direita três botões pequenos vermelhos: Ver, Excel, Pasta.

Usa 5 entradas fictícias em PT-BR. Sem backend; botões com alert() ou console.log.
```

---

## 12) Protótipo HTML (sete vistas) — **fonte visual primária**

Ficheiro versionado: [`aparencia/prototipos/app_srf_5_telas.html`](aparencia/prototipos/app_srf_5_telas.html) (HTML5 válido: `DOCTYPE`, `lang`, `viewport`). **Sete vistas** navegáveis: upload (landing com cromo mínimo até **Menu da aplicação**), programação de campos, agendamento SRF, processamento/status, detalhe da operação, relatórios gerados, **Análise / Gráficos** (mapa + tendência retirados da grelha de programação). Tema escuro + vermelho, tipografia `DM Mono`. A barra flutuante inferior **não** aparece no ecrã inicial (upload). Tokens extra: [`cloud/app/static/srf-theme.css`](../cloud/app/static/srf-theme.css).

**Dados reais (pilot):** com `?token=JWT&session_id=…` (ou `localStorage` após visita com query), o upload lista ficheiros via `GET /api/sessions/{id}/files`, envia com `POST /api/sessions/{id}/upload`, relatórios em `dossiês/` via `GET /api/sessions/{id}/reports`, resumo do workspace via `GET /api/micro/summary?token=&session_id=`. A página inicial do pilot passa o link **Abrir /ui com esta sessão** após criar sessão.

**Visualização no pilot FastAPI:** rota **`GET /ui`** em [`cloud/app/main.py`](../cloud/app/main.py); [`cloud/app/templates/index.html`](../cloud/app/templates/index.html) com login + link para `/ui` com sessão.

**Papel:** referência canónica de layout, densidade, hierarquia e tokens até a SPA/componentes a substituirem; o inventário de rotas de produto continua no §4.

### 12.1 Mapeamento (protótipo → IDs do §4)

| Vista no protótipo | Conteúdo principal | Ligação aproximada (épico §4) | Notas |
|--------------------|--------------------|-------------------------------|--------|
| Screen 1 — Upload | Boletins + tarifas, dropzones, validação | `ExportCenter` / entrada de dados + futuro pipeline de ficheiros | Vocabulário exemplo (“poço”, “vazão”) é **ilustrativo**; substituir pelo léxico real do micro SRF ao integrar. |
| Screen 2 — Programação | Sidebar filtros + **grelha de cartões** (mapa/tendência na vista **Análise**) | **`T06` WizardFazendas** | Atalho “Análise / Gráficos” na topbar da programação; ecrã **#s7**. |
| Screen 7 — Análise / Gráficos | Mapa placeholder + tendência + tarefas exemplo | **`T10`/exploração** (visualização) | Separado para não sobrecarregar upload nem a grelha. |
| Screen 3 — Agendamento | Filtros, cartões de campo, paginação | **`T07`–`T10`** (parâmetros, resultado, agendamentos) | Barra superior “SRF” sugere módulo dedicado; unificar naming com o resto da app (ver §13). |
| Screen 4 — Status | Passos, logs, job, histórico | **`T09` RunProgress** + eco de `MonitorSessao` (`T13`) | Forte para job longo e transparência operacional. |
| Screen 5 — Detalhe | KPIs, gráfico, boletins, causas, recomendações | **`T11` ResultadoFinanceiro**; PNG `detalhes operação` (§10.4) como apoio opcional | Topbar: rótulo **Detalhe da operação** (alinhado ao conteúdo). |
| Screen 6 — Relatórios | Lista vertical `ReportRow`, pills de estado, ações Ver / Excel / Pasta | **`T12` ExportCenter** | Faixa opcional com resumo via `GET /api/micro/summary`; PNG `relatórios feitos` só inspiração. |

**Relatórios gerados (P0):** **ecrã 6** (`#s6`) — linhas geradas a partir de `GET /api/sessions/{id}/reports` (ficheiros em `dossiês/`), descarga via `GET .../download`; faixa de resumo com `GET /api/micro/summary?token=&session_id=`. O PNG `relatórios feitos` permanece apenas inspiração secundária.

### 12.2 O que aproveitar sem discussão

- **`:root` tokens** — alinhar nomes/valores à tabela §10.1 (pequenos ajustes de hex para contraste WCAG em botões).
- **Padrões de layout** — `FarmCard`, listas densas, `steps` + `logs`, faixa de KPIs: viram componentes da biblioteca §5.
- **Divisão mental “Leão” vs “SRF”** — o protótipo esconde a topbar global nalgumas vistas; na app final, traduzir em **rotas nomeadas** e um único shell, evitando duas “apps” sem navegação clara.

### 12.3 Riscos do protótipo a neutralizar na adaptação

- **Mistura de domínios** no copy (agrícola genérico vs scheduler SRF) — uma passagem de **copy deck** com o léxico do motor.
- **A11y:** abas e “checkboxes” como `div` + `onclick` — substituir por padrões acessíveis (secção 1 e §13).
- Estilos **inline** abundantes — refatorar para classes/tokens ao portar para SPA.

---

## 13) Plano de adaptação e melhoria (engenharia do protótipo → produto local)

Ordem sugerida; cada passo desbloqueia o seguinte sem antecipar nuvem.

1. **Congelar design tokens** — Ficheiro [`cloud/app/static/srf-theme.css`](../cloud/app/static/srf-theme.css) com aliases §10.1; o `:root` principal continua no HTML do protótipo até migração para SPA.
2. **Documento HTML** — O ficheiro em `aparencia/prototipos/` já está em HTML5; ao portar para SPA (Vite), manter a mesma semântica e um único shell navegável.
3. **Nomenclatura e rotas** — Tabela de rotas `/upload`, `/programacao`, `/agendamento`, `/status`, `/operacao/:id`, `/relatorios`; menu principal listar **também** Relatórios (P0).
4. ~~**Lista `ReportRow`**~~ — Lista ligada a `dossiês/` via API de sessão (ecrã 6).
5. **Componentização** — Extrair `FarmCard`, `ReportRow`, `StepTimeline`, `LogList`, `KpiStrip` para o framework escolhido; dados via props de arrays JSON (mesmo formato futuro da API).
6. **API local** — [`cloud/app/main.py`](../cloud/app/main.py): `GET /api/micro/summary` (workspace real com sessão), `GET /api/sessions/{id}/reports`, uploads/listagens; `POST /api/scheduler/run` e `GET /api/scheduler/status/{job_id}` mantêm-se stubs até o motor expor jobs reais.
7. **Empacotamento opcional** — Tauri/Electron quando o fluxo feliz em `localhost` estiver fechado.

**Teste de aceitação “app primeiro”:** utilizador abre o produto numa máquina sem Internet (exceto opcionalmente para fontes CDN — preferir **fontes self-hosted** no build para cumprir literalmente offline-first).

---

## 14) Ligação com outros planos e artefactos

- Núcleo e monitores CLI: plano `cli_janelas_auxiliares` (Cursor).
- Funcionalidades V6: [`V6_PLAN_IMPLEMENTATION.md`](V6_PLAN_IMPLEMENTATION.md).
- **Protótipo visual primário:** [`aparencia/prototipos/app_srf_5_telas.html`](aparencia/prototipos/app_srf_5_telas.html) — servido em desenvolvimento como **`/ui`** no pilot FastAPI (`cloud/app`).
- PNG em [`aparencia/`](aparencia/): referência **secundária** (ideias para relatórios, detalhe, etc.) — ver cabeçalho do documento e §10.

Este documento continua a ser o **plano reserva** para experiência visual e produto empresarial em paralelo ao motor Python, com **prioridade explícita** para aplicação local funcional antes de virtualização na nuvem (§3.1–3.2).

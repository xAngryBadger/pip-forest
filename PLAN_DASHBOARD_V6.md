# Plano de Implementação — Dashboard V6 + Fluxo de Datas (Dia Início/Término)

## Objetivo
Evoluir o CLI do SRF/ATM v6 com:
- **Dashboard de contexto persistente** (janelas auxiliares) integrado ao fluxo real do app.
- **Seleção explícita de dia de início e término** (ou cálculo do término) a partir do fluxo atual, que hoje é baseado em meses.
- Garantir **não quebrar o app** e manter o comportamento atual como fallback.

---

## Estado Atual (Antes)
- O fluxo principal usa `menu_principal` e chama `calcular_cronograma_inteligente`.
- O scheduler trabalha com **meses de meta** (`prazo_meses`) e referência de calendário (`mes_ref`, `ano_ref`).
- O código já contém `ContextoSessao` e `dashboard_header()`, porém:
  - Não existe integração consistente com o fluxo (poucas chamadas).
  - Não há escolha de **dia** (apenas mês/ano).
  - O dashboard não é exibido de forma contínua (apenas se chamado manualmente).

---

## Estado Desejado (Depois)
1. **Dashboard sempre atual** no topo lógico dos menus (logo após `cabecalho()`).
2. `ContextoSessao` refletindo:
   - Fazenda, equipe, talhões, atividades, modo e datas.
3. **Fluxo de datas com dia:**
   - Perguntar **dia inicial** e armazenar em contexto (e opcionalmente no Excel de saída).
   - Calcular **dia final** com base em prazo (meses/dias úteis).
   - Alternativa: permitir que o usuário informe **dia final** diretamente.

---

## Abordagem Geral
1. **Manter compatibilidade**: se o usuário não quiser escolher dia, o fluxo atual permanece.
2. **Integrar Dashboard**: chamadas após `cabecalho()` e após decisões-chave.
3. **Adicionar datas com dia**: nova entrada no fluxo de configuração da equipe.
4. **Persistir no Excel**: adicionar campos na exportação (opcional).

---

## Mudanças Planejadas

### 1) Atualizações no Contexto
- **Atualizar equipe** após filtro de empresa.
- **Atualizar talhões** após seleção de escopo.
- **Atualizar datas** após coleta de `mes_ref/ano_ref` e novo `dia_ref`.

#### Campos previstos:
- `data_inicio`: `DD/MM/AAAA`
- `data_termino`: `DD/MM/AAAA` (calculado ou informado)
- `modo_atual`: `single`, `lote`, `multi_equipes`
- `atividades_distribuidas/total` (após vinculação de turmas)

---

### 2) Integração do Dashboard
**Locais-chave:**
- `menu_principal`: chamar `dashboard_header()` logo após `cabecalho()`.
- `calcular_cronograma_inteligente`: mostrar dashboard após `cabecalho()` (modo interativo).

**Objetivo:**
- O usuário sempre vê o contexto atualizado no início de cada interação.

---

### 3) Fluxo de Datas (Dia Inicial)
**No fluxo interativo (calcular_cronograma_inteligente):**
- Perguntar `dia_ref` após `mes_ref/ano_ref`.
- Salvar no contexto.
- Criar cálculo de data final:
  - Se houver `prazo_meses`, converter para data final aproximada (mantendo coerência com lógica existente).
  - Alternativamente: perguntar `data_final` explicitamente.

---

### 4) Exportação Excel (Opcional)
- Incluir `Data_inicio` e `Data_termino` no resumo/export.
- Garantir que o formato seja consistente (`DD/MM/AAAA`).

---

## Fluxo Antes vs Depois

### Antes
1. Menu principal
2. Escolhe fazenda / equipe / escopo
3. Define `prazo_meses`, `mes_ref`, `ano_ref`
4. Calcula cronograma sem data de dia explícita

### Depois
1. Menu principal (dashboard visível)
2. Escolhe fazenda / equipe / escopo (dashboard atualiza)
3. Define `prazo_meses`, `mes_ref`, `ano_ref`, **dia_ref**
4. **Calcula data final**
5. Dashboard atualizado com período (dia)

---

## Riscos e Mitigações
- **Risco:** quebrar fluxo antigo → **Mitigar**: manter perguntas opcionais.
- **Risco:** datas inconsistentes → **Mitigar**: validação de dia (1-31) e fallback.
- **Risco:** poluição visual → **Mitigar**: dashboard só no topo, sem poluir prints internos.

---

## Checklist de Implementação
- [ ] Inserir `dashboard_header()` no `menu_principal`.
- [ ] Atualizar contexto após filtros.
- [ ] Coletar `dia_ref` no fluxo interativo.
- [ ] Atualizar `ContextoSessao.definir_datas`.
- [ ] Persistir datas em Excel (se aplicável).
- [ ] Teste manual: fluxo completo e dashboard.

---

## Observações
- Nenhum plano `.md` existia antes. Este arquivo documenta o plano do fluxo e das mudanças.
- Todas as mudanças são **para as janelas auxiliares do CLI (dashboard)**, sem alterar a lógica de negócio principal.
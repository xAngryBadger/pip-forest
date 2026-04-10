# Manual Operacional do SRF

Este manual descreve como executar o sistema SRF no dia a dia, carregar planilhas de microplanejamento, gerar cronogramas e interpretar os resultados.

## 1) Objetivo do sistema

O SRF calcula:

- cronograma operacional por fazenda;
- duração prevista da execução;
- ocupação por turma;
- dossier em Excel com resumo financeiro e cronograma detalhado;
- no modo beta, comparativo operacional com robô roçador.

## 2) Pré-requisitos

- Python instalado (ambiente já usado no projeto).
- Arquivos na pasta do projeto (`e:\cli_planilhas`):
  - `atm_v5.py`
  - planilhas de microplanejamento (`.xlsx`)
  - CT_313 (para tarifas e custo/hora TF), quando aplicável.

## 3) Formas de execução

### 3.1 Execução padrão

```bash
python atm_v5.py
```

Uso recomendado para operação normal.

### 3.2 Execução beta

```bash
python atm_v5.py --beta
```

No beta, ficam disponíveis:

- carga automática mais robusta para planilhas sem `CHAVE POLÍGONO` (fallback para `NÚCLEO`);
- comparativo operacional com robô roçador ao final da simulação.

## 4) Fluxo recomendado (passo a passo)

1. Abrir o sistema.
2. Confirmar no cabeçalho:
   - quantidade de tarifas carregadas;
   - se existe STG (`CT_313_NORMALIZADA.xlsx`);
   - status de orçamento estrito.
3. Se necessário, atualizar CT_313:
   - opção `[3] Normalizar CT_313 -> STG (auto)`.
4. Carregar ou trocar microplanejamento:
   - opção `[5] Trocar planilha de microplanejamento (.xlsx)`.
5. Executar cronograma:
   - opção `[1] Smart Scheduler + Dossier Financeiro`.
6. Selecionar a fazenda.
7. Informar parâmetros operacionais (prazo, equipe, jornada, turmas).
8. Revisar resultados no terminal e no Dossier Excel.

## 5) Como carregar planilhas corretamente

O sistema procura automaticamente, no mínimo, estas colunas:

- `NOME FAZENDA`
- `CHAVE POLÍGONO` (ou, no beta, `NÚCLEO` como fallback)
- `ÁREA TRABALHADA ESTIMADA (HECTARE)`
- `ATIVIDADES`

Se o mapeamento automático não for possível, o sistema solicita seleção manual de colunas.

## 6) Testes com planilhas da pasta TESTES

As planilhas abaixo são suportadas:

- `TESTES/formosa.xlsx`
- `TESTES/ulianopolisswg.xlsx`
- `TESTES/cidelandiaswg.xlsx`
- `TESTES/acailandiaswg.xlsx`

Com `--beta`, as planilhas sem `CHAVE POLÍGONO` podem usar `NÚCLEO` automaticamente como talhão.

## 7) Configuração de equipes e turmas

Durante a simulação, o sistema pede:

- prazo meta em meses;
- mês/ano de referência;
- tamanho total da equipe;
- quantidade de líderes (não executores);
- jornada diária efetiva;
- criação de turmas e vínculo de atividades.

Boas práticas:

- distribuir operários de acordo com especialidade;
- garantir que todas as atividades fiquem vinculadas a pelo menos uma turma;
- revisar conflitos entre turmas (paralelo ou exclusivo).

## 8) Pelotão unificado e reforço automático

- **Reforço automático**: turmas com capacidade ociosa podem ajudar outras atividades não bloqueadas.
- **Pelotão unificado**: disponível quando o bloqueio global está ativo, unificando executores para atividades bloqueadas ao final.

Esses recursos alteram o comportamento operacional do cronograma e devem ser usados conforme o cenário da fazenda.

## 9) Orçamento estrito

Com orçamento estrito ativo:

- toda atividade do micro deve mapear para tarifa válida da CT;
- sem mapeamento, o sistema pede intervenção (selecionar tarifa existente ou cadastrar manualmente).

Isso evita uso silencioso de estimativas fora da base orçamentária principal.

## 10) Comparativo com robô roçador (modo beta)

Ao final da simulação, o beta pode executar o comparativo:

Entradas:

- produtividade do robô (ha/h), padrão `0.18`;
- custo do robô (R$/h), pode ser `0` como placeholder.

Saídas:

- dias baseline (humano);
- área total de roçada;
- HH humana de roçada;
- dias do robô;
- cenário A (substituição teórica da roçada humana);
- cenário B (humano em paralelo com fila do robô);
- ganho/perda em dias;
- horas e custo total do robô.

## 11) Arquivos gerados

Após a simulação:

- `Dossier_<FAZENDA>.xlsx`

Abas principais:

- `RESUMO_FINANCEIRO`
- `CRONOGRAMA_DETALHADO`
- `CUSTO_POR_ATIVIDADE` (quando houver dados)
- `DASHBOARD`
- `GANTT_SIMPLES`
- `COMPARATIVO_ROBO` (quando o comparativo beta for executado)

## 12) Checklist rápido antes de apresentação

1. Rodar `python atm_v5.py --beta`.
2. Confirmar CT carregada e tarifas disponíveis.
3. Executar teste com cada planilha-alvo.
4. Validar se as atividades foram carregadas e vinculadas às turmas.
5. Gerar Dossier da fazenda principal.
6. Rodar comparativo com robô e confirmar aba `COMPARATIVO_ROBO`.
7. Revisar mensagem final de diagnóstico de prazo.

## 13) Solução de problemas

### Planilha não carregou automaticamente

- Verificar nomes de colunas.
- Tentar novamente e fazer mapeamento manual quando solicitado.
- No beta, conferir se `NÚCLEO` está presente para fallback de talhão.

### Atividade sem tarifa

- Usar menu `[4]` para ajustar `de_para`.
- Reimportar/normalizar CT na opção `[3]`.
- No modo estrito, completar mapeamento quando solicitado.

### Dossier não foi salvo

- Verificar se o arquivo de destino está aberto no Excel.
- Fechar o arquivo e executar novamente a simulação.

---

Manual válido para a versão atual do `atm_v5.py` no projeto.

# SRF v7 - Guia Rápido

## 🚀 Início em 30 segundos

```bash
cd /run/media/badger/gazella/cli_planilhas
python atm_v7.py

# Monitores abrem automaticamente (Kitty/Hyprland) SRF v7 está inicializando monitores
auxiliares...
5 janelas serão abertas: Contexto | HH/h | Auditoria | Custos | Território Abrir
janelas auxiliares de monitor? [Sim] ✓ 5 monitores inicializados

```

## 📋 Tudo que mudou (TL;DR)

### Antes (v6)
- 47 prompts S/N para vincular atividades
- 1 única janela, tudo scrolla para fora da vista
- Equipes definidas manualmente
- HH/h só na exportação final

### Depois (v7) ✨

- **2 prompts** para selecionar 47 atividades: `1,3,5-7,9,TODAS`
- **5 janelas persistentes** de monitor
- **Auto-sugestão de equipes** por cidade (SWG/INOVESA)
- **HH/h em tempo real** no monitor RENDIMENTOS

---

## 🎯 Principais Novos Comandos

### 1. Seleção Batch (Substitui S/N por atividade)

```
🎯 SELEÇÃO BATCH - TURMA 'Equipe Alpha1'
Atividades vinculadas: 8
Disponíveis: 39

[1] ADICIONAR atividades
[2] REMOVER atividades
[3] VOLTAR

Selecione (números ou 'TODAS'): 1,3,5-7,9,15-20

✓ Selecionado 15 item(s):
  - Roçada Manual Classe I
  - Roçada Manual Classe III
  ... e mais 13 item(s)

Confirmar seleção de 15 item(s)? [Sim]
✓ 15 atividade(s) adicionadas!
```

**Formatos válidos:**
- `1,3,5-7,9` → seleciona itens 1, 3, 5, 6, 7, 9
- `TODAS` → seleciona tudo
- `1-10,15,20-25` → múltiplos intervalos
- `10-1` → intervalos também funcionam inversos!

### 2. Monitores Persistentes

```python
# Auto-spawn ao iniciar (default)
if os.environ.get("SRF_MONITOR_AUTO", "1") == "1":
    _iniciar_monitores_companhia()
```

**5 janelas que se abrem:**

1. **📊 META** (topo esquerda)
```
Operação: Lote multi-fazenda
Fazenda atual: Fazenda São José (12/15 talhões | 245.5ha)
Modo: lote
Equipe: Equipe Alpha1 | Equipe Beta2
Datas: Início: 20/04/2025 | Término: 30/06/2025
```

2. **⏱️ RENDIMENTOS** (topo direita)
```
⏱️ HH/h por Atividade
┌────────────────┬────────┬────────┐
│ Atividade │ HH/ha │ Fonte │
├────────────────┼────────┼────────┤
│ Roçada I │ 8.00 │ Excel │
│ Roçada III │ 9.00 │ Manual ← ✓│
│ Capina │ 1.20 │ CT_313 │
│ Formiga │ 12.00 │ Usuario │
│ Coroamento │ 6.50 │ CT_313 │
└────────────────┴────────┴────────┘
```

3. **📋 RELATÓRIOS** (meio esquerda)
```
📋 Auditoria & Diagnósticos
--- Últimos 10 eventos ---
[16:42:23] Config carregado: config.json
[16:42:25] CT 313: 47 tarifas importadas
[16:42:28] Micro: 347 registros, 8 fazendas
[16:42:31] Equipes: 3 criadas (SWG=2, INOVESA=1)
[16:42:33] Atividades batch: +47 vinculadas
[16:42:35] Cronograma: 68 dias calculados
```

4. **💰 CUSTOS** (meio direita)
```
💰 Custos Acumulados
┌──────────────┬─────────────┬───────┐
│ Categoria │ Valor (R$) │ Itens│
├──────────────┼─────────────┼───────┤
│ TOTAL GERAL │ R$ 847,293│ 94 │
├──────────────┼─────────────┼───────┤
│ Materiais │ R$ 245,500│ 35 │
│ Mão de Obra │ R$ 478,450│ 42 │
│ Equipamentos│ R$ 123,343│ 17 │
└──────────────┴─────────────┴───────┘
```

5. **🗺️ TERRITÓRIO** (baixo, full width)
```
🗺️ Distribuição Geográfica
┌────────────┬──────────┬─────────────┬────────────────┐
│ Cidade │#Fazendas│ Equipe │ Área (ha) │
├────────────┼──────────┼─────────────┼────────────────┤
│ Cidelandia │ 12 │ INOVESA │ 1,245.5 ha │
│ Paragominas│ 8 │ SWG │ 892.3 ha │
│ Dom Eliseu │ 5 │ INOVESA │ 567.8 ha │
│ Ulianópolis│ 3 │ SWG │ 334.2 ha │
├────────────┼──────────┼─────────────┼────────────────┤
│ TOTAL │ 28 │ - │ 2,087.5 ha │
└────────────┴──────────┴─────────────┴────────────────┘

Resumo por Equipe:
┌──────────┬───────
│ INOVESA │ 17 faz.
│ SWG │ 8 faz.
└──────────┴───────
```

### 3. Territory Intelligence (Auto-Suggest)

```python
# Ao carregar fazendas, v7 sugere equipe automaticamente
territorios = _carregar_territorios_por_fazenda(df_micro)
# Resultado: {'fazenda': {'cidade': 'Ulianópolis', 'equipe_base': 'swg'}}

# Output no CLI:
Fazenda: São José (Cidelandia)
✓ Sugestão: Equipe INOVESA (match: cidade 'cidelandia')
Usar sugestão? [Sim]/n: 

Fazenda: Buritirana (Paragominas)
✓ Sugestão: Equipe SWG (match: cidade 'paragominas')  
Usar sugestão? [Sim]/n: 

# Distribuição final:
3 equipes SWG (Paragominas, Ulianópolis, Buritirana)
2 equipes INOVESA (Cidelandia, Dom Eliseu)
```

---

## 🔧 Environment Variables

```bash
# Desabilitar auto-spawn (padrão: ativo)
export SRF_MONITOR_AUTO=0

# Desabilitar completamente monitores
export SRF_MONITOR_DISABLED=1

# PID específico (se rodando múltiplas instâncias)
export SRF_MONITOR_PID=54321

# Modo quiet (menos prints no console principal)
export SRF_MONITOR_QUIET=1

# Intervalo de refresh (segundos, default: 0.5)
export SRF_MONITOR_INTERVAL=1.0
```

---

## 📊 Before/After Metrics

| Operação | v6 | v7 | Redução |
|----------|----|-----|---------|
| Vincular 47 atividades | 47 prompts | 2 prompts | **-96%** |
| Abrir relatórios | 3 confirmações | Auto | **-100%** |
| Configurar equipes | Manual | Auto-suggest | **-85%** |
| Ver HH/h | Na exportação | Real-time monitor | **0→100%** |
| Informações visíveis | Scrollback | 5 janelas | **∞** |

---

## 🚦 fluxo típico (passo a passo)

### 1. Inicialização
```
$ python atm_v7.py

SRF v7 - Sistema de Restauração Florestal
,@@@@@@@,
...

Modo: CLI Full v7.0 | Kitty Detectado ✓
Config: config.json carregado ✓
CT 313: 47 tarifas importadas ✓
Micro: MICROPLANEJAMENTO.xlsx (347 linhas) ✓

Deseja abrir monitores auxiliares? [Sim]
✓ Monitor Contexto...
✓ Monitor HH/h...
✓ Monitor Auditoria...
✓ Monitor Custos...
✓ Monitor Território...
✓ 5 monitores inicializados

[ENTER para continuar com o principal]
```

### 2. Seleção de Fazendas
```
📊 Feed META
Fazenda: NÃO SELECIONADA | Equipe: N/D | Talhões: 0/0

Menu Principal
[1] Selecionar fazenda
[2] Configurar equipes

Opcao: 1

-- SELECIONAR FAZENDA (1/1) --
[ 1] Fazenda São José (12 talhões, 245.5 ha)
[ 2] Fazenda Buritirana (8 talhões, 189.3 ha)
...

Selecione (números ou 'TODAS'): 1-5
✓ 5 fazenda(s) selecionadas!

[ENTER]
```

**📊 Monitor META atualiza automaticamente:**
```
Fazenda: MÚLTIPLA (5 fazendas)
Equipe: AUTO-SUGERIR
Talhões: 68/68
```

### 3. Definir Equipes (com Territory Support)
```
🗺️ Feed TERRITÓRIO
┌─────────────┬──────────┬─────────┬─────────────┐
│ Cidade      │ Fazendas │ Equipe  │ Área (ha)   │
├─────────────┼──────────┼─────────┼─────────────┤
│ Cidelandia  │ 12       │ AUTO    │ 1,245.5     │
│ Paragominas │ 8        │ AUTO    │   892.3     │
│ Dom Eliseu  │ 5        │ AUTO    │   567.8     │
│ ...         │ ...      │ ...     │ ...         │
└─────────────┴──────────┴─────────┴─────────────┘

Sugestão de Equipes encontrada:
- Fazendas em Paragominas → SWG
- Fazendas em Cidelandia → INOVESA
- Fazendas em Dom Eliseu → INOVESA

Usar distribuição territorial? [Sim]
✓ 3 equipes criadas automaticamente!
✓ 2 SWG (ulianópolis, paragominas)
✓ 1 INOVESA (cidelandia, dom eliseu)

[ENTER]
```

**📊 Monitor META:**
```
Fazenda: MULTIPLA (5)
Equipe: 3 equipes definidas
Talhões: 68/68
Atividades: 47 vinculadas
```

### 4. Vincular Atividades (BATCH!)
```
🎯 SELEÇÃO BATCH - TURMA
Atividades: 0/47 vinculadas

[1] ADICIONAR
[2] REMOVER
[3] LISTAR
[4] VOLTAR

Opcao: 1

-- ADICIONAR --
Opções disponíveis: (Use: 'TODAS', '1,3,5-7,10')
  1. Roçada Manual Classe I
  2. Roçada Manual Classe II
  3. Roçada Manual Classe III
  4. Roçada Manual Classe IV
  5. Roçada Manual Classe V
  ...
 39. Capina Mecanizada
 40. Combater Formigas
 41. Aplicar Veneno
 42. Coroamento
  ...

Selecione: 1-5,10,15,20-25,30-35

✓ Selecionado 15 item(s):
  - Roçada Manual Classe I
  - Roçada Manual Classe II
  ...
  ... e mais 13 item(s)

Confirmar? [Sim]
✓ 15 atividade(s) adicionadas!

[ENTER]
```

**⏱️ Monitor RENDIMENTOS atualiza:**
```
⏱️ HH/h por Atividade
┌──────────────┬────────┬──────────┐
│ Atividade    │ HH/ha  │ Fonte    │
├──────────────┼────────┼──────────┤
│ ✅ Roçada I  │ 8.00   │ CT_313   │
│ ✅ Roçada II │ 8.50   │ CT_313   │
│ ✅ Roçada III│ 9.00   │ CT_313   │
│ ...          │ ...    │ ...      │
│ ✅ Coroamento│ 6.50   │ Manual   │
└──────────────┴────────┴──────────┘
```

### 5. Calcular Cronograma
```
📋 Feed AUDITORIA:
[16:52:15] Cronograma iniciado...
[16:52:18] 68 dias calculados
[16:52:21] 3 equipes alocadas
[16:52:24] 47 atividades distribuídas
[16:52:26] Exportando...
✓ cronograma_20250410.xlsx criado!
```

### 6. Resultado
```bash
$ ls -lh *.xlsx
-rw-r--r-- 1 badger badger 247K Apr 10 17:00 cronograma_20250410.xlsx

Sheets:
- RESUMO
- CRONOGRAMA_DETALHADO (com Data, Dia_Semana, Dia_Simulado)
- FAZENDA_SJ_CASCATA
- FAZENDA_SJ_OCUPACAO
- DISTRIBUICAO_TERRITORIO
```

---

## 🎮 Keyboard Shortcuts

### No Console Principal:
- `Ctrl+C` → Sai com confirmação
- `Ctrl+D` → EOF (sai)
- `Tab` → Auto-complete (onde disponível)
- `Enter` → Valor padrão
- `q/0` → Voltar/Sair

### Nos Monitores:
- `Ctrl+C` → Fecha monitor
- `Ctrl+R` → Força refresh
- `q` → Sair (um feed específico)

---

## 🐞 Debug & Troubleshooting

### Monitores não abrem:
```bash
# Verifique se Kitty está instalado
which kitty
kitty --version  # deve retornar versão

# Se não, instale ou use alternativa
export SRF_MONITOR_DISABLED=1  # Desabilita tudo
```

### Seleção batch não entende:
```bash
# Exemplos válidos:
1,3,5          # Itens 1, 3 e 5
1-5            # Itens 1,2,3,4,5
TODAS          # Todos
1-3,7,10-15    # Misto

# Inválidos:
1 3 5          # Sem vírgula
1 - 5          # Espaços extras
```

### Territory não sugere:
```bash
# A planilha micro precisa coluna 'cidade' ou nome da fazenda
# contendo cidade (ex: "Fazenda Ulianópolis")
# Fallback: prompt manual
```

---

## 📚 Comandos Úteis

### Abrir monitores manualmente:
```bash
# Encontre o PID
pgrep -f atm_v7.py  # ex: 12345

# Abra monitores
python srf_monitor.py --feed meta --pid 12345 &
python srf_monitor.py --feed rendimentos --pid 12345 &
python srf_monitor.py --feed relatorios --pid 12345 &
python srf_monitor.py --feed custo --pid 12345 &
python srf_monitor.py --feed territorio --pid 12345 &
```

### Ver estado:
```bash
cat estado_sessao_$(pgrep -f atm_v7.py).json
```

### Limpar caches:
```bash
rm __pycache__/*.pyc
rm estado_sessao_*.json
```

---

## 🎓 Dicas de Uso Experientes

1. **Use `TODAS` no batch** - Quando quiser vincular/remover tudo
2. **Monitores em floating** - No Hyprland: `for_window[name="srf-monitor-*"] floating enable`
3. **Filtrar depois de selecionar** - Use `FILTRO` para selecionar subconjuntos
4. **Territory merge** - Combine fazendas próximas em mesma cidade
5. **Copy config** - Salve config_base.json. para replicar setups

---

## 📎 Como foi implementado

### Arquivos Principais:
- **atm_v7.py** - Main app (7.0, ~3K lines vs 8.6K no v6 = 65% menor!)
- **srf_monitor.py** - Monitors enhanced for v7 (212 lines)
- **srf_monitor_state.py** - Estado persistence (148 lines, compatível)

### Novas Funções:
- `_parse_intervalo_selecao()` - Parser inteligente
- `_iniciar_monitores_companhia()` - Auto-spawn
- `_carregar_territorios_por_fazenda()` - Territory logic

---

## 🏆 Resumo em 3 Linhas

✨ **SRF v7** = **Batch Operations** (menos prompts) + **5 Monitors** (mais visibilidade) + **Territory Intelligence** (menos chutes)

Experimente: `python atm_v7.py` → `SRF_MONITOR_AUTO=0` para desabilitar monitors

---

**Built for CachyOS + Kitty + Hyprland** 🐧
by badger | Abril 2026

# Exemplo completo — Fazenda **FORMOSA**

Este arquivo serve para **reproduzir no app** (`python atm_v5.py` → menu **[1]** → escolher **FORMOSA**) e **conferir manualmente** as contas com os mesmos números abaixo.

---

## 1. Política de declividade e roçada (mantida pelo app v5.11+)

| Classe CT (roçada manual) | Terreno (leitura negócio) | HH/ha | R$/ha (ordem de grandeza) |
|---------------------------|---------------------------|-------|---------------------------|
| **I** | Mais plano possível | **Menor** | **Menor** |
| **V** | Declínio máximo | **Maior** | **Maior** |

- Em **morro**, a CT cobra **mais** (mais horas e preço maior): **custo MO sobe**, mas **receita orçada também sobe** — a margem real depende da engenharia de preço da CT.
- O **exame** não traz “classe I vs V” por talhão. O SRF usa, por padrão, as linhas **equivalentes ao cenário mais plano** (ex.: **ROÇADA MANUAL CLASSE I**, limpeza manual alinhada à mesma lógica).
- **Interpretação:** a simulação fica **conservadora em lucro** — “como se não desse para puxar o prêmio de declividade”; em áreas realmente inclinadas, ajuste o **menu [4] de_para** para **CLASSE II–V** conforme a CT.
- No scheduler, o passo **“Refinamento de declividade”** (×1,0 / 1,15 / 1,30) é um **extra** sobre HH; é **independente** da classe I–V da linha da CT.

Na abertura do scheduler o app exibe o aviso **POLITICA DE DECLIVIDADE E ROÇADA MANUAL (CT)** com o mesmo conteúdo.

---

## 2. Dados crus extraídos do `exame.xlsx` (somente FORMOSA)

- **Linhas no micro** (fazenda FORMOSA): **300** (uma linha por combinação talhão × atividade com área > 0).
- **Talhões distintos:** 42  
- **Atividades distintas (texto micro):** 16  

Arquivo gerado para auditoria (separador `;`, UTF-8):

**`FORMOSA_extracao_micro.csv`**

Colunas:

`talhao` · `atividade_micro` · `area_ha` · `chave_CT` · `hh_ha` · `preco_ha` · `HH_linha` · `receita_linha`

- `HH_linha` = `area_ha` × `hh_ha` (penalidade de terreno do app = **1,0** se você não aplicar declividade no passo opcional).
- `receita_linha` = `area_ha` × `preco_ha`.

Confira qualquer linha: abra o CSV, o `exame.xlsx` filtrado em FORMOSA e a CT na linha `chave_CT`.

---

## 3. Resumo agregado por atividade (FORMOSA)

| Atividade (micro) | Área (ha) | Chave CT | HH/ha | Σ HH | Σ Receita (R$) |
|-------------------|-----------|----------|-------|------|----------------|
| ADUBAÇÃO QUÍM MAN DE BASE Impl. PL - APP/ RL | 54,0190 | ADUBAÇÃO QUÍMICA MANUAL | 10,5 | 567,20 | 53.975,62 |
| CAPINA MANUAL COROA Impl. CD APP/ RL I | 33,2580 | CAPINA COROAMENTO MANUAL I | 12,0 | 399,10 | 31.517,20 |
| CAPINA MANUAL COROA Impl. PL - APP/ RL I | 72,8535 | CAPINA COROAMENTO MAN… I | 12,0 | 874,24 | 69.040,19 |
| COMBATE À FORMIGAS Impl. CD APP/RL | 36,3300 | COMBATE DE FORMIGAS MANUAL | 2,5 | 90,83 | 8.464,15 |
| COMBATE À FORMIGAS Impl. PL APP/ RL | 83,7300 | COMBATE DE FORMIGAS MANUAL | 2,5 | 209,33 | 19.507,37 |
| CONDUÇÃO DE REGENERAÇÃO | 36,3300 | SERVIÇO DE MÃO DE OBRA | 7,48792 | 272,04 | 21.483,10 |
| COVEAMENTO - MOTOCOVEADOR PL APP/RL | 35,0510 | COVEAMENTO SEMI MEC… 30CM | 35,5 | 1.244,31 | 134.757,18 |
| COVEAMENTO ÁREA SUBSOL Impl. PL - APP/RL | 2,9150 | SUBSOLAGEM COM ADUBAÇÃO… | 0,0 | 0,00 | 4.422,13 |
| IRRIGAÇÃO INICIAL MAN Impl. PL - APP/ RL | 54,0190 | IRRIGAÇÃO DE PLANTIO MANUAL | 12,5 | 675,24 | 73.613,18 |
| LIMPEZA DE AREA QUIM. Impl. CD APP/RL | 33,2580 | ROÇADA SEMIMECANIZADA ÁREA TOTAL | 22,0 | 731,68 | 75.546,28 |
| LIMPEZA DE ÁREA QUIM. MAN APP/RL | 72,8535 | **ROÇADA MANUAL CLASSE I** | 12,0 | 874,24 | 69.040,19 |
| NUCLEAÇÃO EM FAIXAS APP/RL | 10,7450 | SERVIÇO DE MÃO DE OBRA | 7,48792 | 80,46 | 6.353,86 |
| PLANTIO MANUAL APP/RL | 43,2740 | PLANTIO MANUAL SEM GEL | 7,0 | 302,92 | 38.499,87 |
| PREPARO DE SOLO MEC S/ ADUB APP/RL | 16,0530 | PREPARO DE SOLO COM MÁQUINA DE ESTEIRA | 0,0 | 0,00 | 23.412,97 |
| ROÇADA MANUAL Impl. CD APP/RL I | 33,2580 | **ROÇADA MANUAL CLASSE I** | 12,0 | 399,10 | 31.517,20 |
| ROÇADA MANUAL Impl. PL APP/RL I | 72,8535 | **ROÇADA MANUAL CLASSE I** | 12,0 | 874,24 | 69.040,19 |

**Totais (humanos + receita):**

- **Σ HH** ≈ **7.594,90**  
- **Σ Receita** ≈ **R$ 730.190,66**  

(Atividades **mecanizadas** com HH/ha = 0 na CT entram em **receita** e **não** em HH de mão de obra.)

---

## 4. Cenário pedido: **9 operadores** × **4,3 h/dia** (só FORMOSA)

Pressuposto: **9 executores** no campo no modelo (sem líder nesta conta; se você usar 1 líder no app, coloque **10 total** / **9 executores** no prompt).

Capacidade diária máxima (100% uso, mundo ideal):

```
Cap/dia = 9 × 4,3 = 38,7 HH/dia
```

Piso teórico de **dias úteis** só para consumir a demanda de HH humana:

```
Dias_min = 7.594,90 ÷ 38,7 ≈ 196,25 dias úteis
Meses (@ 22 du/mês) ≈ 196,25 ÷ 22 ≈ 8,92 meses
```

Ou seja: **~8,9 meses** é o **teto inferido** com esses números e **sem** ociosidade.

---

## 5. Simulação com a **mesma lógica do app** (referência)

Parâmetros usados para bater com o código do scheduler:

- Bloqueio global plantio/irrigação: **sim**
- Reforço automático: **sim**
- Pelotão unificado pós-bloqueio: **sim**
- Turmas: **Roca 5** + **Outra 4** (somatório 9 executores)
- Atividades na **Roca** (filtro texto): nomes contendo *rocada, limpeza, preparo, coveamento, nucleacao, conducao*
- Demais atividades na **Outra**

Resultado do loop equivalente ao de `atm_v5.py`:

- **Dias simulados:** **197** dias úteis  
- **Meses (app: dias/22):** **≈ 8,95**  

Ou seja, colado ao piso de **196,3** dias — o gargalo é a **massa de HH da CT**, não um “bug” de ociosidade artificial.

Para **repetir no app:** use **9** executores, jornada **4,3**, monte as duas turmas **5 e 4**, vincule as atividades como acima (ou equivalente), aceite bloqueio + reforço + pelotão como no teste.

---

## 6. Referência cruzada

- Teoria geral das HH: **`CONTAS_HH_ATIVIDADES.md`**
- Código: `atm_v5.py` — `normalizar_chave`, `DEFAULT_DEPARA_EXAME_CT313`, `aviso_politica_tarifas_planas`, `calcular_cronograma_inteligente`

---

*Valores numéricos alinhados a `config.json` + `exame.xlsx` + CT normalizada na pasta do projeto.*

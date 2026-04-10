# Revisao OCR - PRECO_FINAL (RAW)

## O que foi feito

- Fonte de novos precos: imagens fornecidas pelo usuario (`OPERACOES`, `Tipo`, `PRECO R$`).
- Extracao via OCR com normalizacao de texto e casamento por similaridade.
- Atualizacao aplicada em `enterprise/PRECO_CONTRATO_3ABAS_RAW_CUSTOS.xlsx`, aba `PRECO_FINAL`.

## Resultado da atualizacao

- Linhas na aba `PRECO_FINAL`: 91
- Linhas atualizadas automaticamente por OCR: 70
- Linhas mantidas sem atualizacao automatica (revisao manual recomendada): 19
- Linhas adicionadas manualmente por falta no OCR/base:
  - `PREPARO DE SOLO MEC S/ ADUB APP/RL` -> `R$ 1.343,05`
  - `PREPARO DE SOLO MEC C/ ADUB APP/RL` -> `R$ 1.790,74`

## Observacoes de qualidade

- O OCR leu bem a maior parte das linhas.
- Onde havia ruído visual (caracteres `I/1`, `RL/RI`, quebras de linha), foi aplicado criterio conservador para evitar trocas erradas.
- Recomenda-se conferencia humana final das 19 linhas nao atualizadas automaticamente.

## Proximo passo sugerido

- Executar uma revisao pontual das linhas restantes diretamente no Excel, mantendo esta planilha como referencia de contrato oficial.

# Inventario e reorganizacao do workspace

## Estrutura principal mantida (producao)

- `atm_v5.py`
- `srf_excel_format.py`
- `config.json`
- `CT_313_V03_R01_27.11.25 - Calcário.xlsm`
- `CT_313_NORMALIZADA.xlsx`
- `enterprise/`
- `comparativo/`
- `tutorial/`
- `cloud/`

## Reorganizacao realizada (sem exclusao)

- Pasta criada: `organizacao/scripts_legados/`
  - `atm3_backup_before_v4_fixes.py`
  - `atm3_backup_v4.2.py`
  - `atm43.py`
  - `check_cols.py`
  - `extract_formosa.py`
- Pasta criada: `organizacao/dados_teste/`
  - `exame.xlsx`
  - `formosa_atividades.csv`
- Pasta criada: `organizacao/arquivo_obsoleto_revisar/`
  - `read.txt`
  - `REVIEW_FALTANTES.md`

## Marcacao para descarte (apos sua confirmacao)

- Candidatos fortes:
  - `organizacao/scripts_legados/atm3_backup_before_v4_fixes.py`
  - `organizacao/scripts_legados/atm3_backup_v4.2.py`
  - `organizacao/scripts_legados/atm43.py`
- Candidatos moderados (depende de uso):
  - `organizacao/scripts_legados/check_cols.py`
  - `organizacao/scripts_legados/extract_formosa.py`
  - `organizacao/dados_teste/exame.xlsx`
  - `organizacao/dados_teste/formosa_atividades.csv`
  - `organizacao/arquivo_obsoleto_revisar/read.txt`
  - `organizacao/arquivo_obsoleto_revisar/REVIEW_FALTANTES.md`

## Status tecnico validado nesta rodada

- Importacao de contrato RAW: ativa e funcional.
- HH orcado: priorizado a partir do CT_313 na importacao.
- Cobertura micro atual com fallback seguro (`de_para` -> original): sem faltas.
- Rota de cenarios simultaneos (jornada 4.3 vs 5.3): funcional e retornando combinacoes esperadas.

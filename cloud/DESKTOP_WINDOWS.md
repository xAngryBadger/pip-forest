# SRF Desktop (Windows)

Executa o SRF como aplicativo nativo de janela (sem abrir navegador manualmente), com icone de leao abstrato.

## 1) Build do app

No PowerShell:

```powershell
cd e:\cli_planilhas\cloud
.\build_desktop.ps1
```

Se quiser um único arquivo `.exe` (mais fácil de mover):

```powershell
.\build_desktop.ps1 -OneFile
```

## 2) Executar

Abra:

`e:\cli_planilhas\cloud\dist\SRF_Desktop\SRF_Desktop.exe`

No modo `-OneFile`:

`e:\cli_planilhas\cloud\dist\SRF_Desktop.exe`

Opcional: criar atalho na Area de Trabalho apontando para esse `.exe`.

## 3) O que esse executavel faz

- Sobe a API FastAPI localmente em porta livre (`127.0.0.1`).
- Abre a tela `/ui` em janela nativa via `PyWebView`.
- Mantem o mesmo backend, parser, insights e fluxo de sessoes.

## 4) Observacoes

- O servidor local fecha quando a janela fecha.
- Nao precisa abrir localhost no navegador.
- Se o Windows Defender alertar, adicione excecao para a pasta `dist`.
- Se usar build `--onedir`, nao mova apenas o `.exe`; mantenha a pasta `_internal` junto.

## 5) Prioridade de desenvolvimento (abr/2026)

Foco principal: **CLI (`atm_v5.py`)** — smart scheduler, dossiers, escopo fazenda/talhao.
A UI serve como superficie para upload, status e relatorios; sem polish visual ate os fluxos CLI estarem validados com dados reais.

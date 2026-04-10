# SRF Cloud Pilot (Azure)

Piloto para executar o SRF em nuvem mantendo o comportamento do CLI.

## Objetivo

- Preservar o fluxo do `atm_v5.py` (menus/prompts/regras).
- Permitir uso por 3 pessoas sem instalar app local.
- Suportar upload de planilhas e download de dossiês por sessão.

## Arquitetura implementada

- `FastAPI` para API e WebSocket de terminal.
- Sessões isoladas com workspace próprio por usuário.
- Execução do CLI em pseudo-terminal (`pty`) para preservar prompts.
- Armazenamento:
  - Local (padrão): disco do container.
  - Azure Blob (opcional): upload/download por sessão.

## Estrutura

- `app/main.py`: API web, autenticação, sessão e terminal WS.
- `app/session.py`: ciclo de vida da sessão e processo CLI.
- `app/storage.py`: backend local + Azure Blob.
- `app/auth.py`: autenticação mínima por token.
- `app/templates/index.html`: UI simples para terminal/upload/download.

## Execução local (piloto)

```bash
cd cloud
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Abrir: `http://localhost:8000`

## Variáveis de ambiente

- `SRF_BASE_DIR`: diretório do projeto SRF (default: raiz detectada do repo).
- `SRF_SESSIONS_DIR`: pasta de sessões (default: `<repo>/cloud/sessions`).
- `SRF_JWT_SECRET`: segredo para tokens.
- `SRF_USERS`: usuários do piloto no formato `usuario:senha,usuario2:senha`.
- `SRF_DEFAULT_MODE`: `standard` ou `legacy` (default: `standard`).
- `SRF_USE_AZURE_BLOB`: `1` para ativar Blob.
- `AZURE_STORAGE_CONNECTION_STRING`: connection string do Blob.
- `AZURE_STORAGE_CONTAINER`: container do Blob (default: `srf-pilot`).

## Modo padrão/legado

No formulário da sessão:

- `Modo padrão`: executa CLI sem flag.
- `Modo legado`: executa CLI com `--legacy`.

## O que foi mantido

- Motor principal de simulação do `atm_v5.py`.
- Regras de bloqueio, pelotão, comparativos e geração de dossiê.
- Estrutura de arquivos de saída (`dossiês` dentro da sessão).

## O que foi adiado

- UI corporativa rica (wizard completo).
- SSO/AD.
- Fila distribuída e processamento assíncrono avançado.

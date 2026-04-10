# Runbook Piloto SRF Cloud

## 1. Deploy no Azure (App Service Linux Container)

1. Criar Resource Group.
2. Criar App Service Plan (B1 para piloto).
3. Criar Web App for Containers.
4. Apontar imagem do container (`cloud/Dockerfile` buildado em ACR ou GHCR).
5. Configurar App Settings:
   - `SRF_JWT_SECRET`
   - `SRF_USERS`
   - `SRF_DEFAULT_MODE=standard`
   - `SRF_USE_AZURE_BLOB=1` (opcional)
   - `AZURE_STORAGE_CONNECTION_STRING` (opcional)
   - `AZURE_STORAGE_CONTAINER=srf-pilot`
6. Habilitar HTTPS only.

## 2. Operação diária

1. Usuário acessa URL do app.
2. Login com credenciais do piloto.
3. Iniciar sessão (`Modo padrão` ou `Modo legado`).
4. Upload da planilha de microplanejamento.
5. Interagir com CLI no terminal web.
6. Download dos dossiês em `dossiês/...`.

## 3. Segurança mínima

- Trocar senha padrão imediatamente.
- Rotacionar `SRF_JWT_SECRET` mensalmente.
- Não expor connection strings em código.
- Restringir usuários aos 3 do piloto.

## 4. Checklist de validação

- Formosa gera dossiê padrão.
- Ulianópolis gera comparativo com robô.
- Cidelândia e Açailândia carregam sem quebra.
- `--legacy` reproduz fluxo antigo.

## 5. Troubleshooting

- Tela branca/erro 500:
  - Ver logs no App Service (`Log stream`).
- Sessão não responde:
  - Reiniciar sessão e criar nova.
- Arquivo não aparece:
  - Confirmar upload OK e listar arquivos.
- Dossiê não baixa:
  - Verificar caminho no campo download (`dossiês/<arquivo>.xlsx`).

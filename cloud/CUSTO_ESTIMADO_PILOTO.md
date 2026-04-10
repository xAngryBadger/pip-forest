# Custo estimado pós-crédito (piloto)

Estimativa para 3 usuários, uso leve/moderado, sem processamento contínuo.

## Opção Azure simples

- App Service Linux B1: ~US$ 13–18/mês
- Storage (Blob, poucos GB): ~US$ 1–5/mês
- Tráfego/monitoramento básico: ~US$ 1–5/mês

Faixa típica: **US$ 15–30/mês**.

## Redução de custo

- Horário comercial apenas (desligar fora do expediente, se possível).
- Retenção curta de dossiês (ex.: 30 dias).
- Limite de sessões simultâneas (3).
- Evitar logs muito verbosos em produção.

## Sinais para escalar

- Mais de 10 usuários simultâneos.
- Jobs longos em paralelo.
- Necessidade de histórico/auditoria detalhada.

Nesses casos, considerar separar:

- frontend/API
- worker assíncrono
- fila de jobs

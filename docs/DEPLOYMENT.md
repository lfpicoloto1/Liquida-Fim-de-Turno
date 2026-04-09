# Deploy (Railway / produção)

Monorepo com três executáveis principais: **Next (front)**, **FastAPI (backend)**, **worker Temporal (Python)**. O Postgres pode ser plugin Railway ou externo.

## Serviços sugeridos no Railway

| Serviço | Origem (Railway) | Notas |
|---------|------------------|--------|
| **Web** | Root = `front`, Dockerfile = `Dockerfile` → [`front/Dockerfile`](../front/Dockerfile) | `API_PROXY_URL` = URL pública do backend (sem `/` no fim). Alternativa: raiz do repo + [`docker/front/Dockerfile`](../docker/front/Dockerfile). |
| **API** | Root = `backend`, Dockerfile = `Dockerfile` → [`backend/Dockerfile`](../backend/Dockerfile) | *Ou* raiz + [`docker/backend/Dockerfile`](../docker/backend/Dockerfile). |
| **Worker** | Root = `temporal`, Dockerfile = `Dockerfile` → [`temporal/Dockerfile`](../temporal/Dockerfile) | `NEXT_APP_URL` = URL pública do **front**. *Ou* raiz + [`docker/temporal-worker/Dockerfile`](../docker/temporal-worker/Dockerfile). |
| **Temporal** | Cluster já existente | Só variáveis de conexão; não precisa duplicar se já está no projeto. |

## Variáveis críticas

- **`DATABASE_URL`** — Postgres (mesmo para API e para `prisma db push` / migrações no CI se aplicável).
- **`TOKEN_ENCRYPTION_KEY`** — 64 caracteres hex (32 bytes); obrigatória em produção (`backend/app/config.py`).
- **`MAGALU_CLIENT_ID` / `MAGALU_CLIENT_SECRET` / `MAGALU_REDIRECT_URI`** — OAuth; segredos só no ambiente, nunca no Git.
- **`TEMPORAL_INTERNAL_SECRET`** — mesmo valor no **backend** e no **worker**; protege `POST /api/internal/temporal`.
- **`TEMPORAL_ADDRESS`**, **`TEMPORAL_NAMESPACE`**, **`TEMPORAL_TASK_QUEUE`** — apontar para o gRPC do seu cluster (Railway ou Temporal Cloud). Se o provedor exigir **TLS** ou **API key**, será preciso estender `Client.connect` em `backend/app/temporal_admin.py` e alinhar o worker à mesma configuração (ver documentação do SDK `temporalio` e do host).

## Ordem de subida

1. Postgres + variáveis de banco.  
2. Backend (migração/schema).  
3. Front com `API_PROXY_URL`.  
4. Worker com `NEXT_APP_URL` + Temporal + `TEMPORAL_INTERNAL_SECRET`.  

Ao subir o backend com `USE_TEMPORAL=true`, ele tenta registrar o workflow global de refresh de tokens; o worker precisa estar disponível para executar activities (ou haverá retry até o worker subir).

## Checklist de segurança

Ver [`SECURITY_CHECKLIST.md`](SECURITY_CHECKLIST.md). Em produção: `NODE_ENV=production`, cookies `Secure`, chaves fortes, sem `.env.local` no repositório.

# Imagens Docker (monorepo)

Contexto de build (**sempre a raiz do repositório**):

| Imagem | Comando |
|--------|---------|
| **Front** (Next.js) | `docker build -f docker/front/Dockerfile -t liquida-front .` |
| **Backend** (FastAPI) | `docker build -f docker/backend/Dockerfile -t liquida-api .` |
| **Worker Temporal** | `docker build -f docker/temporal-worker/Dockerfile -t liquida-temporal-worker .` |

## Variáveis no runtime

- **Front:** `API_PROXY_URL` (URL pública do backend), demais vars do Next conforme `.env.example` na raiz.
- **Backend:** `DATABASE_URL`, `TOKEN_ENCRYPTION_KEY`, Magalu, `TEMPORAL_*`, `TEMPORAL_INTERNAL_SECRET`, etc. — ver `.env.example`.
- **Worker:** `NEXT_APP_URL` (URL que o worker usa para chamar `/api/internal/temporal`), `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, `TEMPORAL_TASK_QUEUE`, `TEMPORAL_INTERNAL_SECRET` (igual ao backend).

## Railway

- Um serviço por imagem (ou Nixpacks no backend/worker, se preferir).
- **Temporal:** aponte `TEMPORAL_ADDRESS` / namespace para o cluster que você já tem no Railway (gRPC). Se o provedor exigir TLS ou API key, ajuste o client em `backend/app/temporal_admin.py` e no worker conforme a doc do provedor.
- O arquivo [`railway.toml`](../railway.toml) na raiz referencia apenas o **front**; para API e worker, crie serviços no dashboard e defina o Dockerfile correspondente ou use buildpacks.

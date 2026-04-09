# Imagens Docker (monorepo)

## Railway (recomendado)

Para cada serviço, **Root Directory** = pasta do serviço e **Dockerfile path** = `Dockerfile`:

| Serviço | Root Directory | Dockerfile no repo |
|---------|----------------|-------------------|
| API | `backend` | [`backend/Dockerfile`](../backend/Dockerfile) |
| Front | `front` | [`front/Dockerfile`](../front/Dockerfile) |
| Worker | `temporal` | [`temporal/Dockerfile`](../temporal/Dockerfile) |

## Build local com contexto na raiz do repo

| Imagem | Comando |
|--------|---------|
| **Front** | `docker build -f docker/front/Dockerfile -t liquida-front .` |
| **Backend** | `docker build -f docker/backend/Dockerfile -t liquida-api .` |
| **Worker** | `docker build -f docker/temporal-worker/Dockerfile -t liquida-temporal-worker .` |

## Variáveis no runtime

- **Front:** `API_PROXY_URL` (URL pública do backend), demais vars do Next conforme `.env.example` na raiz.
- **Backend:** `DATABASE_URL`, `TOKEN_ENCRYPTION_KEY`, Magalu, `TEMPORAL_*`, `TEMPORAL_INTERNAL_SECRET`, etc. — ver `.env.example`.
- **Worker:** `NEXT_APP_URL` (URL que o worker usa para chamar `/api/internal/temporal`), `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, `TEMPORAL_TASK_QUEUE`, `TEMPORAL_INTERNAL_SECRET` (igual ao backend).

## Railway

- Um serviço por imagem (ou Nixpacks no backend/worker, se preferir).
- **Temporal:** aponte `TEMPORAL_ADDRESS` / namespace para o cluster que você já tem no Railway (gRPC). Se o provedor exigir TLS ou API key, ajuste o client em `backend/app/temporal_admin.py` e no worker conforme a doc do provedor.
- O [`railway.toml`](../railway.toml) na raiz usa `docker/front/Dockerfile` (contexto **raiz** do repo). Se o serviço do front no Railway usar **Root = `front`**, no dashboard ponha Dockerfile path = `Dockerfile` (ficheiro em `front/`) em vez desse `railway.toml`, ou ajusta o TOML para o teu fluxo.

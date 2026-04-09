# Liquida Fim de Turno — monorepo

App para lojistas **aiqfome** configurarem desconto automático na janela antes do **último fechamento** do dia. O código está separado por **pasta** (cada uma pode virar um repositório Git próprio — ver [`REPOS.md`](REPOS.md)).

| Pasta | Projeto |
|-------|---------|
| [`front/`](front/) | Next.js — UI, proxy `/api/*` → FastAPI |
| [`backend/`](backend/) | FastAPI — API HTTP, Postgres, Temporal client |
| [`temporal/`](temporal/) | Worker Temporal (Python) |
| [`docs/`](docs/) | Documentação de produto e arquitetura |

## Requisitos

- Node 20+
- Python 3.11+
- Docker (opcional) ou Postgres
- [Temporal CLI](https://docs.temporal.io/cli#install) para desenvolvimento

## Setup local (resumo)

```bash
docker compose -f infra/docker-compose.postgres.yml up -d
cp .env.example .env.local
# edite .env.local (DATABASE_URL, TOKEN_ENCRYPTION_KEY, TEMPORAL_*, etc.)

cd front && npm install && npm run db:push
```

Terminais separados:

1. **API:** `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
2. **Front:** `cd front && npm run dev`
3. **Temporal:** `temporal server start-dev`
4. **Worker:** `cd temporal && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python run_worker.py`

Abra [http://localhost:3000](http://localhost:3000).

Variáveis e Magalu local: comentários em [`.env.example`](.env.example). Detalhes por serviço: [`front/README.md`](front/README.md), [`backend/README.md`](backend/README.md), [`temporal/README.md`](temporal/README.md).

## Docker

Imagens e comandos: [`docker/README.md`](docker/README.md).

**Railway (recomendado):** em cada serviço, Root Directory = `front` / `backend` / `temporal` e Dockerfile path = `Dockerfile` — ver [`docker/README.md`](docker/README.md).

**Build local com contexto na raiz do repo:**

```bash
docker build -f docker/front/Dockerfile -t liquida-front .
docker build -f docker/backend/Dockerfile -t liquida-api .
docker build -f docker/temporal-worker/Dockerfile -t liquida-temporal-worker .
```

## Deploy

- **Railway / produção:** [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
- **Front:** [`railway.toml`](railway.toml) aponta para [`docker/front/Dockerfile`](docker/front/Dockerfile); defina `API_PROXY_URL` para o FastAPI. Healthcheck `GET /api/health` via proxy.
- **Backend e worker:** serviços separados com os Dockerfiles em `docker/` ou Nixpacks; variáveis em [`.env.example`](.env.example).

## Documentação

Índice em [`docs/README.md`](docs/README.md) — arquitetura, Temporal, base de dados, spec, segurança, QA.

## Licença

MIT (ajustar conforme política da organização).

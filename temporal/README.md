# liquida-temporal-worker

Worker **Temporal** em Python: workflow de ciclo de vida da promoção por loja; activities chamam `POST /api/internal/temporal` em `NEXT_APP_URL` (URL pública do front, que faz proxy para o FastAPI).

## Execução

```bash
cd temporal
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_worker.py
```

## Variáveis

- **Monorepo:** carrega `.env` / `.env.local` na **raiz** do repositório e depois em `temporal/` (último vence).
- Lista: [`.env.example`](.env.example) e [`.env.example` na raiz](../.env.example).

Requer `TEMPORAL_INTERNAL_SECRET` idêntico ao do backend.

## Docker / Railway

- **Railway:** Root Directory = `temporal`, Dockerfile path = `Dockerfile` (ficheiro [`Dockerfile`](Dockerfile) nesta pasta).
- Monorepo com contexto na **raiz:** `docker build -f docker/temporal-worker/Dockerfile -t liquida-temporal-worker .` — ver [`docker/README.md`](../docker/README.md).

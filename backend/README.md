# liquida-backend

API **FastAPI**: auth Magalu, sessão, settings, `POST /api/internal/temporal`, integração Aiqfome (SQLAlchemy/asyncpg).

## Railway / Docker

Com **Root Directory** = `backend` no Railway: **Dockerfile path** = `Dockerfile` (ficheiro [`Dockerfile`](Dockerfile) nesta pasta). Não uses `docker/backend/Dockerfile` nesse modo — esse outro ficheiro assume contexto na **raiz** do monorepo.

## Desenvolvimento

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Variáveis de ambiente

- **Monorepo:** leitura de `../.env`, `../.env.local` e, em seguida, `backend/.env`, `backend/.env.local` (este sobrescreve).
- **Repo isolado:** use só `backend/.env.local`.

Modelo: [`.env.example`](.env.example).

**Magalu / aiqfome:** para listar cardápio e alterar preços promocionais via API V2, o token precisa incluir scopes como `aqf:store:read`, `aqf:menu:read` e `aqf:menu:create` (update item).

**Importante:** deixe `AIQFOME_ACCESS_TOKEN` **vazio** ao testar várias lojas com OAuth. Se estiver preenchido, o código antigo podia usá-lo como Bearer enquanto o path usava outro `externalStoreId` — dados da loja errada. Hoje as rotas por sessão **só** usam o token salvo na `Store` após o Magalu.

Todas as URLs usam **`Store.externalStoreId`** (id da loja na plataforma), carregado do banco por sessão / `storeId` interno no Temporal — não há id de loja fixo no cliente. Em **login dev**, defina `AIQFOME_DEV_EXTERNAL_STORE_ID` com o id numérico real; caso contrário o mock dry-run ecoa o valor gravado (antes caía em `43952`).

## Teste rápido

```bash
python -c "from app.main import app; print(app.title)"
```

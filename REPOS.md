# Repositórios separados (a partir do monorepo)

O código está organizado em pastas que podem virar **repos Git independentes**:

| Pasta | Projeto | Stack |
|-------|---------|--------|
| [`front/`](front/) | UI + proxy `/api/*` | Next.js |
| [`backend/`](backend/) | API HTTP | FastAPI |
| [`temporal/`](temporal/) | Worker Temporal | Python |
| [`docs/`](docs/) | Documentação | Markdown |

## Monorepo (hoje)

- Um único `.env.local` na **raiz** atende `backend/`, `temporal/` e os scripts Prisma em `front/` (via `dotenv -e ../.env.local`).
- `docker compose -f infra/docker-compose.postgres.yml up -d` sobe só Postgres.
- Imagens: [`docker/README.md`](docker/README.md) (contexto sempre a raiz do monorepo).

## Extrair um repositório

Exemplo com `git subtree split` (executar na raiz do monorepo):

```bash
# só o front (histórico da pasta front/)
git subtree split -P front -b split-front
mkdir ../liquida-front && cd ../liquida-front
git init
git pull ../Liquida-Fim-de-Turno split-front
```

Repita com `-P backend`, `-P temporal`, `-P docs` para cada serviço.

Após extrair o **front**, use o [`front/Dockerfile`](front/Dockerfile) com contexto igual à raiz do novo repo (já sem prefixo `front/` nos `COPY`).

Após extrair o **backend** ou **temporal**, copie o [`.env.example`](.env.example) relevante para a raiz desse repo e ajuste caminhos nos READMEs.

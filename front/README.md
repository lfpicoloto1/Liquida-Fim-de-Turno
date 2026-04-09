# liquida-front

Next.js: interface (Geraldo UI), `postMessage` com Magalu e **proxy** de `/api/*` para o FastAPI (`API_PROXY_URL`).

## Desenvolvimento

Na raiz do monorepo, com Postgres e `.env.local` configurados:

```bash
cd front
npm install
npm run dev
```

Abra [http://localhost:3000](http://localhost:3000). O backend Python deve estar em `http://127.0.0.1:8000` (ou defina `API_PROXY_URL`).

## Prisma (schema)

O `prisma/schema.prisma` vive aqui; `npm run db:push` carrega primeiro `../.env.local` e `../.env` (monorepo), depois `.env.local` nesta pasta.

## Build / Docker

- Monorepo: na **raiz** do repositório, `docker build -f docker/front/Dockerfile -t liquida-front .` (ver [`docker/README.md`](../docker/README.md)).
- Repositório **só** com esta pasta: `docker build -t liquida-front .` usando o `Dockerfile` deste diretório.

## Variáveis

Ver [`.env.example`](.env.example). Detalhes completos: [`.env.example` na raiz do monorepo](../.env.example).

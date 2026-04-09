# Build com contexto na raiz do monorepo:
#   docker build -f docker/front/Dockerfile -t liquida-front .
# Com Root Directory = `front` no Railway, use em vez disso `front/Dockerfile` (path `Dockerfile`).
FROM node:22-alpine AS builder
WORKDIR /app

COPY front/package.json front/package-lock.json ./
RUN npm ci

COPY front/ .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY front/package.json front/package-lock.json ./
RUN npm ci --omit=dev

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.mjs ./next.config.mjs
COPY --from=builder /app/package.json ./package.json

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["npm", "run", "start"]

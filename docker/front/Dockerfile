# Build com contexto na raiz do monorepo:
#   docker build -f docker/front/Dockerfile -t liquida-front .
# Com Root Directory = `front` no Railway, use em vez disso `front/Dockerfile` (path `Dockerfile`).
FROM node:22-alpine AS builder
WORKDIR /app

COPY front/package.json front/package-lock.json ./
RUN npm ci

COPY front/ .

ARG ALLOWED_FRAME_ANCESTORS
ARG NEXT_PUBLIC_DEBUG_API
ARG NEXT_PUBLIC_DEV_LOGIN
ARG NEXT_PUBLIC_MAGALU_CLIENT_ID
ARG NEXT_PUBLIC_MAGALU_REDIRECT_URI
ARG NEXT_PUBLIC_POSTMESSAGE_ORIGINS
ENV ALLOWED_FRAME_ANCESTORS=$ALLOWED_FRAME_ANCESTORS
ENV NEXT_PUBLIC_DEBUG_API=$NEXT_PUBLIC_DEBUG_API
ENV NEXT_PUBLIC_DEV_LOGIN=$NEXT_PUBLIC_DEV_LOGIN
ENV NEXT_PUBLIC_MAGALU_CLIENT_ID=$NEXT_PUBLIC_MAGALU_CLIENT_ID
ENV NEXT_PUBLIC_MAGALU_REDIRECT_URI=$NEXT_PUBLIC_MAGALU_REDIRECT_URI
ENV NEXT_PUBLIC_POSTMESSAGE_ORIGINS=$NEXT_PUBLIC_POSTMESSAGE_ORIGINS

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
COPY --from=builder /app/prisma ./prisma

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["npm", "run", "start"]

# Especificação técnica — Liquida Fim de Turno

## Arquitetura (C4 resumido)

- **Browser (iframe no Geraldo)** → **Next.js** (UI + proxy) → **FastAPI** → **Postgres** + **API aiqfome V2** + **Magalu ID** (OAuth).
- **Temporal + worker Python** → `POST /api/internal/temporal` com `Authorization: Bearer $TEMPORAL_INTERNAL_SECRET` (orquestração por loja; ver `docs/TEMPORAL.md`).

## Gap analysis API V2 (a preencher com doc oficial)

A implementação atual usa o cliente no servidor (`backend/app/aiqfome_client.py`), com dry-run/stub onde aplicável. O time deve mapear endpoints reais em [API aiqfome V2](https://developer.aiqfome.com/docs/api/v2):

| Caso de uso | Endpoint V2 (placeholder) | Notas |
|-------------|---------------------------|--------|
| Horário da loja / último fechamento | `Store` (horários de operação) | Derivar **último** `close` do dia civil no TZ da loja |
| Listar itens / preços | `Menu` / `Catalog` | Baseline para reversão |
| Aplicar desconto | *TBD* | Pode ser preço, promoção ou combo — depende da V2 |
| Reverter preço | *TBD* | Restaurar baseline armazenado ou PUT original |

Variáveis: `AIQFOME_API_BASE_URL`, `AIQFOME_PLATFORM_BASE_URL` (padrão `https://plataforma.aiqfome.com`), `AIQFOME_ACCESS_TOKEN` (MVP dev) ou **access token do Magalu** após OAuth.

**ID da loja (`Store.externalStoreId`):** após o `code` Magalu, o BFF chama `GET …/api/v2/store` e escolhe a linha cujo `id` coincide com **`externalStoreId` no body** ou com **`oauthState`** (eco do parâmetro OAuth `state`, tipicamente `btoa(JSON.stringify({ externalStoreId }))`). Se o token retornar **uma** loja só, usa essa; se retornar **várias** e não houver preferência, o login responde **400** listando os ids — o usuário deve informar o id na UI antes de abrir o Magalu.

## Magalu ID

- Fluxo: popup `id.magalu.com` (opcional `state` com id da loja) → callback → `postMessage` `{ type: 'authCode', code, oauthState? }` ou página `/auth/magalu/callback` → BFF `POST /api/auth/magalu/token` com `oauthState` quando existir.
- Env: `MAGALU_CLIENT_ID`, `MAGALU_CLIENT_SECRET`, `MAGALU_TOKEN_URL`, `MAGALU_AUTHORIZE_URL` (se diferentes do padrão).
- **PKCE**: adicionar se obrigatório pela documentação Magalu.

## `postMessage`

- Allowlist: `GERALDO_PARENT_ORIGINS` (CSV).
- Mensagem esperada: `{ type: 'authCode', code: string, oauthState?: string }` (eco do `state` do redirect, se o iframe repassar).

## Modelo de dados (Postgres)

Ver `front/prisma/schema.prisma`:

- `Store`: vínculo lógico da loja + timezone IANA + tokens cifrados + estado do job.
- `StoreSettings`: `discountPercent`, `leadMinutes`, `activeWeekdays` (bitmask 0–127), `routineEnabled`.
- `PriceBaseline`: snapshot JSON por item (MVP) para reversão quando a V2 não fornecer histórico.
- `Session`: sessão httpOnly por `sessionId`.

## Job (pseudocódigo)

```
para cada Store onde routineEnabled e credenciais OK:
  agora = now in store.timezone
  se weekday(agora) não está em activeWeekdays: continuar
  ultimoFechamento = derivar da API V2 ou fallback
  windowStart = ultimoFechamento - leadMinutes
  windowEnd = ultimoFechamento
  se agora em [windowStart, windowEnd): applyPromo()
  senão se agora >= windowEnd e promoAplicadaHoje: revertPromo()
  senão: noop
```

Idempotência: flags `promoAppliedForDate`, `lastJobRunAt` e baseline só gravados após sucesso da API.

## Fuso

- `store.timeZone` (ex.: `America/Sao_Paulo`). Job usa `Intl` / `@js-temporal/polyfill` não necessário se `Temporal` indisponível — MVP usa `date-fns-tz` ou cálculo manual com `luxon`. I'll use `date-fns-tz` for timezone handling.

Actually to reduce deps I can use native with `Intl.DateTimeFormat` and manual - complex. I'll add `date-fns` and `date-fns-tz`.

## Variáveis Railway

Ver `.env.example`.

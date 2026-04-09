# Banco de dados (Postgres + Prisma)

Este documento descreve o **modelo lógico** definido em [`front/prisma/schema.prisma`](../front/prisma/schema.prisma) e traz **consultas SQL** úteis para exploração local (ex.: `psql` contra o Postgres do Docker).

## Conexão local (Docker Compose)

Credenciais padrão do Compose em [`infra/docker-compose.postgres.yml`](../infra/docker-compose.postgres.yml):

| Campo    | Valor      |
|----------|------------|
| Host     | `localhost` |
| Porta    | `5432`     |
| Utilizador | `liquida` |
| Password | `liquida` |
| Database | `liquida` |

URL (Prisma / apps):

```text
postgresql://liquida:liquida@localhost:5432/liquida?schema=public
```

**psql:**

```bash
psql "postgresql://liquida:liquida@localhost:5432/liquida"
```

Alternativa sem cliente local: `docker exec -it liquida-postgres psql -U liquida -d liquida`.

**UI:** na raiz do repo, com `DATABASE_URL` carregada: `npx prisma studio`.

---

## Diagrama relacional (resumo)

```
Store (1) ──┬── (0..1) StoreSettings
            ├── (0..1) JobState
            ├── (0..1) PriceBaseline
            └── (N)    Session
```

- Uma **loja** (`Store`) é a entidade central (identificador externo Magalu / tenant em `externalStoreId`).
- **Config da rotina** fica em `StoreSettings` (1:1 com `Store`).
- **Estado da automação** (última execução, promo aplicada, erros) em `JobState` (1:1).
- **Baseline de preços** (JSON em texto) em `PriceBaseline` (1:1), quando usado.
- **Sessões web** em `Session` (cookie → `storeId`).

---

## Tabelas e colunas (nomes Prisma → Postgres)

O Prisma cria tabelas com o **mesmo nome do model** (identificadores com maiúsculas: use **aspas duplas** no SQL).

### `Store`

| Coluna | Tipo (conceito) | Notas |
|--------|-----------------|--------|
| `id` | texto (cuid) | PK interna |
| `externalStoreId` | texto | Único; id externo (ex. contexto Magalu / loja) |
| `timeZone` | texto | Ex.: `America/Sao_Paulo` |
| `displayName` | texto? | Nome amigável |
| `accessToken`, `accessExpiresAt` | texto?, timestamp? | Token Magalu / API (MVP) |
| `encryptedRefresh` | texto? | Refresh cifrado (app) |
| `createdAt`, `updatedAt` | timestamp | Metadados |

### `StoreSettings`

| Coluna | Tipo (conceito) | Notas |
|--------|-----------------|--------|
| `storeId` | texto | FK → `Store.id`, único (1:1) |
| `discountPercent` | int | % desconto (0–95 na API) |
| `leadMinutes` | int | Antecedência ao fechamento (minutos) |
| `activeWeekdays` | int | **Bitmask**: bit 0 = domingo … bit 6 = sábado (como `getUTCDay`) |
| `routineEnabled` | boolean | Rotina ligada |
| `promoCategoryIds` | `integer[]` | IDs das categorias do cardápio (resposta de `GET /api/v2/menu/:store_id/categories`) em que a promoção deve ser aplicada |

O **horário de fechamento por dia** não fica nesta tabela: vem da API aiqfome `working-hours` em tempo de execução.

**Exemplo de bitmask:** valor `62` em binário usa bits 1–5 → segunda a sexta ativos (domingo = 0).

### `JobState`

| Coluna | Notas |
|--------|--------|
| `lastRunAt` | Última vez que o pipeline (Temporal → API interna) atualizou o estado |
| `lastError` | Mensagem de erro, se houver |
| `promoAppliedForDate` | Chave de data (string) em que a promo foi aplicada |
| `lastRevertDate` | Última reversão (string de data) |

### `PriceBaseline`

| Coluna | Notas |
|--------|--------|
| `payload` | JSON serializado em texto: snapshot **antes** de aplicar a promo, para `PUT` de reversão na API aiqfome |

Formato atual (`v` = 1):

- **`v`**: `1`
- **`items`**: mapa `itemUuid` → mapa `itemSizeId` (string) → `{ "value", "promotional_value" }` (strings como retornadas no [show item](https://developer.aiqfome.com/docs/api/v2/show-item); `promotional_value` pode ser `null` no JSON salvo como ausência).

Gravado **antes** dos `PUT` de aplicação; a rotina de desconto usa `value` como preço de lista e define `promotional_value` com o percentual configurado. Na **reversão**, o PUT restaura só o `value` do snapshot e envia `promotional_value` **nulo** (remove qualquer promo na API), sem reutilizar o `promotional_value` antigo do baseline.

### `Session`

| Coluna | Notas |
|--------|--------|
| `storeId` | FK → `Store` |
| `expiresAt` | Expiração da sessão HTTP |

---

## Nomes reais das tabelas no Postgres

Se alguma query falhar por nome de tabela, liste o que existe no schema `public`:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

Nas queries abaixo assumimos os nomes **`Store`**, **`StoreSettings`**, **`JobState`**, **`PriceBaseline`**, **`Session`** com aspas.

---

## Consultas úteis

### Lojas com config e estado da automação (visão geral)

```sql
SELECT
  s.id,
  s."externalStoreId",
  s."displayName",
  s."timeZone",
  ss."routineEnabled",
  ss."discountPercent",
  ss."leadMinutes",
  ss."activeWeekdays",
  j."lastRunAt",
  j."lastError",
  j."promoAppliedForDate",
  j."lastRevertDate"
FROM "Store" s
LEFT JOIN "StoreSettings" ss ON ss."storeId" = s.id
LEFT JOIN "JobState" j ON j."storeId" = s.id
ORDER BY s."createdAt" DESC;
```

### Apenas lojas com rotina ligada

```sql
SELECT s.id, s."externalStoreId", s."displayName"
FROM "Store" s
JOIN "StoreSettings" ss ON ss."storeId" = s.id
WHERE ss."routineEnabled" = true;
```

### Sessões ainda válidas (não expiradas)

```sql
SELECT se.id, se."storeId", s."externalStoreId", se."expiresAt", se."createdAt"
FROM "Session" se
JOIN "Store" s ON s.id = se."storeId"
WHERE se."expiresAt" > NOW()
ORDER BY se."expiresAt" DESC;
```

### Contagem de sessões por loja

```sql
SELECT s."externalStoreId", COUNT(*) AS sessions
FROM "Session" se
JOIN "Store" s ON s.id = se."storeId"
GROUP BY s.id, s."externalStoreId"
ORDER BY sessions DESC;
```

### Decodificar dias ativos a partir do bitmask (`activeWeekdays`)

Domingo = bit 0 (valor 1), segunda = bit 1 (2), …, sábado = bit 6 (64):

```sql
SELECT
  s."externalStoreId",
  ss."activeWeekdays",
  CASE WHEN ss."activeWeekdays" & 1  <> 0 THEN 'Dom ' ELSE '' END ||
  CASE WHEN ss."activeWeekdays" & 2  <> 0 THEN 'Seg ' ELSE '' END ||
  CASE WHEN ss."activeWeekdays" & 4  <> 0 THEN 'Ter ' ELSE '' END ||
  CASE WHEN ss."activeWeekdays" & 8  <> 0 THEN 'Qua ' ELSE '' END ||
  CASE WHEN ss."activeWeekdays" & 16 <> 0 THEN 'Qui ' ELSE '' END ||
  CASE WHEN ss."activeWeekdays" & 32 <> 0 THEN 'Sex ' ELSE '' END ||
  CASE WHEN ss."activeWeekdays" & 64 <> 0 THEN 'Sáb ' ELSE '' END
    AS dias_ativos
FROM "Store" s
JOIN "StoreSettings" ss ON ss."storeId" = s.id;
```

### Baseline de preços (tamanho e última atualização)

```sql
SELECT
  s."externalStoreId",
  LENGTH(pb.payload) AS payload_chars,
  pb."updatedAt"
FROM "PriceBaseline" pb
JOIN "Store" s ON s.id = pb."storeId";
```

### Últimas lojas criadas

```sql
SELECT id, "externalStoreId", "displayName", "createdAt"
FROM "Store"
ORDER BY "createdAt" DESC
LIMIT 20;
```

---

## Operações de manutenção (só dev / com cuidado)

### Apagar todas as sessões (força novo login)

```sql
DELETE FROM "Session";
```

### Ver tamanho das tabelas (aproximado)

```sql
SELECT
  relname AS table_name,
  pg_size_pretty(
    pg_total_relation_size(format('%I.%I', schemaname, relname)::regclass)
  ) AS total_size
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(format('%I.%I', schemaname, relname)::regclass) DESC;
```

---

## Alterações de schema

O projeto usa **Prisma** em `front/`; mudanças de modelo devem ser feitas em `front/prisma/schema.prisma` e aplicadas com:

```bash
cd front && npm run db:push
```

(ou migrations em fluxo com `migrate`, se a equipa adoptar.)

Não edites só o Postgres “na mão” sem alinhar `front/prisma/schema.prisma`, senão o Prisma e a BD ficam dessincronizados.

---

## Ver também

- [`README.md`](../README.md) — Postgres via Docker e `DATABASE_URL`
- [`front/prisma/schema.prisma`](../front/prisma/schema.prisma) — fonte de verdade dos models

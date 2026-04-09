# Checklist Sec — Liquida Fim de Turno

Usar antes de cada release e após mudanças em auth, API interna Temporal ou dependências críticas.

## Segredos e configuração

- [ ] Nenhum `client_secret`, refresh token, `TEMPORAL_INTERNAL_SECRET` ou `DATABASE_URL` no Git.
- [ ] Variáveis sensíveis apenas no Railway (ou `.env.local` local, coberto pelo `.gitignore` na raiz).
- [ ] Não criar cópias de `.env.local` dentro de `backend/app/` ou outras pastas — um único ficheiro na raiz (ou por serviço documentado) reduz risco de commit por engano.
- [ ] Antes do primeiro `git push`, executar `git status` e `git ls-files | grep -Ei 'env|secret|credential'` (revisar a lista manualmente); se algo sensível foi versionado, **revogar** credenciais no Magalu e **rotacionar** segredos.
- [ ] `TEMPORAL_INTERNAL_SECRET` com entropia alta (≥32 bytes aleatórios).
- [ ] Builds Docker usam [`.dockerignore`](../.dockerignore) na raiz para não enviar `.env*` no contexto da imagem.

## OAuth e sessão

- [ ] Troca de `code` apenas no servidor; `code` de uso único e não logado.
- [ ] Cookies de sessão: `Secure` em produção, `httpOnly`, `SameSite` adequado ao iframe.
- [ ] Escopos OAuth mínimos necessários (revisar ao integrar escrita na V2).

## Iframe e `postMessage`

- [ ] Allowlist de `event.origin` (env `GERALDO_PARENT_ORIGINS`); nunca `*`.
- [ ] Validar formato da mensagem antes de enviar `code` ao BFF.

## BFF e API interna Temporal

- [ ] `POST /api/internal/temporal` exige header `Authorization: Bearer <TEMPORAL_INTERNAL_SECRET>`; segredo não exposto ao browser.
- [ ] Autorização por loja: usuário só lê/escreve config da própria `storeId` da sessão.
- [ ] Validação de input (Zod) em rotas mutáveis.
- [ ] Rate limiting recomendado na borda (Railway/proxy) para `/api/auth/*`.

## Dados em repouso

- [ ] Refresh token cifrado no banco (`TOKEN_ENCRYPTION_KEY`); rotação de chave documentada.

## Supply chain

- [ ] `npm audit` sem críticos não justificados; lockfile commitado.

## Headers

- [ ] `next.config` define headers de segurança; CSP/`frame-ancestors` alinhados ao Geraldo quando soubermos domínios exatos.

## Incidente

- [ ] Procedimento: revogar tokens Magalu/loja, rotacionar `TEMPORAL_INTERNAL_SECRET`, invalidar sessões se necessário.

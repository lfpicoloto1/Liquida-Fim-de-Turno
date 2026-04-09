# Matriz QA — Liquida Fim de Turno

| ID | Regra / área | Tipo | Como validar |
|----|----------------|------|--------------|
| Q1 | Login Magalu + troca de `code` | Funcional | Popup → callback Geraldo → postMessage → sessão em `/api/me` |
| Q2 | `postMessage` origem hostil ignorada | Segurança | Enviar mensagem de outra origem; sessão não muda |
| Q3 | Login dev (`SKIP_OAUTH_VALIDATION`) só non-prod | Segurança | `NODE_ENV=production` não aceita fluxo dev |
| Q4 | API interna Temporal sem secret retorna 401 | Segurança | `POST /api/internal/temporal` sem `Authorization` ou Bearer errado |
| Q5 | Salvar config persiste e recarrega | Funcional | PATCH `/api/settings` + GET + UI |
| Q6 | Dias da semana bitmask | Funcional | Alternar checkboxes; workflow só planeia slot em dias marcados |
| Q7 | Último fechamento + antecedência | Funcional | Unit `front/src/lib/jobs/promo-window.test.ts` + workflow em staging |
| Q8 | Reversão após fechamento | Funcional | Relógio simulado ou loja com fechamento próximo em staging |
| Q9 | `AIQFOME_DRY_RUN=true` não chama rede real | Contrato | Activities via API interna completam apply/revert sem throw |
| Q10 | Smoke Railway | Deploy | Health: app responde 200; API interna 401 sem secret |

## Relógio simulado (non-prod)

- Opcional: estender testes com mock de tempo no `planNextPromoSlot` / workflow em ambiente de QA (não há env dedicada no MVP).

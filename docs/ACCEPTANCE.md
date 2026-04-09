# Critérios de aceite (PO) — Liquida Fim de Turno

## Autenticação

- O lojista autentica via **Magalu ID** (popup + `postMessage` com `authCode`).
- Após troca do `code` no BFF, existe sessão segura (`httpOnly`) associada a **uma loja/tenant**.
- Sessão expirada ou refresh inválido: UI pede novo login sem vazar tokens.

## Configuração persistida

- O lojista define **percentual de desconto** (0–100, validação de faixa configurável).
- Define **antecedência** em horas **ou** minutos (persistido como `lead_minutes`).
- Define **dias da semana** em que a rotina roda (dom–sáb, múltipla escolha).
- Configuração salva no Postgres e reapresentada após reload.

## Automação (sem login diário)

- **Temporal + worker** (um workflow por loja) orquestra tempos; o worker chama o BFF em `POST /api/internal/temporal` para reconciliar, planejar slot, aplicar e reverter. Lojas com rotina ativa e credenciais válidas seguem esse ciclo enquanto o workflow estiver a correr.
- **Último fechamento do dia** (fuso da loja): janela `[ultimo_fechamento − lead, ultimo_fechamento)` aplica promoção; no **último fechamento** reverte para baseline.
- **Múltiplos turnos**: apenas o **último** fechamento do dia civil define janela e reversão.
- O pipeline é **idempotente** onde aplicável (não corrompe baseline nem duplica desconto indevido); o Temporal retoma após falhas sem repetir efeitos já concluídos.

## Edge cases (rastreabilidade)

- **Loja 24h** ou **sem horário**: comportamento definido no Spec (falha controlada + mensagem na UI/status).
- **DST**: uso de timezone IANA da loja; testes em QA cobrem transição quando houver dados de teste.
- **Feriados**: fora do MVP salvo flag futura documentada no Spec.

## Integração API V2

- Leitura de horário de funcionamento e escrita de preço/promo conforme capacidade real da V2 (ver `docs/SPEC.md`).
- Falha de API: retry limitado, log sem segredos, status visível ao lojista quando aplicável.

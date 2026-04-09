# UI handoff — Geraldo UI (iframe)

## Telas

### 1. Não autenticado

- **geraldo-card**: título + texto explicando o app.
- **geraldo-button** (filled, primary): “Entrar com Magalu ID” — abre popup OAuth.
- Texto auxiliar se popup bloqueado (parágrafo simples).

### 2. Autenticado — Configuração

- **geraldo-text** `h3-section`: “Promoção fim de expediente”.
- **geraldo-text-field**: percentual de desconto (número).
- Antecedência: **geraldo-radio-group** “Unidade” (horas | minutos) + **geraldo-text-field** valor.
- Dias: **geraldo-checkbox** por dia (Dom … Sáb).
- **geraldo-switch**: “Rotina ativa”.
- **geraldo-button**: Salvar (loading state).

### 3. Status

- **geraldo-card**: última execução do job, último erro (se houver).
- **geraldo-badge** para estado (ok / atenção).

### 4. Sessão

- **geraldo-button** outline: Sair.

## Tokens e fonte

- Import global: `@aiqfome-org/geraldo-ui/tokens.css` + `lit` + `@aiqfome-org/geraldo-ui`.
- Fonte Ubuntu (link no `layout.tsx`).

## Estados especiais

- Loading inicial ao hidratar sessão.
- Erro genérico em falha de `postMessage` com origem inválida (sem detalhar ao usuário).

import { describe, expect, it } from "vitest";
import { computePromoAction } from "./promo-window";

/** Segunda-feira 20:00 em São Paulo */
const base = new Date("2026-04-06T23:00:00.000Z");

describe("computePromoAction", () => {
  it("aplica dentro da janela antes do fechamento", () => {
    const action = computePromoAction({
      now: base,
      timeZone: "America/Sao_Paulo",
      closingTimeLocal: "22:00",
      leadMinutes: 120,
      weekdayMask: 1 << 1,
      promoAppliedForDate: null,
      lastRevertDate: null,
    });
    expect(action).toEqual({ type: "apply", dateKey: "2026-04-06" });
  });

  it("não aplica fora do dia habilitado", () => {
    const sunday = new Date("2026-04-05T23:00:00.000Z");
    const action = computePromoAction({
      now: sunday,
      timeZone: "America/Sao_Paulo",
      closingTimeLocal: "22:00",
      leadMinutes: 60,
      weekdayMask: 1 << 1,
      promoAppliedForDate: null,
      lastRevertDate: null,
    });
    expect(action.type).toBe("noop");
  });

  it("reverte após o fechamento se promo estava ativa no dia", () => {
    const afterClose = new Date("2026-04-07T01:30:00.000Z");
    const action = computePromoAction({
      now: afterClose,
      timeZone: "America/Sao_Paulo",
      closingTimeLocal: "22:00",
      leadMinutes: 60,
      weekdayMask: 1 << 1,
      promoAppliedForDate: "2026-04-06",
      lastRevertDate: null,
    });
    expect(action).toEqual({ type: "revert", dateKey: "2026-04-06" });
  });
});

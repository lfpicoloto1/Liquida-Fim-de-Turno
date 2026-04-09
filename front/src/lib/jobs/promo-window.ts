import { format, getDay, setHours, setMinutes, setSeconds, subMinutes } from "date-fns";
import { toZonedTime } from "date-fns-tz";

export type PromoAction =
  | { type: "noop" }
  | { type: "apply"; dateKey: string }
  | { type: "revert"; dateKey: string }
  | { type: "revert_stale"; staleDate: string };

export type PromoWindowInput = {
  now: Date;
  timeZone: string;
  closingTimeLocal: string;
  leadMinutes: number;
  weekdayMask: number;
  promoAppliedForDate: string | null;
  lastRevertDate: string | null;
};

/**
 * dateKey sempre no fuso da loja (yyyy-MM-dd).
 * Janela: [close - lead, close). Reversão em close ou após, uma vez por dateKey.
 */
export function computePromoAction(input: PromoWindowInput): PromoAction {
  const zNow = toZonedTime(input.now, input.timeZone);
  const dow = getDay(zNow);
  const dateKey = format(zNow, "yyyy-MM-dd");

  if (input.promoAppliedForDate && input.promoAppliedForDate < dateKey) {
    return { type: "revert_stale", staleDate: input.promoAppliedForDate };
  }

  if ((input.weekdayMask & (1 << dow)) === 0) {
    return { type: "noop" };
  }

  const parts = input.closingTimeLocal.split(":");
  const hh = Number(parts[0]);
  const mm = Number(parts[1] ?? 0);
  if (!Number.isFinite(hh) || !Number.isFinite(mm)) {
    return { type: "noop" };
  }

  const closeToday = setSeconds(setMinutes(setHours(zNow, hh), mm), 0);
  const windowStart = subMinutes(closeToday, input.leadMinutes);

  const t = zNow.getTime();
  const ws = windowStart.getTime();
  const ce = closeToday.getTime();

  if (t < ws) {
    return { type: "noop" };
  }

  if (t >= ws && t < ce) {
    if (input.promoAppliedForDate !== dateKey) {
      return { type: "apply", dateKey };
    }
    return { type: "noop" };
  }

  if (input.promoAppliedForDate === dateKey && input.lastRevertDate !== dateKey) {
    return { type: "revert", dateKey };
  }

  return { type: "noop" };
}

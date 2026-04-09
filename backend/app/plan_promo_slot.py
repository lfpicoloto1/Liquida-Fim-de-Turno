"""Planeia o próximo slot (fim = fechamento do dia, início = fim − lead)."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


@dataclass
class PlannedPromoSlot:
    date_key: str
    promo_start_iso: str
    promo_end_iso: str
    skip_apply: bool


def _dow_js_sunday_zero(dt_local: datetime) -> int:
    """JavaScript getDay(): domingo=0 … sábado=6."""
    return (dt_local.weekday() + 1) % 7


def plan_next_promo_slot(
    now: datetime,
    time_zone: str,
    closing_by_dow: Mapping[int, tuple[int, int]],
    lead_minutes: int,
    weekday_mask: int,
    promo_applied_for_date: str | None,
    max_days: int = 14,
) -> PlannedPromoSlot | None:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if not closing_by_dow:
        return None
    zi = ZoneInfo(time_zone)

    for d in range(max_days):
        probe = now + timedelta(days=d)
        z = probe.astimezone(zi)
        date_key = z.strftime("%Y-%m-%d")
        dow_js = _dow_js_sunday_zero(z)
        if (weekday_mask & (1 << dow_js)) == 0:
            continue

        close_hm = closing_by_dow.get(dow_js)
        if close_hm is None:
            continue
        ch, cm = close_hm

        promo_end = datetime.strptime(
            f"{date_key} {ch:02d}:{cm:02d}:00",
            "%Y-%m-%d %H:%M:%S",
        ).replace(tzinfo=zi)
        promo_start = promo_end - timedelta(minutes=lead_minutes)

        if now >= promo_end.astimezone(timezone.utc):
            continue

        now_utc = now.astimezone(timezone.utc)
        pe_utc = promo_end.astimezone(timezone.utc)
        ps_utc = promo_start.astimezone(timezone.utc)

        in_window = ps_utc <= now_utc < pe_utc
        skip_apply = bool(promo_applied_for_date == date_key and in_window)

        if skip_apply:
            promo_start_iso = now_utc.isoformat().replace("+00:00", "Z")
        elif now_utc < ps_utc:
            promo_start_iso = ps_utc.isoformat().replace("+00:00", "Z")
        else:
            promo_start_iso = now_utc.isoformat().replace("+00:00", "Z")

        return PlannedPromoSlot(
            date_key=date_key,
            promo_start_iso=promo_start_iso,
            promo_end_iso=pe_utc.isoformat().replace("+00:00", "Z"),
            skip_apply=skip_apply,
        )

    return None

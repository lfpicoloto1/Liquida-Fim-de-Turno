"""Parse de horários da API aiqfome GET /api/v2/store/:id/working-hours."""

import re
from typing import Any, Mapping

# API: week_day_number 1=segunda … 7=domingo (ISO 8601). Bitmask do app: domingo=0 … sábado=6 (getDay).


def api_weekday_to_dow_js(week_day_number: int) -> int:
    """1–7 (seg–dom) → 0–6 (dom–sáb), alinhado a `plan_promo_slot._dow_js_sunday_zero`."""
    return week_day_number % 7


def parse_hours_last_close(hours_str: str) -> tuple[int, int] | None:
    """
    Último fechamento do dia a partir de strings como '14:00 - 18:00' ou vários intervalos separados por vírgula.
    """
    s = (hours_str or "").strip()
    if not s:
        return None
    best_mins = -1
    best: tuple[int, int] | None = None
    for m in re.finditer(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", s):
        eh, em = int(m.group(3)), int(m.group(4))
        if not (0 <= eh <= 23 and 0 <= em <= 59):
            continue
        mins = eh * 60 + em
        if mins > best_mins:
            best_mins = mins
            best = (eh, em)
    return best


def build_closing_by_dow_js(rows: list[dict[str, Any]]) -> dict[int, tuple[int, int]]:
    """
    Monta mapa dow_js (0=dom … 6=sáb) → (hora, minuto) do último fechamento daquele dia.
    `status == 1` = ativo. Se houver mais de uma linha para o mesmo dia, fica o fechamento mais tardio.
    """
    out: dict[int, tuple[int, int]] = {}
    for row in rows:
        if row.get("status") != 1:
            continue
        wd = row.get("week_day_number")
        if wd is None:
            continue
        try:
            dow = api_weekday_to_dow_js(int(wd))
        except (TypeError, ValueError):
            continue
        hm = parse_hours_last_close(str(row.get("hours") or ""))
        if hm is None:
            continue
        prev = out.get(dow)
        if prev is None or hm[0] * 60 + hm[1] > prev[0] * 60 + prev[1]:
            out[dow] = hm
    return out

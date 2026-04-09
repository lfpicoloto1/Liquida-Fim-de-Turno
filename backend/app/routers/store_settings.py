import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aiqfome_client import AiqfomeClient
from app.config import get_settings
from app.database import get_db
from app.deps import session_store_id
from app.ids import cuid
from app.models import JobState, Store, StoreSettings
from app.promo_actions import get_access_token_for_store
from app.temporal_admin import (
    reconcile_promo_once_via_temporal,
    start_or_restart_promo_workflow,
    stop_promo_workflow,
)
from app.working_hours import build_closing_by_dow_js

log = logging.getLogger(__name__)
router = APIRouter(tags=["settings"])

_DOW_LABELS_PT = ("Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb")

_AIQFOME_SESSION_TOKEN_MSG = (
    "Sem access token da aiqfome para esta loja (OAuth Magalu). "
    "Saia e entre de novo com Magalu ID. "
    "Se `AIQFOME_ACCESS_TOKEN` estiver no .env, ele não é mais usado para horários/cardápio — evita misturar lojas."
)


class SettingsPatch(BaseModel):
    discountPercent: int | None = Field(None, ge=0, le=95)
    leadMinutes: int | None = Field(None, ge=5, le=24 * 60)
    leadUnit: str | None = None
    leadValue: int | None = Field(None, ge=1)
    activeWeekdays: list[int] | None = None
    routineEnabled: bool | None = None
    timeZone: str | None = Field(None, min_length=3, max_length=64)
    promoCategoryIds: list[int] | None = None


def _bitmask_from_days(days: list[int]) -> int:
    acc = 0
    for d in days:
        acc |= 1 << d
    return acc


def _normalize_promo_category_ids(ids: list[int]) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for x in ids:
        if x <= 0:
            raise HTTPException(status_code=400, detail="promoCategoryIds inválido")
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _dump_settings(st: StoreSettings) -> dict[str, Any]:
    cats = list(st.promoCategoryIds) if st.promoCategoryIds is not None else []
    return {
        "id": st.id,
        "storeId": st.storeId,
        "discountPercent": st.discountPercent,
        "leadMinutes": st.leadMinutes,
        "activeWeekdays": st.activeWeekdays,
        "routineEnabled": st.routineEnabled,
        "promoCategoryIds": cats,
        "updatedAt": st.updatedAt.isoformat() if st.updatedAt else None,
    }


@router.get("/api/settings")
async def get_settings_route(
    db: AsyncSession = Depends(get_db),
    store_id: str = Depends(session_store_id),
):
    st = (await db.execute(select(StoreSettings).where(StoreSettings.storeId == store_id))).scalar_one_or_none()
    if not st:
        return {"settings": None}
    return {"settings": _dump_settings(st)}


@router.get("/api/store/working-hours")
async def get_store_working_hours(
    db: AsyncSession = Depends(get_db),
    store_id: str = Depends(session_store_id),
):
    """Último fechamento por dia (aiqfome GET …/store/:id/working-hours)."""
    s = get_settings()
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    try:
        token = await get_access_token_for_store(s, store)
        if not token:
            raise HTTPException(status_code=401, detail=_AIQFOME_SESSION_TOKEN_MSG)

        async def gt() -> str | None:
            return token

        client = AiqfomeClient(s, gt, allow_env_token_fallback=False)
        rows = await client.fetch_working_hours(store.externalStoreId)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    by_dow = build_closing_by_dow_js(rows)
    last_close_by_dow = [
        {
            "dowJs": d,
            "label": _DOW_LABELS_PT[d],
            "lastClose": f"{by_dow[d][0]:02d}:{by_dow[d][1]:02d}" if d in by_dow else None,
        }
        for d in range(7)
    ]
    return {"data": rows, "lastCloseByDow": last_close_by_dow}


@router.get("/api/store/menu-categories")
async def get_store_menu_categories(
    db: AsyncSession = Depends(get_db),
    store_id: str = Depends(session_store_id),
):
    """Categorias do cardápio (aiqfome GET …/menu/:store_id/categories)."""
    s = get_settings()
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    try:
        token = await get_access_token_for_store(s, store)
        if not token:
            raise HTTPException(status_code=401, detail=_AIQFOME_SESSION_TOKEN_MSG)

        async def gt() -> str | None:
            return token

        client = AiqfomeClient(s, gt, allow_env_token_fallback=False)
        rows = await client.list_menu_categories(store.externalStoreId)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    slim: list[dict[str, Any]] = []
    seen_ids: set[Any] = set()
    for r in rows:
        if not isinstance(r, dict) or r.get("id") is None:
            continue
        rid = r.get("id")
        if rid in seen_ids:
            continue
        seen_ids.add(rid)
        slim.append(
            {
                "id": rid,
                "name": r.get("name"),
                "culinaryId": r.get("culinary_id"),
                "status": r.get("status"),
                "blockedUntilTomorrow": r.get("blocked_until_tomorrow"),
                "hasDailySale": r.get("has_daily_sale"),
            }
        )
    return {"categories": slim}


@router.patch("/api/settings")
async def patch_settings(
    body: SettingsPatch,
    db: AsyncSession = Depends(get_db),
    store_id: str = Depends(session_store_id),
):
    st = (await db.execute(select(StoreSettings).where(StoreSettings.storeId == store_id))).scalar_one_or_none()
    if not st:
        st = StoreSettings(id=cuid(), storeId=store_id)
        db.add(st)
        await db.flush()
        job = (await db.execute(select(JobState).where(JobState.storeId == store_id))).scalar_one_or_none()
        if not job:
            db.add(JobState(id=cuid(), storeId=store_id))
            await db.flush()

    was_routine_enabled = st.routineEnabled

    lead_minutes = body.leadMinutes
    if body.leadUnit is not None and body.leadValue is not None:
        lead_minutes = body.leadValue * 60 if body.leadUnit == "hours" else body.leadValue

    if body.discountPercent is not None:
        st.discountPercent = body.discountPercent
    if lead_minutes is not None:
        st.leadMinutes = lead_minutes
    if body.activeWeekdays is not None:
        for d in body.activeWeekdays:
            if d < 0 or d > 6:
                raise HTTPException(status_code=400, detail="activeWeekdays inválido")
        st.activeWeekdays = _bitmask_from_days(body.activeWeekdays)
    if body.routineEnabled is not None:
        st.routineEnabled = body.routineEnabled
    if body.promoCategoryIds is not None:
        st.promoCategoryIds = _normalize_promo_category_ids(body.promoCategoryIds)

    if body.timeZone is not None:
        store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
        if store:
            store.timeZone = body.timeZone

    turning_off_routine = was_routine_enabled and not st.routineEnabled

    await db.commit()
    await db.refresh(st)

    try:
        if st.routineEnabled:
            await start_or_restart_promo_workflow(store_id)
        else:
            # Rotina desligada: despublicar na aiqfome item a item (Temporal: prepareRevert + N PUTs + finalize),
            # igual ao reconcile do lifecycle. Roda ao desligar agora ou se ainda há promo pendente no job.
            job_row = (await db.execute(select(JobState).where(JobState.storeId == store_id))).scalar_one_or_none()
            promo_still_applied = bool(job_row and job_row.promoAppliedForDate)
            if turning_off_routine or promo_still_applied:
                await reconcile_promo_once_via_temporal(store_id, bypass_routine_check=True)
            await stop_promo_workflow(store_id)
    except Exception as e:
        log.exception("[settings] temporal sync failed: %s", e)

    return {"settings": _dump_settings(st)}

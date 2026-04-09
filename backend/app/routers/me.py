from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.deps import optional_session_store_id
from app.models import JobState, Store, StoreSettings

router = APIRouter(tags=["me"])


def _dt(v):
    if v is None:
        return None
    return v.isoformat() if hasattr(v, "isoformat") else v


@router.get("/api/me")
async def me(
    db: AsyncSession = Depends(get_db),
    store_id: str | None = Depends(optional_session_store_id),
):
    if not store_id:
        return {"authenticated": False}

    store = (
        await db.execute(
            select(Store)
            .options(joinedload(Store.settings_rel), joinedload(Store.job_state_rel))
            .where(Store.id == store_id)
        )
    ).unique().scalar_one_or_none()

    if not store:
        return {"authenticated": False}

    st = store.settings_rel
    job = store.job_state_rel

    settings_out = None
    if st:
        cats = list(st.promoCategoryIds) if st.promoCategoryIds is not None else []
        settings_out = {
            "id": st.id,
            "storeId": st.storeId,
            "discountPercent": st.discountPercent,
            "leadMinutes": st.leadMinutes,
            "activeWeekdays": st.activeWeekdays,
            "routineEnabled": st.routineEnabled,
            "promoCategoryIds": cats,
            "updatedAt": _dt(st.updatedAt),
        }

    job_out = None
    if job:
        job_out = {
            "id": job.id,
            "storeId": job.storeId,
            "lastRunAt": _dt(job.lastRunAt),
            "lastError": job.lastError,
            "promoAppliedForDate": job.promoAppliedForDate,
            "lastRevertDate": job.lastRevertDate,
        }

    return {
        "authenticated": True,
        "store": {
            "id": store.id,
            "externalStoreId": store.externalStoreId,
            "displayName": store.displayName,
            "timeZone": store.timeZone,
        },
        "settings": settings_out,
        "job": job_out,
    }

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aiqfome_client import AiqfomeClient
from app.config import get_settings
from app.database import get_db
from app import menu_promo
from app.models import JobState, PriceBaseline, Store, StoreSettings
from app.plan_promo_slot import plan_next_promo_slot
from app.promo_actions import (
    apply_promo_single_item_for_store,
    clear_price_baseline_for_store,
    finalize_promo_apply_for_store,
    finalize_reconcile_stale_for_store,
    finalize_revert_promo_for_store,
    get_access_token_for_store,
    list_promo_apply_item_entries_for_store,
    prepare_promo_apply_for_store,
    prepare_reconcile_stale_for_store,
    prepare_revert_promo_for_store,
    reconcile_stale_promo,
    revert_promo_for_store,
    revert_promo_single_item_for_store,
)
from app.oauth_token_refresh import refresh_oauth_tokens_all_stores
from app.working_hours import build_closing_by_dow_js

router = APIRouter(tags=["internal"])
log = logging.getLogger(__name__)


def _slot_dict(slot) -> dict:
    return {
        "dateKey": slot.date_key,
        "promoStartIso": slot.promo_start_iso,
        "promoEndIso": slot.promo_end_iso,
        "skipApply": slot.skip_apply,
    }


@router.post("/api/internal/temporal")
async def internal_temporal(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    s = get_settings()
    if not s.temporal_internal_secret:
        raise HTTPException(status_code=503, detail="TEMPORAL_INTERNAL_SECRET não configurado")
    auth = request.headers.get("authorization") or ""
    if auth != f"Bearer {s.temporal_internal_secret}":
        raise HTTPException(status_code=401, detail="Não autorizado")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    op = body.get("op")
    store_id = body.get("storeId")

    try:
        if op == "refreshAllOAuthTokens":
            out = await refresh_oauth_tokens_all_stores(db)
            return out

        if not isinstance(store_id, str) or not store_id:
            raise HTTPException(status_code=400, detail="Payload inválido")

        if op == "reconcileStale":
            bypass = bool(body.get("bypassRoutineCheck"))
            await reconcile_stale_promo(db, store_id, bypass_routine_check=bypass)
            return {"ok": True}

        if op == "prepareReconcileStale":
            bypass = bool(body.get("bypassRoutineCheck"))
            out = await prepare_reconcile_stale_for_store(
                db, store_id, bypass_routine_check=bypass
            )
            return out

        if op == "finalizeReconcileStale":
            prev = body.get("prevPromoDate")
            if not isinstance(prev, str) or not prev.strip():
                raise HTTPException(status_code=400, detail="prevPromoDate inválido")
            await finalize_reconcile_stale_for_store(db, store_id, prev.strip())
            return {"ok": True}

        if op == "revertPromoMenuItem":
            item_uuid = body.get("itemUuid")
            if not isinstance(item_uuid, str) or not item_uuid.strip():
                raise HTTPException(status_code=400, detail="itemUuid inválido")
            await revert_promo_single_item_for_store(db, store_id, item_uuid.strip())
            return {"ok": True}

        if op == "prepareRevertPromo":
            dk = body.get("dateKey")
            if not isinstance(dk, str) or not dk.strip():
                raise HTTPException(status_code=400, detail="dateKey inválido")
            out = await prepare_revert_promo_for_store(db, store_id, dk.strip())
            return out

        if op == "finalizeRevertPromo":
            dk = body.get("dateKey")
            if not isinstance(dk, str) or not dk.strip():
                raise HTTPException(status_code=400, detail="dateKey inválido")
            await finalize_revert_promo_for_store(db, store_id, dk.strip())
            return {"ok": True}

        if op == "planSlot":
            store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
            st = (
                await db.execute(select(StoreSettings).where(StoreSettings.storeId == store_id))
            ).scalar_one_or_none()
            job = (await db.execute(select(JobState).where(JobState.storeId == store_id))).scalar_one_or_none()
            if not store or not st or not st.routineEnabled:
                return {"slot": None}

            closing_by_dow: dict[int, tuple[int, int]] = {}
            rows: list = []
            try:
                token = await get_access_token_for_store(s, store)

                async def gt() -> str | None:
                    return token

                if not token:
                    log.warning("[planSlot] sem access token OAuth na Store %s — não chama working-hours", store_id)
                else:
                    client = AiqfomeClient(s, gt, allow_env_token_fallback=False)
                    rows = await client.fetch_working_hours(store.externalStoreId)
                closing_by_dow = build_closing_by_dow_js(rows)
            except Exception as e:
                log.warning("[planSlot] working-hours: %s", e)

            if not closing_by_dow:
                return {"slot": None}

            slot = plan_next_promo_slot(
                now=datetime.now(timezone.utc),
                time_zone=store.timeZone,
                closing_by_dow=closing_by_dow,
                lead_minutes=st.leadMinutes,
                weekday_mask=st.activeWeekdays,
                promo_applied_for_date=job.promoAppliedForDate if job else None,
            )
            if not slot:
                return {"slot": None}
            slot_dict = _slot_dict(slot)
            # promoAppliedForDate pode estar setado (ex.: truncate em PriceBaseline) sem snapshot — aí skipApply quebraria o apply.
            if slot_dict.get("skipApply"):
                pb = (
                    await db.execute(select(PriceBaseline).where(PriceBaseline.storeId == store_id))
                ).scalar_one_or_none()
                if not pb or not menu_promo.baseline_is_revertible(pb.payload):
                    slot_dict["skipApply"] = False
                    log.info(
                        "[planSlot] skipApply→false: baseline ausente ou não reversível storeId=%s",
                        store_id,
                    )
            return {"slot": slot_dict}

        if op == "clearPriceBaseline":
            await clear_price_baseline_for_store(db, store_id)
            return {"ok": True}

        if op == "listPromoApplyItemUuids":
            entries = await list_promo_apply_item_entries_for_store(db, store_id)
            uuids = [e["itemUuid"] for e in entries]
            return {"ok": True, "itemUuids": uuids, "itemEntries": entries}

        if op == "preparePromoApply":
            dk = body.get("dateKey")
            if not isinstance(dk, str) or not dk:
                raise HTTPException(status_code=400, detail="Payload inválido")
            result = await prepare_promo_apply_for_store(db, store_id, dk)
            return result

        if op == "applyPromoMenuItem":
            dk = body.get("dateKey")
            item_uuid = body.get("itemUuid")
            if not isinstance(dk, str) or not dk:
                raise HTTPException(status_code=400, detail="dateKey inválido")
            if not isinstance(item_uuid, str) or not item_uuid.strip():
                raise HTTPException(status_code=400, detail="itemUuid inválido")
            await apply_promo_single_item_for_store(db, store_id, item_uuid.strip(), dk)
            return {"ok": True}

        if op == "finalizePromoApply":
            dk = body.get("dateKey")
            if not isinstance(dk, str) or not dk:
                raise HTTPException(status_code=400, detail="Payload inválido")
            await finalize_promo_apply_for_store(db, store_id, dk)
            return {"ok": True}

        if op == "revert":
            dk = body.get("dateKey")
            if not isinstance(dk, str) or not dk:
                raise HTTPException(status_code=400, detail="Payload inválido")
            await revert_promo_for_store(db, store_id, dk)
            return {"ok": True}

        raise HTTPException(status_code=400, detail="Payload inválido")
    except HTTPException:
        raise
    except Exception as e:
        log.exception("[internal/temporal] op=%s storeId=%s", op, store_id)
        raise HTTPException(status_code=500, detail=str(e))

"""Workflow de promoção — Temporal garante retries; PUTs de preço: uma activity por item."""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import (
        apply_promo_menu_item_activity,
        finalize_promo_apply_activity,
        finalize_reconcile_stale_activity,
        finalize_revert_promo_activity,
        get_planned_slot_activity,
        list_promo_apply_item_uuids_activity,
        ms_until_activity,
        prepare_promo_apply_activity,
        prepare_reconcile_stale_activity,
        prepare_revert_promo_activity,
        refresh_all_oauth_tokens_activity,
        revert_promo_menu_item_activity,
    )

_RETRY = RetryPolicy(maximum_attempts=10, initial_interval=timedelta(seconds=10))
_RETRY_OAUTH_REFRESH = RetryPolicy(maximum_attempts=4, initial_interval=timedelta(seconds=30))
_ACTIVITY_TIMEOUT = timedelta(minutes=15)
_OAUTH_REFRESH_ACTIVITY_TIMEOUT = timedelta(minutes=30)
_IDLE = timedelta(hours=1)

_PATCH_APPLY_DISPLAY = "liquida-apply-item-display"


def _coerce_item_plans(raw: object) -> list[dict[str, str]]:
    """Compat: histórico antigo com lista de UUIDs (str); novo formato com dicts."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for x in raw:
        if isinstance(x, str) and x.strip():
            out.append({"itemUuid": x.strip(), "itemName": "", "pricesSummary": ""})
        elif isinstance(x, dict):
            uid = str(x.get("itemUuid") or "").strip()
            if not uid:
                continue
            out.append(
                {
                    "itemUuid": uid,
                    "itemName": str(x.get("itemName") or ""),
                    "pricesSummary": str(x.get("pricesSummary") or ""),
                }
            )
    return out


async def _reconcile_stale_block(store_id: str, bypass_routine_check: bool) -> None:
    data = await workflow.execute_activity(
        prepare_reconcile_stale_activity,
        args=[store_id, bypass_routine_check],
        start_to_close_timeout=_ACTIVITY_TIMEOUT,
        retry_policy=_RETRY,
    )
    if not data.get("ok") or data.get("noop"):
        return
    prev = data["prevPromoDate"]
    plans = _coerce_item_plans(data.get("itemEntries"))
    for plan in plans:
        await workflow.execute_activity(
            revert_promo_menu_item_activity,
            args=[store_id, plan["itemUuid"], plan["itemName"], plan["pricesSummary"]],
            start_to_close_timeout=_ACTIVITY_TIMEOUT,
            retry_policy=_RETRY,
        )
    await workflow.execute_activity(
        finalize_reconcile_stale_activity,
        args=[store_id, prev],
        start_to_close_timeout=_ACTIVITY_TIMEOUT,
        retry_policy=_RETRY,
    )


async def _revert_after_slot_block(store_id: str, date_key: str) -> None:
    data = await workflow.execute_activity(
        prepare_revert_promo_activity,
        args=[store_id, date_key],
        start_to_close_timeout=_ACTIVITY_TIMEOUT,
        retry_policy=_RETRY,
    )
    if not data.get("ok"):
        return
    plans = _coerce_item_plans(data.get("itemEntries"))
    for plan in plans:
        await workflow.execute_activity(
            revert_promo_menu_item_activity,
            args=[store_id, plan["itemUuid"], plan["itemName"], plan["pricesSummary"]],
            start_to_close_timeout=_ACTIVITY_TIMEOUT,
            retry_policy=_RETRY,
        )
    await workflow.execute_activity(
        finalize_revert_promo_activity,
        args=[store_id, date_key],
        start_to_close_timeout=_ACTIVITY_TIMEOUT,
        retry_policy=_RETRY,
    )


@workflow.defn(name="storePromoLifecycleWorkflow")
class StorePromoLifecycleWorkflow:
    @workflow.run
    async def run(self, input: dict) -> None:
        store_id = input["storeId"]
        while True:
            await _reconcile_stale_block(store_id, False)
            slot = await workflow.execute_activity(
                get_planned_slot_activity,
                store_id,
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
                retry_policy=_RETRY,
            )
            if not slot:
                await workflow.sleep(_IDLE)
                continue

            ms_to_start = await workflow.execute_activity(
                ms_until_activity,
                slot["promoStartIso"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            if ms_to_start > 0:
                await workflow.sleep(timedelta(milliseconds=ms_to_start))

            skip_apply = bool(slot.get("skipApply"))
            if not skip_apply:
                raw_plans = await workflow.execute_activity(
                    prepare_promo_apply_activity,
                    args=[store_id, slot["dateKey"]],
                    start_to_close_timeout=_ACTIVITY_TIMEOUT,
                    retry_policy=_RETRY,
                )
            else:
                # Já marcamos promo para este dateKey e estamos na janela (ex.: worker reiniciado).
                # Não rodamos prepare de novo (evita sobrescrever baseline com preço já promocional).
                raw_plans = await workflow.execute_activity(
                    list_promo_apply_item_uuids_activity,
                    store_id,
                    start_to_close_timeout=_ACTIVITY_TIMEOUT,
                    retry_policy=_RETRY,
                )

            plans = _coerce_item_plans(raw_plans)
            use_apply_display = workflow.patched(_PATCH_APPLY_DISPLAY)
            for plan in plans:
                item_uuid = plan["itemUuid"]
                item_name = plan["itemName"]
                prices_summary = plan["pricesSummary"]
                if use_apply_display:
                    apply_args = [store_id, item_uuid, slot["dateKey"], item_name, prices_summary]
                else:
                    apply_args = [store_id, item_uuid, slot["dateKey"]]
                await workflow.execute_activity(
                    apply_promo_menu_item_activity,
                    args=apply_args,
                    start_to_close_timeout=_ACTIVITY_TIMEOUT,
                    retry_policy=_RETRY,
                )

            if not skip_apply:
                await workflow.execute_activity(
                    finalize_promo_apply_activity,
                    args=[store_id, slot["dateKey"]],
                    start_to_close_timeout=_ACTIVITY_TIMEOUT,
                    retry_policy=_RETRY,
                )

            ms_to_end = await workflow.execute_activity(
                ms_until_activity,
                slot["promoEndIso"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            if ms_to_end > 0:
                await workflow.sleep(timedelta(milliseconds=ms_to_end))

            await _revert_after_slot_block(store_id, slot["dateKey"])


@workflow.defn(name="promoReconcileOnceWorkflow")
class PromoReconcileOnceWorkflow:
    @workflow.run
    async def run(self, input: dict) -> None:
        store_id = input["storeId"]
        bypass = bool(input.get("bypassRoutineCheck"))
        await _reconcile_stale_block(store_id, bypass)


@workflow.defn(name="oauthTokenRefreshWorkflow")
class OauthTokenRefreshWorkflow:
    """Loop: renova tokens Magalu de todas as lojas; depois dorme `intervalHours` (default 5h)."""

    @workflow.run
    async def run(self, input: dict) -> None:
        raw = float(input.get("intervalHours") or 5.0)
        hours = max(0.25, min(raw, 168.0))
        interval = timedelta(hours=hours)
        while True:
            await workflow.execute_activity(
                refresh_all_oauth_tokens_activity,
                start_to_close_timeout=_OAUTH_REFRESH_ACTIVITY_TIMEOUT,
                retry_policy=_RETRY_OAUTH_REFRESH,
            )
            await workflow.sleep(interval)

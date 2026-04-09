"""Activities chamam o FastAPI (API interna) — PUTs de preço: um item por activity (durabilidade no Temporal)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx
from temporalio import activity


def _base_url() -> str:
    return os.environ.get("NEXT_APP_URL", "http://127.0.0.1:3000").rstrip("/")


def _secret() -> str:
    s = os.environ.get("TEMPORAL_INTERNAL_SECRET", "")
    if not s:
        raise RuntimeError("TEMPORAL_INTERNAL_SECRET é obrigatório")
    return s


async def _post(payload: dict) -> None:
    url = f"{_base_url()}/api/internal/temporal"
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {_secret()}"},
        )
        r.raise_for_status()


def _item_plans_from_internal_response(data: dict) -> list[dict[str, str]]:
    """Normaliza resposta da API interna (itemEntries preferencial, senão itemUuids)."""
    raw_entries = data.get("itemEntries")
    if isinstance(raw_entries, list) and raw_entries:
        out: list[dict[str, str]] = []
        for x in raw_entries:
            if not isinstance(x, dict):
                continue
            uid = x.get("itemUuid") or x.get("item_uuid")
            if not uid:
                continue
            out.append(
                {
                    "itemUuid": str(uid),
                    "itemName": str(x.get("itemName") or x.get("item_name") or ""),
                    "pricesSummary": str(x.get("pricesSummary") or x.get("prices_summary") or ""),
                }
            )
        if out:
            return out
    uuids = data.get("itemUuids")
    if isinstance(uuids, list):
        return [{"itemUuid": str(u), "itemName": "", "pricesSummary": ""} for u in uuids if u]
    return []


async def _post_json(payload: dict) -> dict:
    url = f"{_base_url()}/api/internal/temporal"
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {_secret()}"},
        )
        r.raise_for_status()
        body = r.json()
        if not isinstance(body, dict):
            raise RuntimeError("Resposta interna: JSON inválido")
        return body


@activity.defn(name="prepareReconcileStaleActivity")
async def prepare_reconcile_stale_activity(store_id: str, bypass_routine_check: bool = False) -> dict:
    payload: dict = {"op": "prepareReconcileStale", "storeId": store_id}
    if bypass_routine_check:
        payload["bypassRoutineCheck"] = True
    return await _post_json(payload)


@activity.defn(name="revertPromoMenuItemActivity")
async def revert_promo_menu_item_activity(
    store_id: str,
    item_uuid: str,
    item_name: str | None = None,
    prices_summary: str | None = None,
) -> None:
    """Um PUT revert por item (retry granular). Nome/preços só para o histórico no Temporal UI."""
    await _post(
        {
            "op": "revertPromoMenuItem",
            "storeId": store_id,
            "itemUuid": item_uuid,
        }
    )


@activity.defn(name="finalizeReconcileStaleActivity")
async def finalize_reconcile_stale_activity(store_id: str, prev_promo_date: str) -> None:
    await _post(
        {
            "op": "finalizeReconcileStale",
            "storeId": store_id,
            "prevPromoDate": prev_promo_date,
        }
    )


@activity.defn(name="prepareRevertPromoActivity")
async def prepare_revert_promo_activity(store_id: str, date_key: str) -> dict:
    return await _post_json(
        {"op": "prepareRevertPromo", "storeId": store_id, "dateKey": date_key}
    )


@activity.defn(name="finalizeRevertPromoActivity")
async def finalize_revert_promo_activity(store_id: str, date_key: str) -> None:
    await _post(
        {"op": "finalizeRevertPromo", "storeId": store_id, "dateKey": date_key}
    )


@activity.defn(name="getPlannedSlotActivity")
async def get_planned_slot_activity(store_id: str) -> dict | None:
    url = f"{_base_url()}/api/internal/temporal"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            url,
            json={"op": "planSlot", "storeId": store_id},
            headers={"Authorization": f"Bearer {_secret()}"},
        )
        r.raise_for_status()
        data = r.json()
        return data.get("slot")


@activity.defn(name="msUntilActivity")
async def ms_until_activity(iso: str) -> int:
    """Wall-clock na activity (resultado gravado no histórico do workflow)."""
    s = iso.replace("Z", "+00:00") if iso.endswith("Z") else iso
    target = datetime.fromisoformat(s)
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta_ms = int((target - now).total_seconds() * 1000)
    return max(0, delta_ms)


@activity.defn(name="listPromoApplyItemUuidsActivity")
async def list_promo_apply_item_uuids_activity(store_id: str) -> list[dict[str, str]]:
    """Lê planos de item do baseline já salvo (uuid + nome + preços para o histórico Temporal)."""
    data = await _post_json({"op": "listPromoApplyItemUuids", "storeId": store_id})
    if not data.get("ok"):
        return []
    return _item_plans_from_internal_response(data)


@activity.defn(name="preparePromoApplyActivity")
async def prepare_promo_apply_activity(store_id: str, date_key: str) -> list[dict[str, str]]:
    """Baseline + commit no Postgres; retorna lista de {itemUuid, itemName, pricesSummary} (ordem estável)."""
    data = await _post_json(
        {"op": "preparePromoApply", "storeId": store_id, "dateKey": date_key}
    )
    if not data.get("ok"):
        raise RuntimeError(str(data.get("detail") or "preparePromoApply falhou"))
    return _item_plans_from_internal_response(data)


@activity.defn(name="applyPromoMenuItemActivity")
async def apply_promo_menu_item_activity(
    store_id: str,
    item_uuid: str,
    date_key: str,
    item_name: str | None = None,
    prices_summary: str | None = None,
) -> None:
    """Um PUT update-item na aiqfome por execução (retry granular no Temporal).

    item_name e prices_summary são só para aparecer no input da activity no Temporal Web UI.
    """
    await _post(
        {
            "op": "applyPromoMenuItem",
            "storeId": store_id,
            "itemUuid": item_uuid,
            "dateKey": date_key,
        }
    )


@activity.defn(name="finalizePromoApplyActivity")
async def finalize_promo_apply_activity(store_id: str, date_key: str) -> None:
    """Marca job (promoAppliedForDate) após todos os itens."""
    await _post({"op": "finalizePromoApply", "storeId": store_id, "dateKey": date_key})


@activity.defn(name="revertPromoActivity")
async def revert_promo_activity(store_id: str, date_key: str) -> None:
    await _post({"op": "revert", "storeId": store_id, "dateKey": date_key})


@activity.defn(name="refreshAllOAuthTokensActivity")
async def refresh_all_oauth_tokens_activity() -> dict:
    """Renova access (e refresh se a Magalu devolver) para todas as lojas com refresh no banco."""
    return await _post_json({"op": "refreshAllOAuthTokens"})

import logging
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aiqfome_client import AiqfomeClient, is_dry_run_placeholder_item_uuid
from app.config import Settings, get_settings
from app.crypto_secret import decrypt_secret
from app.ids import cuid
from app import menu_promo
from app.models import JobState, PriceBaseline, Store, StoreSettings

log = logging.getLogger(__name__)


async def _load_store_bundle(
    session: AsyncSession, store_id: str
) -> tuple[Store | None, StoreSettings | None, JobState | None, PriceBaseline | None]:
    store = (await session.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    if not store:
        return None, None, None, None
    settings = (
        await session.execute(select(StoreSettings).where(StoreSettings.storeId == store_id))
    ).scalar_one_or_none()
    job = (await session.execute(select(JobState).where(JobState.storeId == store_id))).scalar_one_or_none()
    baseline = (
        await session.execute(select(PriceBaseline).where(PriceBaseline.storeId == store_id))
    ).scalar_one_or_none()
    return store, settings, job, baseline


async def get_access_token_for_store(settings: Settings, store: Store) -> str | None:
    """
    Token Bearer da própria linha `Store` (OAuth Magalu). Nunca misturar com AIQFOME_ACCESS_TOKEN do .env:
    o path da API usa `externalStoreId` desta loja; o Bearer precisa ser do mesmo vínculo.
    """
    tok = (store.accessToken or "").strip()
    if tok:
        return tok
    if not store.encryptedRefresh:
        return None
    try:
        decrypt_secret(store.encryptedRefresh, settings.encryption_key_hex())
    except Exception:
        return None
    return (store.accessToken or "").strip() or None


def _client_for_token(settings: Settings, token: str | None) -> AiqfomeClient:
    async def gt() -> str | None:
        return token

    return AiqfomeClient(settings, gt, allow_env_token_fallback=False)


async def prepare_reconcile_stale_for_store(
    session: AsyncSession,
    store_id: str,
    *,
    bypass_routine_check: bool = False,
) -> dict[str, Any]:
    """
    Decide se há reconciliação a fazer e devolve a lista de itens (Temporal: uma activity de revert por item).
    """
    s = get_settings()
    store, st, job, baseline = await _load_store_bundle(session, store_id)
    now = datetime.now(timezone.utc)

    if not store or not st or not job:
        return {"ok": True, "noop": True}
    if not bypass_routine_check and not st.routineEnabled:
        return {"ok": True, "noop": True}

    z_now = now.astimezone(ZoneInfo(store.timeZone))
    date_key = z_now.strftime("%Y-%m-%d")
    applied = job.promoAppliedForDate
    if not applied:
        return {"ok": True, "noop": True}
    stale = applied < date_key
    if not bypass_routine_check and not stale:
        return {"ok": True, "noop": True}

    entries: list[dict[str, str]] = []
    if baseline and s.writes_enabled() and menu_promo.baseline_is_revertible(baseline.payload):
        entries = menu_promo.item_entries_from_baseline_json(baseline.payload)

    if entries:
        access = await get_access_token_for_store(s, store)
        if not access:
            await _upsert_job_state(
                session,
                store_id,
                now,
                last_error="Sem access token OAuth para chamar a aiqfome",
            )
            await session.commit()
            return {
                "ok": False,
                "noop": True,
                "detail": "Sem access token OAuth (entre de novo com Magalu)",
            }

    return {
        "ok": True,
        "noop": False,
        "prevPromoDate": applied,
        "itemEntries": entries,
    }


async def finalize_reconcile_stale_for_store(
    session: AsyncSession, store_id: str, prev_promo_date: str
) -> None:
    now = datetime.now(timezone.utc)
    _, _, job, _ = await _load_store_bundle(session, store_id)
    if job is None:
        job = JobState(id=cuid(), storeId=store_id)
        session.add(job)
    job.promoAppliedForDate = None
    job.lastRevertDate = prev_promo_date
    job.lastError = None
    job.lastRunAt = now
    await session.commit()


async def revert_promo_single_item_for_store(session: AsyncSession, store_id: str, item_uuid: str) -> None:
    """Um PUT na aiqfome para um item, restaurando preço de lista do baseline (Temporal: uma activity por item)."""
    s = get_settings()
    store, st, _, baseline = await _load_store_bundle(session, store_id)
    if not store or not st:
        raise RuntimeError("Loja ou config não encontrada")
    if not baseline or not menu_promo.baseline_is_revertible(baseline.payload):
        raise RuntimeError("Baseline de preços ausente ou inválido — rode preparePromoApply antes")

    access = await get_access_token_for_store(s, store)
    if not access:
        raise RuntimeError("Sem access token OAuth para chamar a aiqfome")
    if not s.aiqfome_dry_run and is_dry_run_placeholder_item_uuid(item_uuid):
        raise RuntimeError(
            "Baseline ainda tem UUID de simulação (dry-run). Com AIQFOME_DRY_RUN=false, chame POST /api/internal/temporal "
            'com {"op":"clearPriceBaseline","storeId":"..."} (Bearer TEMPORAL_INTERNAL_SECRET) para apagar o snapshot; '
            "no próximo ciclo o workflow roda preparePromoApply com cardápio real."
        )
    client = _client_for_token(s, access)

    await menu_promo.revert_put_single_item(
        client,
        store.externalStoreId,
        baseline.payload,
        item_uuid,
        dry_run=s.aiqfome_dry_run,
    )


async def reconcile_stale_promo(
    session: AsyncSession,
    store_id: str,
    *,
    bypass_routine_check: bool = False,
) -> None:
    """
    Caminho “all-in-one” (ex.: op legada `reconcileStale`): mesmo efeito que prepare + N reverts + finalize.
    """
    prep = await prepare_reconcile_stale_for_store(
        session, store_id, bypass_routine_check=bypass_routine_check
    )
    if not prep.get("ok") or prep.get("noop"):
        return
    now = datetime.now(timezone.utc)
    prev = str(prep["prevPromoDate"])
    try:
        for entry in prep.get("itemEntries") or []:
            if isinstance(entry, dict) and entry.get("itemUuid"):
                await revert_promo_single_item_for_store(
                    session, store_id, str(entry["itemUuid"]).strip()
                )
    except Exception as e:
        await _upsert_job_state(session, store_id, now, last_error=str(e))
        await session.commit()
        return
    await finalize_reconcile_stale_for_store(session, store_id, prev)


def _promo_category_ids(st: StoreSettings) -> list[int]:
    raw = st.promoCategoryIds
    if not raw:
        return []
    return [int(x) for x in raw]


async def clear_price_baseline_for_store(session: AsyncSession, store_id: str) -> None:
    """
    Remove PriceBaseline e zera promoAppliedForDate (próximo ciclo Temporal roda prepare de novo).
    Use após baseline criado com AIQFOME_DRY_RUN=true ou para desbloquear skipApply preso.
    """
    await session.execute(delete(PriceBaseline).where(PriceBaseline.storeId == store_id))
    job = (await session.execute(select(JobState).where(JobState.storeId == store_id))).scalar_one_or_none()
    if job:
        job.promoAppliedForDate = None
        job.lastError = None
    await session.commit()
    log.info("[promo] clearPriceBaseline storeId=%s", store_id)


async def _upsert_price_baseline(session: AsyncSession, store_id: str, payload: str) -> None:
    pb = (await session.execute(select(PriceBaseline).where(PriceBaseline.storeId == store_id))).scalar_one_or_none()
    if pb:
        pb.payload = payload
    else:
        session.add(PriceBaseline(id=cuid(), storeId=store_id, payload=payload))
    await session.flush()


async def prepare_promo_apply_for_store(
    session: AsyncSession, store_id: str, date_key: str
) -> dict[str, object]:
    """
    Captura baseline e persiste em PriceBaseline (commit). Não aplica PUTs.
    Retorno para Temporal: ok, itemUuids, itemEntries (nome + preços para o histórico), detail.
    """
    s = get_settings()
    store, st, *_ = await _load_store_bundle(session, store_id)
    now = datetime.now(timezone.utc)

    if not store or not st:
        return {"ok": False, "itemUuids": [], "detail": "Loja ou config não encontrada"}

    category_ids = _promo_category_ids(st)
    if not category_ids:
        await _upsert_job_state(
            session,
            store_id,
            now,
            last_error="Nenhuma categoria selecionada para promoção (salve em Categorias do cardápio)",
        )
        await session.commit()
        return {"ok": False, "itemUuids": [], "detail": "Nenhuma categoria selecionada para promoção"}

    if not s.writes_enabled():
        await _upsert_job_state(
            session,
            store_id,
            now,
            last_error="ENABLE_PROMO_WRITE=false",
        )
        await session.commit()
        return {"ok": False, "itemUuids": [], "detail": "ENABLE_PROMO_WRITE=false"}

    access = await get_access_token_for_store(s, store)
    if not access:
        await _upsert_job_state(
            session,
            store_id,
            now,
            last_error="Sem access token OAuth para chamar a aiqfome",
        )
        await session.commit()
        return {"ok": False, "itemUuids": [], "detail": "Sem access token OAuth (entre de novo com Magalu)"}

    if s.aiqfome_dry_run:
        detail = (
            "AIQFOME_DRY_RUN=true: o mock da API usa itens com UUIDs que não existem na plataforma real "
            "(PUT retornaria 404). Defina AIQFOME_DRY_RUN=false no backend, reinicie e rode preparePromoApply de novo."
        )
        await _upsert_job_state(session, store_id, now, last_error=detail)
        await session.commit()
        return {"ok": False, "itemUuids": [], "itemEntries": [], "detail": detail}

    client = _client_for_token(s, access)

    try:
        baseline_json = await menu_promo.build_baseline_payload(
            client, store.externalStoreId, category_ids
        )
    except Exception as e:
        await _upsert_job_state(session, store_id, now, last_error=str(e))
        await session.commit()
        return {"ok": False, "itemUuids": [], "detail": str(e)}

    await _upsert_price_baseline(session, store_id, baseline_json)
    await session.commit()

    uuids = menu_promo.item_uuids_from_baseline_json(baseline_json)
    entries = menu_promo.item_entries_from_baseline_json(baseline_json)
    return {"ok": True, "itemUuids": uuids, "itemEntries": entries, "detail": None}


async def apply_promo_single_item_for_store(
    session: AsyncSession, store_id: str, item_uuid: str, date_key: str
) -> None:
    """
    Um PUT na aiqfome para um item, usando baseline e desconto já salvos.
    """
    if not isinstance(date_key, str) or not date_key.strip():
        raise RuntimeError("dateKey inválido")
    s = get_settings()
    store, st, _, baseline = await _load_store_bundle(session, store_id)
    if not store or not st:
        raise RuntimeError("Loja ou config não encontrada")
    if not baseline or not menu_promo.baseline_is_revertible(baseline.payload):
        raise RuntimeError("Baseline de preços ausente ou inválido — rode preparePromoApply antes")

    access = await get_access_token_for_store(s, store)
    if not access:
        raise RuntimeError("Sem access token OAuth para chamar a aiqfome")
    if not s.aiqfome_dry_run and is_dry_run_placeholder_item_uuid(item_uuid):
        raise RuntimeError(
            "Baseline ainda tem UUID de simulação (dry-run). Com AIQFOME_DRY_RUN=false, chame POST /api/internal/temporal "
            'com {"op":"clearPriceBaseline","storeId":"..."} (Bearer TEMPORAL_INTERNAL_SECRET) para apagar o snapshot; '
            "no próximo ciclo o workflow roda preparePromoApply com cardápio real."
        )
    client = _client_for_token(s, access)

    await menu_promo.apply_put_single_item(
        client,
        store.externalStoreId,
        baseline.payload,
        item_uuid,
        st.discountPercent,
        dry_run=s.aiqfome_dry_run,
    )


async def list_promo_apply_item_entries_for_store(session: AsyncSession, store_id: str) -> list[dict[str, str]]:
    """
    Com baseline reversível: entradas do snapshot (nome + preços).
    Sem baseline: lista uuid/nome via GET list-items nas categorias salvas (preview; pricesSummary = "—").
    """
    store, st, job, baseline = await _load_store_bundle(session, store_id)
    if not store or not st:
        return []
    if baseline and menu_promo.baseline_is_revertible(baseline.payload):
        return menu_promo.item_entries_from_baseline_json(baseline.payload)

    z_now = datetime.now(timezone.utc).astimezone(ZoneInfo(store.timeZone))
    date_key = z_now.strftime("%Y-%m-%d")
    if job and job.promoAppliedForDate == date_key:
        log.warning(
            "[list_promo_apply_item_entries] storeId=%s: baseline ausente mas promoAppliedForDate=%s (hoje local). "
            "Listagem é preview; apply no Temporal exige preparePromoApply ou clearPriceBaseline.",
            store_id,
            job.promoAppliedForDate,
        )

    category_ids = _promo_category_ids(st)
    if not category_ids:
        return []

    s = get_settings()
    access = await get_access_token_for_store(s, store)
    if not access:
        log.warning("[list_promo_apply_item_entries] sem token OAuth storeId=%s", store_id)
        return []

    client = _client_for_token(s, access)
    try:
        return await menu_promo.preview_item_entries_from_category_lists(
            client, store.externalStoreId, category_ids
        )
    except Exception as e:
        log.warning("[list_promo_apply_item_entries] preview API storeId=%s: %s", store_id, e)
        return []


async def finalize_promo_apply_for_store(session: AsyncSession, store_id: str, date_key: str) -> None:
    now = datetime.now(timezone.utc)
    await _upsert_job_state(
        session,
        store_id,
        now,
        clear_last_error=True,
        promo_applied_for_date=date_key,
    )
    await session.commit()


async def prepare_revert_promo_for_store(session: AsyncSession, store_id: str, date_key: str) -> dict[str, Any]:
    """Valida loja / writes / token; lista itens do baseline para revert item a item no Temporal."""
    s = get_settings()
    store, st, _, baseline = await _load_store_bundle(session, store_id)
    now = datetime.now(timezone.utc)

    if not store or not st:
        return {"ok": False, "detail": "Loja ou config não encontrada", "itemEntries": []}

    if not s.writes_enabled():
        await _upsert_job_state(
            session,
            store_id,
            now,
            last_error="ENABLE_PROMO_WRITE=false (revert)",
        )
        await session.commit()
        return {"ok": False, "detail": "ENABLE_PROMO_WRITE=false (revert)", "itemEntries": []}

    entries: list[dict[str, str]] = []
    if baseline and menu_promo.baseline_is_revertible(baseline.payload):
        entries = menu_promo.item_entries_from_baseline_json(baseline.payload)

    if entries:
        access = await get_access_token_for_store(s, store)
        if not access:
            await _upsert_job_state(
                session,
                store_id,
                now,
                last_error="Sem access token OAuth para chamar a aiqfome",
            )
            await session.commit()
            return {
                "ok": False,
                "detail": "Sem access token OAuth (entre de novo com Magalu)",
                "itemEntries": [],
            }

    return {"ok": True, "itemEntries": entries}


async def finalize_revert_promo_for_store(session: AsyncSession, store_id: str, date_key: str) -> None:
    now = datetime.now(timezone.utc)
    await _upsert_job_state(
        session,
        store_id,
        now,
        clear_last_error=True,
        clear_promo_applied=True,
        last_revert_date=date_key,
    )
    await session.commit()


async def revert_promo_for_store(session: AsyncSession, store_id: str, date_key: str) -> None:
    """Caminho all-in-one (op `revert`): prepare + N reverts + finalize."""
    prep = await prepare_revert_promo_for_store(session, store_id, date_key)
    if not prep.get("ok"):
        return
    now = datetime.now(timezone.utc)
    try:
        for entry in prep.get("itemEntries") or []:
            if isinstance(entry, dict) and entry.get("itemUuid"):
                await revert_promo_single_item_for_store(
                    session, store_id, str(entry["itemUuid"]).strip()
                )
    except Exception as e:
        await _upsert_job_state(session, store_id, now, last_error=str(e))
        await session.commit()
        return
    await finalize_revert_promo_for_store(session, store_id, date_key)


async def _upsert_job_state(
    session: AsyncSession,
    store_id: str,
    now: datetime,
    *,
    last_error: str | None = None,
    clear_last_error: bool = False,
    promo_applied_for_date: str | None = None,
    clear_promo_applied: bool = False,
    last_revert_date: str | None = None,
) -> None:
    job = (await session.execute(select(JobState).where(JobState.storeId == store_id))).scalar_one_or_none()
    if job is None:
        job = JobState(id=cuid(), storeId=store_id)
        session.add(job)
    job.lastRunAt = now
    if clear_last_error:
        job.lastError = None
    elif last_error is not None:
        job.lastError = last_error
    if promo_applied_for_date is not None:
        job.promoAppliedForDate = promo_applied_for_date
    if clear_promo_applied:
        job.promoAppliedForDate = None
    if last_revert_date is not None:
        job.lastRevertDate = last_revert_date
    await session.flush()

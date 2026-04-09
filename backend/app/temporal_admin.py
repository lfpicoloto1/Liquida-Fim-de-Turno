import uuid
from datetime import timedelta

from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

from app.config import get_settings

_client: Client | None = None


def promo_workflow_id(store_id: str) -> str:
    return f"liquida-promo-{store_id}"


OAUTH_TOKEN_REFRESH_WORKFLOW_ID = "liquida-oauth-token-refresh"


async def get_temporal_client() -> Client:
    global _client
    if _client is None:
        s = get_settings()
        _client = await Client.connect(s.temporal_address, namespace=s.temporal_namespace)
    return _client


async def start_or_restart_promo_workflow(store_id: str) -> None:
    s = get_settings()
    if not s.use_temporal:
        return
    client = await get_temporal_client()
    wid = promo_workflow_id(store_id)
    handle = client.get_workflow_handle(wid)
    try:
        await handle.terminate("restart")
    except Exception:
        pass
    await client.start_workflow(
        "storePromoLifecycleWorkflow",
        {"storeId": store_id},
        id=wid,
        task_queue=s.temporal_task_queue,
        execution_timeout=timedelta(days=3650),
        run_timeout=timedelta(days=3650),
    )


async def stop_promo_workflow(store_id: str) -> None:
    s = get_settings()
    if not s.use_temporal:
        return
    client = await get_temporal_client()
    try:
        await client.get_workflow_handle(promo_workflow_id(store_id)).terminate("routine_disabled")
    except Exception:
        pass


async def reconcile_promo_once_via_temporal(store_id: str, *, bypass_routine_check: bool) -> None:
    """
    Uma execução de reconcile (mesma API interna que o lifecycle no primeiro passo).
    Com bypass, permite limpar promo do dia após desligar a rotina (settings já commitados).
    """
    s = get_settings()
    if not s.use_temporal:
        from app.database import get_session_factory
        from app.promo_actions import reconcile_stale_promo

        fac = get_session_factory()
        async with fac() as session:
            await reconcile_stale_promo(session, store_id, bypass_routine_check=bypass_routine_check)
        return

    client = await get_temporal_client()
    wid = f"liquida-promo-reconcile-once-{store_id}-{uuid.uuid4().hex[:10]}"
    handle = await client.start_workflow(
        "promoReconcileOnceWorkflow",
        {"storeId": store_id, "bypassRoutineCheck": bypass_routine_check},
        id=wid,
        task_queue=s.temporal_task_queue,
        execution_timeout=timedelta(minutes=30),
    )
    await handle.result()


async def ensure_oauth_token_refresh_workflow() -> None:
    """
    Garante workflow global que renova tokens Magalu de todas as lojas a cada N horas
    (activity chama API interna `refreshAllOAuthTokens`).
    """
    s = get_settings()
    if not s.use_temporal:
        return
    client = await get_temporal_client()
    try:
        await client.start_workflow(
            "oauthTokenRefreshWorkflow",
            {"intervalHours": float(s.oauth_refresh_interval_hours)},
            id=OAUTH_TOKEN_REFRESH_WORKFLOW_ID,
            task_queue=s.temporal_task_queue,
            execution_timeout=timedelta(days=36500),
            run_timeout=timedelta(days=36500),
        )
    except WorkflowAlreadyStartedError:
        pass

"""Worker Temporal (Python). Carrega .env do repo se existir."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

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
from workflows import OauthTokenRefreshWorkflow, PromoReconcileOnceWorkflow, StorePromoLifecycleWorkflow


def _load_env() -> None:
    """Monorepo: raiz do repo, depois `temporal/`. Repositório só worker: pasta do worker."""
    here = Path(__file__).resolve().parent
    parent = here.parent
    roots: list[Path] = []
    if (parent / "front").is_dir() and (parent / "temporal").is_dir():
        roots.append(parent)
    roots.append(here)
    for root in roots:
        for name in (".env", ".env.local"):
            p = root / name
            if p.is_file():
                load_dotenv(p, override=True)


async def main() -> None:
    _load_env()
    if not os.environ.get("TEMPORAL_INTERNAL_SECRET", "").strip():
        print(
            "Erro: TEMPORAL_INTERNAL_SECRET vazio. Defina em .env.local ou .env "
            "(o mesmo valor que o FastAPI usa em /api/internal/temporal).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    address = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE", "liquida-promo")

    client = await Client.connect(address, namespace=namespace)
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[
            StorePromoLifecycleWorkflow,
            PromoReconcileOnceWorkflow,
            OauthTokenRefreshWorkflow,
        ],
        activities=[
            refresh_all_oauth_tokens_activity,
            prepare_reconcile_stale_activity,
            revert_promo_menu_item_activity,
            finalize_reconcile_stale_activity,
            prepare_revert_promo_activity,
            finalize_revert_promo_activity,
            get_planned_slot_activity,
            ms_until_activity,
            list_promo_apply_item_uuids_activity,
            prepare_promo_apply_activity,
            apply_promo_menu_item_activity,
            finalize_promo_apply_activity,
        ],
    )
    print(
        f"Temporal worker (Python) — queue={task_queue} namespace={namespace} {address}",
        file=sys.stderr,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

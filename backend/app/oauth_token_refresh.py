"""Renovação em lote dos tokens Magalu (access + refresh rotativo) persistidos em `Store`."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.crypto_secret import decrypt_secret, encrypt_secret
from app.magalu_oauth import refresh_access_token
from app.models import Store

log = logging.getLogger(__name__)


async def refresh_oauth_tokens_all_stores(session: AsyncSession, *, settings: Settings | None = None) -> dict[str, Any]:
    """
    Para cada loja com `encryptedRefresh`, chama o endpoint de refresh da Magalu e grava
    `accessToken`, `accessExpiresAt` e novo refresh cifrado quando a API devolver.
    """
    s = settings or get_settings()
    if not s.magalu_client_id or not s.magalu_client_secret:
        log.warning("[oauth-refresh] MAGALU_CLIENT_ID / MAGALU_CLIENT_SECRET ausentes — ignorado")
        return {
            "ok": True,
            "refreshed": 0,
            "failed": 0,
            "skipped": 0,
            "detail": "oauth_not_configured",
        }

    key_hex = s.encryption_key_hex()
    result = await session.execute(
        select(Store).where(Store.encryptedRefresh.is_not(None)).where(Store.encryptedRefresh != "")
    )
    stores = list(result.scalars().all())

    refreshed = 0
    failed = 0
    skipped = 0

    for store in stores:
        blob = (store.encryptedRefresh or "").strip()
        if not blob:
            skipped += 1
            continue
        try:
            rt_plain = decrypt_secret(blob, key_hex)
        except Exception as e:
            log.warning("[oauth-refresh] decrypt falhou storeId=%s: %s", store.id, e)
            failed += 1
            continue
        try:
            tokens = await refresh_access_token(s, rt_plain)
        except Exception as e:
            log.warning("[oauth-refresh] Magalu refresh falhou storeId=%s: %s", store.id, e)
            failed += 1
            continue

        access_token = tokens.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            log.warning("[oauth-refresh] resposta sem access_token storeId=%s", store.id)
            failed += 1
            continue

        store.accessToken = access_token.strip()
        exp_in = tokens.get("expires_in")
        if exp_in is not None:
            try:
                store.accessExpiresAt = datetime.now(timezone.utc) + timedelta(seconds=int(exp_in))
            except (TypeError, ValueError):
                store.accessExpiresAt = None

        new_rt = tokens.get("refresh_token")
        if isinstance(new_rt, str) and new_rt.strip():
            store.encryptedRefresh = encrypt_secret(new_rt.strip(), key_hex)

        await session.commit()
        refreshed += 1
        log.info("[oauth-refresh] ok storeId=%s externalStoreId=%s", store.id, store.externalStoreId)

    return {"ok": True, "refreshed": refreshed, "failed": failed, "skipped": skipped}

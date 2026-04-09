from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth_store_pick import parse_oauth_state_for_store_id, pick_store_row
from app.ids import cuid

from app.aiqfome_client import AiqfomeClient
from app.config import Settings, get_settings
from app.constants import SESSION_COOKIE, SESSION_MAX_AGE_SEC
from app.crypto_secret import encrypt_secret
from app.database import get_db
from app.magalu_oauth import exchange_authorization_code
from app.models import Session as DbSession, Store

router = APIRouter(tags=["auth"])


class TokenBody(BaseModel):
    code: str | None = Field(None, min_length=4)
    redirectUri: str | None = None
    externalStoreId: str | None = Field(None, max_length=128)
    oauthState: str | None = Field(
        None,
        max_length=4096,
        description="Eco do OAuth `state` no redirect (ex.: base64 JSON com externalStoreId).",
    )


def _wants_dev_login_shortcut(s: Settings, body: TokenBody) -> bool:
    """Atalho dev só sem `code` Magalu. Com código, troca token de verdade (mesmo com SKIP_OAUTH_VALIDATION)."""
    if not s.dev_oauth_skip():
        return False
    code = (body.code or "").strip()
    return len(code) < 4


@router.post("/api/auth/magalu/token")
async def magalu_token(
    body: TokenBody,
    db: AsyncSession = Depends(get_db),
):
    s = get_settings()

    if _wants_dev_login_shortcut(s, body):
        ext = (
            (body.externalStoreId or "").strip()
            or (s.aiqfome_dev_external_store_id or "").strip()
            or "default-store"
        )
        store = (await db.execute(select(Store).where(Store.externalStoreId == ext))).scalar_one_or_none()
        if not store:
            store = Store(
                id=cuid(),
                externalStoreId=ext,
                timeZone="America/Sao_Paulo",
                displayName="Loja (dev)",
            )
            db.add(store)
            await db.flush()
        else:
            store.displayName = "Loja (dev)"
        await db.commit()
        await db.refresh(store)

        sess = DbSession(id=cuid(), storeId=store.id, expiresAt=_session_expiry())
        db.add(sess)
        await db.commit()

        resp = JSONResponse({"ok": True, "dev": True})
        _set_session_cookie(resp, sess.id, s)
        return resp

    redirect_uri = body.redirectUri or s.magalu_redirect_uri or ""
    code = body.code
    if not code or not redirect_uri:
        raise HTTPException(status_code=400, detail="code e redirectUri obrigatórios")

    try:
        tokens = await exchange_authorization_code(s, code, redirect_uri)
        key = s.encryption_key_hex()
        enc_refresh = encrypt_secret(tokens["refresh_token"], key) if tokens.get("refresh_token") else None
        exp_in = tokens.get("expires_in")
        expires_at = None
        if exp_in is not None:
            from datetime import datetime, timedelta, timezone

            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(exp_in))

        access_token = tokens["access_token"]

        async def gt() -> str | None:
            return access_token

        aiq = AiqfomeClient(s, gt, allow_env_token_fallback=False)
        stores = await aiq.list_stores()
        preferred = (body.externalStoreId or "").strip() or parse_oauth_state_for_store_id(
            body.oauthState
        )
        try:
            primary = pick_store_row(stores, preferred)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        external_store_id = str(primary["id"])
        display_name = primary.get("name")

        store = (await db.execute(select(Store).where(Store.externalStoreId == external_store_id))).scalar_one_or_none()
        if not store:
            store = Store(
                id=cuid(),
                externalStoreId=external_store_id,
                timeZone="America/Sao_Paulo",
                displayName=display_name,
                accessToken=access_token,
                accessExpiresAt=expires_at,
                encryptedRefresh=enc_refresh,
            )
            db.add(store)
            await db.flush()
        else:
            store.displayName = display_name or store.displayName
            store.accessToken = access_token
            store.accessExpiresAt = expires_at
            if enc_refresh is not None:
                store.encryptedRefresh = enc_refresh

        await db.commit()
        await db.refresh(store)

        sess = DbSession(id=cuid(), storeId=store.id, expiresAt=_session_expiry())
        db.add(sess)
        await db.commit()

        resp = JSONResponse({"ok": True})
        _set_session_cookie(resp, sess.id, s)
        return resp
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        raise HTTPException(status_code=502, detail=msg or "Erro OAuth")


def _session_expiry():
    from datetime import datetime, timedelta, timezone

    return datetime.now(timezone.utc) + timedelta(seconds=SESSION_MAX_AGE_SEC)


def _set_session_cookie(resp: JSONResponse, session_id: str, s: Settings) -> None:
    """SameSite=None + Secure quando em produção/HTTPS para Set-Cookie em fetch cross-origin (Geraldo → Liquida)."""
    secure = s.session_cookie_secure
    resp.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        secure=secure,
        samesite=s.session_cookie_samesite,
        max_age=SESSION_MAX_AGE_SEC,
        path="/",
    )

import httpx

from app.config import Settings


async def exchange_authorization_code(
    settings: Settings,
    code: str,
    redirect_uri: str,
) -> dict:
    cid = settings.magalu_client_id
    sec = settings.magalu_client_secret
    if not cid or not sec:
        raise RuntimeError("Magalu OAuth não configurado (MAGALU_CLIENT_ID / MAGALU_CLIENT_SECRET)")

    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": cid,
        "client_secret": sec,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            settings.magalu_token_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if r.status_code >= 400:
        raise RuntimeError(f"Magalu token exchange failed: {r.status_code} {r.text[:200]}")
    return r.json()


async def refresh_access_token(settings: Settings, refresh_token_plain: str) -> dict:
    """OAuth2 refresh_token grant — atualiza access (e opcionalmente refresh) na Magalu."""
    cid = settings.magalu_client_id
    sec = settings.magalu_client_secret
    if not cid or not sec:
        raise RuntimeError("Magalu OAuth não configurado (MAGALU_CLIENT_ID / MAGALU_CLIENT_SECRET)")
    if not (refresh_token_plain or "").strip():
        raise RuntimeError("refresh_token vazio")

    body = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_plain.strip(),
        "client_id": cid,
        "client_secret": sec,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            settings.magalu_token_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if r.status_code >= 400:
        raise RuntimeError(f"Magalu token refresh failed: {r.status_code} {r.text[:200]}")
    return r.json()

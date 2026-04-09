from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import SESSION_COOKIE
from app.database import get_db
from app.models import Session as DbSession


def _session_expired(expires_at: datetime) -> bool:
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        exp = expires_at.replace(tzinfo=timezone.utc)
    else:
        exp = expires_at.astimezone(timezone.utc)
    return exp < now


async def session_store_id(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> str:
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        raise HTTPException(status_code=401, detail="Não autenticado")
    row = (await db.execute(select(DbSession).where(DbSession.id == sid))).scalar_one_or_none()
    if not row or _session_expired(row.expiresAt):
        raise HTTPException(status_code=401, detail="Não autenticado")
    return row.storeId


async def optional_session_store_id(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> str | None:
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        return None
    row = (await db.execute(select(DbSession).where(DbSession.id == sid))).scalar_one_or_none()
    if not row or _session_expired(row.expiresAt):
        return None
    return row.storeId

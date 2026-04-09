from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import SESSION_COOKIE
from app.database import get_db
from app.models import Session as DbSession

router = APIRouter(tags=["auth"])


@router.post("/api/auth/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        await db.execute(delete(DbSession).where(DbSession.id == sid))
        await db.commit()

    s = get_settings()
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    resp.set_cookie(
        SESSION_COOKIE,
        "",
        httponly=True,
        secure=s.is_production,
        samesite="lax",
        max_age=0,
        path="/",
    )
    return resp

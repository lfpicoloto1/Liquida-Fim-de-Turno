import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.routers import auth_logout, auth_magalu, health, internal_temporal, me, store_settings
from app.temporal_admin import ensure_oauth_token_refresh_workflow

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if get_settings().use_temporal:
        try:
            await ensure_oauth_token_refresh_workflow()
        except Exception:
            log.exception("[lifespan] ensure_oauth_token_refresh_workflow falhou (Temporal indisponível?)")
    yield


app = FastAPI(title="Liquida Fim de Turno API", lifespan=lifespan)

app.include_router(health.router)
app.include_router(me.router)
app.include_router(store_settings.router)
app.include_router(auth_magalu.router)
app.include_router(auth_logout.router)
app.include_router(internal_temporal.router)

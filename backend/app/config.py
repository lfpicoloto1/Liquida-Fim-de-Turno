from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_asyncpg_unsupported_query_params(url: str) -> str:
    """Prisma usa `?schema=public`; asyncpg não aceita o argumento `schema` em connect()."""
    parts = urlsplit(url)
    if not parts.query:
        return url
    pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() != "schema"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), parts.fragment))


def _env_file_paths() -> tuple[str, ...]:
    """Monorepo: raiz do repo + pasta backend/. Repositório só backend: só backend/."""
    backend_root = Path(__file__).resolve().parents[1]
    parent = backend_root.parent
    ordered: list[Path] = []
    if (parent / "front").is_dir() and (parent / "backend" / "app").is_dir():
        for name in (".env", ".env.local"):
            p = parent / name
            if p.is_file():
                ordered.append(p)
    for name in (".env", ".env.local"):
        p = backend_root / name
        if p.is_file():
            ordered.append(p)
    return tuple(str(p) for p in ordered)


_ENV_FILES: tuple[str, ...] = _env_file_paths()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES or None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = Field(
        default="postgresql://liquida:liquida@localhost:5432/liquida?schema=public",
    )
    node_env: str = Field(default="development")
    skip_oauth_validation: bool = False
    token_encryption_key: str | None = None

    magalu_client_id: str | None = None
    magalu_client_secret: str | None = None
    magalu_redirect_uri: str | None = None
    magalu_token_url: str = "https://id.magalu.com/oauth/token"

    aiqfome_api_base_url: str = "https://api.aiqfome.com"
    aiqfome_platform_base_url: str = "https://plataforma.aiqfome.com"
    aiqfome_access_token: str | None = None
    aiqfome_dev_external_store_id: str | None = Field(
        default=None,
        description="Login dev: ID da loja na plataforma (gravado em Store.externalStoreId). Env: AIQFOME_DEV_EXTERNAL_STORE_ID",
    )
    aiqfome_dry_run: bool = True
    enable_promo_write: bool = True

    use_temporal: bool = True
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "liquida-promo"
    temporal_internal_secret: str | None = None

    oauth_refresh_interval_hours: float = Field(
        default=5.0,
        description="Intervalo do workflow Temporal que renova tokens Magalu de todas as lojas (horas). Env: OAUTH_REFRESH_INTERVAL_HOURS",
    )

    @field_validator(
        "enable_promo_write",
        "aiqfome_dry_run",
        "skip_oauth_validation",
        "use_temporal",
        mode="before",
    )
    @classmethod
    def _coerce_bool(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return bool(v)

    @property
    def async_database_url(self) -> str:
        u = _strip_asyncpg_unsupported_query_params(self.database_url)
        if "+asyncpg" in u:
            return u
        if u.startswith("postgresql://"):
            return u.replace("postgresql://", "postgresql+asyncpg://", 1)
        return u

    @property
    def is_production(self) -> bool:
        return self.node_env == "production"

    def encryption_key_hex(self) -> str:
        if self.token_encryption_key:
            return self.token_encryption_key
        if not self.is_production:
            return "0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20"
        raise RuntimeError("TOKEN_ENCRYPTION_KEY é obrigatória em produção")

    def writes_enabled(self) -> bool:
        return self.enable_promo_write is True

    def dev_oauth_skip(self) -> bool:
        return self.skip_oauth_validation and not self.is_production


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

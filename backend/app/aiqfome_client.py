from typing import Any, Awaitable, Callable

import httpx

from app.config import Settings, get_settings


def _require_external_store_id(store_external_id: str) -> str:
    """Segmento de path `/store/{id}` e `/menu/{id}` — sempre `Store.externalStoreId` (nunca o id interno cuid)."""
    sid = str(store_external_id).strip()
    if not sid:
        raise RuntimeError("Store.externalStoreId vazio — não é possível chamar a API aiqfome")
    return sid


def _dry_run_store_echo(store_external_id: str) -> Any:
    """Eco do id externo no mock (sem fallback fixo tipo 43952)."""
    s = str(store_external_id).strip()
    if not s:
        return "dry-run-sem-external-store-id"
    return int(s) if s.isdigit() else s


_DRY_RUN_MENU_ITEM_UUIDS_CF: frozenset[str] = frozenset(
    (
        "00000000-0000-4000-8000-000000000001".casefold(),
        "00000000-0000-4000-8000-000000000002".casefold(),
    )
)


def is_dry_run_placeholder_item_uuid(item_uuid: str) -> bool:
    """
    UUIDs fictícios de list-items/show-item quando AIQFOME_DRY_RUN=true.
    PUT na plataforma real retorna 404 — baseline com esses ids deve ser refeito com dry-run desligado.
    """
    return str(item_uuid).strip().casefold() in _DRY_RUN_MENU_ITEM_UUIDS_CF


class AiqfomeClient:
    def __init__(
        self,
        settings: Settings,
        get_access_token: Callable[[], Awaitable[str | None]],
        *,
        allow_env_token_fallback: bool = False,
    ) -> None:
        self._s = settings
        self._get_token = get_access_token
        # Se True, usa AIQFOME_ACCESS_TOKEN quando get_token() vem vazio (só para tooling / um único token global).
        # Chamadas por loja (sessão Magalu) devem ser False — senão o path usa externalStoreId A e o Bearer é da loja B do .env.
        self._allow_env_token_fallback = allow_env_token_fallback

    async def _auth_headers(self) -> dict[str, str]:
        token = await self._get_token()
        if not token and self._allow_env_token_fallback:
            token = self._s.aiqfome_access_token
        if not token:
            raise RuntimeError("Token AIQFome indisponível")
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    @staticmethod
    def _coerce_store_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Aceita `data` como lista ou objeto com lista aninhada (variações da V2)."""
        data = payload.get("data")
        if isinstance(data, list):
            raw = data
        elif isinstance(data, dict):
            raw = (
                data.get("stores")
                or data.get("items")
                or data.get("results")
                or data.get("data")
            )
            if not isinstance(raw, list):
                raw = []
        else:
            raw = []
        out: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            sid = item.get("id") or item.get("store_id") or item.get("storeId")
            if sid is None:
                continue
            name = item.get("name") or item.get("title") or item.get("displayName")
            row = {**item, "id": sid}
            if name is not None:
                row["name"] = name
            out.append(row)
        return out

    async def list_stores(self) -> list[dict[str, Any]]:
        base = self._s.aiqfome_platform_base_url.rstrip("/")
        url = f"{base}/api/v2/store"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(url, headers=await self._auth_headers())
            r.raise_for_status()
            body = r.json()
        if not isinstance(body, dict):
            raise RuntimeError("Resposta AIQFome store: JSON inválido")
        return self._coerce_store_list(body)

    async def fetch_working_hours(self, store_external_id: str) -> list[dict[str, Any]]:
        """
        GET /api/v2/store/:store_id/working-hours
        Scope: aqf:store:read — doc: https://developer.aiqfome.com/docs/api/v2/list-working-hours
        """
        if self._s.aiqfome_dry_run:
            echo = _dry_run_store_echo(store_external_id)
            return [
                {
                    "id": 253823 + i,
                    "store_id": echo,
                    "week_day_number": i + 1,
                    "hours": "14:00 - 18:00",
                    "status": 1,
                }
                for i in range(7)
            ]

        base = self._s.aiqfome_platform_base_url.rstrip("/")
        sid = _require_external_store_id(store_external_id)
        url = f"{base}/api/v2/store/{sid}/working-hours"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(url, headers=await self._auth_headers())
            r.raise_for_status()
            body = r.json()
        if not isinstance(body, dict):
            raise RuntimeError("Resposta AIQFome working-hours: JSON inválido")
        data = body.get("data")
        if not isinstance(data, list):
            return []
        return [x for x in data if isinstance(x, dict)]

    async def list_menu_categories(self, store_external_id: str) -> list[dict[str, Any]]:
        """
        GET /api/v2/menu/:store_id/categories (paginado).
        Scope: aqf:menu:read — https://developer.aiqfome.com/docs/api/v2/list-categories
        """
        if self._s.aiqfome_dry_run:
            echo = _dry_run_store_echo(store_external_id)
            return [
                {
                    "id": 1656271,
                    "name": "Sanduíches Artesanais",
                    "description": "Exemplo (dry-run)",
                    "culinary_id": 481,
                    "status": "AVAILABLE",
                    "blocked_until_tomorrow": False,
                    "has_daily_sale": False,
                    "store_id": echo,
                },
                {
                    "id": 1656272,
                    "name": "Bebidas",
                    "description": None,
                    "culinary_id": 12,
                    "status": "AVAILABLE",
                    "blocked_until_tomorrow": False,
                    "has_daily_sale": False,
                    "store_id": echo,
                },
            ]

        base = self._s.aiqfome_platform_base_url.rstrip("/")
        sid = _require_external_store_id(store_external_id)
        url = f"{base}/api/v2/menu/{sid}/categories"
        async with httpx.AsyncClient(timeout=60.0) as client:
            raw = await self._paginate_menu_data(client, url)
        return [x for x in raw if isinstance(x, dict) and x.get("id") is not None]

    async def _paginate_menu_data(
        self, client: httpx.AsyncClient, initial_url: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        aggregated: list[dict[str, Any]] = []
        page = 1
        last_page: int | None = None
        base_params = dict(params) if params else {}

        while True:
            qp = {**base_params, "page": page}
            r = await client.get(initial_url, headers=await self._auth_headers(), params=qp)
            r.raise_for_status()
            body = r.json()
            if not isinstance(body, dict):
                break
            meta = body.get("meta")
            if isinstance(meta, dict):
                lp = meta.get("last_page")
                if lp is not None:
                    try:
                        last_page = int(lp)
                    except (TypeError, ValueError):
                        last_page = None
            chunk = body.get("data")
            if not isinstance(chunk, list) or not chunk:
                break
            for row in chunk:
                if isinstance(row, dict):
                    aggregated.append(row)
            if last_page is None:
                nxt = (body.get("links") or {}).get("next") if isinstance(body.get("links"), dict) else None
                if not nxt:
                    break
                page += 1
                continue
            if page >= last_page:
                break
            page += 1
        return aggregated

    async def list_category_items(self, store_external_id: str, category_id: int) -> list[dict[str, Any]]:
        """
        GET /api/v2/menu/:store_id/categories/:category_id/items (paginado).
        Scope: aqf:menu:read — https://developer.aiqfome.com/docs/api/v2/list-items
        """
        if self._s.aiqfome_dry_run:
            cid = int(category_id)
            return [
                {
                    "uuid": "00000000-0000-4000-8000-000000000001",
                    "sku": "DRY-001",
                    "name": "Item dry-run 1",
                    "menu_category_id": cid,
                    "status": "AVAILABLE",
                },
                {
                    "uuid": "00000000-0000-4000-8000-000000000002",
                    "sku": "DRY-002",
                    "name": "Item dry-run 2",
                    "menu_category_id": cid,
                    "status": "AVAILABLE",
                },
            ]

        base = self._s.aiqfome_platform_base_url.rstrip("/")
        sid = _require_external_store_id(store_external_id)
        cid = int(category_id)
        url = f"{base}/api/v2/menu/{sid}/categories/{cid}/items"
        async with httpx.AsyncClient(timeout=120.0) as client:
            return await self._paginate_menu_data(client, url)

    async def show_menu_item(self, store_external_id: str, item_uuid: str) -> dict[str, Any]:
        """
        GET /api/v2/menu/:store_id/items/:uuid
        Scope: aqf:menu:read — https://developer.aiqfome.com/docs/api/v2/show-item
        """
        if self._s.aiqfome_dry_run:
            return {
                "uuid": item_uuid,
                "sku": "DRY-SKU",
                "name": "Item dry-run",
                "status": "AVAILABLE",
                "item_sizes": [
                    {
                        "item_size_id": 58487770,
                        "size_id": 1,
                        "name": "Único",
                        "sku": "DRY-SZ",
                        "status": "AVAILABLE",
                        "value": "10.00",
                        "promotional_value": None,
                    }
                ],
                "menu_category_id": 1656271,
            }

        base = self._s.aiqfome_platform_base_url.rstrip("/")
        sid = _require_external_store_id(store_external_id)
        uid = str(item_uuid).strip()
        url = f"{base}/api/v2/menu/{sid}/items/{uid}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(url, headers=await self._auth_headers())
            r.raise_for_status()
            body = r.json()
        if not isinstance(body, dict):
            raise RuntimeError("Resposta AIQFome show-item: JSON inválido")
        data = body.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("Resposta AIQFome show-item: data ausente")
        return data

    async def update_menu_item(self, store_external_id: str, item_uuid: str, body: dict[str, Any]) -> None:
        """
        PUT /api/v2/menu/:store_id/items/:uuid
        Scope: aqf:menu:create — https://developer.aiqfome.com/docs/api/v2/update-item
        """
        if self._s.aiqfome_dry_run:
            return

        base = self._s.aiqfome_platform_base_url.rstrip("/")
        sid = _require_external_store_id(store_external_id)
        uid = str(item_uuid).strip()
        url = f"{base}/api/v2/menu/{sid}/items/{uid}"
        headers = await self._auth_headers()
        headers["Content-Type"] = "application/json"
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.put(url, headers=headers, json=body)
            r.raise_for_status()


def default_aiqfome_client(get_access_token: Callable[[], Awaitable[str | None]]) -> AiqfomeClient:
    return AiqfomeClient(get_settings(), get_access_token, allow_env_token_fallback=True)

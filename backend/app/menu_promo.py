"""Baseline de preços (item_sizes) e PUTs na API V2 aiqfome para promo / reversão."""

from __future__ import annotations

import json
import logging
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.aiqfome_client import AiqfomeClient, is_dry_run_placeholder_item_uuid

log = logging.getLogger(__name__)

BASELINE_V = 1


def baseline_is_revertible(payload: str | None) -> bool:
    if not payload or not str(payload).strip():
        return False
    try:
        d = json.loads(payload)
    except json.JSONDecodeError:
        return False
    if not isinstance(d, dict):
        return False
    if d.get("stub") is True:
        return False
    return d.get("v") == BASELINE_V and isinstance(d.get("items"), dict)


def baseline_has_dry_run_placeholder_uuids(payload: str | None) -> bool:
    """True se algum item do snapshot usa UUID fictício do mock (baseline inválido para PUT real)."""
    if not payload or not str(payload).strip():
        return False
    try:
        d = json.loads(payload)
    except json.JSONDecodeError:
        return False
    items = d.get("items") or {}
    if not isinstance(items, dict):
        return False
    return any(isinstance(k, str) and is_dry_run_placeholder_item_uuid(k) for k in items)


def _dec(x: Any) -> Decimal | None:
    if x is None:
        return None
    try:
        return Decimal(str(x).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None


def _money_float(d: Decimal) -> float:
    return float(d.quantize(Decimal("0.01"), ROUND_HALF_UP))


def _first_non_empty_str_field(obj: dict[str, Any], keys: tuple[str, ...]) -> str:
    for k in keys:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def item_display_name_from_show_payload(data: dict[str, Any]) -> str:
    """Nome amigável do item no show-item (a API nem sempre usa a chave `name`)."""
    return _first_non_empty_str_field(
        data,
        ("name", "title", "label", "item_name", "item_title", "display_name"),
    )


def _uuid_str_from_list_row(row: dict[str, Any]) -> str | None:
    for key in ("uuid", "UUID", "item_uuid"):
        v = row.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def _name_from_list_row(row: dict[str, Any]) -> str:
    """GET list-items: campo `name` no objeto (ou em `attributes` no estilo JSON:API)."""
    for key in ("name", "Name"):
        v = row.get(key)
        if v is not None:
            s = str(v).strip()
            if s:
                return s
    attrs = row.get("attributes")
    if isinstance(attrs, dict):
        for key in ("name", "Name"):
            v = attrs.get(key)
            if v is not None:
                s = str(v).strip()
                if s:
                    return s
    return ""


def _lookup_name_in_map(item_uuid: str, m: dict[str, Any] | None) -> str:
    if not isinstance(m, dict) or not item_uuid:
        return ""
    v = m.get(item_uuid)
    if v is None:
        cf = item_uuid.casefold()
        for k, val in m.items():
            if isinstance(k, str) and k.casefold() == cf:
                v = val
                break
    if v is None:
        return ""
    s = str(v).strip()
    return s


def meaningful_promotional_string(pv: Any) -> str | None:
    """Promo ausente / zerada não entra no baseline nem no texto de UI (evita \"promo R$ 0.00\")."""
    if pv is None:
        return None
    if isinstance(pv, (int, float)) and float(pv) == 0.0:
        return None
    s = str(pv).strip()
    if s == "" or s.lower() in ("null", "none"):
        return None
    d = _dec(pv)
    if d is None:
        return None
    if d == 0:
        return None
    return s


def normalize_discount_percent(percent: Any) -> int:
    """StoreSettings.discountPercent pode vir nulo no DB; aplica padrão e limites."""
    if percent is None:
        return 15
    try:
        p = int(percent)
    except (TypeError, ValueError):
        return 15
    return max(0, min(95, p))


def discounted_promotional(value: Decimal, percent: Any) -> Decimal:
    p = normalize_discount_percent(percent)
    factor = (Decimal(100) - Decimal(p)) / Decimal(100)
    return (value * factor).quantize(Decimal("0.01"), ROUND_HALF_UP)


META_KEY = "__meta"


def _sizes_map_without_meta(entry: dict[str, Any]) -> dict[str, Any]:
    """Remove metadados de exibição do mapa persistido por item no baseline."""
    return {k: v for k, v in entry.items() if k != META_KEY}


def format_prices_summary_for_baseline(item_data: dict[str, Any], bucket: dict[str, dict[str, str | None]]) -> str:
    """Texto curto para UI/Temporal (tamanho + preço de lista e promo atual se houver)."""
    raw_sizes = item_data.get("item_sizes") or []
    if not isinstance(raw_sizes, list):
        return ""
    parts: list[str] = []
    for sz in raw_sizes:
        if not isinstance(sz, dict):
            continue
        sid_raw = sz.get("item_size_id")
        if sid_raw is None:
            continue
        sid = str(int(sid_raw))
        if sid not in bucket:
            continue
        if sz.get("status") and sz.get("status") != "AVAILABLE":
            continue
        sz_name = str(sz.get("name") or "").strip() or sid
        pair = bucket[sid]
        val = pair.get("value")
        pv_ok = meaningful_promotional_string(pair.get("promotional_value"))
        if val is None:
            continue
        piece = f"{sz_name}: R$ {val}"
        if pv_ok is not None:
            piece += f" → promo R$ {pv_ok}"
        parts.append(piece)
    return " · ".join(parts)


def sizes_from_item_detail(item_data: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    """Mapeia item_size_id (str) → { value, promotional_value } capturados antes da promo."""
    raw_sizes = item_data.get("item_sizes") or []
    if not isinstance(raw_sizes, list):
        return {}
    bucket: dict[str, dict[str, str | None]] = {}
    for sz in raw_sizes:
        if not isinstance(sz, dict):
            continue
        sid = sz.get("item_size_id")
        if sid is None:
            continue
        if sz.get("status") and sz.get("status") != "AVAILABLE":
            continue
        val = sz.get("value")
        if val is None:
            continue
        pv_raw = sz.get("promotional_value")
        pv_str = meaningful_promotional_string(pv_raw)
        key = str(int(sid))
        bucket[key] = {
            "value": str(val),
            "promotional_value": pv_str,
        }
    return bucket


async def _collect_uuids_ordered_with_list_names(
    client: AiqfomeClient, store_external_id: str, category_ids: list[int]
) -> tuple[list[str], dict[str, str]]:
    """Ordem estável + nomes do GET list-items (chave = mesmo uuid que entra em `items` no baseline)."""
    seen: set[str] = set()
    ordered: list[str] = []
    list_names_by_uuid: dict[str, str] = {}
    for cid in category_ids:
        rows = await client.list_category_items(store_external_id, cid)
        for row in rows:
            if not isinstance(row, dict):
                continue
            u = _uuid_str_from_list_row(row)
            if not u or u in seen:
                continue
            seen.add(u)
            ordered.append(u)
            nm = _name_from_list_row(row)
            if nm:
                list_names_by_uuid[u] = nm
    return ordered, list_names_by_uuid


async def collect_item_uuids(client: AiqfomeClient, store_external_id: str, category_ids: list[int]) -> list[str]:
    uuids, _ = await _collect_uuids_ordered_with_list_names(client, store_external_id, category_ids)
    return uuids


async def preview_item_entries_from_category_lists(
    client: AiqfomeClient,
    store_external_id: str,
    category_ids: list[int],
) -> list[dict[str, str]]:
    """
    Sem PriceBaseline: uuid + nome via GET list-items nas categorias da loja.
    `pricesSummary` é placeholder — preços do snapshot só existem após preparePromoApply.
    """
    uuids, list_names = await _collect_uuids_ordered_with_list_names(
        client, store_external_id, category_ids
    )
    return [
        {
            "itemUuid": u,
            "itemName": list_names.get(u) or "(sem nome)",
            "pricesSummary": "—",
        }
        for u in uuids
    ]


async def build_baseline_payload(client: AiqfomeClient, store_external_id: str, category_ids: list[int]) -> str:
    """
    GET show-item por UUID; persiste preços atuais (value + promotional_value) por item_size.
    """
    uuids, list_names_by_uuid = await _collect_uuids_ordered_with_list_names(
        client, store_external_id, category_ids
    )
    if not uuids:
        raise RuntimeError("Nenhum item encontrado nas categorias selecionadas")
    items: dict[str, dict[str, dict[str, str | None]]] = {}
    for u in uuids:
        data = await client.show_menu_item(store_external_id, u)
        if not isinstance(data, dict):
            continue
        bucket = sizes_from_item_detail(data)
        if bucket:
            from_list = _lookup_name_in_map(u, list_names_by_uuid)
            from_show = item_display_name_from_show_payload(data)
            display_name = from_list or from_show or "(sem nome)"
            price_line = format_prices_summary_for_baseline(data, bucket)
            items[u] = {
                META_KEY: {"name": display_name, "pricesSummary": price_line},
                **bucket,
            }
    if not items:
        raise RuntimeError("Nenhum tamanho AVAILABLE com preço nas categorias selecionadas")
    # Mapa explícito para Temporal/UI: mesma origem que o GET list-items (não depender só de __meta).
    list_names_snap: dict[str, str] = {}
    for uid in items:
        nm = _lookup_name_in_map(uid, list_names_by_uuid)
        if nm:
            list_names_snap[uid] = nm
    payload_obj: dict[str, Any] = {
        "v": BASELINE_V,
        "items": items,
        "listNamesByItemUuid": list_names_snap,
    }
    return json.dumps(payload_obj, separators=(",", ":"), ensure_ascii=False)


def item_uuids_from_baseline_json(baseline_json: str) -> list[str]:
    """UUIDs estáveis (ordenados) que têm snapshot de preços no baseline."""
    data = json.loads(baseline_json)
    items = data.get("items") or {}
    if not isinstance(items, dict):
        return []
    out: list[str] = []
    for u, entry in items.items():
        if not isinstance(u, str) or not isinstance(entry, dict):
            continue
        if _sizes_map_without_meta(entry):
            out.append(u)
    return sorted(out)


def _legacy_prices_summary_only(sizes_only: dict[str, Any]) -> str:
    parts: list[str] = []

    def _sort_key(sid: str) -> tuple[int, int | str]:
        try:
            return (0, int(sid))
        except ValueError:
            return (1, sid)

    for sid, pair in sorted(sizes_only.items(), key=lambda x: _sort_key(str(x[0]))):
        if not isinstance(pair, dict):
            continue
        v = pair.get("value")
        if v is None:
            continue
        pv_ok = meaningful_promotional_string(pair.get("promotional_value"))
        piece = f"#{sid}: R$ {v}"
        if pv_ok is not None:
            piece += f" → promo R$ {pv_ok}"
        parts.append(piece)
    return " · ".join(parts)


def item_entries_from_baseline_json(baseline_json: str) -> list[dict[str, str]]:
    """
    Lista ordenada para Temporal/UI: uuid, nome amigável e resumo de preços do snapshot.
    Prefere `listNamesByItemUuid` (gravado no prepare a partir do list-items), depois __meta.
    """
    data = json.loads(baseline_json)
    items = data.get("items") or {}
    if not isinstance(items, dict):
        return []
    list_root = data.get("listNamesByItemUuid")
    out: list[dict[str, str]] = []
    for u in sorted(items.keys()):
        if not isinstance(u, str):
            continue
        entry = items[u]
        if not isinstance(entry, dict):
            continue
        sizes_only = _sizes_map_without_meta(entry)
        if not sizes_only:
            continue
        name = _lookup_name_in_map(u, list_root if isinstance(list_root, dict) else None)
        if not name:
            meta = entry.get(META_KEY)
            if isinstance(meta, dict):
                name = str(meta.get("name") or "").strip()
        if not name or name == "(sem nome)":
            name = "(sem nome)"
        # Recalcula sempre a partir dos tamanhos (corrige baselines antigos e regras de promo 0)
        ps = _legacy_prices_summary_only(sizes_only)
        out.append({"itemUuid": u, "itemName": name, "pricesSummary": ps})
    return out


def _item_size_id_int(sid_str: str) -> int | None:
    try:
        return int(sid_str)
    except (TypeError, ValueError):
        return None


def build_apply_put_body(sizes_map: dict[str, Any], percent: Any) -> dict[str, Any] | None:
    """Corpo PUT update-item: promotional_value = value com desconto; value (preço de lista) mantido."""
    sizes_map = _sizes_map_without_meta(sizes_map)
    item_sizes: list[dict[str, Any]] = []
    for sid_str, pair in sizes_map.items():
        if not isinstance(pair, dict):
            continue
        sid = _item_size_id_int(str(sid_str))
        if sid is None:
            continue
        v = _dec(pair.get("value"))
        if v is None:
            continue
        new_pv = discounted_promotional(v, percent)
        item_sizes.append(
            {"id": sid, "value": _money_float(v), "promotional_value": _money_float(new_pv)}
        )
    if not item_sizes:
        return None
    return {"item_sizes": item_sizes}


def build_revert_put_body(sizes_map: dict[str, Any]) -> dict[str, Any] | None:
    """
    Reversão / fim de promo: restaura só o preço de lista (`value`) do baseline e **remove** promo na API
    (`promotional_value` = null). Não reaproveita `promotional_value` gravado no snapshot — evita voltar a um
    desconto antigo se o % mudou entre um apply e outro.
    """
    sizes_map = _sizes_map_without_meta(sizes_map)
    item_sizes: list[dict[str, Any]] = []
    for sid_str, pair in sizes_map.items():
        if not isinstance(pair, dict):
            continue
        sid = _item_size_id_int(str(sid_str))
        if sid is None:
            continue
        v = _dec(pair.get("value"))
        if v is None:
            continue
        item_sizes.append(
            {"id": sid, "value": _money_float(v), "promotional_value": None}
        )
    if not item_sizes:
        return None
    return {"item_sizes": item_sizes}


def _item_entry_for_uuid(items: dict[str, Any], item_uuid: str) -> dict[str, Any] | None:
    """Resolve entrada do baseline (uuid exato ou só diferença de maiúsculas)."""
    uid = str(item_uuid).strip()
    raw = items.get(uid)
    if isinstance(raw, dict):
        return raw
    cf = uid.casefold()
    for k, v in items.items():
        if isinstance(k, str) and k.casefold() == cf and isinstance(v, dict):
            return v
    return None


async def apply_put_single_item(
    client: AiqfomeClient,
    store_external_id: str,
    baseline_json: str,
    item_uuid: str,
    percent: Any,
    *,
    dry_run: bool,
) -> None:
    """Um PUT update-item (Temporal: uma activity por item)."""
    if dry_run:
        log.info("[aiqfome dry-run] ignorando PUT item %s", item_uuid)
        return
    if is_dry_run_placeholder_item_uuid(item_uuid):
        raise RuntimeError(
            "UUID de item de simulação (dry-run) — não existe na plataforma. "
            "Use AIQFOME_DRY_RUN=false e preparePromoApply para gravar um baseline real."
        )
    data = json.loads(baseline_json)
    items = data.get("items") or {}
    if not isinstance(items, dict):
        raise RuntimeError("baseline inválido para apply")
    entry = _item_entry_for_uuid(items, item_uuid)
    if not isinstance(entry, dict):
        raise RuntimeError(
            f"Item {item_uuid!r} não está no baseline de preços — rode preparePromoApply de novo "
            f"(itens no snapshot: {len(items)})."
        )
    body = build_apply_put_body(entry, percent)
    if not body:
        raise RuntimeError(
            f"Item {item_uuid!r}: baseline sem tamanhos com preço válido para aplicar desconto."
        )
    await client.update_menu_item(store_external_id, item_uuid, body)


async def revert_put_single_item(
    client: AiqfomeClient,
    store_external_id: str,
    baseline_json: str,
    item_uuid: str,
    *,
    dry_run: bool,
) -> None:
    """Um PUT update-item restaurando `value` e removendo promo (Temporal: uma activity por item)."""
    if dry_run:
        log.info("[aiqfome dry-run] ignorando PUT revert item %s", item_uuid)
        return
    if is_dry_run_placeholder_item_uuid(item_uuid):
        raise RuntimeError(
            "UUID de item de simulação (dry-run) — não existe na plataforma. "
            "Use AIQFOME_DRY_RUN=false e preparePromoApply para gravar um baseline real."
        )
    if not baseline_is_revertible(baseline_json):
        raise RuntimeError("baseline não reversível")
    data = json.loads(baseline_json)
    items = data.get("items") or {}
    if not isinstance(items, dict):
        raise RuntimeError("baseline inválido para revert")
    entry = _item_entry_for_uuid(items, item_uuid)
    if not isinstance(entry, dict):
        raise RuntimeError(
            f"Item {item_uuid!r} não está no baseline de preços — rode preparePromoApply de novo "
            f"(itens no snapshot: {len(items)})."
        )
    body = build_revert_put_body(entry)
    if not body:
        raise RuntimeError(
            f"Item {item_uuid!r}: baseline sem tamanhos com preço válido para reverter."
        )
    await client.update_menu_item(store_external_id, item_uuid, body)

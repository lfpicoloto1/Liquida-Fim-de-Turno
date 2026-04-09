"""Escolher qual loja da aiqfome (GET /api/v2/store) associa à sessão — nunca assumir só a primeira."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any


def parse_oauth_state_for_store_id(state: str | None) -> str | None:
    """
    Lê `state` devolvido no redirect OAuth (enviado pelo app).
    Aceita: base64url(JSON {"externalStoreId":"53209"}) ou só dígitos.
    """
    if not state:
        return None
    raw = str(state).strip()
    if not raw:
        return None
    if raw.isdigit():
        return raw
    try:
        pad = "=" * (-len(raw) % 4)
        decoded = base64.urlsafe_b64decode(raw + pad)
        j = json.loads(decoded.decode("utf-8"))
        if isinstance(j, dict):
            v = j.get("externalStoreId") or j.get("storeId") or j.get("e")
            if v is not None and str(v).strip():
                return str(v).strip()
    except (ValueError, json.JSONDecodeError, binascii.Error, UnicodeDecodeError):
        return None
    return None


def pick_store_row(stores: list[dict[str, Any]], preferred_external_id: str | None) -> dict[str, Any]:
    """
    `preferred_external_id`: id numérico da loja na plataforma (string), vindo do UI ou OAuth state.
    Se houver várias lojas e nenhuma preferência, falha com mensagem listando IDs.
    """
    if not stores:
        raise ValueError("Nenhuma loja retornada em GET /api/v2/store para este token.")
    pref = (preferred_external_id or "").strip() or None
    if pref:
        for row in stores:
            rid = row.get("id")
            if rid is not None and str(rid) == pref:
                return row
        raise ValueError(
            f"O ID informado ({pref}) não está na lista de lojas deste token. "
            "Confira o retorno de GET /api/v2/store com o mesmo access token."
        )
    if len(stores) == 1:
        return stores[0]
    ids = [str(s.get("id")) for s in stores if s.get("id") is not None]
    preview = ", ".join(ids[:15])
    suffix = " …" if len(ids) > 15 else ""
    raise ValueError(
        f"Este acesso tem {len(stores)} lojas na aiqfome; é preciso indicar qual usar. "
        f"IDs no token: {preview}{suffix}. "
        'Use o campo "ID da loja (aiqfome)" na tela de login antes de abrir o Magalu, '
        "ou envie o mesmo id no OAuth `state` (JSON base64)."
    )

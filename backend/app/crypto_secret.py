"""AES-256-GCM (iv 12 + tag 16 + ciphertext, base64url) — compatível com o formato usado historicamente no front."""

import base64
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from app.config import get_settings


def _key_from_hex(key_hex: str) -> bytes:
    raw = bytes.fromhex(key_hex)
    if len(raw) != 32:
        raise ValueError("TOKEN_ENCRYPTION_KEY must be 64 hex chars (32 bytes)")
    return raw


def encrypt_secret(plaintext: str, key_hex: str | None = None) -> str:
    key = _key_from_hex(key_hex or get_settings().encryption_key_hex())
    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    enc = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()
    tag = encryptor.tag
    blob = iv + tag + enc
    return base64.urlsafe_b64encode(blob).decode("ascii").rstrip("=")


def decrypt_secret(ciphertext: str, key_hex: str | None = None) -> str:
    key = _key_from_hex(key_hex or get_settings().encryption_key_hex())
    pad = "=" * (-len(ciphertext) % 4)
    buf = base64.urlsafe_b64decode(ciphertext + pad)
    iv, tag, data = buf[:12], buf[12:28], buf[28:]
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    pt = decryptor.update(data) + decryptor.finalize()
    return pt.decode("utf-8")

import base64
import hashlib
import os
from typing import Optional

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.services.supabase_auth import AuthUser


def _fernet() -> Fernet:
    secret = os.getenv("API_KEY_ENCRYPTION_SECRET") or os.getenv("SECRET_KEY")
    if not secret or secret.startswith("replace_with"):
        raise HTTPException(
            status_code=500,
            detail="API key sync is not configured. Set API_KEY_ENCRYPTION_SECRET in backend/.env.",
        )
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_api_key(api_key: str) -> str:
    return _fernet().encrypt(api_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_api_key: str) -> str:
    try:
        return _fernet().decrypt(encrypted_api_key.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Saved API key could not be decrypted.") from exc


def key_hint(api_key: str) -> str:
    clean = api_key.strip()
    if len(clean) <= 8:
        return "saved"
    return f"{clean[:4]}...{clean[-4:]}"


def supabase_rest_headers(user: AuthUser) -> dict[str, str]:
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    if not supabase_anon_key:
        raise HTTPException(status_code=500, detail="Supabase anon key is not configured.")
    return {
        "apikey": supabase_anon_key,
        "Authorization": f"Bearer {user.access_token}",
        "Content-Type": "application/json",
    }


def user_api_keys_url() -> str:
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        raise HTTPException(status_code=500, detail="Supabase URL is not configured.")
    return f"{supabase_url.rstrip('/')}/rest/v1/user_api_keys"


async def get_user_api_key_row(user: AuthUser) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            user_api_keys_url(),
            headers=supabase_rest_headers(user),
            params={"user_id": f"eq.{user.id}", "select": "provider,encrypted_api_key,key_hint,updated_at", "limit": "1"},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Could not read synced API key settings: {response.text}")
    rows = response.json()
    return rows[0] if rows else None


async def get_decrypted_user_api_key(user: Optional[AuthUser]) -> tuple[Optional[str], Optional[str]]:
    if not user:
        return None, None
    row = await get_user_api_key_row(user)
    if not row:
        return None, None
    return row.get("provider") or "auto", decrypt_api_key(row["encrypted_api_key"])


async def upsert_user_api_key(user: AuthUser, provider: str, api_key: str) -> dict:
    provider = provider if provider in {"auto", "gemini", "openai"} else "auto"
    clean_key = api_key.strip()
    if not clean_key:
        raise HTTPException(status_code=400, detail="API key is required.")
    payload = {
        "user_id": user.id,
        "provider": provider,
        "encrypted_api_key": encrypt_api_key(clean_key),
        "key_hint": key_hint(clean_key),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            user_api_keys_url(),
            headers={**supabase_rest_headers(user), "Prefer": "resolution=merge-duplicates,return=representation"},
            params={"on_conflict": "user_id", "select": "provider,key_hint,updated_at"},
            json=payload,
        )
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Could not save synced API key settings: {response.text}")
    rows = response.json()
    return rows[0] if rows else {"provider": provider, "key_hint": payload["key_hint"]}


async def delete_user_api_key(user: AuthUser) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.delete(
            user_api_keys_url(),
            headers=supabase_rest_headers(user),
            params={"user_id": f"eq.{user.id}"},
        )
    if response.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail=f"Could not delete synced API key settings: {response.text}")

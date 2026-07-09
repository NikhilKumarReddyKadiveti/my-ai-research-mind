import os
from typing import Optional

import httpx
from fastapi import Header, HTTPException
from pydantic import BaseModel


class AuthUser(BaseModel):
    id: str
    email: Optional[str] = None
    access_token: str


async def require_user(authorization: Optional[str] = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Supabase bearer token.")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_anon_key:
        raise HTTPException(status_code=500, detail="Supabase auth is not configured.")

    token = authorization.split(" ", 1)[1].strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": supabase_anon_key,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{supabase_url.rstrip('/')}/auth/v1/user", headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    data = response.json()
    return AuthUser(id=data["id"], email=data.get("email"), access_token=token)

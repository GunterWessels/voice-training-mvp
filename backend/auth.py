import os
import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import text

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
# JWT secret used for local tests (TESTING=1) and as fallback
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

# Supabase sets role="authenticated" for all logged-in users — never the app role.
# These are the valid application-level roles. Any other value triggers a DB lookup.
_APP_ROLES = {"rep", "trainer", "manager", "admin"}

security = HTTPBearer(auto_error=False)

async def _lookup_role(user_id: str) -> str:
    """Fetch the application role from the users table. Returns 'rep' if not found or DB unreachable."""
    try:
        from db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT role FROM users WHERE id = :uid LIMIT 1"),
                {"uid": user_id},
            )
            row = result.fetchone()
            return row[0] if row else "rep"
    except Exception:
        return "rep"

async def _verify_token_remote(token: str) -> dict:
    """Verify JWT by calling Supabase Auth API. Returns user payload dict."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_ANON_KEY,
            },
            timeout=5.0,
        )
    if resp.status_code != 200:
        import logging as _log
        _log.warning("Supabase auth verify failed: status=%s body=%s", resp.status_code, resp.text[:200])
        raise HTTPException(status_code=401, detail="Invalid token")
    data = resp.json()
    user_id = data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    email = data.get("email") or (data.get("user_metadata") or {}).get("email") or ""
    # app_metadata may carry the role if set via admin API
    role_claim = (data.get("app_metadata") or {}).get("role", "")
    return {"user_id": user_id, "email": email, "role_claim": role_claim}

def _verify_token_local(token: str) -> dict:
    """Verify JWT locally using SUPABASE_JWT_SECRET. Used in tests."""
    payload = jwt.decode(
        token,
        SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated",
    )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    email = (
        payload.get("email")
        or (payload.get("user_metadata") or {}).get("email")
        or ""
    )
    jwt_role = payload.get("role", "")
    return {"user_id": user_id, "email": email, "role_claim": jwt_role}

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials

    try:
        if SUPABASE_JWT_SECRET:
            # Local verification: fast, no network dependency, cryptographically secure.
            # Supabase signs all JWTs with this HS256 secret — local check is equivalent
            # to the remote /auth/v1/user call for authenticity purposes.
            data = _verify_token_local(token)
        else:
            # Fallback: remote verification when secret is unavailable (shouldn't happen in prod)
            data = await _verify_token_remote(token)
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = data["user_id"]
    email = data["email"]
    role_claim = data.get("role_claim", "")

    # If role claim is a known app role, use it; otherwise DB lookup
    role = role_claim if role_claim in _APP_ROLES else await _lookup_role(user_id)
    return {"user_id": user_id, "email": email, "role": role}

def require_role(*roles: str):
    async def checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

async def verify_ws_token(token: str) -> dict | None:
    """Verify JWT passed as WebSocket query parameter."""
    testing = os.environ.get("TESTING") == "1"
    try:
        if testing or not SUPABASE_ANON_KEY:
            payload = jwt.decode(token, SUPABASE_JWT_SECRET,
                                 algorithms=["HS256"], audience="authenticated")
            return {"user_id": payload["sub"], "email": payload.get("email")}
        else:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{SUPABASE_URL}/auth/v1/user",
                    headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_ANON_KEY},
                    timeout=5.0,
                )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return {"user_id": data["id"], "email": data.get("email", "")}
    except Exception:
        return None

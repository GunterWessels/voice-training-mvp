import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import text

SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]

# Supabase sets role="authenticated" for all logged-in users — never the app role.
# These are the valid application-level roles. Any other value triggers a DB lookup.
_APP_ROLES = {"rep", "trainer", "manager", "admin"}

security = HTTPBearer(auto_error=False)

async def _lookup_role(user_id: str) -> str:
    """Fetch the application role from the users table. Returns 'rep' if not found."""
    from db import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT role FROM users WHERE id = :uid LIMIT 1"),
            {"uid": user_id},
        )
        row = result.fetchone()
        return row[0] if row else "rep"

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        # email may be top-level or inside user_metadata (varies by Supabase version)
        email = (
            payload.get("email")
            or (payload.get("user_metadata") or {}).get("email")
            or ""
        )
        # Supabase JWTs carry role="authenticated", not the app role.
        # Fall back to a DB lookup so require_role() works without custom claims config.
        jwt_role = payload.get("role", "")
        role = jwt_role if jwt_role in _APP_ROLES else await _lookup_role(user_id)
        return {"user_id": user_id, "email": email, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*roles: str):
    async def checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

async def verify_ws_token(token: str) -> dict | None:
    """Verify JWT passed as WebSocket query parameter."""
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET,
                             algorithms=["HS256"], audience="authenticated")
        return {"user_id": payload["sub"], "email": payload.get("email")}
    except JWTError:
        return None

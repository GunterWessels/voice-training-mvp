import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]

security = HTTPBearer(auto_error=False)

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
        return {"user_id": payload["sub"], "email": payload.get("email"), "role": payload.get("role", "rep")}
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

import csv
import io
import uuid
import os
from typing import Optional, List, Literal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from auth import get_current_user
from db import AsyncSessionLocal
from models import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


# DB-backed admin guard (JWT role is "authenticated", app role is in DB)
async def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == uuid.UUID(user["user_id"])))
        db_user = result.scalar_one_or_none()
        if not db_user or db_user.role not in ("admin",):
            raise HTTPException(status_code=403, detail="Admin access required")
        return user


# Supabase invite helper — isolated so tests can patch it
async def _invite_user(email: str, first_name: str) -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not (supabase_url and service_key):
        return
    from supabase import create_client
    admin_client = create_client(supabase_url, service_key)
    try:
        invite_resp = admin_client.auth.admin.invite_user_by_email(email)
        user_id = invite_resp.user.id
        admin_client.auth.admin.update_user_by_id(user_id, {"user_metadata": {"first_name": first_name}})
    except Exception:
        pass


# Pydantic schemas
class UserCreate(BaseModel):
    email: str
    first_name: str
    last_name: str = ""
    role: Literal["rep", "manager", "admin"] = "rep"
    cohort_id: Optional[uuid.UUID] = None


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[Literal["rep", "manager", "admin"]] = None
    cohort_id: Optional[uuid.UUID] = None


class UserOut(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    cohort_id: Optional[str]

    @classmethod
    def from_orm(cls, u: User) -> "UserOut":
        return cls(
            id=str(u.id),
            email=u.email,
            first_name=u.first_name,
            last_name=u.last_name,
            role=u.role,
            cohort_id=str(u.cohort_id) if u.cohort_id else None,
        )


class BulkImportBody(BaseModel):
    rows: List[dict]
    send_invites: bool = True

    @validator('rows')
    def max_rows(cls, v):
        if len(v) > 500:
            raise ValueError("Maximum 500 rows per import")
        return v


# Column detection heuristics
_EMAIL_HINTS = {"email", "e-mail", "mail", "emailaddress", "email address"}
_FNAME_HINTS = {"first", "firstname", "first name", "first_name", "fname", "given", "given name"}
_LNAME_HINTS = {"last", "lastname", "last name", "last_name", "lname", "surname", "family", "family name"}
_NAME_HINTS  = {"name", "fullname", "full name", "displayname", "display name"}


def _score_header(h: str) -> Optional[str]:
    norm = h.strip().lower()
    if norm in _EMAIL_HINTS or "@" in norm:
        return "email"
    if norm in _FNAME_HINTS:
        return "first_name"
    if norm in _LNAME_HINTS:
        return "last_name"
    if norm in _NAME_HINTS:
        return "name"
    return None


def _detect_columns(headers: List[str]) -> dict:
    detected = {}
    for h in headers:
        field = _score_header(h)
        if field and field not in detected:
            detected[field] = h
    return detected


def _parse_csv_bytes(content: bytes):
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    rows = [dict(row) for row in reader]
    return headers, rows


def _parse_excel_bytes(content: bytes):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h) if h is not None else "" for h in next(rows_iter, [])]
    rows = []
    for row in rows_iter:
        rows.append({headers[i]: (str(v) if v is not None else "") for i, v in enumerate(row)})
    return headers, rows


# Routes

@router.get("/users", response_model=List[UserOut])
async def list_users(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    _: dict = Depends(get_admin_user),
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
        return [UserOut.from_orm(u) for u in result.scalars().all()]


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, _: dict = Depends(get_admin_user)):
    async with AsyncSessionLocal() as session:
        user = User(
            id=uuid.uuid4(),
            email=body.email.lower().strip(),
            first_name=body.first_name,
            last_name=body.last_name,
            role=body.role,
            cohort_id=body.cohort_id,
        )
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=409, detail="Email already exists")
    await _invite_user(user.email, user.first_name or "")
    return UserOut.from_orm(user)


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: uuid.UUID, body: UserUpdate, _: dict = Depends(get_admin_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if body.first_name is not None:
            user.first_name = body.first_name
        if body.last_name is not None:
            user.last_name = body.last_name
        if body.role is not None:
            user.role = body.role
        if body.cohort_id is not None:
            user.cohort_id = body.cohort_id
        await session.commit()
        await session.refresh(user)
        return UserOut.from_orm(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: uuid.UUID, _: dict = Depends(get_admin_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await session.delete(user)
        await session.commit()


@router.post("/users/{user_id}/invite", status_code=200)
async def resend_invite(user_id: uuid.UUID, _: dict = Depends(get_admin_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    await _invite_user(user.email, user.first_name or "")
    return {"status": "invited"}


@router.post("/users/parse-upload")
async def parse_upload(file: UploadFile = File(...), _: dict = Depends(get_admin_user)):
    content = await file.read()
    fname = (file.filename or "").lower()
    if fname.endswith((".xlsx", ".xls")):
        headers, rows = _parse_excel_bytes(content)
    else:
        headers, rows = _parse_csv_bytes(content)
    detected = _detect_columns(headers)
    return {"headers": headers, "detected": detected, "preview": rows[:5], "all_rows": rows[:500], "total_rows": len(rows)}


@router.post("/users/bulk-import", status_code=201)
async def bulk_import(body: BulkImportBody, _: dict = Depends(get_admin_user)):
    rows = body.rows
    send_invites = body.send_invites
    created, skipped, errors = 0, 0, []

    for row in rows:
        email = (row.get("email") or "").lower().strip()
        if not email or "@" not in email:
            errors.append({"email": email, "reason": "invalid email"})
            continue
        name = row.get("name", "")
        first_name = row.get("first_name") or (name.split()[0] if name else "")
        last_name = row.get("last_name") or (" ".join(name.split()[1:]) if name else "")
        async with AsyncSessionLocal() as session:
            user = User(id=uuid.uuid4(), email=email, first_name=first_name, last_name=last_name, role="rep")
            session.add(user)
            try:
                await session.commit()
                created += 1
            except IntegrityError:
                await session.rollback()
                skipped += 1
                continue
        if send_invites:
            await _invite_user(email, first_name)

    return {"created": created, "skipped": skipped, "errors": errors}

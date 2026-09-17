"""Simple signup/login (shared static password, no JWT)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai import users as app_users

router = APIRouter()


class AuthRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1)
    display_name: str | None = Field(None, max_length=120)


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str


def _user_out(row: dict) -> UserOut:
    return UserOut(
        id=str(row["id"]),
        email=row["email"],
        display_name=row["display_name"],
    )


@router.post("/signup", response_model=UserOut)
async def signup(body: AuthRequest):
    if not app_users.verify_static_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    if app_users.get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    name = (body.display_name or "").strip() or body.email.split("@")[0]
    try:
        row = app_users.create_user(body.email, name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _user_out(row)


@router.post("/login", response_model=UserOut)
async def login(body: AuthRequest):
    if not app_users.verify_static_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    row = app_users.get_user_by_email(body.email)
    if not row:
        raise HTTPException(status_code=404, detail="User not found. Sign up first.")

    return _user_out(row)

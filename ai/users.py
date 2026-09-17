"""Simple app user accounts (demo auth — shared static password, no JWT)."""

from typing import Any, Optional

from ai.config import APP_STATIC_PASSWORD
from ai.db import get_conn


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def verify_static_password(password: str) -> bool:
    return password == APP_STATIC_PASSWORD


def create_user(email: str, display_name: str) -> dict[str, Any]:
    email = _normalize_email(email)
    name = display_name.strip() or email.split("@")[0]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, display_name)
                VALUES (%s, %s)
                RETURNING id, email, display_name, created_at
                """,
                (email, name),
            )
            row = cur.fetchone()
            return dict(row)


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    email = _normalize_email(email)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, display_name, created_at FROM users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, display_name, created_at FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

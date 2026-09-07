"""Direct Postgres access via DATABASE_URL (works without Supabase API keys)."""

import json
import os
from contextlib import contextmanager
from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "")


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def lookup_order(order_number: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT o.order_number, o.status, o.total_amount, o.items, o.created_at,
                       c.name AS customer_name, c.email AS customer_email
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE o.order_number = %s
                """,
                (order_number.upper(),),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def lookup_customer(email: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email FROM customers WHERE email = %s",
                (email.lower(),),
            )
            customer = cur.fetchone()
            if not customer:
                return None
            cur.execute(
                """
                SELECT order_number, status, total_amount
                FROM orders WHERE customer_id = %s
                ORDER BY created_at DESC
                """,
                (customer["id"],),
            )
            orders = [dict(r) for r in cur.fetchall()]
            return {**dict(customer), "orders": orders}


def create_support_ticket(
    customer_email: str, subject: str, description: str, order_number: Optional[str] = None
) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM customers WHERE email = %s", (customer_email.lower(),)
            )
            customer = cur.fetchone()
            if not customer:
                return {"error": f"Customer {customer_email} not found"}

            order_id = None
            if order_number:
                cur.execute(
                    "SELECT id FROM orders WHERE order_number = %s",
                    (order_number.upper(),),
                )
                order = cur.fetchone()
                if order:
                    order_id = order["id"]

            cur.execute(
                """
                INSERT INTO support_tickets (customer_id, order_id, subject, description, status)
                VALUES (%s, %s, %s, %s, 'open')
                RETURNING id
                """,
                (customer["id"], order_id, subject, description),
            )
            ticket = cur.fetchone()
            return {"success": True, "ticket_id": str(ticket["id"])}


def _vec_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(x) for x in embedding) + "]"


def semantic_search_db(embedding: list[float], top_k: int = 3, threshold: float = 0.25) -> list[dict]:
    """Search knowledge base; sort in Python to avoid pooler ORDER BY quirks."""
    vec = _vec_literal(embedding)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, content, category,
                       embedding <=> %s::vector AS distance
                FROM knowledge_base
                WHERE embedding IS NOT NULL
                """,
                (vec,),
            )
            rows = [dict(r) for r in cur.fetchall()]

    for row in rows:
        row["similarity"] = 1 - float(row.pop("distance"))

    rows = [r for r in rows if r["similarity"] > threshold]
    rows.sort(key=lambda r: r["similarity"], reverse=True)
    return rows[:top_k]


def insert_refund_request(
    order_id: str, customer_id: str, amount: float, reason: str, approved_by: str
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO refund_requests (order_id, customer_id, amount, reason, status, approved_by)
                VALUES (%s, %s, %s, %s, 'approved', %s)
                """,
                (order_id, customer_id, amount, reason, approved_by),
            )


def get_order_and_customer_ids(order_number: str, customer_email: str) -> tuple[Optional[str], Optional[str], Optional[float]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT o.id AS order_id, c.id AS customer_id, o.total_amount
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE o.order_number = %s AND c.email = %s
                """,
                (order_number.upper(), customer_email.lower()),
            )
            row = cur.fetchone()
            if not row:
                return None, None, None
            return str(row["order_id"]), str(row["customer_id"]), float(row["total_amount"])

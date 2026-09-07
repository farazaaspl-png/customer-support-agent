"""
CONCEPT 5: Tool Calling
-----------------------
Tools are plain Python functions the agent can invoke for order lookups,
refund creation, and ticket management. LangChain wraps them for the LLM.
"""

import json
from typing import Optional

from langchain_core.tools import tool

from ai.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

# Lazy Supabase client to avoid import errors when env is unset
_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is None:
        from supabase import create_client

        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase


@tool
def lookup_order(order_number: str) -> str:
    """Look up an order by order number (e.g. ORD-1001). Returns status, items, and total."""
    try:
        sb = _get_supabase()
        result = (
            sb.table("orders")
            .select("order_number, status, total_amount, items, created_at, customers(name, email)")
            .eq("order_number", order_number.upper())
            .single()
            .execute()
        )
        if not result.data:
            return json.dumps({"error": f"Order {order_number} not found"})
        return json.dumps(result.data, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def lookup_customer(email: str) -> str:
    """Look up a customer by email address. Returns name and recent orders."""
    try:
        sb = _get_supabase()
        result = (
            sb.table("customers")
            .select("name, email, orders(order_number, status, total_amount)")
            .eq("email", email.lower())
            .single()
            .execute()
        )
        if not result.data:
            return json.dumps({"error": f"Customer {email} not found"})
        return json.dumps(result.data, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def create_support_ticket(
    customer_email: str, subject: str, description: str, order_number: Optional[str] = None
) -> str:
    """Create a support ticket for a customer. Optionally link to an order."""
    try:
        sb = _get_supabase()
        customer = (
            sb.table("customers")
            .select("id")
            .eq("email", customer_email.lower())
            .single()
            .execute()
        )
        if not customer.data:
            return json.dumps({"error": f"Customer {customer_email} not found"})

        order_id = None
        if order_number:
            order = (
                sb.table("orders")
                .select("id")
                .eq("order_number", order_number.upper())
                .single()
                .execute()
            )
            if order.data:
                order_id = order.data["id"]

        ticket = (
            sb.table("support_tickets")
            .insert(
                {
                    "customer_id": customer.data["id"],
                    "order_id": order_id,
                    "subject": subject,
                    "description": description,
                    "status": "open",
                }
            )
            .execute()
        )
        return json.dumps({"success": True, "ticket_id": ticket.data[0]["id"]})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def search_policies(query: str) -> str:
    """Search company policies and FAQs. Use for general policy questions."""
    from ai.rag import semantic_search

    results = semantic_search(query, top_k=3)
    if not results:
        return "No relevant policies found."
    return "\n\n".join(
        f"**{r['title']}** ({r['category']}): {r['content']}" for r in results
    )


# All tools available to the agent loop
AGENT_TOOLS = [lookup_order, lookup_customer, create_support_ticket, search_policies]

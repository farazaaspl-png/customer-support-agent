"""
CONCEPT 5: Tool Calling
-----------------------
Tools are plain Python functions the agent can invoke for order lookups,
refund creation, and ticket management. LangChain wraps them for the LLM.
"""

import json
from typing import Optional

from langchain_core.tools import tool

from ai import db as pg


@tool
def lookup_order(order_number: str) -> str:
    """Look up an order by order number (e.g. ORD-1001). Returns status, items, and total."""
    try:
        data = pg.lookup_order(order_number)
        if not data:
            return json.dumps({"error": f"Order {order_number} not found"})
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def lookup_customer(email: str) -> str:
    """Look up a customer by email address. Returns name and recent orders."""
    try:
        data = pg.lookup_customer(email)
        if not data:
            return json.dumps({"error": f"Customer {email} not found"})
        return json.dumps(data, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def create_support_ticket(
    customer_email: str, subject: str, description: str, order_number: Optional[str] = None
) -> str:
    """Create a support ticket for a customer. Optionally link to an order."""
    try:
        result = pg.create_support_ticket(customer_email, subject, description, order_number)
        return json.dumps(result, default=str)
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

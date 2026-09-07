"""
CONCEPT 2: Nodes
----------------
Each function below is a graph node. Nodes receive AgentState, perform one task,
and return a partial state update dict.
"""

import json
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ai.config import CHAT_MODEL, MAX_RETRIES, OPENAI_API_KEY
from ai.rag import build_rag_context
from ai.state import AgentState
from ai.tools import AGENT_TOOLS, lookup_order

_llm = None
_llm_with_tools = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model=CHAT_MODEL, api_key=OPENAI_API_KEY, temperature=0)
    return _llm


def _get_llm_with_tools() -> ChatOpenAI:
    global _llm_with_tools
    if _llm_with_tools is None:
        _llm_with_tools = _get_llm().bind_tools(AGENT_TOOLS)
    return _llm_with_tools


def _last_user_message(state: AgentState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def _extract_order_number(text: str) -> str | None:
    match = re.search(r"ORD-\d+", text.upper())
    return match.group(0) if match else None


def _extract_email(text: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# Node: classify_intent
# ---------------------------------------------------------------------------
def classify_intent(state: AgentState) -> dict:
    """Classify the user's message into faq | order | refund | unknown."""
    user_msg = _last_user_message(state)

    prompt = f"""Classify this customer support message into exactly one intent:
- faq: general questions about policies, shipping, returns, warranty
- order: questions about order status, tracking, delivery
- refund: requests for refunds or returns of purchased items
- unknown: anything else

Message: "{user_msg}"

Reply with only the intent word (faq, order, refund, or unknown)."""

    response = _get_llm().invoke([HumanMessage(content=prompt)])
    intent = response.content.strip().lower()

    if intent not in ("faq", "order", "refund", "unknown"):
        intent = "unknown"

    return {
        "intent": intent,
        "agent_status": "thinking",
        "order_number": _extract_order_number(user_msg),
        "customer_email": _extract_email(user_msg),
    }


# ---------------------------------------------------------------------------
# Node: rag_faq  (CONCEPT 9: RAG)
# ---------------------------------------------------------------------------
def rag_faq(state: AgentState) -> dict:
    """Retrieve relevant knowledge-base docs and generate an FAQ answer."""
    user_msg = _last_user_message(state)
    context = build_rag_context(user_msg)

    prompt = f"""You are a helpful customer support agent. Answer using ONLY the context below.
If the context doesn't cover the question, say so politely and offer to connect them with a human.

Context:
{context}

Customer question: {user_msg}"""

    response = _get_llm().invoke([HumanMessage(content=prompt)])
    return {
        "rag_context": context,
        "response": response.content,
        "agent_status": "completed",
        "messages": [AIMessage(content=response.content)],
    }


# ---------------------------------------------------------------------------
# Node: order_lookup  (CONCEPT 5: Tool Calling)
# ---------------------------------------------------------------------------
def order_lookup(state: AgentState) -> dict:
    """Look up order details using the lookup_order tool."""
    order_number = state.get("order_number") or _extract_order_number(
        _last_user_message(state)
    )

    if not order_number:
        return {
            "response": "I'd be happy to help with your order. Could you provide your order number (e.g., ORD-1001)?",
            "agent_status": "completed",
            "messages": [
                AIMessage(
                    content="I'd be happy to help with your order. Could you provide your order number (e.g., ORD-1001)?"
                )
            ],
        }

    # CONCEPT 5: invoke tool
    tool_result = lookup_order.invoke({"order_number": order_number})
    data = json.loads(tool_result)

    if "error" in data:
        response_text = f"I couldn't find order {order_number}. Please double-check the number."
    else:
        items = data.get("items", [])
        item_list = ", ".join(
            f"{i.get('name', 'item')} x{i.get('qty', 1)}" for i in items
        )
        response_text = (
            f"Order **{data['order_number']}** is **{data['status']}**.\n"
            f"Items: {item_list}\n"
            f"Total: ${data['total_amount']}\n"
            f"Placed: {data.get('created_at', 'N/A')[:10]}"
        )

    return {
        "response": response_text,
        "agent_status": "completed",
        "tool_results": [data],
        "messages": [AIMessage(content=response_text)],
    }


# ---------------------------------------------------------------------------
# Node: refund_prepare  (CONCEPT 8: HITL setup)
# ---------------------------------------------------------------------------
def refund_prepare(state: AgentState) -> dict:
    """
    Prepare a refund request and pause for human approval.
    The graph interrupts BEFORE refund_execute (see graph.py).
    """
    user_msg = _last_user_message(state)
    order_number = state.get("order_number") or _extract_order_number(user_msg)
    email = state.get("customer_email") or _extract_email(user_msg) or "unknown@example.com"

    pending = {
        "order_number": order_number or "UNKNOWN",
        "customer_email": email,
        "reason": user_msg,
        "amount": None,
        "status": "pending_approval",
    }

    # Try to get order amount for the approval UI
    if order_number:
        tool_result = lookup_order.invoke({"order_number": order_number})
        data = json.loads(tool_result)
        if "total_amount" in data:
            pending["amount"] = float(data["total_amount"])

    response_text = (
        f"I've prepared a refund request for order **{pending['order_number']}**.\n"
        f"Reason: {pending['reason']}\n\n"
        "⏳ **Waiting for human approval** before processing this refund."
    )

    return {
        "pending_refund": pending,
        "agent_status": "waiting_for_human",
        "response": response_text,
        "messages": [AIMessage(content=response_text)],
    }


# ---------------------------------------------------------------------------
# Node: refund_execute  (runs after HITL approval)
# ---------------------------------------------------------------------------
def refund_execute(state: AgentState) -> dict:
    """Execute the approved refund and persist to Supabase."""
    pending = state.get("pending_refund") or {}
    approved = pending.get("approved", False)

    if not approved:
        return {
            "response": "Refund was not approved.",
            "agent_status": "completed",
            "messages": [AIMessage(content="Refund was not approved.")],
        }

    try:
        from supabase import create_client
        from ai.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

        customer = (
            sb.table("customers")
            .select("id")
            .eq("email", pending.get("customer_email", "").lower())
            .maybe_single()
            .execute()
        )
        order = (
            sb.table("orders")
            .select("id, total_amount")
            .eq("order_number", pending.get("order_number", "").upper())
            .maybe_single()
            .execute()
        )

        if order.data and customer.data:
            sb.table("refund_requests").insert(
                {
                    "order_id": order.data["id"],
                    "customer_id": customer.data["id"],
                    "amount": pending.get("amount") or order.data["total_amount"],
                    "reason": pending.get("reason", ""),
                    "status": "approved",
                    "approved_by": pending.get("approved_by", "human_agent"),
                }
            ).execute()

        response_text = (
            f"✅ Refund approved and processed for order **{pending.get('order_number')}**.\n"
            f"You will receive ${pending.get('amount', 'the full amount')} back within 5-7 business days."
        )
    except Exception as e:
        response_text = f"Refund approved but encountered an error saving: {e}"

    return {
        "response": response_text,
        "agent_status": "completed",
        "pending_refund": None,
        "messages": [AIMessage(content=response_text)],
    }


# ---------------------------------------------------------------------------
# Node: agent_loop_step  (CONCEPT 6: Agent Loops)
# ---------------------------------------------------------------------------
def agent_loop_step(state: AgentState) -> dict:
    """
    One step of the ReAct agent loop: LLM decides whether to call a tool or respond.
    The graph loops back to this node until the LLM produces a final answer.
    """
    system = SystemMessage(
        content="You are a helpful customer support agent for Acme Store. "
        "Use tools when needed. Be concise and friendly."
    )
    messages = [system] + list(state["messages"])

    response = _get_llm_with_tools().invoke(messages)

    updates: dict[str, Any] = {"messages": [response]}

    if response.tool_calls:
        updates["agent_status"] = "tool_call"
    else:
        updates["agent_status"] = "completed"
        updates["response"] = response.content

    return updates


def agent_tool_executor(state: AgentState) -> dict:
    """Execute tool calls from the last AI message (part of agent loop)."""
    last_msg = state["messages"][-1]
    tool_map = {t.name: t for t in AGENT_TOOLS}
    results = []

    for tool_call in last_msg.tool_calls:
        tool_fn = tool_map.get(tool_call["name"])
        if tool_fn:
            result = tool_fn.invoke(tool_call["args"])
            results.append({"tool": tool_call["name"], "result": result})

    from langchain_core.messages import ToolMessage

    tool_messages = [
        ToolMessage(content=r["result"], tool_call_id=tc["id"])
        for r, tc in zip(results, last_msg.tool_calls)
    ]

    return {
        "messages": tool_messages,
        "tool_results": results,
        "agent_status": "thinking",
    }


# ---------------------------------------------------------------------------
# Node: handle_error  (CONCEPT 10: Error Handling & Retries)
# ---------------------------------------------------------------------------
@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=1, max=4))
def _retryable_llm_call(messages: list) -> str:
    response = _get_llm().invoke(messages)
    return response.content


def handle_error(state: AgentState) -> dict:
    """Retry failed operations or return a graceful error message."""
    error_count = state.get("error_count", 0) + 1
    user_msg = _last_user_message(state)

    if error_count <= MAX_RETRIES:
        try:
            response = _retryable_llm_call(
                [
                    HumanMessage(
                        content=f"Apologize briefly and help this customer: {user_msg}"
                    )
                ]
            )
            return {
                "response": response,
                "agent_status": "completed",
                "error_count": error_count,
                "messages": [AIMessage(content=response)],
            }
        except Exception:
            pass

    return {
        "response": "I'm sorry, I'm having trouble right now. Please try again or contact support@acmestore.com.",
        "agent_status": "error",
        "error_count": error_count,
        "messages": [
            AIMessage(
                content="I'm sorry, I'm having trouble right now. Please try again or contact support@acmestore.com."
            )
        ],
    }


# ---------------------------------------------------------------------------
# Routing helpers (used by CONCEPT 4: Conditional Edges)
# ---------------------------------------------------------------------------
def route_by_intent(state: AgentState) -> str:
    """Route to the correct handler based on classified intent."""
    return state.get("intent", "unknown")


def should_continue_agent_loop(state: AgentState) -> str:
    """Decide whether the agent loop should call tools or finish."""
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "end"

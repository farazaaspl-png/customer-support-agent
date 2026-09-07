"""Agent service — bridges FastAPI and the LangGraph graph."""

import uuid
from typing import Any, Optional

from langchain_core.messages import HumanMessage

from ai.graph import get_graph
from ai.state import AgentState


def _default_state(message: str, thread_id: str) -> dict:
    return {
        "messages": [HumanMessage(content=message)],
        "intent": "",
        "customer_email": None,
        "order_number": None,
        "rag_context": None,
        "agent_status": "thinking",
        "error_count": 0,
        "pending_refund": None,
        "response": None,
        "tool_results": None,
    }


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def run_chat(message: str, thread_id: Optional[str] = None) -> dict[str, Any]:
    """
    Run the agent graph for a user message.
    Returns response text, agent_status, and thread_id.
    If HITL is triggered, agent_status will be 'waiting_for_human'.
    """
    graph = get_graph()
    thread_id = thread_id or str(uuid.uuid4())
    config = _config(thread_id)

    try:
        result = graph.invoke(_default_state(message, thread_id), config)
    except Exception as e:
        return {
            "thread_id": thread_id,
            "response": f"An error occurred: {e}",
            "agent_status": "error",
            "pending_refund": None,
            "intent": None,
        }

    # Check if graph is paused at HITL interrupt
    state_snapshot = graph.get_state(config)
    is_interrupted = bool(state_snapshot.next)

    return {
        "thread_id": thread_id,
        "response": result.get("response", ""),
        "agent_status": "waiting_for_human" if is_interrupted else result.get("agent_status", "completed"),
        "pending_refund": result.get("pending_refund"),
        "intent": result.get("intent"),
        "rag_context": result.get("rag_context"),
    }


def approve_refund(thread_id: str, approved: bool, approved_by: str = "human_agent") -> dict[str, Any]:
    """Approve or reject a pending refund (HITL)."""
    graph = get_graph()
    config = _config(thread_id)

    state_snapshot = graph.get_state(config)
    if not state_snapshot.values:
        return {"error": "Thread not found", "thread_id": thread_id}

    pending = state_snapshot.values.get("pending_refund") or {}
    pending["approved"] = approved
    pending["approved_by"] = approved_by

    graph.update_state(config, {"pending_refund": pending})

    return {
        "thread_id": thread_id,
        "approved": approved,
        "pending_refund": pending,
    }


def resume_after_hitl(thread_id: str) -> dict[str, Any]:
    """Resume the graph after human approval/rejection."""
    graph = get_graph()
    config = _config(thread_id)

    state_snapshot = graph.get_state(config)
    if not state_snapshot.next:
        return {
            "thread_id": thread_id,
            "response": state_snapshot.values.get("response", ""),
            "agent_status": state_snapshot.values.get("agent_status", "completed"),
        }

    try:
        result = graph.invoke(None, config)
    except Exception as e:
        return {
            "thread_id": thread_id,
            "response": f"Resume failed: {e}",
            "agent_status": "error",
        }

    return {
        "thread_id": thread_id,
        "response": result.get("response", ""),
        "agent_status": result.get("agent_status", "completed"),
        "pending_refund": result.get("pending_refund"),
    }


def get_thread_state(thread_id: str) -> dict[str, Any]:
    """Get current state for a conversation thread."""
    graph = get_graph()
    config = _config(thread_id)
    snapshot = graph.get_state(config)

    if not snapshot.values:
        return {"error": "Thread not found"}

    return {
        "thread_id": thread_id,
        "agent_status": snapshot.values.get("agent_status"),
        "intent": snapshot.values.get("intent"),
        "pending_refund": snapshot.values.get("pending_refund"),
        "is_interrupted": bool(snapshot.next),
        "messages": [
            {"role": type(m).__name__, "content": m.content}
            for m in snapshot.values.get("messages", [])
        ],
    }

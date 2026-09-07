"""Agent service — bridges FastAPI and the LangGraph graph."""

import uuid
from typing import Any, Optional

from langchain_core.messages import HumanMessage

from ai import conversation as conv
from ai.graph import get_graph
from ai.langfuse_tracing import build_run_config, flush_langfuse, langfuse_trace
from ai.state import AgentState


def _state_from_session(session: dict, new_message: str) -> dict:
    """Build agent state using DB history (efficient context window)."""
    messages = conv.build_langchain_messages(session)
    # Ensure the latest user message is included (just saved to DB)
    if not messages or not (
        isinstance(messages[-1], HumanMessage) and messages[-1].content == new_message
    ):
        messages.append(HumanMessage(content=new_message))

    return {
        "messages": messages,
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
    return build_run_config(thread_id)


def run_chat(message: str, thread_id: Optional[str] = None) -> dict[str, Any]:
    """
    Run the agent graph for a user message.
    Persists messages to DB and uses context window management for long chats.
    """
    graph = get_graph()
    session = conv.get_or_create_session(thread_id, first_message=message)
    thread_id = session["thread_id"]

    # Persist user message
    conv.save_message(session["id"], "user", message)
    if session["message_count"] == 0:
        conv.touch_session(session["id"], conv._title_from_message(message))

    # Refresh session (message_count updated)
    session = conv.get_session_by_thread(thread_id)

    try:
        with langfuse_trace(thread_id, message) as config:
            result = graph.invoke(_state_from_session(session, message), config)
    except Exception as e:
        return {
            "thread_id": thread_id,
            "response": f"An error occurred: {e}",
            "agent_status": "error",
            "pending_refund": None,
            "intent": None,
            "title": session["title"],
        }
    finally:
        flush_langfuse()

    state_snapshot = graph.get_state(config)
    is_interrupted = bool(state_snapshot.next)
    response_text = result.get("response", "")

    # Persist assistant response
    if response_text:
        conv.save_message(session["id"], "assistant", response_text)

    conv.touch_session(session["id"])
    conv.maybe_summarize(session["id"])

    return {
        "thread_id": thread_id,
        "response": response_text,
        "agent_status": "waiting_for_human" if is_interrupted else result.get("agent_status", "completed"),
        "pending_refund": result.get("pending_refund"),
        "intent": result.get("intent"),
        "rag_context": result.get("rag_context"),
        "title": session["title"],
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
        with langfuse_trace(thread_id, "hitl_resume") as trace_config:
            result = graph.invoke(None, trace_config)
    except Exception as e:
        return {
            "thread_id": thread_id,
            "response": f"Resume failed: {e}",
            "agent_status": "error",
        }
    finally:
        flush_langfuse()

    response_text = result.get("response", "")
    session = conv.get_session_by_thread(thread_id)
    if session and response_text:
        conv.save_message(session["id"], "assistant", response_text)
        conv.touch_session(session["id"])

    return {
        "thread_id": thread_id,
        "response": response_text,
        "agent_status": result.get("agent_status", "completed"),
        "pending_refund": result.get("pending_refund"),
    }


def get_thread_state(thread_id: str) -> dict[str, Any]:
    """Get current state for a conversation thread."""
    graph = get_graph()
    config = _config(thread_id)
    snapshot = graph.get_state(config)

    session = conv.get_session_by_thread(thread_id)

    if not snapshot.values and not session:
        return {"error": "Thread not found"}

    db_messages = conv.get_all_messages(session["id"]) if session else []

    return {
        "thread_id": thread_id,
        "title": session["title"] if session else None,
        "agent_status": snapshot.values.get("agent_status") if snapshot.values else "completed",
        "intent": snapshot.values.get("intent") if snapshot.values else None,
        "pending_refund": snapshot.values.get("pending_refund") if snapshot.values else None,
        "is_interrupted": bool(snapshot.next),
        "messages": [
            {"role": m["role"], "content": m["content"]}
            for m in db_messages
        ],
    }

"""Langfuse tracing for LLM calls and token usage."""

from contextlib import contextmanager
from typing import Any, Generator, Optional

from ai.config import (
    LANGFUSE_ENABLED,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
)


def is_langfuse_enabled() -> bool:
    return LANGFUSE_ENABLED and bool(LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY)


def get_langfuse_handler():
    """Return a LangChain CallbackHandler for Langfuse, or None if disabled."""
    if not is_langfuse_enabled():
        return None

    from langfuse.langchain import CallbackHandler

    return CallbackHandler()


def build_run_config(thread_id: str) -> dict[str, Any]:
    """Build LangGraph RunnableConfig with Langfuse callbacks and session metadata."""
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    handler = get_langfuse_handler()
    if handler:
        config["callbacks"] = [handler]
        config["metadata"] = {
            "langfuse_session_id": thread_id,
            "thread_id": thread_id,
        }

    return config


@contextmanager
def langfuse_trace(thread_id: str, user_message: str = "") -> Generator[dict[str, Any], None, None]:
    """
    Wrap a graph run in a Langfuse span with session propagation.
    Yields the RunnableConfig to pass to graph.invoke().
    """
    config = build_run_config(thread_id)

    if not is_langfuse_enabled():
        yield config
        return

    from langfuse import get_client, propagate_attributes

    langfuse = get_client()
    with langfuse.start_as_current_observation(
        as_type="span", name="customer-support-chat"
    ) as span:
        span.set_trace_io(
            input={"message": user_message, "thread_id": thread_id},
        )
        with propagate_attributes(session_id=thread_id):
            yield config


def flush_langfuse() -> None:
    """Flush pending Langfuse events (call after graph execution)."""
    if not is_langfuse_enabled():
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:
        pass

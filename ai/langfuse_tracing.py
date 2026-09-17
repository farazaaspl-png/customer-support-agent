"""Langfuse tracing for LLM calls and token usage."""

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

from ai.config import (
    LANGFUSE_ENABLED,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_TRACING_ENVIRONMENT,
)


def is_langfuse_enabled() -> bool:
    return LANGFUSE_ENABLED and bool(LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY)


def get_langfuse_handler():
    """Return a LangChain CallbackHandler for Langfuse, or None if disabled."""
    if not is_langfuse_enabled():
        return None

    from langfuse.langchain import CallbackHandler

    return CallbackHandler()


def _trace_metadata(thread_id: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "langfuse_session_id": thread_id,
        "thread_id": thread_id,
    }
    if LANGFUSE_TRACING_ENVIRONMENT:
        metadata["environment"] = LANGFUSE_TRACING_ENVIRONMENT
    return metadata


def build_run_config(thread_id: str) -> dict[str, Any]:
    """Build LangGraph RunnableConfig with Langfuse callbacks and session metadata."""
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    handler = get_langfuse_handler()
    if handler:
        config["callbacks"] = [handler]
        config["metadata"] = _trace_metadata(thread_id)

    return config


@dataclass
class LangfuseRunContext:
    """Runnable config plus optional trace output for a single graph run."""

    config: dict[str, Any]
    _span: Any = field(default=None, repr=False)

    def set_output(self, output: Any) -> None:
        if self._span is not None:
            self._span.set_trace_io(output=output)


@contextmanager
def langfuse_trace(
    thread_id: str, user_message: str = ""
) -> Generator[LangfuseRunContext, None, None]:
    """
    Wrap a graph run in a Langfuse span with session propagation.
    Yields LangfuseRunContext; pass `.config` to graph.invoke().
    """
    config = build_run_config(thread_id)
    run = LangfuseRunContext(config=config)

    if not is_langfuse_enabled():
        yield run
        return

    from langfuse import get_client, propagate_attributes

    langfuse = get_client()
    propagation_kwargs: dict[str, Any] = {"session_id": thread_id}
    if LANGFUSE_TRACING_ENVIRONMENT:
        propagation_kwargs["environment"] = LANGFUSE_TRACING_ENVIRONMENT

    with langfuse.start_as_current_observation(
        as_type="span", name="customer-support-chat"
    ) as span:
        run._span = span
        span.set_trace_io(
            input={"message": user_message, "thread_id": thread_id},
        )
        with propagate_attributes(**propagation_kwargs):
            yield run


def flush_langfuse() -> None:
    """Flush pending Langfuse events (call after graph execution)."""
    if not is_langfuse_enabled():
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:
        pass

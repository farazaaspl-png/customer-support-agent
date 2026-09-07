"""
CONCEPT 1: State & StateGraph
-----------------------------
AgentState defines the shared state that flows through every node in the graph.
LangGraph merges partial updates from each node into this TypedDict.
"""

from typing import Annotated, Literal, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


# Agent status values surfaced to the frontend
AgentStatus = Literal[
    "thinking",
    "tool_call",
    "waiting_for_human",
    "completed",
    "error",
]


class AgentState(TypedDict):
    """Shared state for the customer support agent graph."""

    # Conversation history (messages reducer appends new messages)
    messages: Annotated[list, add_messages]

    # Classified intent from the user's latest message
    intent: str

    # Resolved customer context
    customer_email: Optional[str]
    order_number: Optional[str]

    # RAG context retrieved from knowledge base
    rag_context: Optional[str]

    # Current agent status for UI feedback
    agent_status: AgentStatus

    # Retry counter for error handling (CONCEPT 10)
    error_count: int

    # Pending refund awaiting human approval (CONCEPT 8: HITL)
    pending_refund: Optional[dict]

    # Final response text
    response: Optional[str]

    # Tool results from the agent loop
    tool_results: Optional[list]

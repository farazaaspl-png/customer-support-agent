"""
LangGraph graph assembly — demonstrates concepts 1-4, 6-8, 10.

CONCEPT 1: State & StateGraph  → AgentState + StateGraph builder
CONCEPT 2: Nodes               → node functions registered below
CONCEPT 3: Edges               → add_edge() connections
CONCEPT 4: Conditional Edges   → add_conditional_edges() routing
CONCEPT 6: Agent Loops         → agent_loop_step ↔ agent_tool_executor cycle
CONCEPT 7: Memory & Checkpointing → MemorySaver checkpointer
CONCEPT 8: Human-in-the-Loop   → interrupt_before=["refund_execute"]
CONCEPT 10: Error Handling     → handle_error node + retry in nodes.py
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from ai.nodes import (
    agent_loop_step,
    agent_tool_executor,
    classify_intent,
    handle_error,
    order_lookup,
    rag_faq,
    refund_execute,
    refund_prepare,
    route_by_intent,
    should_continue_agent_loop,
)
from ai.state import AgentState

# CONCEPT 7: Memory & Checkpointing — persists state per thread_id
checkpointer = MemorySaver()


def build_graph():
    """
    Build and compile the customer support StateGraph.

    Workflow:
        User → classify_intent → [conditional routing]
            ├── faq    → rag_faq → END
            ├── order  → order_lookup → END
            ├── refund → refund_prepare → [HITL pause] → refund_execute → END
            └── unknown → agent_loop (loop) → END
    """
    # CONCEPT 1: StateGraph with shared AgentState
    builder = StateGraph(AgentState)

    # CONCEPT 2: Register nodes
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("rag_faq", rag_faq)
    builder.add_node("order_lookup", order_lookup)
    builder.add_node("refund_prepare", refund_prepare)
    builder.add_node("refund_execute", refund_execute)
    builder.add_node("agent_loop_step", agent_loop_step)
    builder.add_node("agent_tool_executor", agent_tool_executor)
    builder.add_node("handle_error", handle_error)

    # CONCEPT 3: Edges — entry point
    builder.set_entry_point("classify_intent")

    # CONCEPT 4: Conditional Edges — route by intent
    builder.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "faq": "rag_faq",
            "order": "order_lookup",
            "refund": "refund_prepare",
            "unknown": "agent_loop_step",
        },
    )

    # Direct edges to END for simple paths
    builder.add_edge("rag_faq", END)
    builder.add_edge("order_lookup", END)

    # Refund path: prepare → (HITL interrupt) → execute → END
    builder.add_edge("refund_prepare", "refund_execute")
    builder.add_edge("refund_execute", END)

    # CONCEPT 6: Agent Loop — LLM ↔ tools until done
    builder.add_conditional_edges(
        "agent_loop_step",
        should_continue_agent_loop,
        {
            "tools": "agent_tool_executor",
            "end": END,
        },
    )
    builder.add_edge("agent_tool_executor", "agent_loop_step")

    # CONCEPT 8: Human-in-the-Loop — pause before executing refund
    # CONCEPT 7: compile with checkpointer for thread persistence
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["refund_execute"],
    )

    return graph


# Singleton compiled graph
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph

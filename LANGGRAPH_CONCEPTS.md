# LangGraph Concepts — Learning Map

This document maps the **10 core LangGraph concepts** implemented in this project to the actual code, files, and execution flows.

## Quick reference

| # | Concept | Status | Primary files |
|---|---------|--------|---------------|
| 1 | State & StateGraph | ✅ | `ai/state.py`, `ai/graph.py` |
| 2 | Nodes | ✅ | `ai/nodes.py`, `ai/graph.py` |
| 3 | Edges | ✅ | `ai/graph.py` |
| 4 | Conditional edges / routing | ✅ | `ai/graph.py`, `ai/nodes.py` |
| 5 | Tool calling | ✅ | `ai/tools.py`, `ai/nodes.py` |
| 6 | Agent loops | ✅ | `ai/graph.py`, `ai/nodes.py` |
| 7 | Memory & checkpointing | ✅ | `ai/graph.py`, `backend/services/agent_service.py`, `ai/conversation.py` |
| 8 | Human-in-the-loop (HITL) | ✅ | `ai/graph.py`, `backend/routes/hitl.py` |
| 9 | RAG + LangGraph | ✅ | `ai/rag.py`, `ai/nodes.py` |
| 10 | Error handling & retries | ⚠️ Partial | `ai/nodes.py` |

**Score: 9 fully implemented, 1 partial** (`handle_error` node exists but is not wired into the graph).

---

## Graph overview

```text
User message
    ↓
classify_intent          ← Node (2) + State update (1)
    ↓
Conditional routing      ← Concept (4)
    ├── faq      → rag_faq        → END     (RAG = 9)
    ├── order    → order_lookup   → END     (Tools = 5)
    ├── refund   → refund_prepare → [HITL pause] → refund_execute → END  (8)
    └── unknown  → agent_loop_step ↔ agent_tool_executor → END  (6 + 5)
```

---

## 1. State & StateGraph

**Files:** `ai/state.py`, `ai/graph.py`

`AgentState` is a `TypedDict` that flows through every node. LangGraph merges partial updates from each node into this shared state.

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # conversation history (reducer appends)
    intent: str
    customer_email: Optional[str]
    order_number: Optional[str]
    rag_context: Optional[str]
    agent_status: AgentStatus
    error_count: int
    pending_refund: Optional[dict]
    response: Optional[str]
    tool_results: Optional[list]
```

The graph is built with:

```python
builder = StateGraph(AgentState)
```

**Key idea:** Each node returns a dict with only the fields it changes; LangGraph merges them into `AgentState`.

---

## 2. Nodes

**Files:** `ai/nodes.py`, `ai/graph.py`

A **node** is a Python function that receives `AgentState` and returns a partial state update.

| Node | Purpose |
|------|---------|
| `classify_intent` | LLM classifies message as `faq`, `order`, `refund`, or `unknown` |
| `rag_faq` | Retrieves knowledge-base docs and answers FAQ questions |
| `order_lookup` | Calls `lookup_order` tool and formats response |
| `refund_prepare` | Prepares refund request, sets `waiting_for_human` |
| `refund_execute` | Runs after HITL approval, saves refund to DB |
| `agent_loop_step` | One ReAct step: LLM decides to call tools or respond |
| `agent_tool_executor` | Executes tool calls from the LLM |
| `handle_error` | Retry / graceful fallback (registered but not wired — see #10) |

Registered in `ai/graph.py`:

```python
builder.add_node("classify_intent", classify_intent)
builder.add_node("rag_faq", rag_faq)
# ...
```

---

## 3. Edges

**File:** `ai/graph.py`

**Edges** define fixed transitions between nodes.

```python
builder.set_entry_point("classify_intent")
builder.add_edge("rag_faq", END)
builder.add_edge("order_lookup", END)
builder.add_edge("refund_prepare", "refund_execute")
builder.add_edge("refund_execute", END)
builder.add_edge("agent_tool_executor", "agent_loop_step")
```

**Key idea:** `add_edge("A", "B")` means node A always goes to node B.

---

## 4. Conditional edges / routing

**Files:** `ai/graph.py`, `ai/nodes.py`

**Conditional edges** route to different nodes based on state.

### Intent routing (after `classify_intent`)

```python
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
```

`route_by_intent()` returns `state["intent"]`.

### Agent loop routing

```python
builder.add_conditional_edges(
    "agent_loop_step",
    should_continue_agent_loop,
    {"tools": "agent_tool_executor", "end": END},
)
```

`should_continue_agent_loop()` checks if the last LLM message has `tool_calls`.

---

## 5. Tool calling

**Files:** `ai/tools.py`, `ai/nodes.py`

Tools are Python functions decorated with `@tool` from LangChain:

| Tool | Description |
|------|-------------|
| `lookup_order` | Fetch order by order number |
| `lookup_customer` | Fetch customer by email |
| `create_support_ticket` | Create a support ticket |
| `search_policies` | Semantic search over knowledge base |

**Two usage patterns:**

1. **Direct invocation** — `order_lookup` node calls `lookup_order.invoke(...)` directly.
2. **LLM-driven** — `agent_loop_step` uses `_get_llm_with_tools()` (`bind_tools`) and `agent_tool_executor` runs whatever the LLM requests.

---

## 6. Agent loops

**Files:** `ai/graph.py`, `ai/nodes.py`

For `unknown` intent, a **ReAct loop** runs until the LLM produces a final answer:

```text
agent_loop_step
    ↓ (LLM has tool_calls?)
agent_tool_executor
    ↓
agent_loop_step   ← loops back
    ↓ (no tool_calls)
END
```

```python
# agent_loop_step: LLM decides
response = _get_llm_with_tools().invoke(messages)

# agent_tool_executor: run tools, return ToolMessages
# Loop continues until LLM responds without tool_calls
```

---

## 7. Memory & checkpointing

**Files:** `ai/graph.py`, `backend/services/agent_service.py`, `ai/conversation.py`

### In-memory (LangGraph)

```python
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer, ...)
```

Each request passes a `thread_id`:

```python
config = {"configurable": {"thread_id": thread_id}}
graph.invoke(state, config)
```

LangGraph stores checkpointed state per `thread_id` (agent state, HITL pause point, etc.).

### Persistent (database)

`ai/conversation.py` stores full message history in `chat_sessions` / `chat_messages`.

When invoking the graph:

- **All messages** are saved to the DB (for UI history).
- **Only recent messages** (+ optional summary) are sent to the LLM:

| Setting | Value | Purpose |
|---------|-------|---------|
| `MAX_CONTEXT_MESSAGES` | 10 | Last N messages sent to agent |
| `SUMMARIZE_THRESHOLD` | 20 | Auto-summarize older messages into `session.summary` |

```python
messages = conv.build_langchain_messages(session)  # summary + recent window
graph.invoke({"messages": messages, ...}, config)
```

---

## 8. Human-in-the-loop (HITL)

**Files:** `ai/graph.py`, `ai/nodes.py`, `backend/routes/hitl.py`, frontend HITL panel

Refund requests pause for human approval before execution.

### Graph setup

```python
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["refund_execute"],
)
```

### Flow

```text
1. User: "I want a refund for ORD-1001"
2. refund_prepare → sets pending_refund, agent_status = waiting_for_human
3. Graph PAUSES before refund_execute
4. Frontend shows approval panel
5. POST /api/hitl/approve  → updates pending_refund.approved
6. POST /api/hitl/resume    → graph continues → refund_execute
```

**API endpoints:**

| Method | Path | Action |
|--------|------|--------|
| `POST` | `/api/hitl/approve` | Approve or reject pending refund |
| `POST` | `/api/hitl/resume` | Resume graph after decision |

---

## 9. RAG + LangGraph

**Files:** `ai/rag.py`, `ai/nodes.py` (`rag_faq`)

Retrieval-Augmented Generation combines vector search with the LLM inside a graph node.

```text
User question
    ↓
embed_text()                    ← OpenAI text-embedding-3-small (128 dims)
    ↓
semantic_search_db()            ← pgvector cosine similarity
    ↓
build_rag_context()             ← format retrieved chunks
    ↓
rag_faq node                    ← LLM answers using context only
    ↓
Response
```

The `rag_faq` node injects retrieved context into the LLM prompt and stores it in `state["rag_context"]`.

---

## 10. Error handling & retries

**File:** `ai/nodes.py`

### Implemented

- `tenacity` `@retry` decorator on `_retryable_llm_call` (exponential backoff, max 3 attempts).
- `error_count` field in `AgentState`.
- `handle_error` node with graceful fallback message.

### Gap

`handle_error` is **registered** as a node but has **no edges** connecting it to the graph. Errors are currently caught in `backend/services/agent_service.py` try/except instead.

**To complete this concept:** add conditional routing to `handle_error` on failure, e.g.:

```python
# Example (not yet in codebase):
builder.add_edge("some_node", "handle_error")  # on exception path
```

---

## Related features (not core LangGraph)

| Feature | Files | Notes |
|---------|-------|-------|
| **Langfuse tracing** | `ai/langfuse_tracing.py` | LLM/token tracing via LangChain callbacks; `thread_id` = Langfuse session |
| **Chat history UI** | `frontend/src/components/SidePanel.tsx` | Resume conversations; uses DB, not LangGraph directly |
| **Postgres schema** | `customer_support_agent` | All tables in dedicated schema via `DB_SCHEMA` + `search_path` |

---

## Example end-to-end flows

### FAQ (RAG)

```text
POST /api/chat  {"message": "What is your return policy?"}
  → classify_intent  → intent: "faq"
  → rag_faq          → pgvector search + LLM answer
  → END
```

### Order lookup

```text
POST /api/chat  {"message": "Where is order ORD-1001?"}
  → classify_intent  → intent: "order"
  → order_lookup     → lookup_order tool
  → END
```

### Refund with HITL

```text
POST /api/chat  {"message": "Refund order ORD-1001"}
  → classify_intent   → intent: "refund"
  → refund_prepare    → pending_refund set, graph pauses
  → [human approves]
  → POST /api/hitl/approve + /api/hitl/resume
  → refund_execute    → saves to refund_requests table
  → END
```

### Unknown intent (agent loop)

```text
POST /api/chat  {"message": "Look up bob@example.com"}
  → classify_intent     → intent: "unknown"
  → agent_loop_step     → LLM calls lookup_customer tool
  → agent_tool_executor → runs tool
  → agent_loop_step     → LLM formats final answer
  → END
```

---

## File index

| File | LangGraph role |
|------|----------------|
| `ai/state.py` | Shared state definition |
| `ai/graph.py` | Graph assembly, edges, compile, checkpointer, HITL interrupt |
| `ai/nodes.py` | All node functions + routing helpers |
| `ai/tools.py` | Tool definitions |
| `ai/rag.py` | RAG retrieval (used by `rag_faq` node) |
| `ai/conversation.py` | DB history → graph message context |
| `ai/langfuse_tracing.py` | Observability wrapper around graph runs |
| `backend/services/agent_service.py` | Invokes graph, manages thread_id, HITL resume |
| `backend/routes/hitl.py` | HITL REST API |

---

## Further reading

- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- Project README: architecture overview
- `RUNNING.md`: how to run and test each flow

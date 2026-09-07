# Customer Support AI Agent

A LangGraph learning project — customer support chatbot with RAG, tool calling, and human-in-the-loop refunds.

**→ [How to run the project](RUNNING.md)**  
**→ [LangGraph concepts map](LANGGRAPH_CONCEPTS.md)**

## Architecture

```text
customer-support-agent/
├── frontend/        # React + TypeScript chat UI
├── backend/         # FastAPI REST API
├── ai/              # LangGraph agent, tools, RAG
├── supabase/        # SQL schema, sample data, embedding seeder
├── .env.example
└── README.md
```

```text
User (React)
    ↓ POST /api/chat
FastAPI Backend
    ↓
LangGraph Agent
    ↓
Classify Intent
    ↓
Conditional Routing
    ├── FAQ    → RAG (pgvector)     → Response
    ├── Order  → Order Tool          → Response
    ├── Refund → Refund Tool → HITL  → Response
    └── Unknown → Agent Loop         → Response
```

## LangGraph Concepts Map

| # | Concept | Where Implemented |
|---|---------|-------------------|
| 1 | **State & StateGraph** | `ai/state.py` — `AgentState` TypedDict; `ai/graph.py` — `StateGraph(AgentState)` |
| 2 | **Nodes** | `ai/nodes.py` — `classify_intent`, `rag_faq`, `order_lookup`, `refund_prepare`, `agent_loop_step`, etc. |
| 3 | **Edges** | `ai/graph.py` — `add_edge("rag_faq", END)`, `add_edge("refund_prepare", "refund_execute")` |
| 4 | **Conditional Edges / Routing** | `ai/graph.py` — `add_conditional_edges("classify_intent", route_by_intent, {...})` |
| 5 | **Tool Calling** | `ai/tools.py` — `@tool` functions; `ai/nodes.py` — `order_lookup`, `agent_tool_executor` |
| 6 | **Agent Loops** | `ai/graph.py` — `agent_loop_step` ↔ `agent_tool_executor` cycle until LLM stops calling tools |
| 7 | **Memory & Checkpointing** | `ai/graph.py` — `MemorySaver()` checkpointer; `thread_id` in `backend/services/agent_service.py` |
| 8 | **Human-in-the-Loop (HITL)** | `ai/graph.py` — `interrupt_before=["refund_execute"]`; `backend/routes/hitl.py` — approve/resume |
| 9 | **RAG + LangGraph** | `ai/rag.py` — pgvector semantic search; `ai/nodes.py` — `rag_faq` node injects context |
| 10 | **Error Handling & Retries** | `ai/nodes.py` — `handle_error` node + `@retry` decorator with exponential backoff |

## Prerequisites

- Python 3.11+
- Node.js 18+
- A [Supabase](https://supabase.com) project with pgvector enabled
- An [OpenAI API key](https://platform.openai.com/api-keys)

## Setup

### 1. Clone and configure environment

```bash
cp .env.example .env
# Edit .env with your keys:
#   OPENAI_API_KEY
#   SUPABASE_URL
#   SUPABASE_SERVICE_ROLE_KEY
#   SUPABASE_ANON_KEY
```

### 2. Set up Supabase database

In the Supabase SQL Editor, run the migrations in order:

1. `supabase/migrations/001_schema.sql` — tables, pgvector, RLS, search function
2. `supabase/migrations/002_sample_data.sql` — sample customers, orders, tickets, KB docs

Then generate embeddings for the knowledge base:

```bash
pip install -r ai/requirements.txt
python supabase/seed_embeddings.py
```

### 3. Install and run the backend

```bash
cd backend
pip install -r requirements.txt
cd ..
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 4. Install and run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send a message; returns response + agent status |
| `GET`  | `/api/chat/{thread_id}` | Get conversation state |
| `POST` | `/api/hitl/approve` | Approve/reject a pending refund |
| `POST` | `/api/hitl/resume` | Resume graph after HITL decision |
| `GET`  | `/health` | Health check |

### Example: FAQ (RAG)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is your return policy?"}'
```

### Example: Order lookup

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Where is my order ORD-1001?"}'
```

### Example: Refund with HITL

```bash
# Step 1: Request refund (pauses for human approval)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want a refund for order ORD-1001, alice@example.com"}'

# Response includes thread_id and agent_status: "waiting_for_human"

# Step 2: Human approves
curl -X POST http://localhost:8000/api/hitl/approve \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "<thread_id>", "approved": true}'

# Step 3: Resume execution
curl -X POST http://localhost:8000/api/hitl/resume \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "<thread_id>"}'
```

## End-to-End Execution Flow

**Scenario: "I want a refund for order ORD-1001"**

```text
1. User sends message via React UI
2. FastAPI POST /api/chat → agent_service.run_chat()
3. LangGraph invokes with thread_id (checkpointed in MemorySaver)

4. classify_intent node
   → LLM classifies intent as "refund"
   → Conditional edge routes to refund_prepare

5. refund_prepare node
   → Calls lookup_order tool for ORD-1001
   → Sets pending_refund + agent_status: "waiting_for_human"
   → Graph interrupts BEFORE refund_execute (HITL)

6. Frontend shows HITL approval panel
   → Human clicks "Approve Refund"
   → POST /api/hitl/approve → updates state
   → POST /api/hitl/resume → graph continues

7. refund_execute node
   → Writes refund_requests row to Supabase
   → Returns confirmation message
   → agent_status: "completed"
```

**Scenario: "What is your return policy?"**

```text
1. classify_intent → "faq"
2. rag_faq node
   → embed_text() generates 128-dim vector
   → match_knowledge_base() searches pgvector
   → LLM answers using retrieved context
3. Response returned, agent_status: "completed"
```

## Sample Data

| Customer | Email | Orders |
|----------|-------|--------|
| Alice Johnson | alice@example.com | ORD-1001 (delivered), ORD-1002 (shipped) |
| Bob Smith | bob@example.com | ORD-2001 (processing) |

Knowledge base covers: return policy, shipping, refunds, warranty, contact info, order tracking.

## Tech Stack

- **Frontend:** React 18, TypeScript, Vite
- **Backend:** FastAPI, Uvicorn
- **AI:** LangGraph, LangChain, OpenAI (`gpt-4o-mini`, `text-embedding-3-small` @ 128 dims)
- **Database:** Supabase (Postgres + pgvector)

## License

MIT

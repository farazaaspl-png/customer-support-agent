# Running the Customer Support AI Agent

Step-by-step guide to run the full stack locally.

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |
| OpenAI API key | [platform.openai.com](https://platform.openai.com/api-keys) |
| Supabase project | [supabase.com](https://supabase.com) with pgvector enabled |

## 1. Clone and checkout

```bash
git clone https://github.com/farazaaspl-png/customer-support-agent.git
cd customer-support-agent
git checkout develop
```

## 2. Environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required
OPENAI_API_KEY=sk-your-openai-api-key

# Supabase (project ref: rtbeplnzylplpyudrgde)
SUPABASE_URL=https://rtbeplnzylplpyudrgde.supabase.co
DATABASE_URL=postgresql://postgres.rtbeplnzylplpyudrgde:YOUR_PASSWORD@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres

# Optional (REST API — not required if DATABASE_URL is set)
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173

# Frontend
VITE_API_URL=http://localhost:8000

# Langfuse (LLM tracing & token usage) — https://us.cloud.langfuse.com
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
LANGFUSE_ENABLED=true
```

> **Never commit `.env` to git.** It is listed in `.gitignore`.

## 3. Set up Supabase database

### Option A — Supabase SQL Editor

Run these files in order in the [SQL Editor](https://supabase.com/dashboard/project/rtbeplnzylplpyudrgde/sql):

1. `supabase/migrations/001_schema.sql`
2. `supabase/migrations/002_sample_data.sql`

### Option B — psql

```bash
PGPASSWORD='your-password' psql \
  -h aws-0-ap-northeast-2.pooler.supabase.com \
  -p 6543 \
  -U postgres.rtbeplnzylplpyudrgde \
  -d postgres \
  -f supabase/migrations/001_schema.sql

PGPASSWORD='your-password' psql \
  -h aws-0-ap-northeast-2.pooler.supabase.com \
  -p 6543 \
  -U postgres.rtbeplnzylplpyudrgde \
  -d postgres \
  -f supabase/migrations/002_sample_data.sql
```

### Seed knowledge-base embeddings

```bash
pip3 install -r ai/requirements.txt
export $(grep -v '^#' .env | xargs)
python3 supabase/seed_embeddings.py
```

Or seed manually with direct Postgres (see `supabase/SETUP.md`).

## 4. Install dependencies

### Backend + AI

```bash
pip3 install -r backend/requirements.txt
```

### Frontend

```bash
cd frontend
npm install
cd ..
```

## 5. Start the backend

From the project root:

```bash
export $(grep -v '^#' .env | xargs)
PYTHONPATH=. python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Verify:

- Health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## 6. Start the frontend

In a **second terminal**:

```bash
cd frontend
npm run dev
```

Open: http://localhost:5173

## 7. Test the app

### In the browser

Try these messages in the chat UI:

| Message | Expected flow |
|---------|---------------|
| `What is your return policy?` | FAQ → RAG answer |
| `Where is order ORD-1001?` | Order lookup tool |
| `I want a refund for order ORD-1001` | HITL approval panel appears |
| `Look up customer bob@example.com` | Agent loop with tools |

### Via curl

**Health check**

```bash
curl http://localhost:8000/health
```

**FAQ (RAG)**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is your return policy?"}'
```

**Order lookup**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Where is my order ORD-1001?"}'
```

**Refund with HITL**

```bash
# Step 1 — request refund (returns thread_id + waiting_for_human)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want a refund for order ORD-1001, alice@example.com"}'

# Step 2 — approve (use thread_id from step 1)
curl -X POST http://localhost:8000/api/hitl/approve \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "YOUR_THREAD_ID", "approved": true}'

# Step 3 — resume graph
curl -X POST http://localhost:8000/api/hitl/resume \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "YOUR_THREAD_ID"}'
```

## 8. Verified test results

All flows were tested and confirmed working:

| Test | Status | Result |
|------|--------|--------|
| `GET /health` | ✅ | `{"status":"ok"}` |
| FAQ / RAG | ✅ | Returns 30-day return policy |
| Order lookup | ✅ | ORD-1001 → delivered, $149.99 |
| Refund HITL | ✅ | Pauses → approve → resume → refund saved |
| Agent loop | ✅ | Looks up bob@example.com + ORD-2001 |
| Frontend | ✅ | http://localhost:5173 returns 200 |

## Project URLs (when running locally)

| Service | URL |
|---------|-----|
| Chat UI | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| Supabase dashboard | https://supabase.com/dashboard/project/rtbeplnzylplpyudrgde |

## Troubleshooting

### Backend won't start — port in use

```bash
fuser -k 8000/tcp
```

### RAG returns "no policy found"

Re-seed embeddings:

```bash
export $(grep -v '^#' .env | xargs)
python3 supabase/seed_embeddings.py
```

### Database connection fails

- Confirm `DATABASE_URL` password is correct
- Use the **pooler** host: `aws-0-ap-northeast-2.pooler.supabase.com:6543`
- User format: `postgres.rtbeplnzylplpyudrgde`

### Frontend can't reach API

- Ensure backend is running on port 8000
- Check `VITE_API_URL=http://localhost:8000` in `.env`
- Restart frontend after changing env vars

### CORS errors

Add your frontend URL to `CORS_ORIGINS` in `.env`:

```env
CORS_ORIGINS=http://localhost:5173
```

## Supabase MCP (Cursor Desktop)

To manage the database from Cursor chat:

1. Ensure `.mcp.json` exists at the project root
2. Authenticate Supabase MCP in **Cursor Settings → MCP**
3. Select project `rtbeplnzylplpyudrgde`

See `supabase/SETUP.md` for full MCP setup details.

## Sample data reference

| Customer | Email | Orders |
|----------|-------|--------|
| Alice Johnson | alice@example.com | ORD-1001 (delivered), ORD-1002 (shipped) |
| Bob Smith | bob@example.com | ORD-2001 (processing) |
| Carol Williams | carol@example.com | — |

Knowledge base topics: return policy, shipping, refunds, warranty, contact, order tracking.

## Langfuse tracing

LLM calls and token usage are traced automatically when Langfuse env vars are set.

1. Add `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_BASE_URL` to `.env`
2. Start the backend and send a chat message
3. Open [Langfuse dashboard](https://us.cloud.langfuse.com) → **Traces**

Each conversation `thread_id` is used as the Langfuse **session ID**, so you can group traces by chat session. Traces include:

- Intent classification, RAG, order lookup, refund, and agent-loop nodes
- Token usage and model name per LLM call
- Embedding calls for RAG (`embed_text`)

Set `LANGFUSE_ENABLED=false` to disable tracing without removing keys.

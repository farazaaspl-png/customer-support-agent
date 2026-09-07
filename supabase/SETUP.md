# Supabase MCP + Database Setup

This project uses Supabase for Postgres, pgvector RAG, and (optionally) the **Supabase MCP** server in Cursor.

## Project details

| Setting | Value |
|---------|-------|
| Project ref | `rtbeplnzylplpyudrgde` |
| API URL | `https://rtbeplnzylplpyudrgde.supabase.co` |
| DB host | `aws-0-ap-northeast-2.pooler.supabase.com` |
| DB port | `6543` |
| DB user | `postgres.rtbeplnzylplpyudrgde` |
| DB name | `postgres` |

## 1. Authenticate Supabase MCP (Cursor Desktop)

Cloud Agents **cannot** complete OAuth interactively. Authenticate in **Cursor Desktop**:

1. Open this repo in **Cursor Desktop** (not only the cloud agent).
2. Confirm `.mcp.json` exists at the repo root:

```json
{
  "mcpServers": {
    "supabase": {
      "url": "https://mcp.supabase.com/mcp"
    }
  }
}
```

3. Open **Cursor Settings → MCP** (or **Features → MCP**).
4. Find **Supabase** and click **Authenticate** / **Connect**.
5. Complete the browser OAuth flow and select project **`rtbeplnzylplpyudrgde`**.
6. Reload the window or start a new agent chat so MCP tools appear.

After auth, the agent can use MCP tools such as `execute_sql`, `search_docs`, and `get_advisors`.

### Verify MCP is working

In a Cursor chat (desktop), ask:

> Use Supabase MCP to list tables in my project.

You should see `customers`, `orders`, `knowledge_base`, etc.

## 2. API keys (required for the Python app)

The FastAPI backend uses the **Supabase REST API** (not the raw DB password).

1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/rtbeplnzylplpyudrgde/settings/api).
2. Copy into `.env`:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_ANON_KEY`
   - **service_role** → `SUPABASE_SERVICE_ROLE_KEY` (keep secret; server-side only)

```env
SUPABASE_URL=https://rtbeplnzylplpyudrgde.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...   # from dashboard
SUPABASE_ANON_KEY=eyJ...           # from dashboard
DATABASE_URL=postgresql://postgres.rtbeplnzylplpyudrgde:YOUR_PASSWORD@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
```

## 3. Database migrations (already applied)

Migrations were run against your project:

- `supabase/migrations/001_schema.sql` — tables, pgvector, RLS, `match_knowledge_base()`
- `supabase/migrations/002_sample_data.sql` — sample customers, orders, tickets, KB docs
- Knowledge-base **embeddings** seeded (128-dim `text-embedding-3-small`)

### Re-run manually (psql)

```bash
PGPASSWORD='your-db-password' psql \
  -h aws-0-ap-northeast-2.pooler.supabase.com \
  -p 6543 \
  -U postgres.rtbeplnzylplpyudrgde \
  -d postgres \
  -f supabase/migrations/001_schema.sql

PGPASSWORD='your-db-password' psql \
  -h aws-0-ap-northeast-2.pooler.supabase.com \
  -p 6543 \
  -U postgres.rtbeplnzylplpyudrgde \
  -d postgres \
  -f supabase/migrations/002_sample_data.sql
```

### Re-seed embeddings

```bash
python3 supabase/seed_embeddings.py
# Requires SUPABASE_SERVICE_ROLE_KEY in .env
```

## 4. Security notes

- Never commit `.env` or database passwords to git.
- `service_role` bypasses RLS — use only on the backend.
- Rotate credentials if they were shared in chat.

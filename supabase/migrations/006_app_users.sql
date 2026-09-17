-- App users (simple demo auth) + link chat sessions to users for Langfuse user_id tracing

CREATE TABLE IF NOT EXISTS customer_support_agent.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE customer_support_agent.chat_sessions
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES customer_support_agent.users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id
    ON customer_support_agent.chat_sessions(user_id);

ALTER TABLE customer_support_agent.users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all users" ON customer_support_agent.users;
CREATE POLICY "Allow all users" ON customer_support_agent.users
    FOR ALL USING (true) WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE, DELETE ON customer_support_agent.users TO postgres, anon, authenticated, service_role;

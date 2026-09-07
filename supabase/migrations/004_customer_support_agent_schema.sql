-- Move all tables from public → customer_support_agent schema

CREATE SCHEMA IF NOT EXISTS customer_support_agent;

-- Core tables
ALTER TABLE IF EXISTS public.customers SET SCHEMA customer_support_agent;
ALTER TABLE IF EXISTS public.orders SET SCHEMA customer_support_agent;
ALTER TABLE IF EXISTS public.support_tickets SET SCHEMA customer_support_agent;
ALTER TABLE IF EXISTS public.knowledge_base SET SCHEMA customer_support_agent;
ALTER TABLE IF EXISTS public.refund_requests SET SCHEMA customer_support_agent;

-- Chat history tables
ALTER TABLE IF EXISTS public.chat_sessions SET SCHEMA customer_support_agent;
ALTER TABLE IF EXISTS public.chat_messages SET SCHEMA customer_support_agent;

-- Recreate semantic search function in new schema
DROP FUNCTION IF EXISTS public.match_knowledge_base(vector, double precision, integer);

CREATE OR REPLACE FUNCTION customer_support_agent.match_knowledge_base(
    query_embedding vector(128),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    content TEXT,
    category TEXT,
    similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        kb.id,
        kb.title,
        kb.content,
        kb.category,
        1 - (kb.embedding <=> query_embedding) AS similarity
    FROM customer_support_agent.knowledge_base kb
    WHERE kb.embedding IS NOT NULL
      AND 1 - (kb.embedding <=> query_embedding) > match_threshold
    ORDER BY kb.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Grants for Supabase roles
GRANT USAGE ON SCHEMA customer_support_agent TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA customer_support_agent TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA customer_support_agent TO postgres, anon, authenticated, service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA customer_support_agent TO postgres, anon, authenticated, service_role;

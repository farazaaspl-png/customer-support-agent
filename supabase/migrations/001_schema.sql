-- Customer Support AI Agent - Database Schema
-- Run this in Supabase SQL Editor or via supabase db push

-- Enable pgvector for semantic search (128-dim embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_number TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
    total_amount DECIMAL(10, 2) NOT NULL,
    items JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Support tickets
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge base documents for RAG
CREATE TABLE IF NOT EXISTS knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    -- OpenAI text-embedding-3-small with 128 dimensions
    embedding vector(128),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Refund requests (tracked for HITL workflow)
CREATE TABLE IF NOT EXISTS refund_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_approval'
        CHECK (status IN ('pending_approval', 'approved', 'rejected', 'processed')),
    approved_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_support_tickets_customer_id ON support_tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_category ON knowledge_base(category);

-- Semantic search index (IVFFlat for small datasets)
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding
    ON knowledge_base USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

-- RLS: enable on all tables (service role bypasses; anon read for demo)
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_base ENABLE ROW LEVEL SECURITY;
ALTER TABLE refund_requests ENABLE ROW LEVEL SECURITY;

-- Permissive policies for learning/demo (tighten in production)
CREATE POLICY "Allow read customers" ON customers FOR SELECT USING (true);
CREATE POLICY "Allow read orders" ON orders FOR SELECT USING (true);
CREATE POLICY "Allow read support_tickets" ON support_tickets FOR SELECT USING (true);
CREATE POLICY "Allow read knowledge_base" ON knowledge_base FOR SELECT USING (true);
CREATE POLICY "Allow read refund_requests" ON refund_requests FOR SELECT USING (true);
CREATE POLICY "Allow insert refund_requests" ON refund_requests FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow update refund_requests" ON refund_requests FOR UPDATE USING (true);

-- Semantic search function
CREATE OR REPLACE FUNCTION match_knowledge_base(
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
    FROM knowledge_base kb
    WHERE kb.embedding IS NOT NULL
      AND 1 - (kb.embedding <=> query_embedding) > match_threshold
    ORDER BY kb.embedding <=> query_embedding
    LIMIT match_count;
$$;

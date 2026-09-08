-- Role-based access for the customer support agent app.
-- Roles customer_support_readonly and customer_support_agent are created in Supabase;
-- this migration applies schema grants and the HITL refund function.

GRANT USAGE ON SCHEMA customer_support_agent TO customer_support_readonly, customer_support_agent;

-- ---------------------------------------------------------------------------
-- customer_support_readonly: SELECT only
-- ---------------------------------------------------------------------------
GRANT SELECT ON ALL TABLES IN SCHEMA customer_support_agent TO customer_support_readonly;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA customer_support_agent
    FROM customer_support_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA customer_support_agent
    GRANT SELECT ON TABLES TO customer_support_readonly;

-- ---------------------------------------------------------------------------
-- customer_support_agent: read + limited write (no DELETE/TRUNCATE)
-- ---------------------------------------------------------------------------
GRANT SELECT ON ALL TABLES IN SCHEMA customer_support_agent TO customer_support_agent;

GRANT INSERT, UPDATE ON customer_support_agent.chat_sessions TO customer_support_agent;
GRANT INSERT ON customer_support_agent.chat_messages TO customer_support_agent;
GRANT INSERT ON customer_support_agent.support_tickets TO customer_support_agent;

REVOKE DELETE, TRUNCATE ON ALL TABLES IN SCHEMA customer_support_agent
    FROM customer_support_agent;
REVOKE INSERT, UPDATE ON customer_support_agent.refund_requests FROM customer_support_agent;
REVOKE INSERT, UPDATE, DELETE ON customer_support_agent.customers FROM customer_support_agent;
REVOKE INSERT, UPDATE, DELETE ON customer_support_agent.orders FROM customer_support_agent;
REVOKE INSERT, UPDATE, DELETE ON customer_support_agent.knowledge_base FROM customer_support_agent;

ALTER DEFAULT PRIVILEGES IN SCHEMA customer_support_agent
    GRANT SELECT ON TABLES TO customer_support_agent;

-- ---------------------------------------------------------------------------
-- HITL refund: INSERT only via SECURITY DEFINER function
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION customer_support_agent.insert_approved_refund(
    p_order_id UUID,
    p_customer_id UUID,
    p_amount DECIMAL(10, 2),
    p_reason TEXT,
    p_approved_by TEXT
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = customer_support_agent, public
AS $$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO refund_requests (order_id, customer_id, amount, reason, status, approved_by)
    VALUES (p_order_id, p_customer_id, p_amount, p_reason, 'approved', p_approved_by)
    RETURNING id INTO v_id;
    RETURN v_id;
END;
$$;

REVOKE ALL ON FUNCTION customer_support_agent.insert_approved_refund(UUID, UUID, DECIMAL, TEXT, TEXT)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION customer_support_agent.insert_approved_refund(UUID, UUID, DECIMAL, TEXT, TEXT)
    TO customer_support_agent;

GRANT EXECUTE ON FUNCTION customer_support_agent.match_knowledge_base(vector, double precision, integer)
    TO customer_support_readonly, customer_support_agent;

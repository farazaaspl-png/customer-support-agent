-- Rename app_users → users (schema: customer_support_agent)

ALTER TABLE customer_support_agent.app_users RENAME TO users;

DROP POLICY IF EXISTS "Allow all app_users" ON customer_support_agent.users;
CREATE POLICY "Allow all users" ON customer_support_agent.users
    FOR ALL USING (true) WITH CHECK (true);

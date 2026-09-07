-- Sample data for Customer Support AI Agent
-- Embeddings are populated by supabase/seed_embeddings.py

INSERT INTO customers (id, email, name) VALUES
    ('11111111-1111-1111-1111-111111111111', 'alice@example.com', 'Alice Johnson'),
    ('22222222-2222-2222-2222-222222222222', 'bob@example.com', 'Bob Smith'),
    ('33333333-3333-3333-3333-333333333333', 'carol@example.com', 'Carol Williams')
ON CONFLICT (email) DO NOTHING;

INSERT INTO orders (id, customer_id, order_number, status, total_amount, items) VALUES
    (
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        '11111111-1111-1111-1111-111111111111',
        'ORD-1001',
        'delivered',
        149.99,
        '[{"name": "Wireless Headphones", "qty": 1, "price": 149.99}]'::jsonb
    ),
    (
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        '11111111-1111-1111-1111-111111111111',
        'ORD-1002',
        'shipped',
        59.98,
        '[{"name": "USB-C Cable", "qty": 2, "price": 29.99}]'::jsonb
    ),
    (
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        '22222222-2222-2222-2222-222222222222',
        'ORD-2001',
        'processing',
        299.00,
        '[{"name": "Smart Watch", "qty": 1, "price": 299.00}]'::jsonb
    )
ON CONFLICT (order_number) DO NOTHING;

INSERT INTO support_tickets (customer_id, order_id, subject, description, status, priority) VALUES
    (
        '11111111-1111-1111-1111-111111111111',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'Headphones not charging',
        'My wireless headphones stopped charging after 2 weeks of use.',
        'open',
        'high'
    ),
    (
        '22222222-2222-2222-2222-222222222222',
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        'Order delay inquiry',
        'When will my smart watch ship?',
        'in_progress',
        'normal'
    );

INSERT INTO knowledge_base (title, content, category) VALUES
    (
        'Return Policy',
        'We offer a 30-day return policy on all items. Items must be unused and in original packaging. Refunds are processed within 5-7 business days after we receive the returned item.',
        'returns'
    ),
    (
        'Shipping Information',
        'Standard shipping takes 5-7 business days. Express shipping (2-3 days) is available for $9.99. Free shipping on orders over $50.',
        'shipping'
    ),
    (
        'Refund Process',
        'Refunds are issued to the original payment method. Processing takes 5-7 business days. For defective items, we offer full refunds including return shipping costs.',
        'refunds'
    ),
    (
        'Warranty Coverage',
        'All electronics come with a 1-year manufacturer warranty. Extended warranty (2 additional years) is available at checkout for $19.99.',
        'warranty'
    ),
    (
        'Contact Support',
        'Our support team is available Monday-Friday 9am-6pm EST. Email support@acmestore.com or call 1-800-ACME-HELP. Average response time is under 2 hours.',
        'general'
    ),
    (
        'Order Tracking',
        'Track your order using the order number (e.g., ORD-1001) on our website. You will receive a tracking email once your order ships.',
        'orders'
    );

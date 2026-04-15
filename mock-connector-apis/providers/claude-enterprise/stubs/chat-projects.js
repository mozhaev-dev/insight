// Stub for GET /v1/organizations/analytics/apps/chat/projects

module.exports = [
  {
    project_name: 'Marketing Campaign Q1',
    project_id: 'claude_proj_marketing_q1',
    distinct_user_count: 3,
    distinct_conversation_count: 12,
    message_count: 87,
    created_at: '2026-02-15T10:30:00Z',
    created_by: { id: 'user_alice', email_address: 'alice@example.com' },
  },
  {
    project_name: 'Product Roadmap',
    project_id: 'claude_proj_product_roadmap',
    distinct_user_count: 5,
    distinct_conversation_count: 19,
    message_count: 142,
    created_at: '2026-03-01T14:22:00Z',
    created_by: { id: 'user_bob', email_address: 'bob@example.com' },
  },
];

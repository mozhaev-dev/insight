// Stub for GET /v1/organizations/analytics/connectors
// `connector_name` is normalized by the API (e.g., "atlassian" covers multiple
// naming variants upstream).

module.exports = [
  {
    connector_name: 'github',
    distinct_user_count: 2,
    chat_metrics: { distinct_conversation_connector_used_count: 5 },
    claude_code_metrics: { distinct_session_connector_used_count: 3 },
    office_metrics: {
      excel: { distinct_session_connector_used_count: 0 },
      powerpoint: { distinct_session_connector_used_count: 0 },
    },
    cowork_metrics: { distinct_session_connector_used_count: 1 },
  },
  {
    connector_name: 'slack',
    distinct_user_count: 1,
    chat_metrics: { distinct_conversation_connector_used_count: 2 },
    claude_code_metrics: { distinct_session_connector_used_count: 0 },
    office_metrics: {
      excel: { distinct_session_connector_used_count: 0 },
      powerpoint: { distinct_session_connector_used_count: 0 },
    },
    cowork_metrics: { distinct_session_connector_used_count: 1 },
  },
];

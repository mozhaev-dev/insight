// Stub for GET /v1/organizations/analytics/skills

module.exports = [
  {
    skill_name: 'web_search',
    distinct_user_count: 2,
    chat_metrics: { distinct_conversation_skill_used_count: 7 },
    claude_code_metrics: { distinct_session_skill_used_count: 1 },
    office_metrics: {
      excel: { distinct_session_skill_used_count: 0 },
      powerpoint: { distinct_session_skill_used_count: 0 },
    },
    cowork_metrics: { distinct_session_skill_used_count: 1 },
  },
  {
    skill_name: 'code_interpreter',
    distinct_user_count: 1,
    chat_metrics: { distinct_conversation_skill_used_count: 3 },
    claude_code_metrics: { distinct_session_skill_used_count: 2 },
    office_metrics: {
      excel: { distinct_session_skill_used_count: 0 },
      powerpoint: { distinct_session_skill_used_count: 0 },
    },
    cowork_metrics: { distinct_session_skill_used_count: 0 },
  },
];

// Provider configuration for the Anthropic Enterprise Analytics API.
//
// This file declares everything the generic HTTP layer needs to know:
//   - auth semantics (which header, what to return when missing)
//   - date constraints (min date, reporting lag)
//   - endpoint map (path → { stub data, pagination, date param shape })
//
// Add a new provider by creating providers/<name>/provider.js with the same
// shape. The server auto-discovers providers under providers/.

module.exports = {
  name: 'claude-enterprise',
  description: 'Anthropic Enterprise Analytics API (read:analytics scope)',

  auth: {
    header: 'x-api-key',
    // Anthropic returns 404 (not 401) for missing/wrong-scope keys.
    errorStatus: 404,
    errorMessage:
      'Missing or invalid x-api-key header (requires read:analytics scope)',
  },

  dateConstraints: {
    // API rejects dates before this with 400.
    minDate: '2026-01-01',
    // Data for day D is queryable only on day D + lagDays + 1 (3-day lag = available on D+4).
    lagDays: 3,
  },

  endpoints: {
    '/v1/organizations/analytics/users': {
      stub: require('./stubs/users'),
      pagination: 'cursor',
      dateParam: { name: 'date', required: true },
    },
    '/v1/organizations/analytics/summaries': {
      stub: require('./stubs/summaries'),
      pagination: 'none',
      dateRange: {
        startParam: 'starting_date',
        endParam: 'ending_date',
        maxDays: 31,
        exclusiveEnd: true,
      },
      // When dateRange is used, the HTTP layer filters records whose
      // <filterField> falls within [startParam, endParam).
      filterByField: 'date',
    },
    '/v1/organizations/analytics/apps/chat/projects': {
      stub: require('./stubs/chat-projects'),
      pagination: 'cursor',
      dateParam: { name: 'date', required: true },
    },
    '/v1/organizations/analytics/skills': {
      stub: require('./stubs/skills'),
      pagination: 'cursor',
      dateParam: { name: 'date', required: true },
    },
    '/v1/organizations/analytics/connectors': {
      stub: require('./stubs/connectors'),
      pagination: 'cursor',
      dateParam: { name: 'date', required: true },
    },
  },
};

// Bridge between HTTP layer and provider stubs.
//
// The HTTP layer calls `getResponse(provider, endpointPath, params)`.
// This looks up the endpoint in the provider config, applies pagination
// and/or date-range filtering according to that config, and returns a
// response object ready for JSON serialization.
//
// `setProvider(fn)` replaces the default resolver — useful for tests that
// want canned responses, simulated errors, or call recording. The override
// is global to the process (covers all providers).

const { paginate } = require('./pagination');

function defaultResolver(provider, endpointPath, params) {
  const endpointCfg = provider.endpoints[endpointPath];
  if (!endpointCfg) return null;
  const records = endpointCfg.stub;

  // Range-filtered (e.g., /summaries with starting_date/ending_date)
  if (endpointCfg.dateRange) {
    const { startParam, endParam, exclusiveEnd } = endpointCfg.dateRange;
    const start = params[startParam];
    const end = params[endParam];
    const field = endpointCfg.filterByField;

    if (!field) {
      // No field to filter on — return records as-is.
      return { data: records };
    }

    const filtered = records.filter((r) => {
      const v = r[field];
      if (start && v < start) return false;
      if (end) {
        if (exclusiveEnd ? v >= end : v > end) return false;
      }
      return true;
    });
    return { data: filtered };
  }

  // Cursor pagination (most single-date endpoints)
  if (endpointCfg.pagination === 'cursor') {
    const { data, nextPage } = paginate(records, params.page, params.limit);
    return { data, next_page: nextPage };
  }

  // No pagination, no filtering
  return { data: records };
}

let activeResolver = defaultResolver;

module.exports = {
  getResponse: (provider, endpointPath, params) =>
    activeResolver(provider, endpointPath, params),

  setProvider: (fn) => {
    activeResolver = fn || defaultResolver;
  },
  resetProvider: () => {
    activeResolver = defaultResolver;
  },
  defaultResolver,
};

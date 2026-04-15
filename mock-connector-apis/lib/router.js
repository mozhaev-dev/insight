// Generic request router. Reads auth + date validation rules from the
// provider config. No provider-specific logic lives here.

const { getResponse } = require('./stub-provider');
const { errors, json, error } = require('./http-helpers');
const { validateDate, validateDateRange } = require('./date-validation');

function checkAuth(req, authCfg) {
  if (!authCfg || !authCfg.header) return null; // auth not configured — accept all
  const value = req.headers[authCfg.header.toLowerCase()];
  if (!value || !String(value).trim()) {
    return {
      status: authCfg.errorStatus || 401,
      message: authCfg.errorMessage || 'Unauthorized',
    };
  }
  return null;
}

function handle(req, res, urlObj, provider) {
  // Global endpoints (not provider-specific)
  if (urlObj.pathname === '/' || urlObj.pathname === '/health') {
    return json(res, 200, { status: 'ok', provider: provider.name });
  }

  // Auth
  const authErr = checkAuth(req, provider.auth);
  if (authErr) return error(res, authErr.status, authErr.message);

  // Endpoint lookup
  const endpointCfg = provider.endpoints[urlObj.pathname];
  if (!endpointCfg) {
    return errors.notFound(res, `Unknown endpoint: ${urlObj.pathname}`);
  }

  const params = Object.fromEntries(urlObj.searchParams.entries());
  const constraints = provider.dateConstraints || {};

  // Date validation (single date param)
  if (endpointCfg.dateParam) {
    const { name, required } = endpointCfg.dateParam;
    if (required || params[name] != null) {
      const err = validateDate(params[name], constraints, name);
      if (err) return errors.badRequest(res, err);
    }
  }

  // Date validation (range)
  if (endpointCfg.dateRange) {
    const { startParam, endParam } = endpointCfg.dateRange;
    const err = validateDateRange(
      params[startParam],
      params[endParam],
      constraints,
      endpointCfg.dateRange,
    );
    if (err) return errors.badRequest(res, err);
  }

  // Dispatch to stub provider
  const response = getResponse(provider, urlObj.pathname, params);
  if (response === null) {
    return errors.notFound(res, `No stub data for ${urlObj.pathname}`);
  }
  return json(res, 200, response);
}

module.exports = { handle };

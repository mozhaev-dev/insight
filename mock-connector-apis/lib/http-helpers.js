// HTTP response helpers. Thin wrappers around res.writeHead + res.end.

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

function error(res, status, message, { details } = {}) {
  const body = { error: { message } };
  if (details) body.error.details = details;
  return json(res, status, body);
}

// Anthropic Enterprise Analytics API semantics (from docs):
//   400 — invalid query parameter (bad date, future date, pre-2026 date, range > 31d)
//   404 — missing/invalid API key or missing read:analytics scope
//   429 — rate limit exceeded
//   503 — transient failure

const errors = {
  badRequest:   (res, msg)  => error(res, 400, msg),
  notFound:     (res, msg)  => error(res, 404, msg),
  rateLimited:  (res, msg)  => error(res, 429, msg),
  unavailable:  (res, msg)  => error(res, 503, msg),
};

module.exports = { json, error, errors };

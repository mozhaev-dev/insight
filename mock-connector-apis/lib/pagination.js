// Cursor pagination helper.
//
// The real Anthropic API uses an opaque `page` token. We mimic that by
// base64-encoding a JSON object `{ offset: N }`. Clients treat it as opaque.

const DEFAULT_LIMIT = 100;
const MAX_LIMIT = 1000;

function encodeCursor(offset) {
  return Buffer.from(JSON.stringify({ offset })).toString('base64');
}

function decodeCursor(token) {
  if (!token) return 0;
  try {
    const obj = JSON.parse(Buffer.from(token, 'base64').toString('utf8'));
    return Number.isInteger(obj.offset) && obj.offset >= 0 ? obj.offset : 0;
  } catch {
    return 0;
  }
}

function paginate(records, pageToken, limitRaw) {
  const limit = Math.min(
    Math.max(parseInt(limitRaw, 10) || DEFAULT_LIMIT, 1),
    MAX_LIMIT,
  );
  const offset = decodeCursor(pageToken);
  const slice = records.slice(offset, offset + limit);
  const nextOffset = offset + slice.length;
  const hasMore = nextOffset < records.length;
  return {
    data: slice,
    nextPage: hasMore ? encodeCursor(nextOffset) : null,
  };
}

module.exports = { paginate, encodeCursor, decodeCursor, DEFAULT_LIMIT, MAX_LIMIT };

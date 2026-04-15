# mock-connector-apis

Generic multi-provider mock HTTP server for developing Insight connectors locally without real API access.

Each provider is a self-contained folder under `providers/` that declares its endpoints, auth rules, date constraints, and stubs. The HTTP core is provider-agnostic. **Temporary dev tool — not part of any production spec.**

Zero runtime dependencies. Node.js 20+.

## Run

```bash
cd mock-connector-apis

# Show available providers and exit
node server.js --list

# Run one provider
node server.js claude-enterprise
PORT=9090 node server.js claude-enterprise
PROVIDER=claude-enterprise node server.js

# Dev mode (hot reload on file changes)
node --watch server.js claude-enterprise
```

One provider per server instance. To run multiple providers simultaneously, start multiple servers on different ports.

## Available providers

| Provider | Description |
|----------|-------------|
| `claude-enterprise` | Anthropic Enterprise Analytics API (`/v1/organizations/analytics/*`) |

More can be added — see [Adding a provider](#adding-a-provider).

## Quick test

```bash
# Start it
node server.js claude-enterprise

# Then in another shell:
curl -s http://localhost:8080/ | jq                                    # health
curl -s -H 'x-api-key: any' \
  'http://localhost:8080/v1/organizations/analytics/users?date=2026-04-01&limit=2' | jq
```

## Structure

```
mock-connector-apis/
├── package.json
├── server.js                     # HTTP entry — CLI, provider selection
├── lib/                          # Provider-agnostic core
│   ├── router.js                 # auth + validation + dispatch (reads provider config)
│   ├── http-helpers.js           # JSON / error response helpers
│   ├── pagination.js             # cursor pagination (base64 opaque token)
│   ├── date-validation.js        # validateDate / validateDateRange
│   ├── provider-loader.js        # discovers providers/ and validates configs
│   └── stub-provider.js          # getResponse / setProvider (runtime override)
└── providers/
    └── claude-enterprise/
        ├── provider.js           # endpoint map + auth + date constraints
        └── stubs/
            ├── users.js
            ├── summaries.js
            ├── chat-projects.js
            ├── skills.js
            └── connectors.js
```

The HTTP core (`lib/`) has zero provider-specific logic. Every endpoint behavior is read from `providers/<name>/provider.js` at startup.

## Adding a provider

1. Create `providers/<your-provider>/` with a `provider.js` and a `stubs/` folder.
2. Write a provider config:

   ```js
   // providers/example/provider.js
   module.exports = {
     name: 'example',
     description: 'One-line description shown in --list',

     auth: {
       header: 'authorization',      // or 'x-api-key', etc.
       errorStatus: 401,              // what to return when missing
       errorMessage: 'Missing token',
     },

     // Optional. Omit for providers without date constraints.
     dateConstraints: {
       minDate: '2020-01-01',
       lagDays: 0,
     },

     endpoints: {
       '/api/v1/things': {
         stub: require('./stubs/things'),
         pagination: 'cursor',                          // or 'none'
         dateParam: { name: 'date', required: false },  // single-date endpoint
       },
       '/api/v1/events': {
         stub: require('./stubs/events'),
         pagination: 'none',
         dateRange: {
           startParam: 'from',
           endParam: 'to',
           maxDays: 30,
           exclusiveEnd: false,
         },
         filterByField: 'date',   // records whose r.date falls in [from, to]
       },
     },
   };
   ```

3. Write stubs: each stub file is a plain JS module that exports an array of records matching the API's response shape for that endpoint. Example:

   ```js
   // providers/example/stubs/things.js
   module.exports = [
     { id: 1, name: 'one' },
     { id: 2, name: 'two' },
   ];
   ```

4. Run: `node server.js example`

## Endpoint behavior recipes

| Endpoint shape | `pagination` | `dateParam` / `dateRange` | Result |
|----------------|--------------|---------------------------|--------|
| `GET /x?date=Y&page=T&limit=N` | `'cursor'` | `dateParam: { name: 'date', required: true }` | Cursor-paginated, date validated |
| `GET /x?from=A&to=B` returns records with `date` field in range | `'none'` | `dateRange: { startParam, endParam, maxDays, exclusiveEnd }` + `filterByField: 'date'` | Range-filtered, no pagination |
| `GET /x` (no dates, returns all) | `'cursor'` or `'none'` | omit both | All records, optional pagination |

Date validation rules come from `provider.dateConstraints`:
- `minDate` — reject anything earlier (`400`)
- `lagDays` — effective upper bound is `today − lagDays` (`400` for anything later)
- Omit both to disable date validation entirely

## Pagination

`page` is an opaque token (base64-encoded JSON with `{ offset }` inside). `next_page` is returned in the response until there are no more records, at which point it's `null`. `limit` defaults to 100, max 1000.

## Runtime override (for tests)

Replace the resolver that turns `(provider, endpoint, params)` into a response:

```js
const { setProvider, resetProvider } = require('./lib/stub-provider');

// Simulate an error or return canned data
setProvider((provider, endpoint, params) => {
  if (endpoint === '/v1/organizations/analytics/users') {
    return { data: [{ user: { id: 'fixed' } }], next_page: null };
  }
  return null; // → router returns 404
});

// Later
resetProvider();
```

The override is global to the process (covers all providers).

## Use from a connector

Set the `base_url` override on the connector's K8s Secret:

```yaml
stringData:
  # Any non-empty auth value works — mock only checks the header is present
  analytics_api_key: "dev-any-value"
  base_url: "http://host.docker.internal:8080"
```

The connector calls the mock identically to how it would call the real API — no code paths differ.

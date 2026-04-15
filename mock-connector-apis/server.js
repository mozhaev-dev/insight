#!/usr/bin/env node
// Mock connector APIs — multi-provider stub server.
//
// Usage:
//   node server.js <provider>              # listen on 0.0.0.0:8080
//   node server.js --provider=<provider>   # long form
//   PROVIDER=<provider> node server.js     # env var
//   node server.js --list                  # list available providers
//
// Port/host:
//   PORT=9090 HOST=127.0.0.1 node server.js
//
// Override stubs at runtime (for tests):
//   const { setProvider } = require('./lib/stub-provider');
//   setProvider((provider, endpoint, params) => ({ data: [...] }));

const http = require('node:http');
const { URL } = require('node:url');
const { handle } = require('./lib/router');
const { loadProvider, listProviders } = require('./lib/provider-loader');

// ── CLI & env parsing ──────────────────────────────────────────────────────

const args = process.argv.slice(2);
let providerName = process.env.PROVIDER || null;
let showList = false;
let showHelp = false;

for (const arg of args) {
  if (arg === '--list') showList = true;
  else if (arg === '--help' || arg === '-h') showHelp = true;
  else if (arg.startsWith('--provider=')) providerName = arg.slice(11);
  else if (!arg.startsWith('--')) providerName = arg; // positional
}

function printUsage(stream = process.stderr) {
  const providers = listProviders();
  stream.write(
    'Usage: node server.js <provider> [--port <n>]\n' +
      '       node server.js --list\n' +
      '       node server.js --help\n' +
      '\nAvailable providers:\n',
  );
  if (providers.length === 0) {
    stream.write('  (none — add a directory under providers/ with provider.js)\n');
  } else {
    for (const name of providers) {
      try {
        const cfg = loadProvider(name);
        stream.write(`  ${name}  —  ${cfg.description || ''}\n`);
      } catch (err) {
        stream.write(`  ${name}  —  (failed to load: ${err.message.split('\n')[0]})\n`);
      }
    }
  }
}

if (showHelp) {
  printUsage(process.stdout);
  process.exit(0);
}

if (showList) {
  printUsage(process.stdout);
  process.exit(0);
}

if (!providerName) {
  process.stderr.write('ERROR: no provider specified.\n\n');
  printUsage();
  process.exit(1);
}

let provider;
try {
  provider = loadProvider(providerName);
} catch (err) {
  process.stderr.write(`ERROR: ${err.message}\n`);
  process.exit(1);
}

// ── HTTP server ────────────────────────────────────────────────────────────

const PORT = parseInt(process.env.PORT, 10) || 8080;
const HOST = process.env.HOST || '0.0.0.0';

const server = http.createServer((req, res) => {
  const urlObj = new URL(req.url, `http://${req.headers.host || 'localhost'}`);

  const started = Date.now();
  res.on('finish', () => {
    const ms = Date.now() - started;
    process.stdout.write(
      `[${new Date().toISOString()}] ${req.method} ${urlObj.pathname}${urlObj.search} → ${res.statusCode} (${ms}ms)\n`,
    );
  });

  if (req.method !== 'GET') {
    res.writeHead(405, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ error: { message: 'Method Not Allowed' } }));
    return;
  }

  try {
    handle(req, res, urlObj, provider);
  } catch (err) {
    process.stderr.write(`[${new Date().toISOString()}] handler error: ${err.stack || err}\n`);
    if (!res.headersSent) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: { message: 'Internal error' } }));
    }
  }
});

server.listen(PORT, HOST, () => {
  process.stdout.write(
    `mock-connector-apis listening on http://${HOST}:${PORT}\n` +
      `  Provider: ${provider.name}${provider.description ? ' — ' + provider.description : ''}\n` +
      `  Auth: ${provider.auth ? `requires "${provider.auth.header}" header` : 'none'}\n` +
      `  Endpoints:\n`,
  );
  for (const [path, cfg] of Object.entries(provider.endpoints)) {
    const mode = cfg.dateRange
      ? `range(${cfg.dateRange.startParam}, ${cfg.dateRange.endParam})`
      : cfg.dateParam
        ? `date(${cfg.dateParam.name})`
        : 'no-date';
    const pag = cfg.pagination || 'none';
    process.stdout.write(`    GET ${path}  [${mode}, pag:${pag}]\n`);
  }
});

// Graceful shutdown
function shutdown(signal) {
  process.stdout.write(`\nReceived ${signal} — shutting down...\n`);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

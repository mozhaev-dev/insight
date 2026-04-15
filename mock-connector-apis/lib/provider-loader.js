// Discovers and loads providers from the providers/ directory.
// A provider is a directory containing a `provider.js` file that exports
// the config shape documented in providers/<name>/provider.js.

const fs = require('node:fs');
const path = require('node:path');

const PROVIDERS_DIR = path.join(__dirname, '..', 'providers');

function listProviders() {
  if (!fs.existsSync(PROVIDERS_DIR)) return [];
  return fs
    .readdirSync(PROVIDERS_DIR, { withFileTypes: true })
    .filter(
      (d) =>
        d.isDirectory() &&
        fs.existsSync(path.join(PROVIDERS_DIR, d.name, 'provider.js')),
    )
    .map((d) => d.name)
    .sort();
}

function loadProvider(name) {
  const providerDir = path.join(PROVIDERS_DIR, name);
  const providerFile = path.join(providerDir, 'provider.js');
  if (!fs.existsSync(providerFile)) {
    throw new Error(
      `Provider "${name}" not found at ${providerFile}. ` +
        `Known providers: ${listProviders().join(', ') || '(none)'}`,
    );
  }
  const cfg = require(providerFile);
  validate(cfg, name);
  return cfg;
}

function validate(cfg, name) {
  const errors = [];
  if (!cfg.name || cfg.name !== name) {
    errors.push(`provider.name must equal "${name}" (directory name)`);
  }
  if (!cfg.endpoints || typeof cfg.endpoints !== 'object') {
    errors.push('provider.endpoints must be an object');
  } else {
    for (const [pathKey, ep] of Object.entries(cfg.endpoints)) {
      if (!pathKey.startsWith('/')) {
        errors.push(`endpoint path "${pathKey}" must start with "/"`);
      }
      if (!ep || !Array.isArray(ep.stub)) {
        errors.push(`endpoint "${pathKey}" must have a stub array`);
      }
      if (ep && ep.pagination && !['cursor', 'none'].includes(ep.pagination)) {
        errors.push(`endpoint "${pathKey}" has invalid pagination "${ep.pagination}"`);
      }
    }
  }
  if (errors.length) {
    throw new Error(`Invalid provider config "${name}":\n  - ${errors.join('\n  - ')}`);
  }
}

module.exports = { listProviders, loadProvider, PROVIDERS_DIR };

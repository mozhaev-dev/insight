#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Airbyte Toolkit — Environment resolver
#
# Auto-detects host vs in-cluster runtime.
# Resolves Airbyte API URL, JWT token, workspace ID.
#
# Usage: source airbyte-toolkit/lib/env.sh
# Exports: AIRBYTE_API, AIRBYTE_TOKEN, WORKSPACE_ID
# ---------------------------------------------------------------------------

set -euo pipefail

# All Insight components share a single namespace (default: insight).
# Override with INSIGHT_NAMESPACE=... for non-default installs.
_ns="${INSIGHT_NAMESPACE:-insight}"

# Auto-detect runtime
if [[ -f /var/run/secrets/kubernetes.io/serviceaccount/token ]]; then
  export AIRBYTE_API="${AIRBYTE_API:-http://airbyte-airbyte-server-svc.${_ns}.svc.cluster.local:8001}"
else
  export AIRBYTE_API="${AIRBYTE_API:-http://localhost:8001}"
fi

# Read Airbyte auth secrets from the Insight namespace (single-namespace model)
_secret_json=$(kubectl get secret -n "$_ns" airbyte-auth-secrets -o json 2>/dev/null) || {
  echo "ERROR: cannot read airbyte-auth-secrets from namespace $_ns" >&2
  return 1 2>/dev/null || exit 1
}

_jwt_secret=$(echo "$_secret_json" | python3 -c "import sys,json,base64; print(base64.b64decode(json.load(sys.stdin)['data']['jwt-signature-secret']).decode())")

# Mint JWT token. Default TTL is 1 hour: register.sh builds CDK connector
# images on the fly (multi-minute Docker builds), so the original 5-minute
# token used to expire mid-script and produce 401s after the first build.
# Override via AIRBYTE_TOKEN_TTL_SECONDS — must be a positive integer; a
# malformed value would otherwise be interpolated raw into the JS literal
# `exp:n+<value>` below, breaking the token mint with a parse error or
# letting an attacker inject JS through the env var.
_token_ttl="${AIRBYTE_TOKEN_TTL_SECONDS:-3600}"
if ! [[ "$_token_ttl" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR: AIRBYTE_TOKEN_TTL_SECONDS=${_token_ttl} must be a positive integer" >&2
  return 1 2>/dev/null || exit 1
fi

# Capture into a local first so node failures (and an empty stdout) do not
# silently produce an exported but invalid AIRBYTE_TOKEN. With `set -e`,
# `export AIRBYTE_TOKEN=$(node ...)` masks the node exit status because
# the assignment to a builtin's argument is what set -e checks.
# Pass _jwt_secret via env var (JWT_SECRET) instead of string-interpolating it
# into the JS source. The secret is base64-decoded raw bytes from the
# Bitnami-generated airbyte-auth-secrets Secret and can contain `'`, `\`,
# newline, or `${...}` sequences — interpolation either breaks the JS parse
# or, worse, mutates the HMAC input. process.env reads the bytes verbatim.
# Bonus: the secret no longer appears in `ps` listings or `set -x` traces.
_token=$(JWT_SECRET="$_jwt_secret" node -e "
  const c=require('crypto');
  const h=Buffer.from(JSON.stringify({alg:'HS256',typ:'JWT'})).toString('base64url');
  const n=Math.floor(Date.now()/1000);
  const p=Buffer.from(JSON.stringify({iss:'airbyte-server',sub:'00000000-0000-0000-0000-000000000000',iat:n,exp:n+${_token_ttl}})).toString('base64url');
  const s=c.createHmac('sha256',process.env.JWT_SECRET).update(h+'.'+p).digest('base64url');
  console.log(h+'.'+p+'.'+s);
")
if [[ -z "$_token" ]]; then
  echo "ERROR: failed to mint Airbyte JWT token (node returned empty)" >&2
  return 1 2>/dev/null || exit 1
fi
export AIRBYTE_TOKEN="$_token"
unset _token

# Resolve workspace ID
export WORKSPACE_ID=$(curl -sf -H "Authorization: Bearer $AIRBYTE_TOKEN" \
  "${AIRBYTE_API}/api/v1/workspaces/list_by_organization_id" \
  -X POST -H "Content-Type: application/json" \
  -d '{"organizationId":"00000000-0000-0000-0000-000000000000"}' \
  | python3 -c "
import sys,json
ws = json.load(sys.stdin).get('workspaces',[])
print(ws[0]['workspaceId'] if ws else '')
" 2>/dev/null)

if [[ -z "$WORKSPACE_ID" ]]; then
  echo "ERROR: no Airbyte workspace found" >&2
  return 1 2>/dev/null || exit 1
fi

echo "  Workspace: $WORKSPACE_ID" >&2

unset _secret_json _jwt_secret _ns

"""Base stream classes for the GitHub Copilot connector.

Two stream archetypes:

  CopilotRestStream     — single-step REST endpoint on api.github.com (e.g., /seats).
  CopilotReportsStream  — two-step pattern: GET envelope on api.github.com, then GET
                          NDJSON from a signed URL on copilot-reports.github.com WITHOUT
                          an Authorization header. Implements an _fetch_ndjson_records()
                          helper used by user_metrics and org_metrics.

Both inherit from HttpStream (CDK retry mechanics) and share two helpers:
  _make_unique_key  — ADR-0004 formula `{tenant}-{source}-{natural_key...}` with `-` separator
  _add_envelope     — injects tenant_id, source_id, data_source, collected_at, unique_key
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional

import requests
from airbyte_cdk.sources.streams.http import HttpStream

from source_github_copilot.auth import download_headers, rest_headers

logger = logging.getLogger("airbyte")


def _now_iso() -> str:
    """UTC ISO-8601 timestamp for the `collected_at` framework field."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_unique_key(tenant_id: str, source_id: str, *natural_key_parts: str) -> str:
    """Compose a `unique_key` per ADR-0004.

    Formula: `{insight_tenant_id}-{insight_source_id}-{natural_key_part_1}-{...}`
    with `-` (hyphen) separator. The tenant-source prefix prevents collisions
    across connector instances and tenants by construction.
    """
    parts = [tenant_id, source_id, *(str(p) for p in natural_key_parts)]
    return "-".join(parts)


class CopilotAuthError(RuntimeError):
    """Raised on 401/403 (non-rate-limit) auth failures so child streams can't swallow them."""
    pass


def _is_rate_limit_403(resp: requests.Response) -> bool:
    """Distinguish 403 due to rate limit from 403 due to insufficient PAT scope."""
    if resp.status_code != 403:
        return False
    if resp.headers.get("Retry-After"):
        return True
    if resp.headers.get("X-RateLimit-Remaining") == "0":
        return True
    try:
        body = resp.text.lower()
        if "rate limit" in body or "secondary rate limit" in body:
            return True
    except Exception:
        pass
    return False


class CopilotRestStream(HttpStream, ABC):
    """Single-step REST stream over api.github.com (Bearer-auth)."""

    url_base = "https://api.github.com/"
    primary_key = "unique_key"
    raise_on_http_errors = False  # We inspect status in parse_response / _guard_response

    @property
    def request_timeout(self) -> Optional[int]:
        return 60

    def __init__(
        self,
        token: str,
        tenant_id: str,
        source_id: str,
        org: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._token = token
        self._tenant_id = tenant_id
        self._source_id = source_id
        self._org = org

    def request_headers(self, **kwargs) -> Mapping[str, Any]:
        return rest_headers(self._token)

    def should_retry(self, response: requests.Response) -> bool:
        if not isinstance(response, requests.Response):
            return True  # connection error — retry
        if response.status_code == 403 and _is_rate_limit_403(response):
            return True
        if response.status_code in (401, 403, 404, 409):
            return False
        # 204 = "no data for this day", treated as a normal terminal response — don't retry
        if response.status_code == 204:
            return False
        return response.status_code in (429, 500, 502, 503, 504)

    def backoff_time(self, response: requests.Response) -> Optional[float]:
        if not isinstance(response, requests.Response):
            return 60.0
        if response.status_code == 429 or (response.status_code == 403 and _is_rate_limit_403(response)):
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                return max(float(retry_after), 1.0)
            reset = response.headers.get("X-RateLimit-Reset")
            if reset:
                wait = float(reset) - time.time() + 1
                return max(wait, 1.0)
        if response.status_code in (502, 503):
            return 60.0
        return None

    def _guard_response(self, response: requests.Response) -> bool:
        """Distinguish auth failures (raise) from rate-limit / 4xx-other (log + skip)."""
        if response.status_code in (401, 403) and not _is_rate_limit_403(response):
            raise CopilotAuthError(
                f"GitHub Copilot auth error ({response.status_code}). "
                f"Verify the PAT has `manage_billing:copilot` AND `read:org` scopes "
                f"and was created by an Organization Owner. "
                f"Body: {response.text[:200]}"
            )
        if response.status_code == 204:
            # No data for the requested day. Caller emits zero records, advances cursor.
            return False
        if response.status_code >= 400:
            logger.error(f"Unexpected HTTP {response.status_code}: {response.url} — {response.text[:200]}")
            return False
        return True

    def _add_envelope(self, record: dict, pk_parts: Optional[List[str]] = None) -> dict:
        """Inject framework fields. Per DESIGN §3.2 inject_tenant_fields()."""
        record = dict(record)  # shallow copy — don't mutate caller's dict
        record["tenant_id"] = self._tenant_id
        record["source_id"] = self._source_id
        record["data_source"] = "insight_github_copilot"
        record["collected_at"] = _now_iso()
        if pk_parts:
            record["unique_key"] = _make_unique_key(self._tenant_id, self._source_id, *pk_parts)
        return record


class CopilotReportsStream(CopilotRestStream, ABC):
    """Two-step pattern for /copilot/metrics/reports/* endpoints.

    Step 1: GET envelope from api.github.com (CDK handles this via the standard
            HttpStream flow — request_headers / parse_response).
    Step 2: For each URL in `download_links`, GET NDJSON from copilot-reports.github.com
            WITHOUT an Authorization header. Each NDJSON line is a separate JSON record.

    Subclasses override:
      _path()                — endpoint path (e.g., metrics/reports/users-1-day)
      _record_pk_parts(rec)  — list of natural-key parts for unique_key composition
      _filter_record(rec)    — optional per-record validation/filter
    """

    @abstractmethod
    def _record_pk_parts(self, record: dict, day: str) -> List[str]:
        """Natural-key parts for unique_key composition — concrete per stream."""
        ...

    def parse_response(self, response: requests.Response, stream_slice=None, **kwargs) -> Iterable[Mapping[str, Any]]:
        """Step 1 envelope handler. HTTP 204 → emit nothing (data not available for day)."""
        if not self._guard_response(response):
            # 204 No Content or other non-2xx — emit zero records, cursor advances.
            return
        try:
            envelope = response.json()
        except ValueError as e:
            logger.error(f"Step 1 envelope is not JSON: {e}; body={response.text[:200]}")
            return

        download_links = envelope.get("download_links") or []
        if not download_links:
            logger.info(f"Empty download_links for {response.url} (day data not yet ready)")
            return

        day = (stream_slice or {}).get("day", "")
        for entry in download_links:
            url = entry.get("url") if isinstance(entry, dict) else entry
            if not url:
                continue
            yield from self._fetch_ndjson_records(url, day)

    def _fetch_ndjson_records(self, signed_url: str, day: str) -> Iterable[Mapping[str, Any]]:
        """Step 2: GET signed URL without Authorization, parse NDJSON line-by-line.

        Signed URLs expire shortly; on retry we re-fetch the envelope (handled at the
        Airbyte sync level, not here). Within a single sync run, treat 4xx as terminal.
        """
        try:
            resp = requests.get(
                signed_url,
                headers=download_headers(),
                stream=True,
                timeout=self.request_timeout,
            )
        except requests.RequestException as e:
            logger.error(f"Signed URL fetch failed: {e}")
            return

        if resp.status_code >= 400:
            logger.error(f"Signed URL returned HTTP {resp.status_code}: {signed_url[:120]}...")
            return

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                record = __import__("json").loads(line)
            except ValueError:
                logger.warning(f"Skipping malformed NDJSON line: {line[:200]}")
                continue
            if not self._filter_record(record):
                continue
            pk_parts = self._record_pk_parts(record, day)
            yield self._add_envelope(record, pk_parts=pk_parts)

    def _filter_record(self, record: dict) -> bool:
        """Override to drop bad records. Default: accept all."""
        return True

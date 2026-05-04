"""Per-user daily Copilot metrics — incremental, two-step signed-URL fetch + NDJSON.

Endpoint: GET /orgs/{org}/copilot/metrics/reports/users-1-day?day=YYYY-MM-DD

Step 1 returns: { "download_links": [{"url": "..."}, ...], "report_day": "YYYY-MM-DD" }
Step 2 (per signed URL): NDJSON, one JSON object per line — each = one user's day.

Day boundaries:
  - Cursor field: `day` (ISO YYYY-MM-DD), step P1D (one API call per day).
  - First-run start: `github_start_date` config (default 90 days ago).
  - End: yesterday UTC (data for day D available ~24h after end-of-day D).
  - Data availability: API has data from 2025-10-10 onwards; earlier dates → HTTP 204.

Source-native field names per `cpt-insightspec-principle-ghcopilot-source-native-schema`:
NDJSON object includes `user_login` (NOT `login`), `loc_added_sum`,
`code_acceptance_activity_count`, `user_initiated_interaction_count`,
`used_chat`, `used_agent`, `used_cli`. We pass these through unchanged.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional

import requests

from source_github_copilot.streams.base import CopilotReportsStream

logger = logging.getLogger("airbyte")


def _yesterday_utc() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


class CopilotUserMetricsStream(CopilotReportsStream):
    """Incremental per-user daily metrics."""

    name = "copilot_user_metrics"
    cursor_field = "day"

    def __init__(
        self,
        start_date: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._start_date = start_date or self._default_start_date()

    @staticmethod
    def _default_start_date() -> str:
        return (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")

    def path(self, **kwargs) -> str:
        return f"orgs/{self._org}/copilot/metrics/reports/users-1-day"

    def request_params(
        self,
        stream_slice: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> MutableMapping[str, Any]:
        day = (stream_slice or {}).get("day")
        if not day:
            raise ValueError("CopilotUserMetricsStream requires `day` in stream_slice")
        return {"day": day}

    def stream_slices(
        self,
        sync_mode=None,
        cursor_field=None,
        stream_state: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        """Yield one slice per day from cursor (or start_date) through yesterday UTC."""
        cursor = (stream_state or {}).get(self.cursor_field)
        start = self._next_day(cursor) if cursor else self._start_date
        end = _yesterday_utc()  # inclusive

        try:
            current = date.fromisoformat(start)
            stop = date.fromisoformat(end)
        except ValueError as e:
            logger.error(f"Invalid date in stream_slices (start={start}, end={end}): {e}")
            return

        while current <= stop:
            yield {"day": current.isoformat()}
            current += timedelta(days=1)

    @staticmethod
    def _next_day(d: str) -> str:
        return (date.fromisoformat(d) + timedelta(days=1)).isoformat()

    def get_updated_state(
        self,
        current_stream_state: Mapping[str, Any],
        latest_record: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Advance the day cursor to max(seen) — Airbyte calls this per record."""
        latest_day = latest_record.get(self.cursor_field) or ""
        prev = (current_stream_state or {}).get(self.cursor_field, "")
        return {self.cursor_field: max(latest_day, prev)}

    def _record_pk_parts(self, record: dict, day: str) -> List[str]:
        """unique_key composition: {tenant}-{source}-{user_login}-{day}."""
        user_login = record.get("user_login") or ""
        return [user_login, day]

    def _filter_record(self, record: dict) -> bool:
        """Drop records without identity (cannot resolve to a person)."""
        return bool(record.get("user_login"))

    def parse_response(
        self,
        response: requests.Response,
        stream_slice=None,
        **kwargs,
    ) -> Iterable[Mapping[str, Any]]:
        """Override to inject `day` into each record (NDJSON doesn't always carry it)."""
        day = (stream_slice or {}).get("day", "")
        for record in super().parse_response(response, stream_slice=stream_slice, **kwargs):
            # Ensure `day` field is present and matches the requested slice
            if not record.get("day"):
                record = dict(record)
                record["day"] = day
            yield record

    def get_json_schema(self) -> Mapping[str, Any]:
        """JSON Schema for `bronze_github_copilot.copilot_user_metrics`."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": True,
            "properties": {
                # framework-injected
                "tenant_id": {"type": "string"},
                "source_id": {"type": "string"},
                "unique_key": {"type": "string"},
                "data_source": {"type": "string"},
                "collected_at": {"type": "string"},
                # grain / identity
                "day": {"type": "string"},
                "user_login": {"type": "string"},
                # metrics
                "loc_added_sum": {"type": ["null", "number"]},
                "code_acceptance_activity_count": {"type": ["null", "number"]},
                "user_initiated_interaction_count": {"type": ["null", "number"]},
                "used_chat": {"type": ["null", "boolean"]},
                "used_agent": {"type": ["null", "boolean"]},
                "used_cli": {"type": ["null", "boolean"]},
            },
        }

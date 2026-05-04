"""Org-level daily Copilot metrics — incremental, two-step signed-URL fetch + NDJSON.

Endpoint: GET /orgs/{org}/copilot/metrics/reports/organization-1-day?day=YYYY-MM-DD

Same pattern as user_metrics but the NDJSON contains org-wide aggregates instead
of per-user rows. Typical envelope returns 1 download_link, and each NDJSON file
contains a single line with the org's daily totals.

Field names are PROVISIONAL — the live reports API may use different naming
conventions than what's in our spec. JSON Schema uses additionalProperties=true
so unexpected fields pass through. Confirm exact field names against live API
before activating the deferred Silver model `copilot__ai_org_usage`.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional

import requests

from source_github_copilot.streams.base import CopilotReportsStream

logger = logging.getLogger("airbyte")


def _yesterday_utc() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


class CopilotOrgMetricsStream(CopilotReportsStream):
    """Incremental org-level daily metrics."""

    name = "copilot_org_metrics"
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
        return f"orgs/{self._org}/copilot/metrics/reports/organization-1-day"

    def request_params(
        self,
        stream_slice: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> MutableMapping[str, Any]:
        day = (stream_slice or {}).get("day")
        if not day:
            raise ValueError("CopilotOrgMetricsStream requires `day` in stream_slice")
        return {"day": day}

    def stream_slices(
        self,
        sync_mode=None,
        cursor_field=None,
        stream_state: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        cursor = (stream_state or {}).get(self.cursor_field)
        start = self._next_day(cursor) if cursor else self._start_date
        end = _yesterday_utc()

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
        latest_day = latest_record.get(self.cursor_field) or ""
        prev = (current_stream_state or {}).get(self.cursor_field, "")
        return {self.cursor_field: max(latest_day, prev)}

    def _record_pk_parts(self, record: dict, day: str) -> List[str]:
        """unique_key composition: {tenant}-{source}-{day}.

        Org metrics have no user dimension; tenant + source + day uniquely identify
        the row. The tenant-source prefix makes multi-org tenants collision-safe
        by construction (different `source_id` values per Copilot connection).
        """
        return [day]

    def parse_response(
        self,
        response: requests.Response,
        stream_slice=None,
        **kwargs,
    ) -> Iterable[Mapping[str, Any]]:
        day = (stream_slice or {}).get("day", "")
        for record in super().parse_response(response, stream_slice=stream_slice, **kwargs):
            if not record.get("day"):
                record = dict(record)
                record["day"] = day
            yield record

    def get_json_schema(self) -> Mapping[str, Any]:
        """JSON Schema for `bronze_github_copilot.copilot_org_metrics`. additionalProperties=true
        because the live API field names are not yet confirmed (see DESIGN §3.7 provisional note)."""
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
                # grain
                "day": {"type": "string"},
                # provisional org-level fields
                "total_code_acceptance_activity_count": {"type": ["null", "number"]},
                "total_loc_added_sum": {"type": ["null", "number"]},
                "total_active_user_count": {"type": ["null", "number"]},
                "total_engaged_user_count": {"type": ["null", "number"]},
                "total_used_chat_count": {"type": ["null", "number"]},
                "total_used_agent_count": {"type": ["null", "number"]},
                "total_used_cli_count": {"type": ["null", "number"]},
            },
        }

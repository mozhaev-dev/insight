"""Org-level daily Copilot metrics — incremental, two-step signed-URL fetch + NDJSON.

Endpoint: GET /orgs/{org}/copilot/metrics/reports/organization-1-day?day=YYYY-MM-DD

Same pattern as user_metrics but the NDJSON contains org-wide aggregates instead
of per-user rows. Typical envelope returns 1 download_link, and each NDJSON file
contains a single line with the org's daily totals.

Field names are PROVISIONAL — the live reports API may use different naming
conventions than what's in our spec. JSON Schema uses additionalProperties=true
so unexpected fields pass through. Confirm exact field names against live API
before activating the deferred Silver model `copilot__ai_org_usage`.

Cursor advancement (Major #5 fix): same IncrementalMixin pattern as
user_metrics — state advances per-slice so HTTP 204 days don't get re-fetched
on every sync.
"""

import logging
from datetime import date, timedelta
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional

import requests
from airbyte_cdk.sources.streams import IncrementalMixin

from source_github_copilot.streams.base import CopilotReportsStream, yesterday_utc

logger = logging.getLogger("airbyte")


class CopilotOrgMetricsStream(CopilotReportsStream, IncrementalMixin):
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
        self._state: Mapping[str, Any] = {}

    @property
    def state(self) -> Mapping[str, Any]:
        return self._state

    @state.setter
    def state(self, value: Mapping[str, Any]):
        self._state = value or {}

    @staticmethod
    def _default_start_date() -> str:
        from datetime import datetime, timezone
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
        # Prefer in-memory state (advanced per-slice in read_records below) over
        # stream_state argument — see Major #5 fix in user_metrics.py.
        cursor = (self._state or {}).get(self.cursor_field) or (stream_state or {}).get(self.cursor_field)
        start = self._next_day(cursor) if cursor else self._start_date
        end = yesterday_utc()

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

    def read_records(
        self,
        sync_mode,
        cursor_field=None,
        stream_slice: Optional[Mapping[str, Any]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Mapping[str, Any]]:
        """Advance state per-slice — see user_metrics.py for Major #5 rationale."""
        for record in super().read_records(
            sync_mode=sync_mode,
            cursor_field=cursor_field,
            stream_slice=stream_slice,
            stream_state=stream_state,
        ):
            yield record
        if stream_slice and stream_slice.get("day"):
            slice_day = stream_slice["day"]
            current_max = (self._state or {}).get(self.cursor_field, "")
            if slice_day > current_max:
                self._state = {self.cursor_field: slice_day}

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

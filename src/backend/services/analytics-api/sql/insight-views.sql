-- Insight Analytics Views
-- Run on ClickHouse to create the views for the Analytics API.
-- Depends on: silver.class_comms_events, bronze_zoom.participants
--
-- Usage:
--   clickhouse-client --multiquery < insight-views.sql

CREATE DATABASE IF NOT EXISTS insight;

-- ---------------------------------------------------------------------------
-- 1. Email activity per person per day (from silver M365 comms)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW insight.email_daily AS
SELECT
    lower(user_email)  AS person_id,
    activity_date      AS metric_date,
    lower(user_email)  AS user_email,
    emails_sent,
    source
FROM silver.class_comms_events;

-- ---------------------------------------------------------------------------
-- 2. Zoom activity per person per day (from bronze Zoom participants)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW insight.zoom_person_daily AS
SELECT
    lower(p.email)                              AS person_id,
    toDate(parseDateTimeBestEffort(p.join_time)) AS metric_date,
    lower(p.email)                              AS user_email,
    COUNT(DISTINCT p.meeting_uuid)              AS zoom_calls,
    SUM(
        dateDiff('second',
            parseDateTimeBestEffort(p.join_time),
            parseDateTimeBestEffort(p.leave_time)
        )
    ) / 3600.0                                  AS meeting_hours
FROM bronze_zoom.participants AS p
WHERE p.email IS NOT NULL AND p.email != ''
GROUP BY
    lower(p.email),
    toDate(parseDateTimeBestEffort(p.join_time));

-- ---------------------------------------------------------------------------
-- 3. Combined daily comms: email + zoom merged per person per day
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW insight.comms_daily AS
SELECT
    person_id,
    toString(metric_date) AS metric_date,
    SUM(emails_sent)      AS emails_sent,
    SUM(zoom_calls)       AS zoom_calls,
    SUM(meeting_hours)    AS meeting_hours
FROM (
    SELECT
        person_id,
        toDate(metric_date)          AS metric_date,
        toFloat64(emails_sent)       AS emails_sent,
        toFloat64(0)                 AS zoom_calls,
        toFloat64(0)                 AS meeting_hours
    FROM insight.email_daily

    UNION ALL

    SELECT
        person_id,
        metric_date,
        toFloat64(0)                 AS emails_sent,
        toFloat64(zoom_calls)        AS zoom_calls,
        meeting_hours
    FROM insight.zoom_person_daily
)
GROUP BY person_id, metric_date;

-- ---------------------------------------------------------------------------
-- 4. Bullet-chart rows: unpivoted comms_daily (one row per metric_key)
--    Used by Analytics API for TEAM_BULLET_COLLAB / IC_BULLET_COLLAB queries
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW insight.collab_bullet_rows AS
SELECT person_id, metric_date, 'm365_emails_sent' AS metric_key, emails_sent    AS metric_value FROM insight.comms_daily
UNION ALL
SELECT person_id, metric_date, 'zoom_calls'       AS metric_key, zoom_calls     AS metric_value FROM insight.comms_daily
UNION ALL
SELECT person_id, metric_date, 'meeting_hours'    AS metric_key, meeting_hours  AS metric_value FROM insight.comms_daily;

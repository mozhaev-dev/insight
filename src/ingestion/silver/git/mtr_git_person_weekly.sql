{{ config(
    materialized='table',
    schema='silver',
    tags=['silver']
) }}

WITH commits AS (
    SELECT
        tenant_id,
        person_key,
        week,
        count() AS commits
    FROM {{ ref('fct_git_commit') }}
    WHERE is_merge_commit = 0
      AND person_key != ''
      AND date IS NOT NULL
    GROUP BY tenant_id, person_key, week
),
loc AS (
    SELECT
        tenant_id,
        person_key,
        week,
        SUM(if(file_category = 'spec', 0, lines_added)) AS code_loc,
        SUM(if(file_category = 'spec', lines_added, 0)) AS spec_lines
    FROM {{ ref('fct_git_file_change') }}
    WHERE is_merge_commit = 0
      AND person_key != ''
      AND week IS NOT NULL
    GROUP BY tenant_id, person_key, week
),
prs AS (
    SELECT
        tenant_id,
        person_key,
        toStartOfWeek(closed_on, 1) AS week,
        count() AS prs_merged
    FROM {{ ref('fct_git_pr') }}
    WHERE state_norm = 'merged'
      AND closed_on IS NOT NULL
      AND person_key != ''
    GROUP BY tenant_id, person_key, week
)
SELECT
    coalesce(commits.tenant_id, loc.tenant_id, prs.tenant_id)    AS tenant_id,
    coalesce(commits.person_key, loc.person_key, prs.person_key) AS person_key,
    coalesce(commits.week, loc.week, prs.week)                   AS week,
    coalesce(commits.commits, 0)                                 AS commits,
    coalesce(prs.prs_merged, 0)                                  AS prs_merged,
    coalesce(loc.code_loc, 0)                                    AS code_loc,
    coalesce(loc.spec_lines, 0)                                  AS spec_lines
FROM commits
FULL OUTER JOIN loc USING (tenant_id, person_key, week)
FULL OUTER JOIN prs USING (tenant_id, person_key, week)

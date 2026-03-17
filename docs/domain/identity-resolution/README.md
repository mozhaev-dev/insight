# Identity Resolution Domain

Identity Resolution maps disparate identity signals — emails, usernames, employee IDs, system-specific handles — from all connected source systems into canonical person records.

## Documents

| Document | Description |
|---|---|
| [`specs/DESIGN.md`](specs/DESIGN.md) | Technical design: architecture layers, domain model, component model, API, DDL, open questions |

## Scope

This domain covers:
- Person Registry (canonical persons + SCD Type 2 history)
- Alias store (many-to-one mapping of source identifiers to `person_id`)
- Org unit hierarchy with temporal assignments
- Bootstrap Job (seeding from HR/directory Silver data)
- Match rules engine (B1 exact → B2 normalization → B3 fuzzy review)
- Golden Record assembly (best-value attributes from all sources)
- Conflict detection and operator review workflow
- Merge / split operations with full audit trail
- ClickHouse integration (Dictionary + External Engine)
- GDPR erasure procedure

Out of scope: permission / access-control architecture (see `docs/domain/permissions/`), connector implementation, metric aggregation.

## Source Documents (Inbox)

The `specs/DESIGN.md` synthesizes the following inbox documents:
- `inbox/architecture/IDENTITY_RESOLUTION_V2.md` — MariaDB reference, matching engine, API
- `inbox/architecture/IDENTITY_RESOLUTION_V3.md` — Silver layer contract, PostgreSQL added
- `inbox/architecture/IDENTITY_RESOLUTION_V4.md` — canonical v4: Golden Record, Source Federation, multi-tenancy
- `inbox/IDENTITY_RESOLUTION.md` — ClickHouse-native min-propagation algorithm
- `inbox/architecture/EXAMPLE_IDENTITY_PIPELINE.md` — end-to-end walkthrough

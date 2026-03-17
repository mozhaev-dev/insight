# Connector Domain

The Connector Framework is the data ingestion subsystem of the Insight platform. It collects raw data from source systems and delivers it into the Medallion Architecture (Bronze → Silver → Gold) where it becomes analytically useful.

## Documents

| Document | Description |
|---|---|
| [`specs/DESIGN.md`](specs/DESIGN.md) | Framework architecture: Medallion layers, connector contract, BaseConnector, UnifierRegistry, automation boundary, AI-assisted onboarding, open questions |

## Scope

This domain covers:
- Connector Framework (BaseConnector, manifest contract, framework-owned mechanics)
- Medallion Architecture layers and their responsibilities (Bronze / Silver step 1 / Silver step 2 / Gold)
- Unifier schema and semantic metadata propagation
- Automation boundary — what can and cannot be generated
- Connector Onboarding UI and AI-assisted Silver mapping
- Custom fields pattern (`_ext` tables → Silver `Map` columns)
- Orchestration integration (AirByte / Dagster)
- Connector SDK and authorship tiers (first-party / community / self-service)

Out of scope: per-source Bronze table schemas, per-source API details, connector-specific field mappings → see `docs/components/connectors/`.

## Source Documents (Inbox)

The `specs/DESIGN.md` synthesizes the following inbox documents:
- `inbox/architecture/CONNECTORS_ARCHITECTURE.md` — connector ecosystem, contract, unifier, semantic metadata
- `inbox/architecture/CONNECTOR_AUTOMATION.md` — automation boundary, SDK design, AI-assisted onboarding
- `inbox/CONNECTORS_REFERENCE.md` — §How Data Flows, §Custom Fields Pattern, §Open Questions (architecture sections only)

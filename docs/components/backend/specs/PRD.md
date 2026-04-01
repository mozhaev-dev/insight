---
status: proposed
date: 2026-03-31
---

# PRD -- Backend

<!-- toc -->

- [1. Overview](#1-overview)
  - [1.1 Purpose](#11-purpose)
  - [1.2 Background / Problem Statement](#12-background--problem-statement)
  - [1.3 Goals (Business Outcomes)](#13-goals-business-outcomes)
  - [1.4 Glossary](#14-glossary)
- [2. Actors](#2-actors)
  - [2.1 Human Actors](#21-human-actors)
  - [2.2 System Actors](#22-system-actors)
- [3. Operational Concept & Environment](#3-operational-concept--environment)
  - [3.1 Module-Specific Environment Constraints](#31-module-specific-environment-constraints)
- [4. Scope](#4-scope)
  - [4.1 In Scope](#41-in-scope)
  - [4.2 Out of Scope](#42-out-of-scope)
- [5. Functional Requirements](#5-functional-requirements)
  - [5.1 Analytics](#51-analytics)
  - [5.2 Connector Management](#52-connector-management)
  - [5.3 Identity and Access Control](#53-identity-and-access-control)
  - [5.4 Cross-Source Identity Resolution](#54-cross-source-identity-resolution)
  - [5.5 Authentication](#55-authentication)
  - [5.6 Alerts](#56-alerts)
  - [5.7 Audit](#57-audit)
  - [5.8 Email](#58-email)
  - [5.9 Data Transformation](#59-data-transformation)
  - [5.10 Database Operations](#510-database-operations)
- [6. Non-Functional Requirements](#6-non-functional-requirements)
  - [6.1 NFR Inclusions](#61-nfr-inclusions)
  - [6.2 NFR Exclusions](#62-nfr-exclusions)
- [7. Public Library Interfaces](#7-public-library-interfaces)
  - [7.1 Public API Surface](#71-public-api-surface)
  - [7.2 External Integration Contracts](#72-external-integration-contracts)
- [8. Use Cases](#8-use-cases)
- [9. Acceptance Criteria](#9-acceptance-criteria)
- [10. Dependencies](#10-dependencies)
- [11. Assumptions](#11-assumptions)
- [12. Risks](#12-risks)

<!-- /toc -->

## 1. Overview

### 1.1 Purpose

The Insight Backend is the API and business logic tier of the Decision Intelligence Platform. It serves analytics data from ClickHouse Silver and Gold layers, manages connector configurations and encrypted credentials, maintains organizational hierarchy imported from HR/directory systems (Active Directory, BambooHR, Workday, or similar), delivers business alerts, provides a compliance audit trail, and centralizes email delivery.

### 1.2 Background / Problem Statement

Organizations collect operational data across dozens of tools (version control, task trackers, collaboration, AI tools, HR systems) but lack a unified view of team performance, process bottlenecks, and AI adoption metrics. The ingestion layer (Airbyte, Kestra, dbt) extracts and transforms this data into ClickHouse. The backend must expose this data through secure, tenant-isolated, org-scoped APIs while giving administrators control over connector configurations, user roles, and alert thresholds.

The product is deployed as a standalone installation on customer Kubernetes clusters. It must not depend on any specific cloud provider, external secret manager, or bundled identity provider. Customers bring their own OIDC provider and HR/directory system (Active Directory, BambooHR, Workday, or similar).

### 1.3 Goals (Business Outcomes)

- Enable unit managers to view analytics metrics scoped to their organizational subtree with strict temporal boundaries on personnel transfers
- Provide self-service connector configuration so customers can onboard new data sources without vendor involvement
- Deliver proactive business alerts when key metrics cross configured thresholds, reducing time-to-awareness from days to minutes
- Maintain a queryable audit trail of all data access and configuration changes for compliance purposes
- Support multi-tenant data isolation so a single deployment can serve multiple organizational tenants

### 1.4 Glossary

| Term | Definition |
|------|------------|
| Silver layer | Unified ClickHouse tables with standardized schemas across data sources |
| Gold layer | Aggregated ClickHouse tables with computed business metrics |
| Org unit | A node in the organizational hierarchy (team, department, division) |
| Follow-the-unit-strict | Visibility policy where data access follows org membership periods |
| KEK | Key Encryption Key -- master key provided at deployment, wraps per-tenant DEKs |
| DEK | Data Encryption Key -- per-tenant key that encrypts secret values |
| Envelope encryption | Encryption pattern where data keys are themselves encrypted by a master key |

## 2. Actors

### 2.1 Human Actors

#### Viewer

**ID**: `cpt-insightspec-actor-viewer`

**Role**: End user who consumes dashboards and analytics within their org scope.
**Needs**: View dashboards, browse metrics, export data as CSV.

#### Analyst

**ID**: `cpt-insightspec-actor-analyst`

**Role**: Power user who creates and configures dashboards and chart visualizations.
**Needs**: All Viewer capabilities plus create, edit, and delete dashboard configurations and chart definitions.

#### Connector Administrator

**ID**: `cpt-insightspec-actor-connector-admin`

**Role**: Technical user responsible for configuring data source connectors and managing credentials.
**Needs**: Create, update, and delete connector configurations. Manage API keys and tokens. Trigger and monitor sync operations.

#### Identity Administrator

**ID**: `cpt-insightspec-actor-identity-admin`

**Role**: Administrator responsible for organizational structure and identity resolution.
**Needs**: Edit org tree, manage identity resolution rules, override person-to-identity mappings, trigger LDAP sync.

#### Tenant Administrator

**ID**: `cpt-insightspec-actor-tenant-admin`

**Role**: Top-level administrator with full control over tenant configuration.
**Needs**: All capabilities of other roles plus manage role assignments, configure notification rules, provision new tenants.

### 2.2 System Actors

#### OIDC Provider

**ID**: `cpt-insightspec-actor-oidc-provider`

**Role**: Customer's existing identity provider that issues JWT tokens for authentication.

#### HR/Directory System

**ID**: `cpt-insightspec-actor-hr-directory`

**Role**: Customer's HR or directory system (Active Directory via LDAP, BambooHR via API, Workday via API, or similar) that provides organizational hierarchy and person records. The Identity Service supports pluggable adapters for different source systems.

#### Airbyte

**ID**: `cpt-insightspec-actor-airbyte`

**Role**: Data extraction platform that manages connector syncs. The backend interacts with its API for connection management and sync triggering.

#### SMTP Server

**ID**: `cpt-insightspec-actor-smtp-server`

**Role**: Customer's email server used for delivering alert notifications and operational emails.

## 3. Operational Concept & Environment

### 3.1 Module-Specific Environment Constraints

- Deployed on Kubernetes (1.27+) via Helm chart
- All infrastructure bundled (ClickHouse, MariaDB, Redis, Redpanda, MinIO)
- No dependency on cloud-provider-specific services
- Authentication exclusively via customer OIDC provider
- Organizational structure sourced from customer HR/directory system via pluggable adapters (AD/LDAP, BambooHR API, Workday API)

## 4. Scope

### 4.1 In Scope

- Analytics read API over ClickHouse Silver and Gold layers with OData filtering
- Metrics catalog management (CRUD for metric definitions)
- Dashboard and chart configuration management
- CSV data export with temporary S3 storage
- Connector configuration management via Airbyte API
- Credential management with per-tenant envelope encryption
- Org tree sync from HR/directory systems via pluggable adapters
- OIDC-to-person identity resolution (login mapping)
- Cross-source identity resolution (alias matching, golden records, merge/split)
- RBAC with five roles (Viewer, Analyst, Connector Admin, Identity Admin, Tenant Admin)
- Org-tree-based data visibility with follow-the-unit-strict policy
- dbt transform rules management (Silver/Gold table configs, field mappings, dependency graph)
- Business alerts on metric thresholds with email notifications
- Append-only audit trail in ClickHouse
- Centralized email delivery service
- Forward-only database migrations for continuous deployment
- Operational monitoring via Prometheus, Grafana, Alertmanager

### 4.2 Out of Scope

- Tenant onboarding wizard (future -- initial tenant seeded via Helm values)
- Dashboard sharing across users or org units (future v2)
- Circuit breaker pattern (future v2 -- retry with backoff is sufficient for v1)
- GDPR data deletion workflows (future -- schema designed to not preclude it)
- Custom report scheduling (future -- CSV export is manual in v1)
- PDF report generation (future v2 -- LLM-generated documents following a configurable structure: section descriptions, metric analysis, trend narratives, executive summary; charts embedded from analytics data; intended for stakeholder distribution)
- Public analytics API (future v2 -- external API for customers to query analytics data programmatically, build custom integrations, and process metrics outside the bundled frontend; v1 exposes internal APIs consumed only by the bundled React SPA)
- Frontend implementation (separate PRD)

## 5. Functional Requirements

### 5.1 Analytics

#### Analytics Query Execution

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-analytics-read`

The system **MUST** execute read queries against ClickHouse Silver and Gold tables with OData-style filtering, sorting, pagination, and field projection, scoped to the requesting user's visible org units and membership time ranges.

**Rationale**: Core product value -- users need to access analytics data within their authorized scope.

**Actors**: `cpt-insightspec-actor-viewer`, `cpt-insightspec-actor-analyst`

#### Metrics Catalog Management

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-metrics-catalog`

The system **MUST** provide CRUD operations for metric definitions (name, description, unit, formula reference, category) stored in a dedicated MariaDB database.

**Rationale**: Metrics must be discoverable and described for dashboard builders and analysts.

**Actors**: `cpt-insightspec-actor-analyst`, `cpt-insightspec-actor-tenant-admin`

#### Dashboard Configuration

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-dashboard-config`

The system **MUST** provide CRUD operations for dashboard and chart configurations (chart type, metric references, dimensions, filters) stored in MariaDB.

**Rationale**: No-code dashboard building requires persistent chart configurations.

**Actors**: `cpt-insightspec-actor-analyst`

#### CSV Data Export

- [ ] `p2` - **ID**: `cpt-insightspec-fr-be-csv-export`

The system **MUST** allow users to trigger CSV exports of query results, store exports on S3-compatible storage, return a download link, and auto-expire exports after one week.

**Rationale**: Users need to export data for offline analysis and reporting.

**Actors**: `cpt-insightspec-actor-viewer`, `cpt-insightspec-actor-analyst`

### 5.2 Connector Management

#### Connector Configuration

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-connector-crud`

The system **MUST** provide CRUD operations for connector configurations (source type, parameters, schedule) and manage Airbyte connections via the Airbyte API (create, update, trigger sync, delete).

**Rationale**: Customers must be able to configure and manage their data sources without vendor involvement.

**Actors**: `cpt-insightspec-actor-connector-admin`

#### Credential Management

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-secret-management`

The system **MUST** store connector credentials using envelope encryption with per-tenant data encryption keys (DEK) wrapped by a deployment-level key encryption key (KEK). Tenant key compromise **MUST NOT** affect other tenants.

**Rationale**: API keys and tokens are sensitive. Per-tenant isolation limits blast radius of key compromise.

**Actors**: `cpt-insightspec-actor-connector-admin`

### 5.3 Identity and Access Control

#### Org Tree Synchronization

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-org-tree-sync`

The system **MUST** automatically synchronize the organizational hierarchy from customer HR/directory systems on a configurable schedule, maintaining person-org membership records with temporal validity (effective_from, effective_to). The system **MUST** support pluggable source adapters (Active Directory via LDAP, BambooHR via API, Workday via API) so customers can use their existing HR infrastructure.

**Rationale**: Org-based data visibility requires an up-to-date org tree that tracks membership history. Different customers use different HR/directory systems.

**Actors**: `cpt-insightspec-actor-hr-directory`, `cpt-insightspec-actor-identity-admin`

#### Identity Resolution

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-identity-resolution`

The system **MUST** map OIDC subject claims to internal person records by matching email from token claims to known persons. On first login, the mapping **MUST** be created automatically and cached for subsequent logins.

**Rationale**: OIDC sub claims are opaque and IdP-specific. The system needs a stable internal person_id.

**Actors**: `cpt-insightspec-actor-oidc-provider`

#### Role-Based Access Control

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-rbac`

The system **MUST** enforce role-based access control with five roles (Viewer, Analyst, Connector Admin, Identity Admin, Tenant Admin). Each role **MUST** grant a defined set of permissions. Roles **MUST** be assignable per-tenant per-user by Tenant Administrators.

**Rationale**: Different users need different levels of access to platform features.

**Actors**: `cpt-insightspec-actor-tenant-admin`

#### Org-Based Data Visibility

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-visibility-policy`

The system **MUST** enforce follow-the-unit-strict visibility: when a person transfers between org units, the previous manager sees metrics only before the transfer date and the new manager sees metrics only from the transfer date onward. Unit members **MUST** see only their own unit's data.

**Rationale**: Prevents data leakage across organizational boundaries even for historical data.

**Actors**: `cpt-insightspec-actor-viewer`, `cpt-insightspec-actor-analyst`

### 5.4 Cross-Source Identity Resolution

#### Identity Resolution Service

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-identity-resolution-service`

The system **MUST** map disparate identity signals (emails, usernames, employee IDs, system-specific handles) from multiple source systems into canonical person records. The system **MUST** support conflict detection for ambiguous matches, manual merge and split operations with audit trail, and GDPR erasure. See [Identity Resolution DESIGN](../../domain/identity-resolution/specs/DESIGN.md) and [Backend DESIGN section 3.2](./DESIGN.md) for implementation details.

**Rationale**: Cross-source analytics (correlating a person's Git commits with their Jira tasks, calendar events, and HR data) requires a single canonical person_id across all data sources. Without identity resolution, each source has its own user identifiers that cannot be joined.

**Actors**: `cpt-insightspec-actor-identity-admin`, `cpt-insightspec-actor-tenant-admin`

### 5.5 Authentication

#### OIDC Authentication

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-oidc-auth`

The system **MUST** authenticate all API requests via OIDC/JWT tokens issued by the customer's identity provider. No bundled identity provider or user/password management **MUST** be included.

**Rationale**: Enterprise customers have existing IdPs. The product must integrate, not replace.

**Actors**: `cpt-insightspec-actor-oidc-provider`

### 5.6 Alerts

#### Business Alerts

- [ ] `p2` - **ID**: `cpt-insightspec-fr-be-business-alerts`

The system **MUST** allow users to define alert rules (metric, threshold, comparison operator, evaluation interval, recipients). The system **MUST** periodically evaluate thresholds against ClickHouse data and send email notifications when thresholds are crossed. Alert rules **MUST** respect org-tree visibility.

**Rationale**: Proactive notifications reduce time-to-awareness for process degradation.

**Actors**: `cpt-insightspec-actor-analyst`, `cpt-insightspec-actor-tenant-admin`

### 5.7 Audit

#### Audit Trail

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-audit-trail`

The system **MUST** log all data access, configuration changes, secret access, and authentication events as structured audit events. The audit trail **MUST** be queryable with OData filtering and stored in ClickHouse with configurable retention.

**Rationale**: Compliance requires knowing who accessed what data, when, and what was changed.

**Actors**: `cpt-insightspec-actor-tenant-admin`

### 5.8 Email

#### Centralized Email Delivery

- [ ] `p2` - **ID**: `cpt-insightspec-fr-be-email-delivery`

The system **MUST** provide a centralized email delivery service that consumes email requests from an event stream, renders templates, delivers via SMTP with retry logic, and tracks delivery status. No other service **MUST** interact with SMTP directly.

**Rationale**: Centralizing email avoids SMTP configuration duplication and enables unified retry, rate-limiting, and template management.

**Actors**: `cpt-insightspec-actor-smtp-server`

### 5.9 Data Transformation

#### Transform Rules Management

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-transform-rules`

The system **MUST** provide CRUD operations for dbt transform rules that define how Bronze data from multiple connectors is merged into Silver unified tables (e.g., `class_commits` from GitHub + GitLab + Bitbucket) and how Silver data is aggregated into Gold metric tables. The system **MUST** manage a dependency graph between connectors and transforms so that dbt runs execute after relevant syncs complete. The system **MUST** trigger dbt runs via Kestra API and expose transform run status.

**Rationale**: Transforms are cross-source logic (merging multiple connectors into unified schemas) and cannot be managed per-connector. A dedicated management surface enables administrators to configure field mappings, union rules, and Gold metric formulas without touching dbt code directly.

**Actors**: `cpt-insightspec-actor-tenant-admin`, `cpt-insightspec-actor-connector-admin`

### 5.10 Database Operations

#### Forward-Only Database Migrations

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-forward-only-migrations`

The system **MUST** use forward-only database migrations for all MariaDB schema changes. Rollback migrations **MUST NOT** exist. Every migration **MUST** be backward-compatible with the previous application version so that rolling deployments can run old and new code against the same schema simultaneously. Destructive schema changes (column drops, table drops) **MUST** be deferred to a subsequent migration after the old code is fully decommissioned.

**Rationale**: Forward-only migrations are critical for continuous deployment via ArgoCD. Rollback scripts create a false sense of safety -- in practice they are rarely tested, often fail on production data, and introduce risk of data loss. Instead, a broken migration is fixed by shipping a new forward migration. This approach enables zero-downtime rolling deployments where old and new pod versions coexist during rollout.

**Actors**: `cpt-insightspec-actor-tenant-admin`

#### Migration Execution via K8s Jobs

- [ ] `p1` - **ID**: `cpt-insightspec-fr-be-migration-on-startup`

Each service **MUST** provide a migration binary (or CLI command) that runs pending database migrations. Migrations **MUST** be executed as Kubernetes Jobs (Helm pre-upgrade hook or ArgoCD sync wave) before new application pods are rolled out. The migration Job **MUST** complete successfully before the deployment proceeds. Migrations **MUST** be idempotent -- re-running a migration that has already been applied **MUST** be a no-op.

**Rationale**: K8s Jobs run once per deployment, have clear success/failure semantics, and complete before new pods start. This eliminates leader election complexity, avoids slowing service startup, and provides a clean separation between migration (deployment step) and application runtime.

**Actors**: `cpt-insightspec-actor-tenant-admin`

## 6. Non-Functional Requirements

### 6.1 NFR Inclusions

#### Tenant Data Isolation

- [ ] `p1` - **ID**: `cpt-insightspec-nfr-be-tenant-isolation`

The system **MUST** isolate tenant data at the application layer via tenant_id filtering on all storage systems (MariaDB, ClickHouse, Redis, S3, Redpanda). A query from tenant A **MUST NOT** return data belonging to tenant B under any circumstances.

**Threshold**: Zero cross-tenant data leaks.

**Rationale**: Multi-tenant deployment requires strict data boundaries.

#### Query Safety

- [ ] `p1` - **ID**: `cpt-insightspec-nfr-be-query-safety`

All ClickHouse queries **MUST** use parameterized bind parameters only. No string interpolation or concatenation **MUST** be used in query building. Query timeouts **MUST** be enforced per request.

**Threshold**: Zero SQL injection vectors in query builder code.

**Rationale**: OData-to-SQL translation is a high-risk injection surface.

#### Secret Isolation

- [ ] `p1` - **ID**: `cpt-insightspec-nfr-be-secret-isolation`

Compromise of one tenant's data encryption key **MUST NOT** expose secrets of other tenants. Key rotation for one tenant **MUST NOT** require re-encryption of other tenants' data.

**Threshold**: Per-tenant blast radius containment.

**Rationale**: Shared deployment means defense-in-depth for credential storage.

#### Rate Limiting

- [ ] `p2` - **ID**: `cpt-insightspec-nfr-be-rate-limiting`

The system **MUST** enforce per-route rate limiting (requests per second, burst, max in-flight) on all API endpoints with configurable defaults.

**Threshold**: 429 response returned before service degradation occurs.

**Rationale**: Prevents one tenant or user from impacting service availability for others.

#### Graceful Shutdown

- [ ] `p2` - **ID**: `cpt-insightspec-nfr-be-graceful-shutdown`

On SIGTERM, the system **MUST** stop accepting new requests, drain in-flight requests within 30 seconds, commit event stream offsets, and close database connections before exiting. Kubernetes termination grace period **MUST** be 60 seconds.

**Threshold**: Zero message loss during rolling deployments.

**Rationale**: Standalone product with customer SLAs requires zero-downtime deployments.

#### Retry Resilience

- [ ] `p2` - **ID**: `cpt-insightspec-nfr-be-retry-resilience`

All retryable operations **MUST** use exponential backoff with jitter. Client errors (4xx) and permanent failures **MUST NOT** be retried. Each retry **MUST** emit a warning log with attempt number and delay.

**Threshold**: Recovery within retry budget (3-5 attempts depending on operation).

**Rationale**: Downstream dependencies (ClickHouse, MariaDB, LDAP, Airbyte, SMTP) will have transient failures.

#### API Versioning

- [ ] `p2` - **ID**: `cpt-insightspec-nfr-be-api-versioning`

Every service **MUST** expose versioned API endpoints (`/api/v1/...`) from day one. Older API versions **MUST** continue working during rolling updates.

**Threshold**: Zero breaking changes to v1 endpoints without v2 migration path.

**Rationale**: Standalone product deployed to customer environments cannot force-upgrade clients.

### 6.2 NFR Exclusions

- **Horizontal ClickHouse sharding**: Not required for v1. Vertical scaling sufficient for expected data volumes. Revisit when single-node capacity is exceeded.
- **Distributed tracing (OpenTelemetry)**: Out of scope for v1. Structured logging with correlation_id provides sufficient debugging capability initially.

## 7. Public Library Interfaces

### 7.1 Public API Surface

#### Analytics API

- [ ] `p1` - **ID**: `cpt-insightspec-interface-analytics-api`

**Type**: REST API

**Stability**: stable

**Description**: Read API for analytics queries, metrics catalog, dashboard configurations, and CSV exports.

**Breaking Change Policy**: Major version bump required for breaking changes. V1 endpoints maintained until V2 is stable.

#### Connector Manager API

- [ ] `p1` - **ID**: `cpt-insightspec-interface-connector-api`

**Type**: REST API

**Stability**: stable

**Description**: CRUD API for connector configurations, credential management, and sync operations.

**Breaking Change Policy**: Major version bump required for breaking changes.

#### Identity Service API

- [ ] `p1` - **ID**: `cpt-insightspec-interface-identity-api`

**Type**: REST API

**Stability**: stable

**Description**: Read API for org tree, person details, role management, and LDAP sync triggers.

**Breaking Change Policy**: Major version bump required for breaking changes.

#### Alerts Service API

- [ ] `p2` - **ID**: `cpt-insightspec-interface-alerts-api`

**Type**: REST API

**Stability**: stable

**Description**: CRUD API for alert rules and alert history.

**Breaking Change Policy**: Major version bump required for breaking changes.

#### Identity Resolution Service API

- [ ] `p1` - **ID**: `cpt-insightspec-interface-identity-resolution-api`

**Type**: REST API

**Stability**: stable

**Description**: API for managing resolved persons (golden records), aliases, merge/split operations, conflict resolution, and bootstrap job triggers.

**Breaking Change Policy**: Major version bump required for breaking changes.

#### Transform Service API

- [ ] `p1` - **ID**: `cpt-insightspec-interface-transform-api`

**Type**: REST API

**Stability**: stable

**Description**: CRUD API for Silver transform rules, Gold metric rules, transform dependency graph, and dbt run triggers.

**Breaking Change Policy**: Major version bump required for breaking changes.

#### Audit Service API

- [ ] `p2` - **ID**: `cpt-insightspec-interface-audit-api`

**Type**: REST API

**Stability**: stable

**Description**: Read-only API for querying the audit trail with OData filtering.

**Breaking Change Policy**: Major version bump required for breaking changes.

### 7.2 External Integration Contracts

#### Airbyte API Contract

- [ ] `p1` - **ID**: `cpt-insightspec-contract-airbyte`

**Direction**: required from client (Connector Manager calls Airbyte API)

**Protocol/Format**: HTTP/REST

**Compatibility**: Depends on Airbyte API version. Connector Manager abstracts Airbyte API details.

#### HR/Directory Source Contract

- [ ] `p1` - **ID**: `cpt-insightspec-contract-hr-directory`

**Direction**: required from client (Identity Service queries org source via pluggable adapter)

**Protocol/Format**: LDAP/LDAPS (Active Directory, OpenLDAP) or HTTP/REST (BambooHR API, Workday API)

**Compatibility**: Adapter-based -- each adapter implements a common interface for org tree and person data retrieval.

#### Kestra API Contract

- [ ] `p1` - **ID**: `cpt-insightspec-contract-kestra`

**Direction**: required from client (Transform Service triggers dbt runs via Kestra API)

**Protocol/Format**: HTTP/REST

**Compatibility**: Depends on Kestra API version. Transform Service abstracts Kestra API details.

#### SMTP Contract

- [ ] `p2` - **ID**: `cpt-insightspec-contract-smtp`

**Direction**: required from client (Email Service delivers via SMTP)

**Protocol/Format**: SMTP (port 587, STARTTLS)

**Compatibility**: Standard SMTP. Customer provides server.

## 8. Use Cases

#### View Org-Scoped Dashboard

- [ ] `p1` - **ID**: `cpt-insightspec-usecase-view-dashboard`

**Actor**: `cpt-insightspec-actor-viewer`

**Preconditions**:
- User authenticated via OIDC
- User has Viewer role or higher
- Dashboard exists with chart configurations

**Main Flow**:
1. User navigates to dashboard
2. System resolves person_id from OIDC token
3. System evaluates RBAC (Viewer role allows "view" action)
4. System computes visible org units and time ranges from memberships
5. System queries ClickHouse with org and time scope filters
6. System returns filtered metrics data
7. Frontend renders charts via Recharts

**Postconditions**:
- User sees metrics only from their visible org subtree and membership periods
- Audit event logged

**Alternative Flows**:
- **No role assigned**: System returns 403 Forbidden
- **No org membership**: System returns empty dataset

#### Configure New Connector

- [ ] `p1` - **ID**: `cpt-insightspec-usecase-configure-connector`

**Actor**: `cpt-insightspec-actor-connector-admin`

**Preconditions**:
- User authenticated with Connector Admin role
- Airbyte is reachable

**Main Flow**:
1. Admin creates connector configuration (source type, parameters, schedule)
2. Admin provides API credentials
3. System encrypts credentials with tenant DEK
4. System creates Airbyte connection via API
5. Admin triggers initial sync
6. System monitors sync status

**Postconditions**:
- Connector configured and syncing
- Credentials stored encrypted
- Audit events logged for creation and secret write

**Alternative Flows**:
- **Airbyte unreachable**: System retries with backoff, returns 503 after max attempts
- **Invalid credentials format**: System returns 400 with validation errors

## 9. Acceptance Criteria

- [ ] Authenticated user can query analytics data scoped to their org unit and membership period
- [ ] Tenant A cannot access Tenant B data through any API endpoint
- [ ] Connector admin can configure, trigger, and monitor a data source sync end-to-end
- [ ] Business alert fires email within 10 minutes of threshold breach
- [ ] Audit trail captures all data access and configuration changes with queryable retention
- [ ] Identity resolution maps aliases from multiple sources into a single person golden record
- [ ] dbt transform rules can be configured and triggered, producing Silver step 2 and Gold tables
- [ ] Database migrations run as K8s Jobs before pod rollout with zero-downtime deployments
- [ ] System deploys on a fresh Kubernetes cluster via single `helm install` command
- [ ] System recovers from dependency failures (ClickHouse, MariaDB, LDAP) within retry budget without data loss

## 10. Dependencies

| Dependency | Description | Criticality |
|------------|-------------|-------------|
| ClickHouse | Analytics storage (Silver/Gold layers) and audit log | `p1` |
| MariaDB | Per-service metadata storage (configs, secrets, org tree, alerts, email) | `p1` |
| Redis | Caching and rate limiting | `p2` |
| Redpanda | Event streaming for audit events, email requests, cache invalidation | `p1` |
| MinIO | S3-compatible storage for CSV exports | `p2` |
| Airbyte | Data extraction platform (connector management via API) | `p1` |
| Kestra | Pipeline orchestration -- scheduling, retries, dbt runs (used by Connector Manager and Transform Service) | `p1` |
| Customer OIDC provider | Authentication | `p1` |
| Customer HR/directory system | Organizational hierarchy source (AD, BambooHR, Workday, etc.) | `p1` |
| Customer SMTP server | Email delivery | `p2` |

## 11. Assumptions

- Customer has an OIDC-compliant identity provider capable of issuing JWT tokens
- Customer has an HR or directory system that provides organizational hierarchy (Active Directory, BambooHR, Workday, or similar)
- Customer provides an SMTP server for outbound email
- Kubernetes cluster has sufficient resources for all bundled infrastructure (ClickHouse, MariaDB, Redis, Redpanda, MinIO, Airbyte, Kestra, monitoring stack)
- Airbyte API is stable enough for programmatic connection management
- Single MariaDB instance is sufficient for metadata workloads across all services

## 12. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Airbyte API breaking changes | Connector Manager integration breaks on Airbyte upgrades | Abstract Airbyte API behind adapter layer; pin Airbyte version in Helm chart |
| ClickHouse single-node capacity limits | Query performance degrades with large data volumes | Vertical scaling first; sharding architecture designed but deferred to v2 |
| Org source sync latency | Org tree updates delayed; stale access scopes | Configurable sync interval; manual sync trigger for Identity Admins; cache TTL limits stale window |
| Per-tenant DEK management complexity | Key rotation errors could lock out tenant | Automated key rotation tested in integration suite; KEK rotation only re-wraps DEKs |
| Redpanda-to-Kafka migration | Future migration may introduce compatibility issues | Use only Kafka-compatible rdkafka API; no Redpanda-specific features |
| Customer K8s cluster variability | Helm chart may not work on all K8s distributions | Test on EKS, GKE, AKS, and k3s; document minimum resource requirements |
| Identity resolution ambiguity | Same person may have conflicting aliases across sources; false merges corrupt analytics | Conflict detection with manual override; merge/split audit trail; conservative matching defaults |
| dbt transform failures | Broken transform rules block Silver/Gold pipeline | Transform status monitoring via Redpanda; alerts on failure; transforms are idempotent and re-runnable |
| Kestra API breaking changes | Transform Service integration breaks on Kestra upgrades | Abstract Kestra API behind adapter layer; pin Kestra version in Helm chart |

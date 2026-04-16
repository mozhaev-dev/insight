# Multi-stage build for Identity Resolution stub
#
# Build context: src/backend/
# Usage: docker build -f services/identity/Dockerfile -t insight-identity:dev .

# Stage 1: Builder
FROM rust:1.92-bookworm AS builder

WORKDIR /build

# --- Dependency caching layer ---
COPY Cargo.toml Cargo.lock ./
COPY libs/insight-clickhouse/Cargo.toml ./libs/insight-clickhouse/Cargo.toml
COPY plugins/oidc-authn-plugin/Cargo.toml ./plugins/oidc-authn-plugin/Cargo.toml
COPY services/api-gateway/Cargo.toml ./services/api-gateway/Cargo.toml
COPY services/analytics-api/Cargo.toml ./services/analytics-api/Cargo.toml
COPY services/identity/Cargo.toml ./services/identity/Cargo.toml

RUN mkdir -p libs/insight-clickhouse/src && echo "" > libs/insight-clickhouse/src/lib.rs && \
    mkdir -p plugins/oidc-authn-plugin/src && echo "" > plugins/oidc-authn-plugin/src/lib.rs && \
    mkdir -p services/api-gateway/src && echo "fn main() {}" > services/api-gateway/src/main.rs && \
    mkdir -p services/analytics-api/src && echo "fn main() {}" > services/analytics-api/src/main.rs && \
    mkdir -p services/identity/src && echo "fn main() {}" > services/identity/src/main.rs

RUN cargo build --release --bin identity-resolution 2>/dev/null || true

# --- Source layer ---
RUN rm -rf libs/insight-clickhouse/src services/identity/src \
    target/release/identity-resolution target/release/deps/identity_resolution* \
    target/release/deps/insight_clickhouse* target/release/deps/libinsight_clickhouse*

COPY libs/insight-clickhouse/src/ ./libs/insight-clickhouse/src/
COPY services/identity/src/ ./services/identity/src/

RUN cargo build --release --bin identity-resolution

# Stage 2: Runtime
FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/target/release/identity-resolution /app/identity-resolution

RUN useradd -U -u 1000 appuser && \
    chown -R 1000:1000 /app
USER 1000

EXPOSE 8082

CMD ["/app/identity-resolution"]

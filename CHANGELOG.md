# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Ingestion Worker entry point and UDP receiver (`services/ingestion/main.py`, `services/ingestion/udp_server.py`) with `asyncio.DatagramProtocol`, component wiring, graceful shutdown via OS signals, and MTU payload validation. ([#218](https://github.com/SWP-47/traffic-processing-platform/issues/218))
- Sequence tracking and Fast Path state management (`services/ingestion/sequence_tracker.py`, `services/ingestion/state_manager.py`) featuring Redis-backed `last_sequence` persistence, >1,000,000 threshold reset detection, conditional `last_activity_at` updates, `dropped_delta` accumulation, and 6-second TTL enforcement. ([#218](https://github.com/SWP-47/traffic-processing-platform/issues/218))
- Redis Capped List buffering (`services/ingestion/buffer_manager.py`) with `LLEN` checks and `LTRIM` enforcement at 100,000 items to prevent OOM, alongside a background asyncio flusher (`services/ingestion/flusher.py`) utilizing Lua atomic pops and `asyncpg.executemany` for batch `INSERT` operations into the `packet_flows` hypertable. ([#219](https://github.com/SWP-47/traffic-processing-platform/issues/219))
- Docker orchestration (`docker-compose.yml`, `docker-compose.dev.yml`) for 4 microservices, TimescaleDB, and Redis with `restart: always` policies. ([#216](https://github.com/SWP-47/traffic-processing-platform/issues/216))
- Redis configured in ephemeral mode (`save ""`, `appendonly no`) to maximize IOPS and prevent disk-write bottlenecks. ([#216](https://github.com/SWP-47/traffic-processing-platform/issues/216))
- Lightweight Dockerfiles for `ingestion`, `reporting`, `websocket`, and `api` services utilizing `uv` for fast dependency resolution. ([#216](https://github.com/SWP-47/traffic-processing-platform/issues/216))
- Alembic setup and initial relational schema migrations for `users`, `channels`, and `user_channel_scopes` tables. ([#217](https://github.com/SWP-47/traffic-processing-platform/issues/217))
- TimescaleDB initialization including `packet_flows` hypertables, `telemetry_1s` Continuous Aggregates, and 7-day automated retention policies via pure SQL and migrations. ([#217](https://github.com/SWP-47/traffic-processing-platform/issues/217))
- Project initialization with `pyproject.toml` (service extras), `Makefile` aliases, and environment templates. ([#214](https://github.com/SWP-47/traffic-processing-platform/issues/214))
- Typed configuration via Pydantic Settings and structured logging with a custom `TokenMaskingFilter` for sensitive data redaction. ([#214](https://github.com/SWP-47/traffic-processing-platform/issues/214))
- Custom exception hierarchy (`CnSSBaseError` -> `AuthError`, `ValidationError`) for standardized error handling. ([#214](https://github.com/SWP-47/traffic-processing-platform/issues/214))
- Pydantic data contracts for UDP telemetry batches and WebSocket subscription payloads. ([#214](https://github.com/SWP-47/traffic-processing-platform/issues/214))
- `asyncpg` pool manager and `redis.asyncio` client with auto-loading Lua scripts for atomic operations. ([#215](https://github.com/SWP-47/traffic-processing-platform/issues/215))
- Security mechanisms including `passlib` (Argon2id) for password hashing, HS256 JWT encode/decode, and scope verification. ([#215](https://github.com/SWP-47/traffic-processing-platform/issues/215))
- SQLAlchemy ORM models for `users`, `channels`, and `packet_flows` to support database migrations and type hints. ([#215](https://github.com/SWP-47/traffic-processing-platform/issues/215))
- WebSocket server implementation with upgrade handling, JWT validation, `jwt:revoked` checks, and `channel_id` verification returning specific close codes (4001-4004). Includes a 5-second Heartbeat mechanism and a 10-second TTL for `ws:session` keys in Redis to track active connections. ([#220](https://github.com/SWP-47/traffic-processing-platform/issues/220))
- Deterministic `query_hash` (SHA256) generation for subscriptions with a strict Initial Snapshot order (`SUBSCRIBE` -> DB query -> push to client -> listen to Pub/Sub). Implemented Garbage Collection to clean listener sets on disconnect and remove empty `sub:registry` entries, alongside `channel_id` match validation between URL and control message (close code 4003). ([#221](https://github.com/SWP-47/traffic-processing-platform/issues/221))
- Reporting Worker with a 1Hz polling loop to read `sub:active_hashes` and a dynamic SQL generator featuring a strict whitelist for `sort_by` and `sort_order` to prevent SQL injection. Includes Ghost Cleanup to validate `ws:session` via `EXISTS`/`SREM`, atomic drop flushing (Lua -> UPDATE PG -> LTRIM Redis), and mass `UPDATE is_active=FALSE` for timed-out sessions. ([#222](https://github.com/SWP-47/traffic-processing-platform/issues/222))
- FastAPI application factory with dependency injection (`get_db`, `get_current_user`, `require_scope`), Pydantic DTOs for request/response validation, and a `POST /api/v1/auth/login` endpoint for Argon2id credential validation and HS256 JWT issuance with claims (`sub`, `iat`, `exp`, `role`, `scope`). ([#223](https://github.com/SWP-47/traffic-processing-platform/issues/223))
- REST API data routes including `GET /channels` and `GET /status` reading from the `channels` table, `GET /history` calculating historical data using TimescaleDB's `time_bucket` function, and a `GET /health` endpoint for system monitoring. ([#224](https://github.com/SWP-47/traffic-processing-platform/issues/224))
- CLI utilities and scripts including `init_db.py` for admin user creation, `seed_data.py` for test data generation, `revoke_token.py` for adding a token's `jti` to the `jwt:revoked` set in Redis, and `load_test_udp.py` as a UDP stress generator. ([#225](https://github.com/SWP-47/traffic-processing-platform/issues/225))
- Testing infrastructure setup using `conftest.py` with `fake_redis` and `fake_db` fixtures, an asynchronous UDP mock, and comprehensive unit tests for `sequence_tracker` (reset detection), `sql_builder` (SQL injection prevention), `query_hash` (determinism), and `scopes` (access matrix). ([#226](https://github.com/SWP-47/traffic-processing-platform/issues/226))
- Integration tests for the ingestion pipeline, WebSocket subscription flow, ghost cleanup, and authentication flow using `testcontainers` to spin up real Redis and PostgreSQL instances, alongside an E2E test verifying the full pipeline from UDP packet reception to WebSocket client delivery. ([#227](https://github.com/SWP-47/traffic-processing-platform/issues/227))
- Comprehensive documentation including `architecture.md`, `api.md`, `websocket_protocol.md`, and `deployment.md`, OpenAPI descriptions for all REST endpoints, and PlantUML diagrams (`data_flow.puml`, `subscription_lifecycle.puml`) visualizing system architecture and protocols. ([#228](https://github.com/SWP-47/traffic-processing-platform/issues/228))
- Top Tables component on the dashboard page of MUI. ([#205](https://github.com/SWP-47/traffic-processing-platform/issues/205))
- Added another (more user-friendly) behavior of button to turn on and off the blocking using it ([#240](https://github.com/SWP-47/traffic-processing-platform/issues/240))
- Added hosts page to the dashboard of MUI. ([#197](https://github.com/SWP-47/traffic-processing-platform/issues/197))
- Added subscription system to MUI to handle WebSocket subscription. ([#197](https://github.com/SWP-47/traffic-processing-platform/issues/197))

### Changed

- N/A

### Deprecated

- N/A

### Removed

- N/A

### Fixed

- N/A

### Security

- N/A

## [1.1.0] - 2026-06-28

### Added
- Native TimescaleDB retention policies for automated historical data cleanup, replacing manual in-memory garbage collection. ([#179](https://github.com/SWP-47/traffic-processing-platform/issues/179))
- Documented the new REST endpoint `GET /api/v1/channel/{channel_id}/history` for lazy-loading historical telemetry data (Line Chart) with dynamic time-bucketing based on the requested period. ([#167](https://github.com/SWP-47/traffic-processing-platform/issues/167))
- Documented WebSocket control messages (`subscribe`/`unsubscribe`) and the `hosts_update` payload schema to support real-time LAN/WAN host tables via the "Initial Snapshot on Subscribe" pattern. ([#167](https://github.com/SWP-47/traffic-processing-platform/issues/167))
- Added new Sequence Diagrams for Line Chart history retrieval and WebSocket host table subscriptions to the Data Flow & Sequence Diagrams section. ([#167](https://github.com/SWP-47/traffic-processing-platform/issues/167))
- Documented TimescaleDB data aggregation strategies for LAN/WAN host tables, detailing directional mapping and `UNION ALL` usage for calculating packets per second. ([#167](https://github.com/SWP-47/traffic-processing-platform/issues/167))
- Configurable sliding window aggregation (`reporting_window_sec`) to calculate smoother, more accurate `packets_per_sec` metrics and prevent data gaps during task scheduling delays. ([#148](https://github.com/SWP-47/traffic-processing-platform/issues/148))
- Background `reporting_worker` task that periodically queries TimescaleDB to aggregate metrics and push `telemetry_update` payloads to WebSocket listeners. ([#147](https://github.com/SWP-47/traffic-processing-platform/issues/147))
- Sliding window aggregation (configurable via `reporting_window_sec`) to calculate smoother, more accurate `packets_per_sec` metrics and prevent data gaps during task scheduling delays. ([#147](https://github.com/SWP-47/traffic-processing-platform/issues/147))
- `dropped_batches` accumulation in `ChannelState` to be consumed and reset by the reporting worker. ([#147](https://github.com/SWP-47/traffic-processing-platform/issues/147))
- `init.sql` initialization script to automatically create the `packet_flows` hypertable, composite index `(channel_id, time DESC)`, and 7-day retention policy on TimescaleDB container startup. ([#145](https://github.com/SWP-47/traffic-processing-platform/issues/145))
- `app/db.py` module implementing `asyncpg` connection pool management and high-performance `executemany` batch inserts into TimescaleDB. ([#145](https://github.com/SWP-47/traffic-processing-platform/issues/145))
- TimescaleDB service integration across `docker-compose.yml`, `docker-compose.prod.yml`, and `docker-compose.test.yml` with health checks and proper dependency management. ([#145](https://github.com/SWP-47/traffic-processing-platform/issues/145))
- In-memory sequence tracking and `dropped_batches` calculation logic within the UDP ingestion pipeline (`app/udp_server.py`). ([#146](https://github.com/SWP-47/traffic-processing-platform/issues/146))
- `PacketMetadata` Pydantic model in `app/models.py` to parse raw packet metadata (IPs, ports, direction) from the MVP v2 `TelemetryBatch` schema. ([#146](https://github.com/SWP-47/traffic-processing-platform/issues/146))
- Comprehensive TimescaleDB schema specification (`packet_flows` hypertable with `BIGSERIAL` and composite PK) and retention policies in `system-documentation.md`. ([#141](https://github.com/SWP-47/traffic-processing-platform/issues/141))
- `PacketMetadata` schema definition and strict UDP MTU constraint (< 1400 bytes) guidelines across `README.md`, `openapi.yaml`, and `system-documentation.md`. ([#141](https://github.com/SWP-47/traffic-processing-platform/issues/141))
- Architectural descriptions of the new `Ingestion Worker` (UDP to DB) and `Reporting Worker` (DB to WebSocket) in CnSS responsibilities. ([#141](https://github.com/SWP-47/traffic-processing-platform/issues/141))
- Line chart component (apache echarts library) to preview historical data ([#153](https://github.com/SWP-47/traffic-processing-platform/issues/153))
- Information aboud how to build Docker containers added to CN and TP loacl README files ([#181](https://github.com/SWP-47/traffic-processing-platform/issues/181))
- Added basic blocking logic for blocking 1 hardcoded ip address. Block and allow flag now saves in variable, because buttots and switches are not used yet ([#210](https://github.com/SWP-47/traffic-processing-platform/issues/210))

### Changed
- Migrated CnSS telemetry storage from the legacy in-memory MVP v1 dictionary to TimescaleDB, restricting the in-memory `StateStore` strictly to lightweight metadata tracking and WebSocket session management. ([#179](https://github.com/SWP-47/traffic-processing-platform/issues/179))
- Refactored the `ChannelState` Pydantic model to drop the persistent `is_active` flag, shifting channel activity status to be computed on-the-fly based on `last_activity_timestamp`. ([#179](https://github.com/SWP-47/traffic-processing-platform/issues/179))
- Updated the Reporting Worker to derive channel activity timeouts directly from database timestamps instead of relying on legacy in-memory state flags. ([#179](https://github.com/SWP-47/traffic-processing-platform/issues/179))
- Updated the test suite to eliminate assertions against deprecated in-memory legacy behaviors and mock DB queries for scope intersection. ([#179](https://github.com/SWP-47/traffic-processing-platform/issues/179))
- Updated CnSS responsibilities in the System Architecture to include in-memory `WSClientSession` management and targeted broadcasting for resource optimization. ([#167](https://github.com/SWP-47/traffic-processing-platform/issues/167))
- Updated the Database & Memory Leak Prevention section to reflect WebSocket GC for `WSClientSession` objects and conditional DB querying based on active subscriptions. ([#167](https://github.com/SWP-47/traffic-processing-platform/issues/167))
- Updated `broadcast_telemetry_update` to accept and correctly apply the `window_sec` parameter for accurate rate calculations instead of hardcoding a 1-second window. ([#148](https://github.com/SWP-47/traffic-processing-platform/issues/148))
- Refactored `test_websocket.py` to remove unused `TelemetryBatch` and `PacketMetadata` instantiations in broadcast tests, aligning with the new pre-calculated metrics signature. ([#148](https://github.com/SWP-47/traffic-processing-platform/issues/148))
- Updated `test_timeout_and_gc.py` to mock DB queries and validate the new `reporting_worker` and GC task lifecycles with the sliding window configuration. ([#148](https://github.com/SWP-47/traffic-processing-platform/issues/148))
- Refactored channel timeout detection (`is_active` status) to be determined by querying `MAX(time)` from TimescaleDB instead of relying solely on in-memory timestamps. ([#147](https://github.com/SWP-47/traffic-processing-platform/issues/147))
- Updated `broadcast_telemetry_update` signature to accept pre-calculated metrics (`packets_in`, `packets_out`, `window_sec`) instead of a raw `TelemetryBatch`. ([#147](https://github.com/SWP-47/traffic-processing-platform/issues/147))
- Refactored `background_timeout_and_gc_task` to strictly handle Garbage Collection of inactive channels, decoupling it from timeout detection and broadcasting. ([#147](https://github.com/SWP-47/traffic-processing-platform/issues/147))
- Updated integration tests to mock DB queries and validate the new `reporting_worker` and GC task lifecycles. ([#147](https://github.com/SWP-47/traffic-processing-platform/issues/147))
- Refactored `app/broadcast.py` to derive real-time `direction_in` and `direction_out` metrics by iterating over the raw `packets` array instead of reading pre-aggregated counters. ([#146](https://github.com/SWP-47/traffic-processing-platform/issues/146))
- Updated `app/config.py` to include database connection settings (`DATABASE_URL`, pool sizes) loaded from environment variables. ([#145](https://github.com/SWP-47/traffic-processing-platform/issues/145))
- Updated `app/main.py` lifespan to initialize and close the `asyncpg` connection pool on startup/shutdown. ([#145](https://github.com/SWP-47/traffic-processing-platform/issues/145))
- Migrated all existing tests to construct `TelemetryBatch` payloads using the new `packets` array schema and mocked `insert_packet_flows`. ([#146](https://github.com/SWP-47/traffic-processing-platform/issues/146))
- Completely revised `TelemetryBatch` payload schema to transmit raw packet metadata (IPs, ports, integer direction) instead of aggregated counters, reflecting the MVP v2 data pipeline. ([#141](https://github.com/SWP-47/traffic-processing-platform/issues/141))
- Updated `timestamp` field type from ISO 8601 string to Unix timestamp (integer) in all API specifications and OpenAPI schemas. ([#141](https://github.com/SWP-47/traffic-processing-platform/issues/141))
- Updated WebSocket `telemetry_update` push frequency description from `2-10 Hz` to `1 Hz (aggregated from TimescaleDB)` in `README.md`, `openapi.yaml`, and `postman_collection.json`. ([#141](https://github.com/SWP-47/traffic-processing-platform/issues/141))
- Rewrote CnSS architectural sequence diagrams to illustrate the new flow: CN -> UDP -> CnSS Ingestion -> TimescaleDB -> CnSS Reporting -> WebSocket. ([#141](https://github.com/SWP-47/traffic-processing-platform/issues/141))
- Bumped `openapi.yaml` version from `1.0.0` to `2.0.0` to reflect the major architectural shift. ([#141](https://github.com/SWP-47/traffic-processing-platform/issues/141))
- Added Docker configuration for Traffic Processor (TP) to simplify deployment and ensure environment consistency. ([#90](https://github.com/SWP-47/traffic-processing-platform/issues/90))
- Added Docker configuration for Communication Node (CN) to simplify deployment and ensure environment consistency. ([#88](https://github.com/SWP-47/traffic-processing-platform/issues/88))
- Added JSON format validation using library jsonschema ([#152](https://github.com/SWP-47/traffic-processing-platform/issues/152))
- Architecture of hardware (FPGA) part of TP was updated to make it more stroung and useful for future development ([#209](https://github.com/SWP-47/traffic-processing-platform/issues/209))


### Deprecated

- N/A

### Removed
- Removed the legacy `background_timeout_and_gc_task` and obsolete state mutation methods (e.g., `set_channel_active`, `set_channel_inactive`). ([#179](https://github.com/SWP-47/traffic-processing-platform/issues/179))
- Removed obsolete unit and integration tests (`test_recovery.py`, GC-related tests in `test_timeout_and_gc.py`) that validated deprecated in-memory state mutations. ([#179](https://github.com/SWP-47/traffic-processing-platform/issues/179))
- Dead code and unused variable assignments (e.g., `dropped` return value in `udp_server.py`, unused `batch` object in `test_websocket.py`) to improve code clarity and maintainability. ([#148](https://github.com/SWP-47/traffic-processing-platform/issues/148))
- Immediate WebSocket broadcasting from the UDP ingestion path (`udp_server.py`), shifting all push responsibilities to the reporting worker. ([#147](https://github.com/SWP-47/traffic-processing-platform/issues/147))
- Timeout detection and broadcasting logic from the background GC task. ([#147](https://github.com/SWP-47/traffic-processing-platform/issues/147))
- Legacy `DirectionStats` Pydantic model from `app/models.py`, replaced by `PacketMetadata` and the raw `packets` array. ([#146](https://github.com/SWP-47/traffic-processing-platform/issues/146))
- References to in-memory `Dict` state management and legacy aggregated counter payloads (`direction_out`, `direction_in` objects) from all API and system documentation. ([#141](https://github.com/SWP-47/traffic-processing-platform/issues/141))

### Fixed
- Fixed an issue where the JWT scope intersection during login relied on the in-memory store, causing empty scopes after a server restart before the first UDP packet arrived. The scope is now correctly derived from the database. ([#179](https://github.com/SWP-47/traffic-processing-platform/issues/179))
- Fixed runtime `AttributeError` in the Reporting Worker caused by calls to the removed `state_store.set_channel_active()` method. ([#179](https://github.com/SWP-47/traffic-processing-platform/issues/179))
- Added graceful error handling and lazy pool re-initialization in `app/db.py` and `app/udp_server.py` to ensure the UDP listener never crashes if TimescaleDB becomes temporarily unreachable (AC 4). ([#145](https://github.com/SWP-47/traffic-processing-platform/issues/145), [#146](https://github.com/SWP-47/traffic-processing-platform/issues/146))
- Resolved `pytest-asyncio` collection errors caused by invalid method signatures in WebSocket integration tests. ([#146](https://github.com/SWP-47/traffic-processing-platform/issues/146))
- Fixed case-sensitivity mismatch in UDP invalid UTF-8 logging assertion in `test_udp_server.py`. ([#146](https://github.com/SWP-47/traffic-processing-platform/issues/146))
- Upper bound for time window of sending packets by CN was added to fix problems with fragmentation. ([#89](https://github.com/SWP-47/traffic-processing-platform/issues/89))

### Security
- Documented UDP MTU enforcement (< 1400 bytes) as a critical mitigation against network-level fragmentation and silent packet drops in the CN Trust Model section. ([#141](https://github.com/SWP-47/traffic-processing-platform/issues/141))


## [1.0.0] - 2026-06-21

### Added

- Functional MUI Login page, centralized JWT token management via `AuthenticationService`, visual error feedback for invalid credentials, and automatic redirection upon successful authentication. ([#115](https://github.com/SWP-47/traffic-processing-platform/issues/115))
- REST endpoint `GET /api/v1/health` returning CnSS operational status with aggregate channel statistics (`channels_active`, `channels_total`) and component health indicators. ([#84](https://github.com/SWP-47/traffic-processing-platform/issues/84))
- REST endpoint `GET /api/v1/channels` listing all channels accessible to the authenticated user with `is_active` status and `last_activity_timestamp` for each channel. ([#84](https://github.com/SWP-47/traffic-processing-platform/issues/84))
- REST endpoint `GET /api/v1/channel/{channel_id}/status` providing detailed status for a specific channel including activity state and last activity timestamp. ([#84](https://github.com/SWP-47/traffic-processing-platform/issues/84))
- WebSocket endpoint `WS /api/v1/ws/telemetry` for real-time telemetry streaming with channel-scoped subscriptions and automatic event broadcasting at 2-10 Hz. ([#85](https://github.com/SWP-47/traffic-processing-platform/issues/85))
- Channel-scoped WebSocket subscriptions allowing MUI clients to subscribe to specific channels and receive isolated `telemetry_update` events. ([#85](https://github.com/SWP-47/traffic-processing-platform/issues/85))
- Authorization middleware validating JWT tokens on all protected REST and WebSocket endpoints with role-based access control (admin/viewer). ([#83](https://github.com/SWP-47/traffic-processing-platform/issues/83))
- Per-channel access control enforcing scope restrictions: `admin` role bypasses scope checks (unrestricted access), `viewer` role restricted to channels in JWT `scope` array. ([#83](https://github.com/SWP-47/traffic-processing-platform/issues/83))
- Token masking filter (`TokenMaskingFilter`) sanitizing logs to prevent JWT token leakage via query parameters, replacing tokens with `?token=[REDACTED]`. ([#86](https://github.com/SWP-47/traffic-processing-platform/issues/86))
- WebSocket ping/pong keep-alive mechanism sending protocol-level ping frames every 30 seconds with 10-second pong timeout for dead connection detection. ([#86](https://github.com/SWP-47/traffic-processing-platform/issues/86))
- Automatic WebSocket listener cleanup on disconnect/error to prevent memory leaks, ensuring immediate removal from `channel.listeners` sets. ([#86](https://github.com/SWP-47/traffic-processing-platform/issues/86))
- Comprehensive integration test suite for REST endpoints (health, channels, status) validating authentication, authorization, response structure, and error handling. ([#84](https://github.com/SWP-47/traffic-processing-platform/issues/84))
- Integration tests for WebSocket telemetry endpoint covering connection validation, channel subscriptions, broadcast isolation, and custom close codes. ([#85](https://github.com/SWP-47/traffic-processing-platform/issues/85))
- Integration tests for JWT authorization middleware covering missing headers, expired tokens, invalid signatures, admin unrestricted access, and viewer scope enforcement. ([#83](https://github.com/SWP-47/traffic-processing-platform/issues/83))
- Per-channel timeout detection: CnSS now monitors channel activity and automatically sets `is_active=false` if no UDP telemetry is received within `activity_timeout_ms` (default: 5000ms), implementing the Channel Activity Indicator (US-001). ([#81](https://github.com/SWP-47/traffic-processing-platform/issues/81))
- Channel garbage collection: Inactive channels (`is_active=false`) that have zero WebSocket listeners and exceed `channel_retention_ms` (default: 24 hours) are automatically removed from the in-memory registry to prevent memory leaks. ([#81](https://github.com/SWP-47/traffic-processing-platform/issues/81))
- Real-time state broadcasting: CnSS now pushes `telemetry_update` events to all subscribed WebSocket listeners when a channel's `is_active` state changes to `false` (timeout) or recovers to `true` (new UDP batch received), enabling real-time MUI dashboard updates (US-015). ([#81](https://github.com/SWP-47/traffic-processing-platform/issues/81))
- Background asynchronous task (`background_timeout_and_gc_task`) to periodically evaluate channel timeouts and perform garbage collection without blocking the main event loop. ([#81](https://github.com/SWP-47/traffic-processing-platform/issues/81))
- Configurable timeout and retention thresholds (`activity_timeout_ms`, `channel_retention_ms`) via environment variables in `app/config.py`. ([#81](https://github.com/SWP-47/traffic-processing-platform/issues/81))
- Comprehensive integration and unit test suite covering Acceptance Criteria for timeout detection, channel isolation, WebSocket broadcasting on state change, and garbage collection logic. ([#81](https://github.com/SWP-47/traffic-processing-platform/issues/81))
- OpenAPI TypeScript type generation from CnSS API schema using `openapi-typescript` for end-to-end type safety between frontend and backend. ([#60](https://github.com/SWP-47/traffic-processing-platform/issues/60))
- Type-safe REST API client using `openapi-fetch` singleton with centralized error handling middleware and standardized `ApiError` class for HTTP error mapping. ([#60](https://github.com/SWP-47/traffic-processing-platform/issues/60))
- Real-time telemetry WebSocket service with automatic reconnection and ping/pong protocol. ([#60](https://github.com/SWP-47/traffic-processing-platform/issues/60))
- Vite development proxy configuration for seamless API and WebSocket forwarding during local development, eliminating CORS issues. ([#60](https://github.com/SWP-47/traffic-processing-platform/issues/60))
- Production nginx configuration with WebSocket upgrade support. ([#60](https://github.com/SWP-47/traffic-processing-platform/issues/60))
- `POST /api/v1/auth/login` endpoint for user authentication, issuing HS256-signed JWT tokens containing `role` and `scope` claims for per-channel access control. ([#80](https://github.com/SWP-47/traffic-processing-platform/issues/80))
- Pydantic models (`LoginRequest`, `LoginResponse`, `TokenPayload`) for strict validation of authentication payloads and JWT claims. ([#80](https://github.com/SWP-47/traffic-processing-platform/issues/80))
- Global `HTTPException` handler to enforce the standardized error response format (`{"error": "<code>", "message": "<text>"}`) across all REST endpoints. ([#80](https://github.com/SWP-47/traffic-processing-platform/issues/80))
- `decode_token` utility and FastAPI dependencies (`get_current_user`, `get_ws_user`) for stateless JWT verification and scope extraction. ([#80](https://github.com/SWP-47/traffic-processing-platform/issues/80))
- Comprehensive unit and integration test suite for the authentication system, covering JWT generation, signature verification, expiration handling, missing fields, invalid credentials, and scope intersection logic. ([#80](https://github.com/SWP-47/traffic-processing-platform/issues/80))
- UDP listener in CnSS to ingest `TelemetryBatch` payloads from Communication Nodes on port 5140, featuring auto-channel creation and sequence tracking for dropped batch detection. ([#79](https://github.com/SWP-47/traffic-processing-platform/issues/79))
- Repository pattern for CnSS state management (`StateStore` interface) with an initial thread-safe in-memory implementation, preparing the architecture for future database integration. ([#79](https://github.com/SWP-47/traffic-processing-platform/issues/79))
- Centralized environment configuration using `pydantic-settings` for type-safe management of CnSS ports, logging levels, and JWT secrets. ([#79](https://github.com/SWP-47/traffic-processing-platform/issues/79))
- Comprehensive unit and integration test suite validating UDP ingestion, state management, and sequence tracking logic. ([#79](https://github.com/SWP-47/traffic-processing-platform/issues/79))
- Multi-channel architecture: CnSS now supports multiple Communication Nodes (CNs) and multiple MUI clients concurrently, with per-channel state management. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- User authentication via `POST /api/v1/auth/login` with JWT tokens containing `role` and `scope` claims for per-channel access control. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- New REST endpoint `GET /api/v1/channels` to list channels accessible to the authenticated user (filtered by JWT `scope` for `viewer` role, all channels for `admin`). ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- Per-channel WebSocket subscription via `?channel_id={{channel_id}}` query parameter, allowing MUI clients to subscribe to specific monitored bridges. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- Granular WebSocket close codes for authentication and authorization failures: `4001` (invalid_token), `4002` (missing_channel), `4003` (channel_forbidden), `4004` (channel_not_found). ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- `docs/system-architecture.md` defining the end-to-end telemetry pipeline, sequence diagrams, and edge-case handling for MVP v1. ([#64](https://github.com/SWP-47/traffic-processing-platform/issues/64))
- `dropped_batches` and `received_at` fields to the `telemetry_update` WebSocket payload to track UDP datagram losses and ensure accurate server-side timeout calculation. ([#64](https://github.com/SWP-47/traffic-processing-platform/issues/64))
- Initial Management User Interface (MUI) mock dashboard with interactive column chart for MVP v0 demonstration. ([#27](https://github.com/SWP-47/traffic-processing-platform/issues/27))
- Initial monorepo structure and component directories (TP, CN, CnSS, MUI). ([#3](https://github.com/SWP-47/traffic-processing-platform/issues/3))
- GitHub Issue Forms for User Stories, Course Tasks, and Bug Reports. ([#6](https://github.com/SWP-47/traffic-processing-platform/issues/6))
- Pull Request template with issue linking and changelog verification checklist. ([#6](https://github.com/SWP-47/traffic-processing-platform/issues/6))
- Added foundational MVP v0 structure for Control and Status Server (CnSS), including `/health` endpoint, Docker configurations (Dev/Prod/Test), integration tests, and CI workflow. ([#30](https://github.com/SWP-47/traffic-processing-platform/issues/30))
- Implemented bidirectional packet counting in Traffic Processor and aggregated UDP dispatch to Control and Status Server via Communication Node ([#77](https://github.com/SWP-47/traffic-processing-platform/issues/77))
- Implemented FPGA-based minimal packet analysis in addition to forwarding ([#87](https://github.com/SWP-47/traffic-processing-platform/issues/87))
- Constraints file (`.xdc`) for deploying bitstream to ARTIX-7 FPGA Development Board AX7201 ([#87](https://github.com/SWP-47/traffic-processing-platform/issues/87))
- Added MUI PacketsColumnChart component to show Rx/Tx rate obtained from WS telemetry. ([#69](https://github.com/SWP-47/traffic-processing-platform/issues/69))

### Changed

- All protected REST and WebSocket endpoints now require `Authorization: Bearer {{access_token}}` header or query parameter for authentication. ([#83](https://github.com/SWP-47/traffic-processing-platform/issues/83))
- Updated `docker-compose.yml` to expose and map the UDP port 5140 for telemetry ingestion. ([#79](https://github.com/SWP-47/traffic-processing-platform/issues/79))
- WebSocket endpoint URL now requires `channel_id` query parameter: `wss://{{cnss_host}}:{{cnss_ws_port}}/api/v1/ws/telemetry?token={{access_token}}&channel_id={{channel_id}}`. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- Channel status endpoint moved from `GET /api/v1/channel/status` to `GET /api/v1/channel/{channel_id}/status` with `channel_id` as a path parameter. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- Health endpoint `GET /api/v1/health` now returns CnSS status and aggregate channel statistics (`channels_active`, `channels_total`) instead of individual TP/CN component statuses. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- Updated `openapi.yaml` and `postman_collection.json` to reflect the new multi-channel API and authentication flow. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- Renamed telemetry traffic directions from `direction_a`/`direction_b` to `direction_out`/`direction_in` across API documentation, `openapi.yaml`, and `postman_collection.json` for improved clarity. ([#46](https://github.com/SWP-47/traffic-processing-platform/issues/46))
- Updated WebSocket Connection Lifecycle to explicitly mandate server-initiated `ping`/`pong` mechanism for dead peer detection and memory leak prevention. ([#64](https://github.com/SWP-47/traffic-processing-platform/issues/64))
- Changes Communication Node (CN) telemetry sender to correctly format JSON payloads and transmit UDP batches to CnSS ([#76](https://github.com/SWP-47/traffic-processing-platform/issues/76)).
- Restructured `traffic-processor/` directory layout for improved navigation ([#87](https://github.com/SWP-47/traffic-processing-platform/issues/87))
- MUI StatusIndicator component now can get real data from CnSS via WebSocket. ([#68](https://github.com/SWP-47/traffic-processing-platform/issues/68))
- Traffic Processor (TP) now extracts and forwards individual packet metadata (IP addresses, ports, direction) instead of aggregated counters, and switched to standard UDP sockets for reliable delivery ([#142](https://github.com/SWP-47/traffic-processing-platform/issues/142)).
- Communication Node (CN) telemetry payload updated to send a flat array of individual packet metadata with Unix timestamps and integer ports, aligning with the revised API specification ([#143](https://github.com/SWP-47/traffic-processing-platform/issues/143)).

### Deprecated

- `GET /api/v1/channel/status` (without `channel_id` in path) is deprecated and will be removed in a future release. Use `GET /api/v1/channel/{channel_id}/status` instead. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))

### Removed

- N/A

### Fixed

- Fixed incorrect IPv4 EtherType value in the Traffic Processor (FPGA) packet recognition logic ([#87](https://github.com/SWP-47/traffic-processing-platform/issues/87)).

### Security

- Implemented log sanitization to prevent JWT token leakage in access logs via query parameter masking. ([#86](https://github.com/SWP-47/traffic-processing-platform/issues/86))
- Added WebSocket ping/pong mechanism for dead peer detection and connection health monitoring. ([#86](https://github.com/SWP-47/traffic-processing-platform/issues/86))
- Enforced per-channel authorization matrix with role-based access control (admin/viewer) and scope validation for all REST and WebSocket endpoints. ([#83](https://github.com/SWP-47/traffic-processing-platform/issues/83))
- Implemented stateless JWT-based authentication (HS256) with automatic expiration checking (`exp` claim) to protect REST endpoints and prepare for WebSocket authorization. ([#80](https://github.com/SWP-47/traffic-processing-platform/issues/80))
- Added JWT-based authentication for all REST and WebSocket endpoints to protect telemetry data and prevent unauthorized access. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- CnSS now sanitizes access logs to prevent `access_token` leakage via query parameters. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))


[Unreleased]: https://github.com/SWP-47/traffic-processing-platform/compare/v1.1.0...HEAD
[1.0.0]: https://github.com/SWP-47/traffic-processing-platform/releases/tag/v1.0.0
[1.1.0]: https://github.com/SWP-47/traffic-processing-platform/releases/tag/v1.1.0

<!-- 
RELEASE TEMPLATE (For Release Manager use only):
When creating a release (e.g., v0.1.0), copy the [Unreleased] section below, 
rename it to the version and date, and create a fresh [Unreleased] section above it.

## [0.1.0] - 2026-06-11

### Added
- ... (entries from Unreleased) ...

[Unreleased]: https://github.com/SWP-47/traffic-processing-platform/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SWP-47/traffic-processing-platform/releases/tag/v0.1.0
-->
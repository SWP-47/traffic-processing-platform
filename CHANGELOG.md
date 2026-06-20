# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- MUI Login page with username/password form, client-side validation, and loading state during authentication submission. ([#114](https://github.com/SWP-47/traffic-processing-platform/issues/114))
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

### Deprecated

- `GET /api/v1/channel/status` (without `channel_id` in path) is deprecated and will be removed in a future release. Use `GET /api/v1/channel/{channel_id}/status` instead. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))

### Removed

- N/A

### Fixed

- N/A

### Security

- Implemented log sanitization to prevent JWT token leakage in access logs via query parameter masking. ([#86](https://github.com/SWP-47/traffic-processing-platform/issues/86))
- Added WebSocket ping/pong mechanism for dead peer detection and connection health monitoring. ([#86](https://github.com/SWP-47/traffic-processing-platform/issues/86))
- Enforced per-channel authorization matrix with role-based access control (admin/viewer) and scope validation for all REST and WebSocket endpoints. ([#83](https://github.com/SWP-47/traffic-processing-platform/issues/83))
- Implemented stateless JWT-based authentication (HS256) with automatic expiration checking (`exp` claim) to protect REST endpoints and prepare for WebSocket authorization. ([#80](https://github.com/SWP-47/traffic-processing-platform/issues/80))
- Added JWT-based authentication for all REST and WebSocket endpoints to protect telemetry data and prevent unauthorized access. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- CnSS now sanitizes access logs to prevent `access_token` leakage via query parameters. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))

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
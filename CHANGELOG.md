# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

### Changed
- Updated `docker-compose.yml` to expose and map the UDP port 5140 for telemetry ingestion. ([#79](https://github.com/SWP-47/traffic-processing-platform/issues/79))
- WebSocket endpoint URL now requires `channel_id` query parameter: `wss://{{cnss_host}}:{{cnss_ws_port}}/api/v1/ws/telemetry?token={{access_token}}&channel_id={{channel_id}}`. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- Channel status endpoint moved from `GET /api/v1/channel/status` to `GET /api/v1/channel/{channel_id}/status` with `channel_id` as a path parameter. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- Health endpoint `GET /api/v1/health` now returns CnSS status and aggregate channel statistics (`channels_active`, `channels_total`) instead of individual TP/CN component statuses. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- Updated `openapi.yaml` and `postman_collection.json` to reflect the new multi-channel API and authentication flow. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))
- Renamed telemetry traffic directions from `direction_a`/`direction_b` to `direction_out`/`direction_in` across API documentation, `openapi.yaml`, and `postman_collection.json` for improved clarity. ([#46](https://github.com/SWP-47/traffic-processing-platform/issues/46))
- Updated WebSocket Connection Lifecycle to explicitly mandate server-initiated `ping`/`pong` mechanism for dead peer detection and memory leak prevention. ([#64](https://github.com/SWP-47/traffic-processing-platform/issues/64))

### Deprecated

- `GET /api/v1/channel/status` (without `channel_id` in path) is deprecated and will be removed in a future release. Use `GET /api/v1/channel/{channel_id}/status` instead. ([#75](https://github.com/SWP-47/traffic-processing-platform/issues/75))

### Removed

- N/A

### Fixed

- N/A

### Security

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
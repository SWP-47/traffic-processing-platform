# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `docs/system-architecture.md` defining the end-to-end telemetry pipeline, sequence diagrams, and edge-case handling for MVP v1. ([#64](https://github.com/SWP-47/traffic-processing-platform/issues/64))
- `dropped_batches` and `received_at` fields to the `telemetry_update` WebSocket payload to track UDP datagram losses and ensure accurate server-side timeout calculation. ([#64](https://github.com/SWP-47/traffic-processing-platform/issues/64))
- Initial Management User Interface (MUI) mock dashboard with interactive column chart for MVP v0 demonstration. ([#27](https://github.com/SWP-47/traffic-processing-platform/issues/27))
- Initial monorepo structure and component directories (TP, CN, CnSS, MUI). ([#3](https://github.com/SWP-47/traffic-processing-platform/issues/3))
- GitHub Issue Forms for User Stories, Course Tasks, and Bug Reports. ([#6](https://github.com/SWP-47/traffic-processing-platform/issues/6))
- Pull Request template with issue linking and changelog verification checklist. ([#6](https://github.com/SWP-47/traffic-processing-platform/issues/6))
- Added foundational MVP v0 structure for Control and Status Server (CnSS), including `/health` endpoint, Docker configurations (Dev/Prod/Test), integration tests, and CI workflow. ([#30](https://github.com/SWP-47/traffic-processing-platform/issues/30))

### Changed

- Renamed telemetry traffic directions from `direction_a`/`direction_b` to `direction_out`/`direction_in` across API documentation, `openapi.yaml`, and `postman_collection.json` for improved clarity. ([#46](https://github.com/SWP-47/traffic-processing-platform/issues/46))
- Updated WebSocket Connection Lifecycle to explicitly mandate server-initiated `ping`/`pong` mechanism for dead peer detection and memory leak prevention. ([#64](https://github.com/SWP-47/traffic-processing-platform/issues/64))

### Deprecated

- N/A

### Removed

- N/A

### Fixed

- N/A

### Security

- N/A

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
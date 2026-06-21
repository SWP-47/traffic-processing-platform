# Project Roadmap

This document outlines the Sprint-by-Sprint delivery plan for the Traffic Processing Platform.

*Last updated: June 21, 2026*

---

## Sprint 1: MVP v1

**Milestone:** [Sprint 1 Milestone](https://github.com/SWP-47/traffic-processing-platform/milestone/1)

**Dates:** June 15 to June 21, 2026

**Sprint Goal:** Deliver a functional, transparent inline network bridge that counts packets and displays real-time channel activity remotely without disrupting end-user internet access.

**Focus / Expected Outcome:**

Establish the core four-component data pipeline (TP → CN → CnSS → MUI). The Traffic Processor will act as a zero-latency inline bridge while extracting basic telemetry. The Management User Interface will display a real-time binary activity indicator and bidirectional packet counters via WebSockets, accessible remotely via JWT authentication.

> Note: during this sprint, [US-15: Real-time MUI Dashboard Updates](https://github.com/SWP-47/traffic-processing-platform/issues/98) was implemented in preparation for the next MVP stages. Additionally, after the customer review, [US-012:  Basic Password Protection for MUI](https://github.com/SWP-47/traffic-processing-platform/issues/103) was added to the current sprint.

**Linked Planned Items:**

*User Stories:*

- [US-001: Channel Activity Indicator](https://github.com/SWP-47/traffic-processing-platform/issues/48)
- [US-002: Basic Network Usage Statistics](https://github.com/SWP-47/traffic-processing-platform/issues/51)
- [US-004: Modular Platform Integration](https://github.com/SWP-47/traffic-processing-platform/issues/52)
- [US-005: Invisible Traffic Analyzer Deployment](https://github.com/SWP-47/traffic-processing-platform/issues/53)
- [US-009: Seamless Bidirectional Packet Passing](https://github.com/SWP-47/traffic-processing-platform/issues/54)
- [US-014: Remote MUI Access](https://github.com/SWP-47/traffic-processing-platform/issues/55)
- [US-15: Real-time MUI Dashboard Updates](https://github.com/SWP-47/traffic-processing-platform/issues/98)
- [US-012:  Basic Password Protection for MUI](https://github.com/SWP-47/traffic-processing-platform/issues/103)

*Supporting PBIs:*

- [UDP telemetry ingestion with per-channel state management](https://github.com/SWP-47/traffic-processing-platform/issues/79)
- [JWT-based authentication and token issuance](https://github.com/SWP-47/traffic-processing-platform/issues/80)
- [JWT authorization middleware for REST and WebSocket](https://github.com/SWP-47/traffic-processing-platform/issues/83)
- [Implement Login UI Components](https://github.com/SWP-47/traffic-processing-platform/issues/114)
- [Implement Authentication API Integration](https://github.com/SWP-47/traffic-processing-platform/issues/115)

---

## Sprint 2: MVP v2

**Milestone:** [Sprint 2 Milestone](https://github.com/SWP-47/traffic-processing-platform/milestone/2)

**Dates:** June 22 to June 28, 2026

**Sprint Goal:** Enhance the monitoring capabilities by introducing byte-level volume counting, historical data retention, and protocol-based display filtering for deeper network analysis.

**Focus / Expected Outcome:**
Transition from basic packet counting to advanced telemetry. The Traffic Processor will be upgraded to count byte volumes in addition to packets. The Control and Status Server will integrate a database to store historical statistics, and the MUI will introduce UI filtering for protocol types and specific IP/port tracking, enabling security-focused analysis as discussed with the customer.

**Linked Planned Items:**

*User Stories:*

- [US-016: Byte Volume Counting](https://github.com/SWP-47/traffic-processing-platform/issues/16)
- [US-013: Historical Traffic Statistics Storage](https://github.com/SWP-47/traffic-processing-platform/issues/13)
- [US-010: Protocol Type Traffic Display Filtering](https://github.com/SWP-47/traffic-processing-platform/issues/10)
- [US-006: Specific IP Traffic Analysis](https://github.com/SWP-47/traffic-processing-platform/issues/6)

*Supporting PBIs:*

- Integrate Postgres/TimescaleDB for CnSS historical data storage
- Upgrade TP telemetry extraction to calculate byte volumes
- Implement MUI frontend filtering logic for protocols and IP addresses
- Add WebSocket ping/pong mechanism and client-side timeout fallback

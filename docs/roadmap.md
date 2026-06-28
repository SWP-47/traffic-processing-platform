# Project Roadmap

This document outlines the Sprint-by-Sprint delivery plan for the Traffic Processing Platform.

*Last updated: June 28, 2026*

---

## Sprint 1: MVP v1

**Milestone:** [Sprint 1 Milestone](https://github.com/SWP-47/traffic-processing-platform/milestone/1)

**Dates:** June 15 to June 21, 2026

**Sprint Goal:** Deliver a functional, transparent inline network bridge that counts packets and displays real-time channel activity remotely without disrupting end-user internet access.

**Focus / Expected Outcome:**

Establish the core four-component data pipeline (TP → CN → CnSS → MUI). The Traffic Processor will act as a zero-latency inline bridge while extracting basic telemetry. The Management User Interface will display a real-time binary activity indicator and bidirectional packet counters via WebSockets, accessible remotely via JWT authentication.

> Note: during this sprint, [US-015: Real-time MUI Dashboard Updates](https://github.com/SWP-47/traffic-processing-platform/issues/98) was implemented in preparation for the next MVP stages. Additionally, after the customer review, [US-012: Basic Password Protection for MUI](https://github.com/SWP-47/traffic-processing-platform/issues/103) was added to the current sprint.

**Linked Planned Items:**

*User Stories:*

- [US-001: Channel Activity Indicator](https://github.com/SWP-47/traffic-processing-platform/issues/48)
- [US-002: Basic Network Usage Statistics](https://github.com/SWP-47/traffic-processing-platform/issues/51)
- [US-004: Modular Platform Integration](https://github.com/SWP-47/traffic-processing-platform/issues/52)
- [US-005: Invisible Traffic Analyzer Deployment](https://github.com/SWP-47/traffic-processing-platform/issues/53)
- [US-009: Seamless Bidirectional Packet Passing](https://github.com/SWP-47/traffic-processing-platform/issues/54)
- [US-014: Remote MUI Access](https://github.com/SWP-47/traffic-processing-platform/issues/55)
- [US-015: Real-time MUI Dashboard Updates](https://github.com/SWP-47/traffic-processing-platform/issues/98)
- [US-012: Basic Password Protection for MUI](https://github.com/SWP-47/traffic-processing-platform/issues/103)

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

**Sprint Goal:** Implement database integration for historical data retention and deliver initial historical data visualization in the MUI.

**Focus / Expected Outcome:**
Transition from in-memory storage to a persistent database to handle historical statistics.

**Linked Planned Items:**

*User Stories:*

- [US-013: Historical Traffic Statistics Storage](https://github.com/SWP-47/traffic-processing-platform/issues/97)

*Supporting PBIs:*

- [Implement `/api/v1/health` database metrics query (distinct/active channels)](https://github.com/SWP-47/traffic-processing-platform/issues/148)
- [Implementat the correct packet fragmentation in CN](https://github.com/SWP-47/traffic-processing-platform/issues/89)
- [Create line chart component](https://github.com/SWP-47/traffic-processing-platform/issues/153)

---

## Sprint 3: MVP v3

**Milestone:** [Sprint 3 Milestone](https://github.com/SWP-47/traffic-processing-platform/milestone/3)

**Dates:** June 29 to July 5, 2026

**Sprint Goal:** Implement a comprehensive, large-scale table view of all channels and complete deferred telemetry and filtering features.

**Focus / Expected Outcome:**
Develop a dedicated, large-scale detailed statistics page featuring a filterable and sortable table of all monitored channels and hosts.

**Linked Planned Items:**

*User Stories:*

- [US-019: Packet Metadata Capture and View](https://github.com/SWP-47/traffic-processing-platform/issues/107)
- [US-006: Specific IP Traffic Analysis](https://github.com/SWP-47/traffic-processing-platform/issues/96)
- [US-010: Protocol Type Traffic Display Filtering](https://github.com/SWP-47/traffic-processing-platform/issues/101)
- [US-016: Byte Volume Counting](https://github.com/SWP-47/traffic-processing-platform/issues/104)

*Supporting PBIs:*

- Implement large, filterable, and sortable data table component in MUI for all channels
- Develop backend REST API endpoints for paginated and filtered host/channel metadata retrieval
- Upgrade TP telemetry extraction to calculate byte volumes
- Implement MUI frontend filtering logic for protocols and IP addresses

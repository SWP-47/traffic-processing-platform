# Project Roadmap

This document outlines the Sprint-by-Sprint delivery plan for the Traffic Processing Platform.

*Last updated: July 5, 2026*

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

## Sprint 2: MVP v1 maintenence

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

## Sprint 3: MVP v2

**Milestone:** [Sprint 3 Milestone](https://github.com/SWP-47/traffic-processing-platform/milestone/3)

**Dates:** June 29 to July 5, 2026

**Sprint Goal:** Transition to MVP v2 by implementing FPGA-based packet blocking, redesigning a scalable, secure backend architecture, and delivering host tracking and host statistics tables on the MUI dashboard.

**Focus / Expected Outcome:**
Completely redesigned the CnSS architecture into a decoupled, microservice-oriented backend with Redis buffering and TimescaleDB persistence. Executed a comprehensive MUI redesign introducing the detailed "Host Statistics" table with advanced filtering and sorting. Fully containerized the Traffic Processor (TP) and Communication Node (CN) for reproducible edge deployment, and implemented physical hardware traffic blocking via the FPGA. Removed US-016 (Byte Volume Counting) from the active scope based on customer feedback.

**Linked Planned Items:**

*User Stories:*

- [US-017: Traffic Blocking / Dropping](https://github.com/SWP-47/traffic-processing-platform/issues/105) (Partially implemented via FPGA)
- [US-022: Secure https and wss connection](https://github.com/SWP-47/traffic-processing-platform/issues/252)

*Supporting PBIs:*

- [Backend Architecture Redesign](https://github.com/SWP-47/traffic-processing-platform/issues/208) Decouple CnSS into four distinct components (Database, REST API, UDP Ingestion Listener, WebSocket Service) with Redis buffering for high-throughput ingestion.
- [Secure User Database](https://github.com/SWP-47/traffic-processing-platform/issues/215) Integrate a persistent user database for authentication, replacing hardcoded credentials.
- [MUI Dashboard Redesign](https://github.com/SWP-47/traffic-processing-platform/issues/208) Implement the detailed "Host Statistics" table featuring advanced real-time filtering (Direction IN/OUT, IP subnet/regex, RX/TX min/max bounds, LastSeen ranges) and bi-directional sorting. Add summary "Top Hosts" widgets to the main dashboard.

---

## Sprint 4: Stability, UI/UX Refinement, and Real-Time Reactivity

**Milestone:** [Sprint 4 Milestone](https://github.com/SWP-47/traffic-processing-platform/milestone/4)

**Dates:** July 6 to July 12, 2026

**Sprint Goal:** Resolve critical stability issues discovered during UAT, refine the MUI filtering experience based on customer feedback, and enhance the real-time reactivity of historical data visualizations.

**Focus / Expected Outcome:**
Address the critical CN/CnSS state corruption crash triggered by physical network disconnects. Replace the quick text-based filtering syntax in the host statistics table with structured, user-friendly sidebar controls. Implement fine-grained time-scale zooming (1-minute/5-minute windows) for the historical line chart to allow near real-time observation of traffic state changes. Polish the hardware blocking implementation by fixing the physical button debounce and expanding blocking rules beyond a single hardcoded IP.

**Linked Planned Items:**

*User Stories:*

- [US-006: Specific IP Traffic Analysis](https://github.com/SWP-47/traffic-processing-platform/issues/96) (Expand hardware blocking to support configurable per-host or per-channel rules)
- [US-010: Protocol Type Traffic Display Filtering](https://github.com/SWP-47/traffic-processing-platform/issues/101) (Implement protocol-based display filtering in the MUI)

*Supporting PBIs:*

- **[Critical] Physical Fault Tolerance:** Investigate and resolve the CN/CnSS state corruption crash when a network interface is physically disconnected. Implement graceful error handling and state recovery so telemetry automatically resumes without manual restarts (UAT-003).
- **UI/UX Filtering Refinement:** Redesign the host table filtering UI to replace raw text-field syntax with structured sidebar/dropdown controls (e.g., tags, min/max bounds, subnet selectors) (UAT-004).
- **Historical Chart Reactivity:** Implement a 1-minute/5-minute minimum time window toggle for the historical line chart to improve real-time reactivity and visibility of immediate traffic state changes (UAT-002).
- **Hardware Polish:** Fix the Key1 button contact bounce (debounce) on the FPGA to prevent multiple unintended state toggles. Expand the blocking logic to support configurable rules rather than a single hardcoded IP (UAT-005).
- **UAT Environment Preparation:** Prepare dedicated high-traffic test environments (e.g., local Speedtest servers, continuous streaming tabs) to properly validate telemetry counters and visually demonstrate hardware blocking effects during future demos (UAT-001).

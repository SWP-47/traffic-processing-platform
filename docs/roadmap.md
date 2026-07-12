# Project Roadmap

This document outlines the Sprint-by-Sprint delivery plan for the Traffic Processing Platform.

*Last updated: July 12, 2026*

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

## Sprint 4: Trial Release, Stability Fixes, and Handover Preparation

**Milestone:** [Sprint 4 Milestone](https://github.com/SWP-47/traffic-processing-platform/milestone/4)

**Dates:** July 6 to July 12, 2026

**Sprint Goal:** Deliver a stable Week 6 trial release (MVP v3 candidate), resolve critical hardware stability issues, introduce detailed host statistics, and prepare the initial customer handover documentation.

**Focus / Expected Outcome:**
Resolve the critical CN/CnSS crash triggered by physical network cable disconnects, ensuring the test stand recovers gracefully. Achieve 70% automated backend test coverage and implement protocol-aware telemetry aggregation in TimescaleDB. Deliver the first iteration of the detailed host statistics page in the MUI. Draft the customer handover documentation.

**Linked Planned Items:**

*User Stories:*

- [US-006: Specific IP Traffic Analysis](https://github.com/SWP-47/traffic-processing-platform/issues/96) (Initial detailed host statistics page implementation)
- [US-013: Historical Traffic Statistics Storage](https://github.com/SWP-47/traffic-processing-platform/issues/97) (Protocol-aware aggregation and backend test coverage)

*Supporting PBIs:*

- **Physical Stand Stability:** Fix the CN/CnSS state corruption/crash when a network interface is physically disconnected and reconnected (UAT-003).
- **Backend Test Coverage & Protocol Aggregation:** Write integration and unit tests to reach 70% backend coverage. Implement protocol binding in the 1-second real-time telemetry aggregation buckets.
- **MUI Detailed Host Statistics:** Implement the first version of the detailed host statistics page, displaying packet transfer stats, historical graphs, and destination addresses.
- **Handover Documentation:** Draft `docs/customer-handover.md` with initial deployment and usage instructions.

---

## Sprint 5: Final Maintenance, Byte-Volume Metrics, and MVP v3 Transition

**Milestone:** [Sprint 5 Milestone](https://github.com/SWP-47/traffic-processing-platform/milestone/5)

**Dates:** July 13 to July 19, 2026

**Sprint Goal:** Incorporate customer feedback from the Week 6 trial, implement byte-volume counting, automate deployment, finalize handover documentation, and deliver the final `MVP v3` release.

**Focus / Expected Outcome:**
Respond to the customer's request for more globally useful network metrics by implementing byte-volume counting (sum of packet sizes) in the backend and adding a UI toggle in the MUI. Automate the database migration process to simplify server deployment. Deploy the previously written fragmented packet fix to the physical FPGA stand to enable live hardware blocking demonstrations. Investigate the 250 Mbps queue overflow, document the maximum stable throughput, and finalize the customer handover documentation to complete the product transition.

**Linked Planned Items:**

*User Stories:*

- [US-016: Byte Volume Counting](https://github.com/SWP-47/traffic-processing-platform/issues/104) (Implement byte-volume counting and MUI toggle)
- [US-017: Traffic Blocking / Dropping](https://github.com/SWP-47/traffic-processing-platform/issues/105) (Deploy fragmented packet fix to physical FPGA stand)

*Supporting PBIs:*

- **Byte-Volume Counting Backend & API:** Implement packet size aggregation in the TimescaleDB telemetry buckets and update the API endpoints to expose bytes/second.
- **MUI Byte/Packet Toggle:** Add a UI toggle in the MUI dashboard to switch between "Packets per second" and "Bytes per second" views.
- **Deployment Automation:** Update the deployment/startup script to automatically wait for database readiness and execute migration commands, removing the need for manual DB migrations.
- **FPGA Fragmented Packet Fix Deployment:** Deploy the fix for fragmented packets during hardware blocking to the physical test stand and verify live blocking.
- **Throughput Limits & Handover Finalization:** Investigate the CN/CnSS queue overflow at >200 Mbps. Update `docs/customer-handover.md` to explicitly state the maximum supported stable throughput and finalize all transition documentation for `MVP v3`.

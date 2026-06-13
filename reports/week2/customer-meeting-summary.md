# Customer Meeting Summary

**Date:** June 12, 2026

## Participants

* **Project Manager**: @jinseisieko
* **Technical Writer**: @arinamnova
* **Frontend Lead**: @Minnezing
* **Core Systems Engineer**: @Rena-ln

## Artifacts Demonstrated

1. **Draft User Stories Document**: Initial list of requirements with unique IDs and MoSCoW priorities.
2. **Technical Architecture Diagram**: Proposed MVP setup illustrating the Traffic Processor (FPGA + Laptop), Communication Node, and CnSS Server.
![system-architecture-diagram](/reports/week2/images/system-architecture-diagram.png)
3. **Management User Interface (MUI) Mockup**: Proposed MVP dashboard, including channel activity indicators, Rx/Tx rate graphs, host statistics, packet metadata views, and security monitoring concepts.
![mui-mvp-dashboard-prototype](/reports/week2/images/mui-mvp-dashboard-prototype.png)

## Discussion Points

* **Licensing & Publication**: Confirmed customer consent for the public MIT-licensed development model and cosent to publish the meeting transcript.
* **MoSCoW Prioritization**: Confirmed Must, Should, and Could priorities relative to the MVP v1 scope.
* **User Story Clarifications**:
  * **US-006 (Specific IP Traffic Analysis)**: Customer suggested adding "port" to the IP address selection to analyze specific socket connections.
  * **US-010 (Protocol Type Traffic Filtering)**: Clarified that "filtering" refers strictly to UI/display filtering on the dashboard, not active traffic modification or dropping.
  * **US-005 & US-007 (Invisible Deployment / No Slowdown)**: Clarified that "invisible deployment" implies a modular, non-monolithic architecture where component failures do not disrupt the main traffic flow. "No noticeable slowdown" should be achieved via direct wire/media passing (US-009) rather than strict numerical speed benchmarks.
  * **US-014 (Remote MUI Access)**: Customer advised rephrasing "via the internet" to "via a global network" to accurately reflect the university local network server constraints.
  * **US-002 (Basic Network Usage Statistics)**: Discussed the complexity of exact byte counting and timestamping. Agreed that for MVP, exact per-packet timestamps are not critical and can be applied homogeneously at the database (CnSS) recording level.
* **MUI Dashboard Feedback**: Customer recommended prioritizing the display of active client counts (MAC/IP addresses) over raw protocol lists. Historical statistics for MVP can be handled dynamically on the frontend to avoid backend database complexity.
* **Advanced Features (Packet Capture & Security)**:
  * Full packet capture and export (Network Analyzer functionality) was discussed. Customer noted this is a valuable but complex feature, suitable for future iterations rather than MVP.
* **Security Monitoring**: Customer validated the idea of tracking SYN packet ratios for flood detection (US-008) and suggested adding monitoring for atypical connections/ports (e.g., SSH on non-standard ports) as a future `Could Have` feature.

## Decisions

1. The customer explicitly approved the documented user stories, their MoSCoW priorities, and the initial proposed MVP v1 scope.
2. **US-015** (Real-time MUI Dashboard Updates) was downgraded from `Must Have` to `Should Have`, as manual refreshing (F5) is acceptable for the initial MVP.
3. Byte volume counting was separated from US-002 into a new **US-016** (`Should Have`), as it is a prerequisite for US-011 (Throughput Values Display).
4. Four new `Could Have` user stories were added to the backlog based on customer feedback: **US-017** (Traffic Blocking), **US-018** (Traffic Tunneling), **US-019** (Packet Metadata Capture), and **US-020** (Atypical Connection Monitoring).

## Action Points

* [x] Update `reports/week2/user-stories.md` with refined wording, adjusted priorities, and newly added stories (Completed: see `user-stories-new.md`).
* [x] Refine the MUI prototype to increase the visual hierarchy of Tx/Rx rates and emphasize client counts over raw protocol lists. [See: Updated Figma Prototype](https://www.figma.com/design/pbN9YeX8NosxN7wQgAeXbe/Traffic-Processor-App?node-id=119-268&t=CWDKMx5dmF0WB8DI-1)

## Risks

* **Latency and Timestamp Accuracy**: The proposed architecture (FPGA + Laptop for Traffic Processor) may introduce variable latency.  
  *Mitigation*: The customer agreed that for the MVP, homogeneous delay in timestamp application at the database recording level is acceptable.
* **Scope Creep via Advanced Analysis**: Full packet capture, export, and deep inspection are technically complex and resource-intensive.  
  *Mitigation*: Explicitly categorized these as `Could Have` / Backlog items to protect the MVP v1 scope and timeline.

## Feedback

The customer validated the overall product direction, stating that the proposed MVP scope is realistic, well-structured, and aligned with project goals. The customer provided highly constructive, minor wording improvements to ensure technical accuracy (e.g., "global network" vs. "internet").

## Customer Approvals

* [x] **Documented User Stories**: Approved.
* [x] **MoSCoW Priorities**: Approved.
* [x] **Initial Proposed MVP v1 Scope**: Approved.
* [x] **MIT License Consent**: Approved

## Resulting Changes & Links

The following artifacts were updated as a direct result of this meeting:

* **Updated User Stories Document**: [user-stories.md](user-stories.md#us-001-channel-activity-indicator)
* **Affected User Stories**:
  * **Refined Notes/Constraints**: [US-001](user-stories.md#us-001-channel-activity-indicator), [US-002](user-stories.md#us-002-basic-network-usage-statistics), [US-004](user-stories.md#us-004-modular-platform-integration), [US-005](user-stories.md#us-005-invisible-traffic-analyzer-deployment), [US-007](user-stories.md#us-007-uninterrupted-internet-access), [US-009](user-stories.md#us-009-seamless-bidirectional-packet-passing), [US-014](user-stories.md#us-014-remote-mui-access)
  * **Refined Scope/Notes**: [US-006](user-stories.md#us-006-specific-ip-traffic-analysis), [US-010](user-stories.md#us-009-seamless-bidirectional-packet-passing), [US-013](user-stories.md#us-013-historical-traffic-statistics-storage), [US-003](user-stories.md#us-003-traffic-information-export), [US-008](user-stories.md#us-008-syn-flood-attack-detection), [US-011](user-stories.md#us-011-throughput-values-display)
  * **Priority Changed**: [US-015](user-stories.md#us-015-real-time-mui-dashboard-updates) (`Must Have` → `Should Have`)
  * **Newly Added Stories**: [US-016](user-stories.md#us-016-byte-volume-counting), [US-017](user-stories.md#us-017-traffic-blocking--dropping), [US-018](user-stories.md#us-018-traffic-tunneling--allowing), [US-019](user-stories.md#us-019-packet-metadata-capture-and-view), [US-020](user-stories.md#us-020-atypical-connection--port-monitoring)
* **Interface Prototype**: [Figma Prototype](https://www.figma.com/design/pbN9YeX8NosxN7wQgAeXbe/Traffic-Processor-App?node-id=119-268&t=CWDKMx5dmF0WB8DI-1)
* **MVP v0 Report**: [mvp-v0-report.md](mvp-v0-report.md)
* **Customer Meeting Transcript**: [customer-meeting-transcript.md](customer-meeting-transcript.md)

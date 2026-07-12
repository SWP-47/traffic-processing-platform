# Sprint 4 Review Summary (Week 6)

**Date:** July 11, 2026  
**Sprint:** Sprint 4 (Week 6 Trial Release / MVP v3 Candidate)  
**Location:** Physical Test Stand & Remote  

## Participants

* @arinamnova (Project Manager / Scrum Master)
* @jinseisieko (Backend Lead)
* @Rena-ln (Core Systems Engineer)
* @Minnezing (Frontend Lead)
* Customer

## Artifacts Demonstrated

* **Week 6 Trial Release:** Physical test stand (Traffic Processor & Communication Node) and deployed CnSS/MUI.
* **MUI Dashboard:** New detailed host statistics page and button-based filtering.
* **Handover Documentation:** Draft of `docs/customer-handover.md` and deployment instructions.

## Scope / Goal Reviewed

The goal of this Sprint Review was to demonstrate the Week 6 trial release (MVP v3 candidate), validate the physical test stand's reliability under real-world conditions, review the customer-facing handover documentation, and assess transition readiness. The team also conducted live User Acceptance Testing (UAT) and stress testing with the Customer.

## Feedback & Observations

### 1. Metric Measurement Asymmetry (Packets vs. Bytes)

* **Observation:** During a live streaming test (online radio via TCP), the Customer noted that the MUI showed nearly identical RX and TX *packet* counts, despite TCP streaming being highly asymmetric (large data packets incoming, small ACK packets outgoing).
* **Root Cause:** The system currently measures and displays metrics strictly by the *number of packets*, not by data volume.
* **Customer Feedback:** Displaying metrics in bits/bytes per second is globally more useful for network analysis than packet counts. Since the backend already stores packet headers (including sizes), the Customer suggested aggregating the sum of packet sizes per bucket.
* **Team Response:** Backend Lead confirmed this is highly feasible and requires minimal backend changes. The team agreed to prioritize this over the remaining UI map features.

### 2. System Stability Under Extreme Load

* **Observation:** The Customer performed an ad-hoc stress test using a heavy download, pushing traffic to ~30 MB/s (~240-250 Mbps).
* **Result:** The system crashed/hung. Core Systems Engineer identified via logs that the CN/CnSS queue overflowed.
* **Customer Feedback:** While 250 Mbps is an extreme edge case, the team must investigate the queue limits. If the system cannot handle 250 Mbps, the handover documentation must explicitly state the maximum stable throughput (e.g., "Rated for 100 Mbps"). This was marked as a "nice to have" but necessary for operational transparency.

### 3. Hardware Blocking Bug

* **Observation:** Previous issues with the physical stand disconnecting/reconnecting were successfully resolved. However, a bug causing fragmented packets during hardware blocking was fixed in the codebase but not yet deployed to the physical FPGA stand. Therefore, live hardware blocking was not demonstrated today.

### 4. Deployment & Handover Documentation

* **Observation:** The PM presented the draft `docs/customer-handover.md`. The Customer found the high-level instructions clear but noted that deep-diving will be required.
* **Customer Feedback:** Backend Lead highlighted that server deployment is currently complex due to manual database migrations. The Customer advised automating this by adding a startup script that waits for database readiness and automatically executes the migration commands.

## Approvals or Requested Changes

* **Requested Change:** Implement byte-volume counting (sum of packet sizes) in the backend and expose it via the API.
* **Requested Change:** Add a UI toggle in the MUI to switch between "Packets per second" and "Bytes per second" views.
* **Requested Change:** Automate the database migration process within the deployment/startup script.
* **Approval:** The Customer approved the overall architecture and the direction of the handover documentation, pending the deployment automation updates.

## Risks

* **Throughput Limits:** The CN/CnSS pipeline currently fails at ~250 Mbps due to queue overflow. If the Customer's environment approaches this limit, the system will fail silently. We must define and document the hard limits.
* **Sprint 5 Timebox:** Implementing the byte-counting feature, updating the MUI, and finalizing the deployment scripts must be completed in Week 7 (Sprint 5) before the final `MVP v3` handover.

## Action Points

1. **Backend:** Implement packet size aggregation in the TimescaleDB telemetry buckets and update the API endpoints.
2. **Frontend:** Update the MUI dashboard to display bytes/second and implement a toggle switch between packet counts and byte volumes.
3. **DevOps/Core:** Deploy the fragmented packet fix to the physical FPGA stand and verify hardware blocking live.
4. **DevOps:** Update the deployment/startup script to automatically handle database readiness checks and run migrations.
5. **Documentation:** Update `docs/customer-handover.md` to explicitly state the maximum supported throughput and include the new automated deployment steps.

## Resulting Backlog / Scope Changes

* **Added to Sprint 5 Backlog:**
  * PBI: Implement byte-volume counting and MUI toggle (Prioritized over host map).
  * PBI: Automate DB migrations in deployment script.
  * PBI: Investigate CN/CnSS queue overflow at >200 Mbps and document max stable throughput.
* **Deferred/Removed from current scope:** Detailed host map visualization (deferred to post-course backlog to make room for byte-counting).

## Evidence & Links

* [Sprint 4 Milestone](https://github.com/SWP-47/traffic-processing-platform/milestone/4)
* [Week 6 SemVer Release] PLACEHOLDER
* [`docs/customer-handover.md`](../../docs/customer-handover.md)
* [UAT Public Result Summary](../../docs/user-acceptance-tests.md)

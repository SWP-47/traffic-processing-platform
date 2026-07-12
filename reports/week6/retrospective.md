# Sprint 4 Retrospective (Week 6)

## What went well

* **Physical Stand Stability:** The critical crash from Week 5, which occurred when physically disconnecting and reconnecting network cables, was completely resolved. The Communication Node and CnSS now handle physical interface drops gracefully and recover without requiring manual service restarts.
* **Backend Quality and Coverage:** We successfully achieved 70% automated backend test coverage. Writing extensive integration and unit tests for the new TimescaleDB and Redis pipeline gave us high confidence in the protocol-aware telemetry aggregation.
* **Proactive Customer Engagement:** The customer didn't just passively watch the demo; they actively stress-tested the system (pushing ~250 Mbps) and tested asymmetric TCP streaming (online radio). This yielded incredibly valuable, real-world feedback that directly shaped our Sprint 5 backlog.
* **Handover Documentation Drafting:** Creating the first draft of `docs/customer-handover.md` was highly effective. Walking the customer through it immediately exposed the manual database migration bottleneck, allowing us to identify and plan a fix for the transition blockers before the final handover.

## What did not go well

* **Hardware Deployment Gap:** We wrote the code fix for the fragmented packet bug (which causes broken packets during hardware blocking), but we failed to flash it to the physical FPGA board before the Week 6 meeting. Because of this, we had to intentionally skip the live hardware blocking demonstration to avoid showing broken behavior.
* **Unknown Throughput Limits:** During the customer's ad-hoc stress test (~30 MB/s or ~240 Mbps), the CN/CnSS queue overflowed and the system hung. We had not previously investigated or documented our maximum stable throughput, leaving a blind spot in our operational transparency.
* **Metric Misalignment:** We spent significant effort refining packet-per-second counters, only for the customer to point out that packet counts are highly misleading for asymmetric TCP traffic. We should have anticipated the need for byte-volume counting earlier, as it is the industry standard for network analysis.

## What the team changed or attempted to change based on the previous Sprint Retrospective, and what results they observed

* **Previous Action Point (from Sprint 3):** "Stabilize the edge deployment and increase backend test coverage following the massive Sprint 3 microservice and database redesign."
* **Observed Results:** This was highly successful. The edge deployment is now robust against physical tampering (cable disconnects no longer crash the system). Furthermore, the backend test coverage jumped to 70%, and our new integration tests caught several edge cases in the TimescaleDB bucketing logic before they reached production. The decoupled architecture introduced in Sprint 3 is now proven to be stable under normal operational loads.

## Action points

1. **Automate Database Migrations:** Update the deployment/startup script to automatically wait for database readiness and execute migration commands. This will eliminate the manual friction identified during the handover review and unblock the customer's ability to deploy the server independently.
2. Conduct stress testing to provide strict throughput limitation quidelines for the product.

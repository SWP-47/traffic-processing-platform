# Week 6 Reflection (Sprint 4)

## Learning points

* **Metric Relevance Over Mere Functionality:** During the Week 6 trial, the customer pointed out that displaying telemetry in *packets per second* is highly misleading for asymmetric protocols like TCP streaming (where large data packets flow in, but only small ACK packets flow out). We learned that simply having a working telemetry pipeline is not enough; the metrics displayed must align with industry standards (bytes/bits per second) to be genuinely useful to a network administrator.
* **The Necessity of Explicit Limitations:** When the customer performed an ad-hoc stress test (~250 Mbps), the system's queue overflowed and hung. We learned that if a system's maximum throughput limits are not explicitly investigated and documented, the customer will naturally assume it can handle their maximum network capacity. Transparency about system limits is crucial for operational trust.

## Validated assumptions

* **Physical Stand Robustness:** We assumed that resolving the Week 5 crash (caused by physically disconnecting the Ethernet cable) would stabilize the test environment. The Week 6 trial validated this; the physical stand now handles cable reconnects gracefully without requiring manual service restarts, proving the edge-deployment is robust enough for physical tampering.
* **Backend Architecture Scalability:** We assumed our TimescaleDB architecture and Redis buffering could handle complex, real-time bucketing. Achieving 70% backend test coverage and successfully demonstrating protocol-aware telemetry aggregation validated that our decoupled CnSS architecture is stable and performant under normal operational loads.
* **Customer Readiness for Trial:** We assumed the customer would be able to interact with the Week 6 trial release like a real product. This was validated when the customer independently initiated high-traffic scenarios (Wikipedia, online radio) and ad-hoc stress tests, providing deep, technical feedback that directly shaped our Sprint 5 backlog.

## Friction and gaps

* **Asymmetric Traffic Visualization Gap:** The most significant product gap identified during UAT-001 is the lack of byte-volume counting. The current packet-count metric caused confusion during the TCP streaming test, highlighting a gap between our current MVP capabilities and the customer's actual analytical needs.
* **Hardware-to-Software Deployment Gap:** We wrote the fix for the fragmented packet bug (UAT-005), but failed to flash it to the physical FPGA stand before the Week 6 meeting. This created a gap in our execution: we could not demonstrate live hardware blocking, forcing us to defer UAT-005. We need a smoother pipeline for deploying software fixes to physical hardware.
* **Undefined Throughput Limits:** We know the system breaks at ~250 Mbps due to queue overflow, but we lack data on the *safe, rated maximum throughput* (e.g., is it stable at 100 Mbps?). This gap leaves a risk for the customer if they deploy the system on a high-capacity link.

## Planned response

* **Implement Byte-Volume Counting (Sprint 5):** We will immediately pivot to implement packet size aggregation in the TimescaleDB telemetry buckets and expose this via the API. We will also add a UI toggle in the MUI to switch between "Packets per second" and "Bytes per second", directly addressing the customer's most critical feedback.
* **Deploy Hardware Fix & Complete UAT-005:** In Week 7, we will flash the fragmented packet fix to the physical FPGA stand and successfully execute the hardware blocking UAT to close this gap.
* **Investigate and Document Throughput Limits:** We will investigate the CN/CnSS queue overflow behavior, determine the maximum stable throughput, and explicitly document this limit (along with the new automated deployment steps) in the final `docs/customer-handover.md` for the `MVP v3` release.

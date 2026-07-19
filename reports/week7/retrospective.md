# Sprint 5 Retrospective (Week 7)

## What went well

* **Customer Handover & Acceptance:** The final transition was highly successful. The customer explicitly confirmed that the product is ready for independent use ("Yes, everything works. Excellent."), and the handover documentation was approved without major blockers.
* **Deployment Automation:** The interactive `make deploy` script completely eliminated the manual database migration bottleneck identified in Week 6. The customer found the automated environment setup, JWT generation, and test data seeding to be clear and easy to use.
* **Hardware Polish (Dynamic Blocking):** Replacing the hardcoded FPGA blocking IP with a dynamic CLI script (defaulting to `0.0.0.0`) worked flawlessly. We successfully demonstrated targeted traffic dropping (e.g., blocking a specific laptop or proxy IP) during the review.
* **Frontend UX Stabilization:** Implementing the 10-minute frontend state timeout for the "Top Hosts" table completely resolved the customer's complaint about IP addresses "jumping" too fast. The table is now stable, readable, and supports deep-dive clickable rows.
* **System Stability Under Load:** Following the Week 6 crash at ~250 Mbps, the team successfully optimized the CN/CnSS queues. The system was stress-tested and proven stable at 588 Mbps without hanging or dropping telemetry.

## What did not go well

* **Protocol Telemetry Limitations:** As highlighted by the customer, ICMP (ping) packets and other protocols without source/destination ports are currently ignored by the telemetry pipeline due to strict database typing. This means ping traffic is invisible in the port statistics.
* **Directional Metric Limits:** The "Top Ports" widget currently only aggregates the OUT (transmit) direction, which limits the depth of asymmetric traffic analysis.

## What the team changed or attempted to change based on the previous Sprint Retrospective, and what results they observed

* **Previous Action:** *Automate the server deployment process to remove manual DB migration steps.*
  * **Result:** **Highly Successful.** @jinseisieko developed the `make deploy` and cleanup scripts. The customer tested the workflow and confirmed it is now fully self-service.
* **Previous Action:** *Deploy the fragmented packet fix to the physical FPGA stand and enable dynamic IP blocking.*
  * **Result:** **Successful.** @Rena-ln deployed the fix and implemented the dynamic IP injection script. Live hardware blocking was verified during the Week 7 UAT and Sprint Review.
* **Previous Action:** *Investigate the CN/CnSS queue overflow crash (occurred at ~250 Mbps in Week 6) and document the maximum stable throughput.*
  * **Result:** **Successful.** The team optimized the queue handling and successfully stress-tested the system up to 588 Mbps. The ~600 Mbps theoretical ceiling was explicitly documented in the `docs/customer-handover.md` as a known limitation.

## Action points

*(Note: As this is the final sprint of the course, action points are focused on Demo Day preparation and final submission wrap-up.)*

1. **Demo Day Rehearsal & Timing:** Finalize the pre-recorded demo video to ensure it is strictly under 2 minutes and highlights the dynamic FPGA blocking and the new byte-volume toggle. Rehearse the full 7-minute presentation to ensure all team members smoothly transition between slides and stay within the time limit.
2. **Final repository polishing:** Check all documentation to make sure it is up to date. Close any remanining issues as not planned to show that the project is complete.

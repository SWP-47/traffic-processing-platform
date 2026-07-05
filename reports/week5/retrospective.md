# Sprint 3 Retrospective

## What the team changed or attempted to change based on the previous Sprint Retrospective, and what results they observed

In our Sprint 2 retrospective, we identified a need to standardize the deployment of our edge nodes (Traffic Processor and Communication Node) to reduce setup time, improve reproducibility, and isolate dependencies. We attempted to address this by fully containerizing the TP and CN using Docker.

**Result observed:** While the Docker configurations are now standardized and work well in isolated environments, we encountered unexpected friction when deploying them to the specific Ubuntu environment on the physical FPGA test stand. The containers did not seamlessly interact with the physical network interfaces during the live demo, requiring manual workarounds to get the hardware blocking and telemetry flowing. We also introduced `pip-audit` for dependency vulnerability scanning in CI, which successfully passed and improved our security posture without adding significant pipeline overhead.

## What went well

* **Scalable Backend Architecture:** The complete redesign of the CnSS into four decoupled components (Database, REST, UDP Listener, WebSocket) with Redis buffering proved highly effective. The system comfortably handled 100 Mbps stress tests without optimization, and the 1Hz Reporting Worker successfully offloaded heavy aggregation from the main event loop.
* **MUI Dashboard Responsiveness:** The frontend redesign successfully implemented the customer's requested toggle between raw numerical RX/TX rates and visual column charts. This significantly improved data readability and addressed prior feedback about visual clutter.
* **Hardware Traffic Blocking:** The implementation of physical traffic blocking via the FPGA `Key1` button functionally achieved its goal. Pressing the button successfully dropped traffic at the IP level and provided immediate visual feedback via the board's LED, demonstrating the hardware-software integration.

## What did not go well

* **Physical Layer Fault Tolerance:** During UAT-003, disconnecting the Ethernet cable to test inactive host marking caused the CN/CnSS pipeline to experience state corruption and stop transmitting entirely. The customer noted that a component "got tired" and the system required a manual restart. This highlighted a critical gap in our software fault tolerance regarding physical layer disruptions.
* **UI/UX Friction in Filtering:** To meet the sprint goal for the new host statistics table, we implemented a quick text-based filtering syntax. The customer immediately identified this as poor UX compared to the structured sidebar filters used elsewhere in the application, noting that strict text syntax is not user-friendly. We prioritized speed of implementation over user-centric design.
* **Real-Time Reactivity vs. Aggregation:** The historical line chart appeared as a flatline during the hardware blocking test (UAT-002). The 5-minute aggregation window smoothed out rapid, real-time changes, failing to visually reflect the immediate impact of pressing the physical blocking button. The customer requested a 1-minute/5-minute minimum time window toggle for near real-time observation.
* **Hardware Polish (Contact Bounce):** The physical `Key1` button suffers from contact bounce (debounce), causing multiple unintended state toggles when pressed. This degraded the demonstration experience and requires a software/hardware debounce fix.
* **Test Environment Limitations:** The university network segment provided very low traffic (~3 packets/second), making it difficult to visually demonstrate the macroscopic effects of hardware blocking or properly validate telemetry counters during the UAT. The customer correctly questioned if the values were hardcoded constants due to the lack of active high-traffic scenarios.
* The Frontend and Backend lead discovered that they do not understand how to implement data aggregation.

## Action points

1. **Implement Graceful Physical Fault Tolerance:** Investigate and resolve the CN/CnSS state corruption crash triggered by physical network interface disconnects. The system must implement graceful error handling and state recovery so that telemetry transmission automatically resumes when the interface is reconnected, without requiring a manual service restart.
2. **Refine MUI Filtering and Prepare High-Traffic UAT Environments:** Redesign the host table filtering UI to replace the raw text-field syntax with structured sidebar/dropdown controls (e.g., tags, min/max bounds for RX/TX, subnet selectors). Additionally, prepare dedicated high-traffic test environments (e.g., local Speedtest servers, continuous streaming/radio tabs) for the next UAT session to properly validate counters and visually demonstrate the effects of hardware blocking.
3. Discuss best approach to implement aggregation with customer.

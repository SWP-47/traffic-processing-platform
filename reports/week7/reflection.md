# Week 7 Reflection (Sprint 5)

## Learning points

* **Deployment Automation is Critical for Handover:** Developing the interactive `make deploy` script and the environment cleanup script taught us that a product is only truly "ready for independent use" when the customer can spin it up without developer intervention. Automating the DB migrations, JWT secret generation, and container networking removed the biggest bottleneck to customer adoption.
* **Decoupling Data Fetching from UI State:** The customer's feedback regarding "jumping" IP addresses in the Top Hosts table highlighted a crucial UX lesson. Just because data updates every second doesn't mean the UI should reflect that volatility. Implementing a frontend state management layer with a 10-minute timeout for stale entries transformed a chaotic, unreadable table into a stable, professional administrative tool.
* **Hardware Intervention Requires Dynamic Tooling:** Hardcoding the blocked IP on the FPGA was a viable MVP v2 prototype, but MVP v3 required dynamic CLI tooling. Learning to inject the target IP dynamically (defaulting to `0.0.0.0`) made the hardware blocking feature actually usable for a network administrator targeting specific devices or services.
* **Asymmetric Traffic Demands Byte-Level Metrics:** The customer's validation of the byte-volume toggle confirmed that packet counts are largely insufficient for analyzing modern TCP streams (like online radio or large downloads), where ACK packets skew the visual representation of network load.

## Validated assumptions

* **System Stability Ceiling:** In Week 6, the system crashed at ~250 Mbps due to queue overflow. We assumed this might be a hard architectural limit. However, after optimizing the CN/CnSS queues in Sprint 5, we successfully stress-tested the system to 588 Mbps. This validated that our telemetry pipeline is highly robust for standard university/enterprise network segments, even if a theoretical ceiling exists.
* **Customer's Definition of "Useful":** We assumed that providing deep, granular data was the primary goal. The customer's explicit confirmation ("Yes, everything works. Excellent.") and positive reaction to the simplified, automated deployment and stable UI validated that *usability* and *reliability* are just as critical as raw feature depth for a handover product.
* **Iterative Documentation Works:** Drafting the `docs/customer-handover.md` in Week 6 and refining it based on the customer's trial feedback in Week 7 proved to be the right approach. The customer felt confident accepting the handover because the documentation evolved alongside the product's actual deployment mechanics.

## Friction and gaps

* **Protocol Telemetry Limitations (ICMP/Ping):** Due to strict database typing and our telemetry schema, packets without source/destination ports (like ICMP) are currently ignored. The customer noted this, and while we explained the technical constraint, it remains a gap in the platform's comprehensive monitoring capabilities.
* **Directional Metric Limits:** The "Top Ports" widget currently only aggregates the OUT (transmit) direction. This limits the depth of asymmetric traffic analysis and was a missed opportunity to fully map bidirectional port usage.
* **Network Environment Instability:** During the final review, the university router/network segment experienced unexpected lag, which momentarily complicated the live demonstration of streaming and blocking, though the core FPGA logic remained sound.

## Planned response

* **Demo Day Execution:** For the Week 8 Demo Day, we will rely heavily on our pre-recorded, sanitized demo video to bypass live network instability and strictly adhere to the 7-minute time limit. We will ensure the video clearly highlights the dynamic FPGA blocking and the new byte-volume toggle.

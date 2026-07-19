# Sprint Review Summary (Week 7 / Sprint 5)

**Date**: July 18, 2026  
**Sprint**: Sprint 5 (Week 7)  
**Sprint Goal**: Implement byte-volume counting, deliver final maintenance, transition-readiness improvements, and finalize the customer handover for `MVP v3`.

## Participants

* **Project Manager / Backend Lead**: @jinseisieko
* **Frontend Lead**: @Minnezing
* **Core Systems Engineer**: @Rena-ln
* **Technical Writer**: @arinamnova

## Scope & Artifacts Demonstrated

The team demonstrated the final `MVP v3` increment, focusing on DevOps automation, UI/UX refinements based on previous feedback, and hardware-level traffic management.

**Artifacts & Features Demonstrated:**

1. **Frontend Enhancements**:
   * **Automatic Token Refresh**: Session preservation across page reloads without requiring manual re-login.
   * **Traffic Unit Toggle**: Ability to switch statistics display between packets per second and bytes/bits per second.
   * **Interactive Host Tables**: Clickable host rows revealing detailed statistics (Top Destinations, Top Ports).
2. **DevOps & Deployment Automation**:
   * **Interactive Deployment Script (`make deploy`)**: Automates container startup, DB migrations, `.env` setup, JWT secret generation, and optional test data population.
   * **CLI User Management**: Script to dynamically create admin/viewer users.
   * **Environment Cleanup**: Script to safely wipe production environments (containers, networks, volumes).
3. **Core Systems / Hardware**:
   * **Dynamic IP Blocking**: Replaced hardcoded IP blocking with a script allowing dynamic IP targeting on the FPGA board (default `0.0.0.0` means no blocking).
   * **Stress Testing**: Demonstrated system stability under heavy load (withstood 588 Mbps without freezing, though the traffic generation utility acted as a bottleneck).
4. **Documentation**:
   * Reviewed the updated [`docs/customer-handover.md`](../../docs/customer-handover.md), specifically the new `make deploy` instructions.

## Feedback, Discussions & Decisions

### 1. UI/UX: Data Aggregation & Table Synchronization

* **Discussion**: The customer noted confusion regarding the difference in aggregation times between the historical chart (10-minute window) and the real-time host tables (1-second window).
* **Decision**: The team and customer agreed on a frontend-side state management solution. The frontend will request new data every second, update metrics for existing IPs, and automatically remove IPs from the table if they have not updated for more than 10 minutes. This avoids complex backend query changes while providing a logical UI experience.

### 2. Protocol Limitations (ICMP / Ping)

* **Discussion**: The customer asked if Ping (ICMP) packets would be displayed. The team clarified that due to strict typing, protocols without source/destination ports are currently ignored in the port statistics.
* **Decision**: Acknowledged as a current system limitation. Fixing this would require DB schema and parsing logic changes, which are out of scope for the final `MVP v3` handover but noted for future iterations.

## Approvals & Handover Confirmation

* **Customer-Facing Documentation**: The customer reviewed the updated `docs/customer-handover.md` and the interactive deployment scripts, confirming the instructions are clear and sufficient.
* **Handover Level Reached**: **`Ready for independent use`**
* **Customer-Confirmation Status**: **`Accepted`**
  *(The customer explicitly confirmed: "Yes, everything works. Excellent." when asked if the product is ready for independent use and if the handover documentation is sufficient).*

## Risks & Known Limitations

* **Network Instability during Demo**: Minor physical network/cable instability occurred during the live demonstration, causing a brief disconnect between the laptop and router. This was an environmental issue, not a product defect.
* **ICMP/Portless Protocols**: As discussed, portless protocols are filtered out of the detailed statistics.
* **Stress Test Tooling**: The internal traffic generation utility bottlenecked at ~588 Mbps, meaning the absolute maximum throughput limit of the FPGA/CnSS pipeline remains theoretically higher but untested with this specific tool.

## Action Points & Backlog Updates

| Action Item | Owner | Status / Target |
| :--- | :--- | :--- |
| **Frontend Table State Management**: Implement the agreed 10-minute timeout logic for the Host Details table on the frontend side. | @Minnezing | Sprint 5 / MVP v3 |

## Resulting Backlog / Scope Changes

* **Added/Refined PBI**: Frontend state management for Host Details table (10-minute inactivity timeout).
* **Deferred/Out of Scope**: ICMP/Ping protocol parsing and display (deferred to post-course future work).
* **Completed**: All MVP v3 transition and handover documentation requirements.

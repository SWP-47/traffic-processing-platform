# User stories

## US-001: Channel Activity Indicator

**Requirement Status:** Active\
**MoSCoW priority:** Must Have

As a system administrator,\
I want to see a simple indicator of channel activity\
so that I can quickly see if a connection is active.

> Suggestion: place indicator at the very top of the dashboard for immediate visibility.

---

## US-002: Basic Network Usage Statistics

**Requirement Status:** Active\
**MoSCoW priority:** Must Have

As a system administrator,\
I want to see how many packets are passing through the channel,\
so that I can gather basic network usage statistics.\

> For the MVP, exact per-packet timestamps are not critical. Timestamps can be applied at the database recording level (e.g., CnSS) as long as the delay in applying them is homogeneous/consistent.

---

## US-004: Modular Platform Integration

**Requirement Status:** Active\
**MoSCoW priority:** Must Have

As a system administrator,\
I want to integrate the platform to existing network by parts\
so each component can be easily deployed in any place.

> For MVP: Traffic Processor and Control Server can run as separate virtual components on the same physical hardware (e.g., a single laptop) to simplify the initial testbed setup.

---

## US-005: Invisible Traffic Analyzer Deployment

**Requirement Status:** Active\
**MoSCoW priority:** Must Have

As a network user,\
I want the deployment of the traffic analyzer to be completely\ invisible to both me and my router,
so that my internet access is not disrupted.

> "invisible deployment" means a modular, non-monolithic system architecture. If any component (other than the core traffic processor/router) fails, it must not disrupt the main traffic flow, and components must be able to be restarted or replaced independently.

---

## US-007: No Noticeable Network Slowdown

**Requirement Status:** Active\
**MoSCoW priority:** Must Have

As an end user,\
I want the traffic analyzer to operate without noticeably slowing down my network speed,\
so that my internet access isn't disrupted.

> Specify "noticeably"
>
> The analyzer's operation must not disrupt, break, or negatively impact the user's internet access or connectivity to external resources

---

## US-009: Seamless Bidirectional Packet Passing

**Requirement Status:** Active\
**MoSCoW priority:** Must Have

As a system administrator,\
I want the Traffic Processor to seamlessly pass network packets in both directions,\
so that the primary internet connection remains fully functional.

> Physical packet forwarding should be handled by a direct wire/media connection.

---

## US-014: Remote MUI Access

**Requirement Status:** Active\
**MoSCoW priority:** Must Have

As a system administrator,\
I want to access the MUI from anywhere via a global network,\
so that I can monitor a closed local network remotely.

---

## US-006: Specific IP Traffic Analysis

**Requirement Status:** Active\
**MoSCoW priority:** Should Have

As an Information Security specialist,\
I want to be able to select a specific IP address and port and view all its traffic,\
so that I can quickly understand what a particular computer on the network is doing and detect any suspicious activity originating from it.

---

## US-013: Historical Traffic Statistics Storage

**Requirement Status:** Active\
**MoSCoW priority:** Should Have

As a system administrator,\
I want the server to save traffic statistics to a database,
so that I can view historical data and not just the current real-time state.

> For MVP: historical statistics (e.g., data from the last 30 minutes) can be temporarily accumulated and stored dynamically on the frontend (MUI) instead of the backend.

---

## US-015: Real-time MUI Dashboard Updates

**Requirement Status:** Active\
**MoSCoW priority:** Should Have

As a system administrator,\
I want the MUI dashboard to update automatically in real-time without manual refreshing,\
so that I always see the current state of the channel.

---

## US-003: Traffic Information Export

**Requirement Status:** Active\
**MoSCoW priority:** Could Have

As a system administrator,\
I want to export all brief information which the system got from the traffic as a single file\
so that I can analyse it and find critical network vulnerabilities.

> Capturing and exporting full packet data is difficult to realize, low priority feature.

---

## US-008: SYN Flood Attack Detection

**Requirement Status:** Active\
**MoSCoW priority:** Could Have

As an Information Security specialist,\
I want the system to count how many SYN packets (handshake requests) arrive and how many of them actually receive responses,\
so that I can detect attempts to overwhelm the network with thousands of empty requests (SYN flood attacks).

> Suggested three-step approach for security monitoring:
>
> 1. Monitor the ratio of SYN packets to detect general network health and potential overloads.
> 2. If the counters breach a threshold, trigger a visual alert on the dashboard.
> 3. Allow the user to click the alert, view detailed packet metadata, and eventually apply blocking rules (tied to the traffic blocking/tunneling stories).

---

## US-010: Protocol Type Traffic Filtering

**Requirement Status:** Active\
**MoSCoW priority:** Could Have

As a system administrator,\
I want to filter the traffic display by protocol type (TCP, UDP, ICMP),\
so that I can focus analysis on specific communication types.

> "filtering" means for UI/display purposes on the dashboard

---

## US-011: Throughput Values Display

**Requirement Status:** Active\
**MoSCoW priority:** Could Have

As a system administrator,\
I want the interface to show average, minimum, and maximum throughput values,\
so that I can understand network capacity utilization.

> Calculation of minimum, average, and maximum throughput values is directly dependent on accurately counting byte volumes. Implement together with US-016.

---

## US-012: Basic Password Protection for MUI

**Requirement Status:** Active\
**MoSCoW priority:** Could Have

As a system administrator,\
I want the web interface (MUI) to be protected by a basic password,\
so that unauthorized users cannot view the network statistics.

---

## US-016: Byte Volume Counting

**Requirement Status:** Active\
**MoSCoW priority:** Should Have

As a system administrator,\
I want to see how many bytes are passing through the channel,\
so that I can gather more detailed network usage statistics.

---

## US-017: Traffic Blocking / Dropping

**Requirement Status:** Active\
**MoSCoW priority:** Could Have

As an Information Security specialist,\
I want the system to be able to block or drop specific parts of the traffic,\
so that I can mitigate threats or enforce network policies.

---

## US-018: Traffic Tunneling / Allowing

**Requirement Status:** Active\
**MoSCoW priority:** Could Have

As a system administrator,\
I want the system to allow specific traffic through a tunnel,\
so that I can securely route or bypass certain network segments.

---

## US-019: Packet Metadata Capture and View

**Requirement Status:** Active\
**MoSCoW priority:** Could Have

As a system administrator or security specialist,\
I want to continuously capture and view packet metadata (and potentially full packets with advanced filters),\
so that I can perform deep packet inspection and logical analysis similar to a network analyzer.

---

## US-020: Atypical Connection / Port Monitoring

**Requirement Status:** Active\
**MoSCoW priority:** Could Have

As an Information Security specialist,\
I want the system to monitor for and alert on atypical connections (e.g., standard protocols running on non-standard ports),\
so that I can detect suspicious or unauthorized tunneling activity.

> Difficult to implement. Low priority, more for the Backlog.

---

## Initial proposed MVP v1 scope

All "Must Have" user stories:

* US-001
* US-002
* US-004
* US-005
* US-007
* US-009
* US-014

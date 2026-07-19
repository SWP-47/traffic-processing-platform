# User Acceptance Tests (UAT)

This document defines the end-user-facing scenarios that customers or relevant stakeholders execute to inspect whether the Traffic Processing Platform supports intended user goals.

*Note: UAT IDs must remain stable. If a scenario needs clarification, edit it in place. If it becomes obsolete, mark it `Retired`. If the user goal changes materially, create a new ID.*

---

## UAT-001: Assessment of the current channel load

**Scenario Status:** Active

**User Goal:**
As a network administrator, I want to quickly and accurately count the numeric values of RX/TX rate in order to understand the actual channel load.

**Preconditions:**

- CnSS and MUI are working, TP/CN are sending telemetry
- The user is logged in to the account
- A channel has been selected

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | Open the dashboard and look at the RX/TX bar chart. | Two columns are visible, the bar height reflects the current load in one direction. |
| 2 | Switch the widget to the numerical mode (click on the hashtag icon in the right top corner). | The column bars disappear, and large numbers of RX and TX rate appear and display current channel load in pkt/s. |

### UAT-001 Execution Results (Week 5)

- **Execution Date:** July 4, 2026
- **Result:** Passed with minor feedback
- **Observations:** The dashboard rendered correctly and the toggle between chart and numerical display worked as expected. However, the displayed values hovered around ~3 packets/second regardless of activity, leading the customer to question whether the value was a hardcoded constant. The team confirmed the values were real but acknowledged the low throughput was due to the university network segment and lack of active high-traffic scenarios during the test.
- **Comments:** "It's as if three packets per second is some hardcoded constant." — The customer questioned whether the data was real or stubbed. After clarification, the customer accepted the values but noted that higher-traffic test scenarios (Speedtest, online radio, streaming) should be prepared for future demos to properly validate the counters.
- **Resulting PBIs/Issues:**
  - Prepare dedicated high-traffic test tabs (Speedtest, Wikipedia, online radio/TV) for future UAT sessions to generate meaningful packet rates.

### UAT-001 Execution Results (Week 6)

- **Execution Date:** July 11, 2026
- **Result:** Passed with major feedback
- **Observations:** The customer tested the dashboard using an asymmetric TCP workload (online radio streaming). The MUI displayed nearly identical RX and TX *packet* counts, which was confusing because TCP streaming involves large incoming data packets and small outgoing ACK packets. The customer pointed out that packet counts are less globally useful for network analysis than data volume (bits/bytes per second).
- **Comments:** "Displaying statistics in bits or bytes per second would be much more useful... If you store the packet header in the database, it's not that hard." The customer suggested aggregating the sum of packet sizes per bucket.
- **Resulting PBIs/Issues:**
  - Implement byte-volume counting (sum of packet sizes) in the backend TimescaleDB telemetry buckets and update the API endpoints.
  - Add a UI toggle in the MUI to switch between "Packets per second" and "Bytes per second" views. (Prioritized over remaining UI map features).

### UAT-001 Execution Results (Week 7)

- **Execution Date:** July 18, 2026
- **Result:** Passed
- **Observations:** The team demonstrated the newly implemented toggle to switch between "packets per second" and "bytes per second" (bps, Kbps, Mbps). The customer verified that this successfully resolves the previous feedback regarding asymmetric TCP traffic (e.g., streaming), providing a much more accurate and useful metric for network load analysis.
- **Comments:** The customer confirmed the feature works as expected and directly addresses the prior concern. The implementation was approved.
- **Resulting PBIs/Issues:** None. The feature is complete and validated.

---

## UAT-002: A retrospective analysis of channel activity

**Scenario Status:** Active

**User Goal:**
As a network administrator, I want to find the moment of an anomaly or load surge in the past in order to understand exactly when the network problems started.

**Preconditions:**

- CnSS and MUI are working, TP/CN are sending telemetry
- The user is logged in to the account
- A channel has been selected
- The channel has historical data of Rx/Tx changes

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | Open the dashboard and find the line chart of the RX/TX rate history. | Two lines are visible (blue - RX, pink - TX) for the last hour. |
| 2 | Hover the cursor over a point on the chart. | A tooltip appears with the exact values of RX/TX and time. |

### UAT-002 Execution Results (Week 5)

- **Execution Date:** July 4, 2026
- **Result:** Failed
- **Observations:** The historical chart rendered and was scalable, but the graph appeared as a flatline at ~3 packets/second and did not visibly react when traffic blocking was toggled. The bottom tables aggregate data over five-minute windows, and the top graphs have a per-second delay, but the smoothing/aggregation makes real-time changes nearly invisible. The customer noted the graph should visibly drop when blocking is activated.
- **Comments:** "It doesn't react very actively to changes, unfortunately." The customer requested adding a smaller time-scale division — a minimum window of 1 minute or 5 minutes — so the graph can be fully zoomed in for near real-time observation. "So the graph is fully zoomed in, and you can look at it almost in real-time and change things."
- **Resulting PBIs/Issues:**
  - Add a 1-minute / 5-minute minimum time window toggle to the historical chart to improve real-time reactivity and visibility of traffic state changes.
  - Investigate why the chart does not visually reflect traffic drops when hardware blocking is engaged (possible over-aggregation or smoothing issue).

### UAT-002 Execution Results (Week 7)

- **Execution Date:** July 18, 2026
- **Result:** Passed with minor feedback
- **Observations:** The historical chart and real-time tables were reviewed. The customer noted that IP addresses in the real-time table jump around due to the 1-second aggregation window. The team and customer collaboratively designed a solution: manage the table state on the frontend to maintain existing IPs, zero out their metrics if no new data arrives, and remove them after a 10-minute timeout. This keeps the left side (IPs/Locations) stable while the right side (Unique Destinations, Ports) updates in real-time.
- **Comments:** "Excellent idea. On the frontend, this will be much simpler. We periodically request new data, update the state, and use a 10-minute timeout to clear outdated records."
- **Resulting PBIs/Issues:**
  - Refactor the frontend host table state management to maintain IP stability over a longer window (e.g., 10 minutes) while allowing real-time updates for destination/port metrics.

---

## UAT-003: Fast identification of the top consumer in the network

**Scenario Status:** Active

**User Goal:**
As a network administrator, I want to quickly understand who is generating the main load on the network right now.

**Preconditions:**

- CnSS and MUI are working, TP/CN are sending telemetry
- The user is logged in to the account
- A channel has been selected
- The channel has several hosts with different received and sent per second metrics

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | Find the "Top LAN hosts" table. | A table with a maximum of 5 hosts and their current activity is visible. |
| 2 | Click on the Received column to apply sorting by traffic consumption. | The table is sorted by the desired column. |
| 3 | Determine which host receives the most packets. | The user sees the "leader" by RX or TX metrics in the first row of the table. |

### UAT-003 Execution Results (Week 5)

- **Execution Date:** July 4, 2026
- **Result:** Failed
- **Observations:** The table initially rendered and displayed the LAN host IP dynamically. However, during the test the team disconnected the Ethernet cable from the board to verify that the host would be marked as inactive. After this, the system stopped transmitting and receiving data entirely and did not recover. The customer attributed this to a system component "getting tired from working too long" and suggested a restart, but noted this needs to be investigated.
- **Comments:** "I think one of the system components just got tired, it worked for a long time. Alright, let's just restart it, and it will most likely work." The customer was understanding but flagged this as a stability concern that must be addressed.
- **Resulting PBIs/Issues:**
  - **[Critical]** Investigate and fix CN/CnSS state corruption or crash when a network interface is physically disconnected and reconnected. The system must recover gracefully without requiring a manual restart.

### UAT-003 Execution Results (Week 6)

- **Execution Date:** July 11, 2026
- **Result:** Passed with minor feedback
- **Observations:** The team demonstrated the first version of the detailed host statistics page. It successfully displayed packet transfer statistics, a historical graph, and destination addresses for a specific host.
- **Comments:** "Great. So the local address and the address it sends data to." The customer approved the basic layout but noted it currently only shows packet counts, tying back to the need for byte-volume counting discussed in UAT-001.
- **Resulting PBIs/Issues:**
  - Update the detailed host statistics page to support and display the new byte-volume counting metric once the backend feature is implemented.

### UAT-003 Execution Results (Week 7)

- **Execution Date:** July 18, 2026
- **Result:** Passed
- **Observations:** The detailed host statistics page was fully demonstrated. The customer verified that clicking on a specific host successfully opens a detailed view showing packet transfer statistics, a historical activity graph, Top Destinations, and Top Ports.
- **Comments:** "Great. So the local address and the address it sends data to." The customer approved the detailed statistics layout and functionality.
- **Resulting PBIs/Issues:** None. The feature is complete and validated.

---

## UAT-004: Overview of the list of active network hosts

**Scenario Status:** Active

**User Goal:**
As a network administrator, I want to see the full picture of network activity and find a specific host in order to understand what is happening on the network as a whole.

**Preconditions:**

- CnSS and MUI are working, TP/CN are sending telemetry
- The user is logged in to the account
- A channel has been selected
- The channel has several hosts with different received and sent per second metrics

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | Click on the "View all entries" button at the bottom of the "Top LAN hosts" table. | The `/hosts` page opened with the full table of hosts activity. |
| 2 | Locate filter input field right above the table and write `location: LAN` here. | The table is filtered to show only hosts in the local area network. |
| 3 | Click on the Received column to apply sorting by traffic consumption. | The table is sorted by the desired column. |
| 4 | Change "Results per page" limit at the bottom of the table to 50. | Table shows more rows on one page. |

### UAT-004 Execution Results (Week 5)

- **Execution Date:** July 4, 2026
- **Result:** Passed with minor feedback
- **Observations:** The hosts page rendered correctly with the full table. Basic text-based filtering (`location: LAN`) worked and correctly filtered to show only LAN hosts. Sorting by columns functioned as expected. The customer acknowledged the filtering works but emphasized that text-based filter fields are a poor UX choice and referenced prior feedback on this topic. The team acknowledged that sidebar-style filters could be added with minimal code changes.
- **Comments:** "I assume you already feel how hard it is to work with text fields for filtering?" / "This is exactly what I was talking about last time." The customer reiterated that strict text syntax (case-sensitive, space-sensitive) is not user-friendly and should be replaced or supplemented with structured filter controls.
- **Resulting PBIs/Issues:**
  - Redesign the host table filtering UI to use structured controls (dropdowns, tags, or sidebar filters) instead of raw text-field syntax queries.

---

## UAT-005: Hardware traffic blocking

**Scenario Status:** Active

**User Goal:**
As a network administrator, I want to physically stop unwanted traffic and make sure that the system displays this status correctly.

**Preconditions:**

- Demo LAN laptop is connected to the network
- Traffic processor is connected to the network
- CnSS and MUI are working, CN is sending telemetry
- The channel has been selected

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | Open some internet page on the demo LAN laptop. | Ensure that the internet is working as expected. |
| 2 | Press the physical button on the FPGA board to block traffic from the demo LAN laptop. | Opened internet page stops loading. |
| 3 | Check MUI dashboard charts. | The overall channel activity decreases. |
| 4 | Press the physical button on the FPGA board again to stop blocking traffic from the demo LAN laptop. | Internet is working on the demo laptop again and channel activity on the MUI increases. |

### UAT-005 Execution Results (Week 5)

- **Execution Date:** July 4, 2026
- **Result:** Passed with minor feedback
- **Observations:** Pressing Key1 successfully blocked traffic — the LED1 turned off and the laptop lost internet access immediately. Pressing the button again restored connectivity. The customer tested with Wikipedia (fast loading when unblocked, no access when blocked) and attempted streaming to observe sustained blocking behavior. The customer observed via the board LEDs that requests arrive but are not forwarded back, and noted the router would see broken packets. The team acknowledged the current implementation is a basic version that drops traffic at the IP level and that contact bounce (debounce) on the physical button has not yet been fixed. Blocking is currently hardcoded to a single device IP.
- **Comments:** "So the router sees a bunch of broken packets." / "With video, it's a bit harder to see because video has a 10-15-30 second buffer." The customer understood the current implementation limitations and was satisfied that blocking works at a functional level. Requested that future demos prepare active streaming/radio tabs to better visualize the blocking effect in real time.
- **Resulting PBIs/Issues:**
  - Fix hardware button debounce (contact bounce) on Key1 to prevent multiple unintended state toggles.
  - Expand blocking beyond the single hardcoded IP to support configurable per-host or per-channel blocking rules.

### UAT-005 Execution Results (Week 6)

- **Execution Date:** July 11, 2026
- **Result:** Not Executed / Deferred
- **Observations:** The team reported that the critical stability issue from Week 5 (system crash/hang when physically disconnecting and reconnecting cables) was successfully resolved. The physical stand now handles cable reconnects correctly. However, a known bug causing fragmented packets during hardware blocking was fixed in the codebase but had not yet been deployed to the physical FPGA stand. Therefore, live hardware blocking was intentionally not demonstrated to avoid showing broken behavior.
- **Comments:** "The fix is already written, but it hasn't been deployed to the stand yet, so the hardware blocking function won't be demonstrated today."
- **Resulting PBIs/Issues:**
  - Deploy the fragmented packet fix to the physical FPGA stand and verify hardware blocking live in Week 7.

### UAT-005 Execution Results (Week 7)

- **Execution Date:** July 18, 2026
- **Result:** Passed
- **Observations:** The team demonstrated the new dynamic IP blocking feature on the FPGA. Instead of a hardcoded IP, a script is now used to dynamically set the target IP for blocking (e.g., the demo laptop's IP). When the IP was entered, the laptop immediately lost connection, and the MUI correctly showed the packet count dropping to zero. The customer also inquired about ICMP (ping) visibility, and the team clarified that protocols without ports are currently filtered out of port statistics due to strict typing, which is an accepted limitation for the current scope. Additionally, the system successfully handled a stress test of 588 Mbps without hanging or crashing.
- **Comments:** "So `0.0.0.0` is not perceived as a mask, but blocks a specific address? ... Yes, this is a specific address. But now you can enter any IP that needs to be blocked." The customer was satisfied with the dynamic blocking demonstration and the system's stability under load.
- **Resulting PBIs/Issues:** None. The feature is complete and validated.

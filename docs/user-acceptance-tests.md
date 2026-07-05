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

*Record the results of the customer executing this scenario during the recorded UAT session.*

- **Execution Date:** [YYYY-MM-DD]
- **Result:** [Passed / Failed / Passed with minor feedback]
- **Observations:** [e.g., "Customer noted the counters update smoothly, but requested higher contrast for the activity indicator."]

### UAT-001 Customer Comments & Resulting PBIs

- **Comments:** [Direct quotes or summarized feedback from the customer during/after execution]
- **Resulting PBIs/Issues:**

  - [e.g., [#145] - Increase contrast on StatusIndicator component]
  - [e.g., None]

---

## UAT-002: A retrospective analysis of channel activity

**Scenario Status:** Active

**User Goal:**

As a network administrator, I want to find the moment of an anomaly or load surge in the past in order to understand exactly when the network problems started.

**Preconditions:**

- CnSS and MUI are working, TP/CN are sending telemetry
- The user is logged in to the account
- A channel has been selected
- The channel have historical data of Rx/Tx changes

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | Open the dashboard and find the line chart of the RX/TX rate history. | Two lines are visible (blue - RX, pink - TX) for the last hour. |
| 2 | Hover the cursor over a point on the chart. | A tooltip appears with the exact values of RX/TX and time. |

### UAT-002 Execution Results (Week 5)

- **Execution Date:** [YYYY-MM-DD]
- **Result:** [Passed / Failed / Passed with minor feedback]
- **Observations:** [e.g., "Switching is instantaneous. Customer verified that data from the previous channel does not bleed into the new view."]

### UAT-002 Customer Comments & Resulting PBIs

- **Comments:** [Customer feedback]
- **Resulting PBIs/Issues:** [Links to issues or "None"]

---

## UAT-003: Fast identification of the top consumer in the network

**Scenario Status:** Active

**User Goal:**

As a network administrator, I want to quickly understand who is generating the main load on the network right now.

**Preconditions:**

- CnSS and MUI are working, TP/CN are sending telemetry
- The user is logged in to the account
- A channel has been selected
- The channel have several hosts with different received and sent per second metrics

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | Find the "Top LAN hosts" table. | A table with a maximum of 5 hosts and their current activity is visible. |
| 2 | Click on the Received column to apply sorting by traffic consumption. | The table is sorted by the desired column. |
| 3 | Determine which host receives the most packets. | The user sees the "leader" by RX or TX metrics in the first row of the table. |

### UAT-003 Execution Results (Week 5)

- **Execution Date:** [YYYY-MM-DD]
- **Result:** [Passed / Failed / Passed with minor feedback]
- **Observations:** [e.g., "Customer successfully verified that the UI correctly filters the dropdown and the backend correctly rejects unauthorized WS connections."]

### UAT-003 Customer Comments & Resulting PBIs

- **Comments:** [Customer feedback]
- **Resulting PBIs/Issues:** [Links to issues or "None"]

---

## UAT-004: Overview of the list of active network hosts

**Scenario Status:** Active

**User Goal:**

As a network administrator, I want to see the full picture of network activity and find a specific host in order to understand what is happening on the network as a whole.

**Preconditions:**

- CnSS and MUI are working, TP/CN are sending telemetry
- The user is logged in to the account
- A channel has been selected
- The channel have several hosts with different received and sent per second metrics

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | Click on the "View all entries" button at the bottom of the "Top LAN hosts" table. | The `/hosts` page opened with the full table of hosts activity. |
| 2 | Locate filter input field right above the table and write `location: LAN` here. | The table is filtered to show only hosts in the local area network. |
| 3 | Click on the Received column to apply sorting by traffic consumption. | The table is sorted by the desired column. |
| 4 | Change "Results per page" limit at the bottom of the table to 50. | Table shows more rows on one page. |

### UAT-004 Execution Results (Week 5)

- **Execution Date:** [YYYY-MM-DD]
- **Result:** [Passed / Failed / Passed with minor feedback]
- **Observations:** [e.g., "Customer successfully verified that the UI correctly filters the dropdown and the backend correctly rejects unauthorized WS connections."]

### UAT-004 Customer Comments & Resulting PBIs

- **Comments:** [Customer feedback]
- **Resulting PBIs/Issues:** [Links to issues or "None"]

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
| 1 | Open some internet page on the demo LAN laptop. | Ensure, that the internet is working as expected. |
| 2 | Press the physical button on the FPGA board to block traffic from the demo LAN laptop. | Opened intenet page stops loading. |
| 3 | Check MUI dashboard charts. | The overall channel activity decreases. |
| 4 | Press the physical button on the FPGA board again to stop blocking traffic from the demo LAN laptop. | Internet is working on the demo laptop again and channel activity on the MUI increases. |

### UAT-005 Execution Results (Week 5)

- **Execution Date:** [YYYY-MM-DD]
- **Result:** [Passed / Failed / Passed with minor feedback]
- **Observations:** [e.g., "Customer successfully verified that the UI correctly filters the dropdown and the backend correctly rejects unauthorized WS connections."]

### UAT-005 Customer Comments & Resulting PBIs

- **Comments:** [Customer feedback]
- **Resulting PBIs/Issues:** [Links to issues or "None"]

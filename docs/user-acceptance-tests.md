# User Acceptance Tests (UAT)

This document defines the end-user-facing scenarios that customers or relevant stakeholders execute to inspect whether the Traffic Processing Platform supports intended user goals.

*Note: UAT IDs must remain stable. If a scenario needs clarification, edit it in place. If it becomes obsolete, mark it `Retired`. If the user goal changes materially, create a new ID.*

---

## UAT-001: [Short Title, e.g., Authenticate and View Real-Time Telemetry]

**Scenario Status:** [Active / Retired / Superseded]

**User Goal:**
[What the user is trying to achieve. e.g., "As a system administrator, I want to log in and view real-time packet counts so that I can monitor network activity."]

**Preconditions:**

- [e.g., The CnSS and MUI are deployed and accessible.]
- [e.g., The TP is actively forwarding traffic and sending telemetry to the CN.]
- [e.g., Valid administrator credentials are available.]

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | Navigate to the MUI deployment URL. | The login screen is displayed. |
| 2 | Enter valid username and password, then click "Login". | The user is redirected to the main dashboard. No error messages are shown. |
| 3 | Observe the Channel Activity indicator and Rx/Tx packet counters. | The activity indicator shows "Active" (Green). The Rx/Tx counters update in real-time (every 0.5 - 2 seconds) reflecting actual traffic. |
| 4 | [Add further steps...] | [Add expected outcomes...] |

### UAT-001 Execution Results (Week 4)

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

## UAT-002: [Short Title, e.g., Switch Between Monitored Channels]

**Scenario Status:** [Active / Retired / Superseded]

**User Goal:**
[What the user is trying to achieve. e.g., "As an administrator with access to multiple bridges, I want to switch between them to compare their network states."]

**Preconditions:**

- [e.g., User is logged in with an account that has `scope` access to at least two distinct channels (e.g., `bridge-berlin` and `bridge-prague`).]
- [e.g., Both channels are actively receiving telemetry.]

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | On the dashboard, open the channel selection dropdown. | The dropdown lists all channels accessible to the user's JWT scope. |
| 2 | Select a different channel (e.g., switch from `bridge-berlin` to `bridge-prague`). | The dashboard immediately clears the previous data and begins displaying the real-time telemetry for the newly selected channel. |
| 3 | [Add further steps...] | [Add expected outcomes...] |

### UAT-002 Execution Results (Week 4)

- **Execution Date:** [YYYY-MM-DD]
- **Result:** [Passed / Failed / Passed with minor feedback]
- **Observations:** [e.g., "Switching is instantaneous. Customer verified that data from the previous channel does not bleed into the new view."]

### UAT-002 Customer Comments & Resulting PBIs

- **Comments:** [Customer feedback]
- **Resulting PBIs/Issues:** [Links to issues or "None"]

---

## UAT-003: [Short Title, e.g., Verify Access Control for Restricted Viewer]

**Scenario Status:** [Active / Retired / Superseded]

**User Goal:**
[What the user is trying to achieve. e.g., "As a restricted viewer, I want to ensure I cannot access channels outside my assigned scope."]

**Preconditions:**

- [e.g., A `viewer` account exists with a JWT scope restricted to only `bridge-berlin`.]

**Step-by-step Instructions & Expected Outcomes:**

| Step | Action | Expected Outcome |
|---|---|---|
| 1 | Log in using the restricted `viewer` credentials. | Login is successful, dashboard loads. |
| 2 | Check the channel selection dropdown. | Only `bridge-berlin` is visible. Other channels are hidden. |
| 3 | Attempt to manually construct a WebSocket URL for an unauthorized channel (e.g., `bridge-prague`). | The WebSocket connection is rejected with close code `4003` (channel_forbidden), and the UI handles the disconnection gracefully. |

### UAT-003 Execution Results (Week 4)

- **Execution Date:** [YYYY-MM-DD]
- **Result:** [Passed / Failed / Passed with minor feedback]
- **Observations:** [e.g., "Customer successfully verified that the UI correctly filters the dropdown and the backend correctly rejects unauthorized WS connections."]

### UAT-003 Customer Comments & Resulting PBIs

- **Comments:** [Customer feedback]
- **Resulting PBIs/Issues:** [Links to issues or "None"]

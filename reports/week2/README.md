# Assignment 2 Report

## Project Overview

**Project Name:** Traffic Processing Platform

This is a monorepo containing minimally intrusive network traffic monitoring system. It consists of four distinct components designed to capture, process, forward, and visualize network telemetry in real-time without degrading network performance:

- **`traffic-processor/`**: Core packet counting and telemetry engine (transparent inline bridge).
- **`communication-node/`**: Local data forwarding node.
- **`cnss/`**: Control and Status Server (Backend) aggregating data via API/WebSocket.
- **`mui/`**: Management User Interface (Frontend) for real-time visualization.

**License:** [MIT License](../../LICENSE)

---

## 1. User Stories and Prioritization

The complete list of documented, prioritized, and customer-validated user stories can be found here:  
🔗 [User Stories](./user-stories.md)

---

## 2. Prototype and Interface Artifacts
We have designed the foundational interface and architecture for the MVP v1 scope. 

*   🔗 **System Architecture Diagram:** [system-architecture-diagram.png](./images/system-architecture-diagram.png)  
    *Describes the data flow from the Traffic Processor (FPGA + Laptop) through the Communication Node to the CnSS, as validated with the customer.*
*   🔗 **MUI MVP Dashboard Prototype:** [mui-mvp-dashboard-prototype.png](./images/mui-mvp-dashboard-prototype.png)  
    *Visualizes the primary dashboard, including channel activity status, Rx/Tx rates, and protocol statistics.*
*   🔗 **[PLACEHOLDER: Interactive Figma/Prototype Link]**

---

## 3. MVP v0 Foundation

🔗 [MVP v0 Report and Smoke-Check Scenario](./mvp-v0-report.md)  
🔗 **[PLACEHOLDER: Deployed MVP v0 URL or Runnable Artifact Link]**  
🔗 **[PLACEHOLDER: Public Video Demonstration Link (< 2 minutes)]**  
🔗 **[PLACEHOLDER: Local Setup Instructions (Root README.md)]**

---

## 4. Development Workflow and CI/CD
Our team strictly follows the Gitflow branching model with mandatory merge commits to preserve history, as per course requirements.

*  🔗 **Minimal PR/MR Template:** [`.github/pull_request_template.md`](../../.github/pull_request_template.md)
*   🔗 [Example Reviewed PR/MR](https://github.com/SWP-47/traffic-processing-platform/pull/23)

 *The screenshot below demonstrates an approved review, required CI checks passing, and a merge commit.*  
  ![Example Reviewed PR](./images/example-reviewed-pr.png)

*   🔗 **Lychee Configuration:** [`.github/workflows/lychee.yml`](../../.github/workflows/README.md)
*   🔗 [Latest Successful Lychee Run](https://github.com/SWP-47/traffic-processing-platform/actions/runs/27464347659)
*   **Excluded Lychee Links & Manual Verification:**  
  *[PLACEHOLDER: List any localhost, private, or dynamic links excluded from Lychee, and confirm they were manually verified. E.g., "Localhost API endpoints were excluded and manually verified via Postman."]*

---

## 5. Coverage and Traceability

### Prototype Coverage
The provided interface artifacts directly address the following stable User Story IDs:
*   **US-001 & US-015:** Addressed by the "Channel Activity" indicator (Red/Green status) and real-time auto-updating design in the MUI prototype.
*   **US-002 & US-011:** Addressed by the Rx/Tx Rate counters and throughput statistics display. *(Customer feedback noted: Tx/Rx numbers will be made larger/higher contrast, and byte counting may be refined alongside US-011).*
*   **US-014:** Addressed by the web-based nature of the MUI, designed for remote access.

### MVP v0 Coverage
The MVP v0 foundation targets the core plumbing required to support:
*   **US-004:** Modular integration (separate `traffic-processor`, `communication-node`, and `cnss` directories).
*   **US-009:** Basic bidirectional packet passing logic in the TP.
*   *(See [MVP v0 Report](./mvp-v0-report.md) for detailed smoke-check mapping).*

---

## 6. Customer Validation and Meeting Artifacts

*   🔗 **Customer Meeting Summary:** [customer-meeting-summary.md](./customer-meeting-summary.md)
*   🔗 **Customer Meeting Transcript:** [customer-meeting-transcript.md](./customer-meeting-transcript.md)  

---

## 7. Weekly Analysis
🔗 [Week 2 Analysis Report](./analysis.md)  

---

## 8. LLM Usage Report
🔗 [LLM Usage Report](./llm-report.md)  

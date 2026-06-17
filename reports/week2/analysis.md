# Week 2 Analysis

## Learning points

- **User Stories & Prioritization**: We learned the importance of properly prioritizing user stories to avoid scope creep. For example, after customer feedback, we changed **US-015** (Real-time MUI Dashboard Updates) to "Should Have", as it was not 100% necessary for the MVP.
- **Prototyping & Interface Design**: Presenting the MUI mockup revealed that stakeholders prioritize high-level, actionable metrics over granular data dumps. The customer's feedback to emphasize *active client counts* and increase the visual contrast of Tx/Rx rates, while deprioritizing raw protocol lists on the main dashboard, will directly guide our UI/UX refinements.
- **Customer Validation & Terminology**: Direct dialogue is essential for disambiguating technical terms. For example, clarifying that "filtering" in **US-010** refers strictly to UI/display filtering, *not* active traffic modification or dropping, prevented a massive scope misunderstanding and potential architectural misstep.

## Validated assumptions

- **Architecture & Latency**: We initially assumed that processing telemetry on a laptop alongside the FPGA Traffic Processor might introduce unacceptable latency. **Validated/Refined**: The customer confirmed that for the MVP, homogeneous timestamp delays applied at the CnSS database recording level (rather than per-packet at the edge) are perfectly acceptable.
- **Deployment Constraints**: We assumed "invisible deployment" meant zero physical disruption. **Refined**: The customer clarified that it specifically implies a modular, non-monolithic system architecture where component failures (excluding the core traffic processor/router) do not disrupt the main traffic flow, allowing for independent restarts or replacements (**US-005**, **US-007**).
- **Data Storage Complexity**: We assumed historical traffic statistics (**US-013**) required immediate backend database implementation. **Refined**: The customer suggested that for the MVP, historical stats (e.g., the last 30 minutes) can be dynamically accumulated and stored on the frontend (MUI) to reduce backend complexity.

## Needs clarification

- **Byte Counting Accuracy (US-002 / US-016)**: While packet counting is straightforward, accurate byte volume counting (distinguishing between payload, headers, and total frame size) requires further technical investigation. We must ensure this calculation does not violate the "no noticeable network slowdown" constraint (**US-007**).
- **Advanced Security Features (US-019, US-020)**: The customer expressed strong interest in packet metadata capture and atypical port monitoring (e.g., SSH on non-standard ports). However, they acknowledged these are complex. We need to clarify the exact performance overhead of metadata capture and define the specific rules/thresholds for "atypical" connections before committing engineering resources.
- **Global Network Access (US-014)**: We need to finalize the exact networking and firewall constraints of the Innopolis University local server to ensure that "global network" access is configured securely and functions as intended without violating university IT policies.

## Planned response

- **Artifact Updates**: All discussed changes have been formally applied to the [user stories document](user-stories.md). This includes splitting byte counting into **US-016**, adding **US-017** through **US-020** to the backlog, adjusting the priority of **US-015**, and refining the wording of **US-014** and **US-10**.
- **Prototype Refinement**: The [MUI Figma prototype](https://www.figma.com/design/pbN9YeX8NosxN7wQgAeXbe/Traffic-Processor-App?node-id=119-268&t=CWDKMx5dmF0WB8DI-1) will be updated to increase the visual hierarchy of Tx/Rx rates and emphasize active client counts over raw protocol lists, directly addressing the customer's dashboard feedback.
- **MVP v1 Scope Adherence**: Development for the upcoming sprint will be strictly limited to the confirmed `Must Have` stories: **US-001**, **US-002**, **US-004**, **US-005**, **US-007**, **US-009**, and **US-014**.

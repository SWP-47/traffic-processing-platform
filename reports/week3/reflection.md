# Week 3 Analysis

## Learning points

- We learned the practical value of using `openapi-ts` and `openapi-fetch` to auto-generate type-safe TypeScript clients from our FastAPI OpenAPI specification. This significantly reduced manual integration errors and streamlined communication between the MUI and CnSS.
- We learned how to effectively decompose large, cross-component user stories (like US-004: Modular Platform Integration) into role-specific PBIs. This allowed team members to work in parallel on their respective components (TP, CN, CnSS, MUI) while contributing to a shared user story.
- We learned to remain flexible with the Sprint scope. Based on customer feedback, we successfully integrated US-012 (Basic Password Protection) into the current Sprint to ensure the dashboard was secure from the initial release.

## Validated assumptions

- We assumed that a simple UDP/JSON schema would be sufficient for the CN-to-CnSS telemetry pipeline in MVP v1. The customer validated this, advising against overengineering with gRPC/Protobuf at this early stage.
- We initially assumed that exact, high-precision per-packet timestamps would be critical for the MVP. The customer rejected this, confirming that for basic packet counting, homogeneous delay and server-side timestamping are perfectly acceptable.

## Friction and gaps

- The initial MVP v1 scope did not include authentication (US-012). This gap was identified during the customer review, requiring us to rapidly add and implement basic JWT password protection to secure the remote dashboard.
- While the TP and CN are currently functioning on separate physical/virtual setups, consolidating them into a single physical device using Docker containers is still pending and represents a technical gap in our local deployment architecture.
- Because all "Must Have" stories were included in MVP v1, the entire Product Backlog was pulled into Sprint 1, making the Product and Sprint Backlog sizes identical (74 Story Points) and leaving future PBIs unestimated.

## Planned response

- In Sprint 2, we will focus on the "Should Have" features, including byte volume counting, per-IP/port tracking, and historical data retention, building upon the secure foundation established in MVP v1.
- We will address the hardware optimization gap by migrating both the TP and CN software components into a unified Dockerized environment on a single physical device to streamline the testbed setup.
- We will refine and estimate the remaining Product Backlog items for Sprint 2, ensuring that future sprints have a more balanced distribution of Story Points and a clear focus on advanced analytics.

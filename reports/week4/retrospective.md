# Sprint 2 Retrospective

## What went well

1. The team successfully integrated TimescaleDB and validated our architecture through stress testing. The customer was highly satisfied with the system's ability to handle high-throughput channels (up to 100 Mbps) without performance degradation.
2. We overcame initial confusion regarding non-functional metrics and successfully defined and automated three Quality Requirements (QRs) in our CI pipeline.
3. The MUI redesign effectively reduced visual noise and introduced historical charts and host tables. The customer approved this direction, confirming that our UI/UX choices align well with the practical needs of system administrators.

## What did not go well

1. We did not fully remove legacy code after migrating to TimescaleDB. This leftover code clutters the backend and could cause confusion or unexpected behavior in future sprints.
2. We prioritized backend database integration and metadata pipelines, but did not have time to implement UI changes. Our backlog is now UI-heavy. This shows a slight imbalance in our sprint capacity planning.
3. While we integrated automated tests, most of them cover the CnSS component. Other components are lacking test coverage.

## Action points

1. Completely eliminate legacy code from the CnSS backend to maintain code quality and readability.
2. Implement the deferred UI/UX improvements requested by the customer (RX/TX toggle, all host tables) to ensure we are continuously responding to user feedback and not just focusing on backend infrastructure.
3. Expand our CI tests to cover all project components.

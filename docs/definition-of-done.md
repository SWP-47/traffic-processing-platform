# Definition of Done

This document defines the shared minimum completion standard for all work in the Traffic Processing Platform repository. A Product Backlog Item (PBI) may only be marked as `Done` when **both** its issue-specific acceptance criteria and the team-level Definition of Done outlined below are fully satisfied.

## 1. General Criteria (Applies to all PBIs)

- [ ] All acceptance criteria defined in the issue are fully satisfied and verified.
- [ ] The work has been reviewed and explicitly approved by at least one other team member (the designated reviewer).
- [ ] All required automated checks (e.g., linting, formatting, unit tests, Lychee link-checking) pass successfully on the issue-linked PR/MR.
- [ ] No sensitive data, secrets, API keys, PII, or real customer names are committed. Environment variables use `.env.example` placeholders.
- [ ] Evidence of verification (e.g., API response logs, or written description of test results) is preserved in the issue comments or the final merged PR/MR.
- [ ] The PR/MR and relevant issue are explicitly linked (e.g., using `Closes #<issue-number>` and the PR/MR is linked in the "development" tab for the issue.)

## 2. Criteria for Supporting / Implementation PBIs (Code & Tech Tasks)

- [ ] The issue-linked PR/MR is successfully merged into the protected default branch (`develop`)
- [ ] Relevant unit or integration tests have been added or updated to cover the new logic (where applicable).
- [ ] If the change is user-visible, an entry has been added to the `## [Unreleased]` section of the root `CHANGELOG.md` under the appropriate category (`Added`, `Changed`, `Fixed`, etc.) and linked to the issue. *(Note: Internal refactoring or CI updates do not require a changelog entry).*
- [ ] For our tightly coupled monorepo, adjacent components have been verified (e.g., if TP telemetry format changed, CN parsing is verified; if CnSS API changed, MUI rendering is verified).

## 3. Criteria for User Stories

- [ ] All linked supporting PBIs (tasks, bugs, tech debt, UI/UX implementations) required to satisfy the user story's acceptance criteria are marked `Done`.

## 4. Criteria for Documentation / Non-Code PBIs

- [ ] **Published/Merged**: Documentation is merged into the protected default branch.
- [ ] **Links Verified**: All internal and external links pass the Lychee CI check.
- [ ] **Clarity & Accuracy**: The documentation accurately reflects the current state of the system and is free of placeholders or outdated architectural diagrams.

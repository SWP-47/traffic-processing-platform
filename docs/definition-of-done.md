# Definition of Done

This document defines the shared minimum completion standard for all work in the Traffic Processing Platform repository. A Product Backlog Item (PBI) may only be marked as `Done` when **both** its issue-specific acceptance criteria and the team-level Definition of Done outlined below are fully satisfied.

## 1. General Criteria (Applies to all PBIs)

- [ ] All acceptance criteria defined in the issue are fully satisfied and verified.
- [ ] The work has been reviewed and explicitly approved by at least one other team member (the designated reviewer).
- [ ] All required automated checks for the product stack pass successfully on the issue-linked PR/MR.
- [ ] Relevant automated quality requirement tests (QRTs) are included and pass on the issue-linked PR/MR.
- [ ] Critical module coverage gates are satisfied for affected modules.
- [ ] No sensitive data, secrets, API keys, PII, or real customer names are committed. Environment variables use `.env.example` placeholders.
- [ ] Evidence of verification (e.g., API response logs, test results, or CI status summaries) is preserved in the issue comments or the final merged PR/MR.
- [ ] The PR/MR and relevant issue are explicitly linked (e.g., using `Closes #<issue-number>` and the PR/MR is linked in the "development" tab for the issue.)

## 2. Criteria for Supporting / Implementation PBIs (Code & Tech Tasks)

- [ ] The issue-linked PR/MR is successfully merged into the protected default branch (`develop`).
- [ ] Relevant unit or integration tests have been added or updated to cover the new logic (where applicable).
- [ ] Relevant automated quality requirement tests are added or updated for new or changed quality-relevant behavior.
- [ ] The backend coverage gate enforces at least 30% line coverage for the critical CnSS codebase.
- [ ] If the change is user-visible, an entry has been added to the `## [Unreleased]` section of the root `CHANGELOG.md` under the appropriate category (`Added`, `Changed`, `Fixed`, etc.) and linked to the issue. *(Note: Internal refactoring or CI updates do not require a changelog entry.)*
- [ ] For the monorepo, adjacent components have been verified for integration impact (for example, if CnSS API changed, MUI behavior is reviewed; if TP/CN telemetry format changed, downstream ingestion is verified).

## 3. Criteria for User Stories

- [ ] All linked supporting PBIs (tasks, bugs, technical work, UI/UX implementations) required to satisfy the user story's acceptance criteria are marked `Done`.

## 4. Criteria for Documentation / Non-Code PBIs

- [ ] **Published/Merged**: Documentation is merged into the protected default branch.
- [ ] **Links Verified**: All internal and external links pass the Lychee CI check.
- [ ] **Clarity & Accuracy**: The documentation accurately reflects the current state of the system and is free of placeholders or outdated architectural diagrams.

## 5. Additional Assignment 4 Quality Gates

- [ ] Issue-linked PR/MR includes evidence that the updated Definition of Done is satisfied.
- [ ] The additional QA check selected for Assignment 4 is configured and passing in CI.
- [ ] Testing evidence is preserved in PR/MR comments, docs, or linked issue history.

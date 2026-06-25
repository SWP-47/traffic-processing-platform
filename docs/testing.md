# Testing and Quality Status

This document serves as the canonical testing status artifact for the Traffic Processing Platform. It details our critical modules, automated test coverage, CI/QA check status, and manual evidence.

## Critical Modules and Coverage

Critical modules are source files, packages, or product areas responsible for core user workflows, persistence, external integration, security, or business rules. Each critical module must maintain at least 30% automated line coverage.

| Critical module | Why critical | Required line coverage | Current line coverage | Evidence |
|---|---|---:|---:|---|
| `cnss/app/api/routes/` | Core REST API and WebSocket endpoints handling authentication and telemetry routing. | 30% | [XX]% | [Coverage run link] |
| `cnss/app/core/auth.py` | JWT token generation, validation, and scope enforcement (Security). | 30% | [XX]% | [Coverage run link] |
| `mui/src/services/` | Frontend API and WebSocket services handling real-time telemetry and auth state. | 30% | [XX]% | [Coverage run link] |
| *[Add/Remove modules as needed]* | *[Reason]* | 30% | [XX]% | [Link] |

*If global repository coverage is lower than critical-module coverage, explain why here: [Explanation or "N/A - Global coverage meets or exceeds critical module thresholds"]*

## Automated Test Status

| Test type | Scope | Command or CI check | Latest result | Evidence |
|---|---|---|---|---|
| Unit tests | Critical backend logic (auth, state management, telemetry parsing) | `pytest cnss/tests/unit/` | [Passing/Failing] | [CI run link] |
| Unit tests | Frontend component logic and services | `npm run test:unit` | [Passing/Failing] | [CI run link] |
| Integration tests | CnSS REST API endpoints and WebSocket lifecycle | `pytest cnss/tests/integration/` | [Passing/Failing] | [CI run link] |
| Automated QRTs | QR-001, QR-002, QR-003 (See `docs/quality-requirement-tests.md`) | `pytest tests/quality/` | [Passing/Failing] | [QRT report link] |

## CI and QA Check Status

| Gate or check | Required for Done? | Latest protected-branch status | Evidence |
|---|---|---|---|
| Linting (Python/JS) | Yes | [Passing/Failing] | [CI run link] |
| Formatting/Type checking (Black/Ruff/tsc) | Yes | [Passing/Failing] | [CI run link] |
| Build / Testable snapshot | Yes | [Passing/Failing] | [CI run link] |
| Lychee Link Checking | Yes | [Passing/Failing] | [CI run link] |
| Additional QA check (See below) | Yes | [Passing/Failing] | [Check report link] |

**Branch Protection Evidence:**
[Insert screenshot link or description of branch protection rules on the `develop`/`general` branch, e.g., "Requires 1 approval, requires status checks to pass, disables squash/rebase"]

## Additional QA Check Rationale

Link checking (Lychee) does not satisfy the Assignment 4 additional QA check requirement. The following check was selected to address specific project risks.

| QA objective or risk | Additional QA check | Scope | Latest result | Evidence | Limitations or follow-up |
|---|---|---|---|---|---|
| *[e.g., Dependencies with known vulnerabilities may expose deployments to avoidable risk.]* | *[e.g., Automated dependency vulnerability scan (e.g., pip-audit / npm audit)]* | *[e.g., Product dependency manifests and lockfiles]* | [Passing/Failing] | [CI run link] | *[e.g., Some vulnerabilities may require manual triage or delayed upstream fixes.]* |

## Manual Evidence That Does Not Count as QRT

Manual tests, observations, or exploratory checks that do not qualify as automated Quality Requirement Tests (QRTs).

| Evidence | Scope | Result | Follow-up PBI or issue |
|---|---|---|---|
| *[e.g., Manual smoke test of FPGA bitstream deployment]* | *[e.g., TP hardware data plane]* | [Passed/Failed with notes] | [Link to issue or "None"] |
| *[e.g., Exploratory UI check on mobile viewport]* | *[e.g., MUI Dashboard]* | [Passed/Failed with notes] | [Link to issue or "None"] |

## Active Quality Gates for Future Sprints

The following Assignment 4 quality gates, tests, and CI checks are maintained as active repository requirements for all future project work. Later PBIs must satisfy these gates unless explicitly superseded by a documented equivalent or stronger check.

- [ ] All automated unit and integration tests must pass.
- [ ] Automated Quality Requirement Tests (QRT-001, QRT-002, QRT-003) must pass.
- [ ] Critical modules must maintain ≥ 30% line coverage.
- [ ] Linting, formatting, and type-checking gates must pass.
- [ ] Additional QA check ([Name of check]) must pass.
- [ ] Lychee link checking must pass.

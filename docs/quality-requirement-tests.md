# Quality Requirement Tests (QRT)

This document defines the automated tests and CI checks that verify the measurable scenarios outlined in [docs/quality-requirements.md](quality-requirements.md).

---

## QRT-001: CnSS health API responsiveness

**Linked quality requirement:** QR-001

**Verification method:** Automated integration test.

**Test data, setup, or environment:** CnSS running in the standard CI container test environment with a healthy backend database and a valid admin JWT token.

**Automated command or CI check:** `docker compose -f cnss/docker-compose.test.yml up --build --abort-on-container-exit`

**Expected measurable result:** The CnSS health endpoint returns `200 OK` with a valid `components.cnss` value and a `timestamp` field, and the integration test suite passes.

**Evidence link:** Latest protected-branch CI run showing the CnSS integration job result.

---

## QRT-002: JWT scope enforcement

**Linked quality requirement:** QR-002

**Verification method:** Automated integration test.

**Test data, setup, or environment:** CnSS running in the CI container environment with authorized and unauthorized JWT tokens, verifying access to `POST /api/v1/auth/login` and scoped channel results.

**Automated command or CI check:** `docker compose -f cnss/docker-compose.test.yml up --build --abort-on-container-exit`

**Expected measurable result:** Authorized admin requests succeed, invalid credentials return `401 Unauthorized`, and viewer scope is limited to authorized channel IDs only.

**Evidence link:** Latest protected-branch CI run showing the CnSS integration job result.

---

## QRT-003: Critical module unit coverage

**Linked quality requirement:** QR-003

**Verification method:** Automated coverage gate.

**Test data, setup, or environment:** Standard CI Python environment for the CnSS backend.

**Automated command or CI check:** `pytest --cov=app --cov-report=term-missing --cov-fail-under=30 tests/`

**Expected measurable result:** The backend test suite completes successfully and the coverage gate enforces at least 30% line coverage for the CnSS codebase.

**Evidence link:** Latest protected-branch CI run showing the CnSS coverage gate result.

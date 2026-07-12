# Quality Requirement Tests (QRT)

This document defines the automated tests and CI checks that verify the measurable scenarios outlined in [docs/quality-requirements.md](quality-requirements.md).

---

## QRT-001: CnSS health API responsiveness

**Linked quality requirement:** QR-001

**Verification method:** Automated integration test.

**Test data, setup, or environment:** CnSS REST API service running against a live TimescaleDB and Redis instance (started via `docker compose -f docker-compose.dev.yml up -d` in CI). A valid admin JWT token is obtained via `POST /api/v1/auth/login` before the health request is made.

**Automated command or CI check:**

```bash
uv run pytest tests/integration/test_api.py::test_api_health_check_healthy -q
```

The test is executed as part of the full coverage gate run in CI:

```bash
uv run pytest --cov=core --cov=services --cov-report=term-missing --cov-fail-under=30 tests/ -q
```

**What is verified:**

1. `GET /api/v1/health` with a valid Bearer token returns `200 OK`.
2. The response body contains `status: "healthy"`, `components.cnss: "active"`, and a `timestamp` field.
3. The total response time is within the 1-second threshold (verified by the synchronous nature of the FastAPI + httpx.AsyncClient test client).

A complementary test (`test_api_health_check_unhealthy`, `test_api_health_check_redis_unhealthy`) verifies that the endpoint returns `503 Unhealthy` when the database or Redis is unavailable, confirming the endpoint correctly reflects degraded state.

**Expected measurable result:** `GET /api/v1/health` returns `200 OK` with valid health fields within 1 second, and all integration tests in the CI coverage gate pass.

**Evidence link:** Latest protected-branch CI run → CnSS Check → "Run coverage gate" step.

---

## QRT-002: JWT scope enforcement

**Linked quality requirement:** QR-002

**Verification method:** Automated integration tests.

**Test data, setup, or environment:** CnSS REST API service running against live TimescaleDB and Redis. Test fixtures create isolated users (`test-viewer`, `test-admin`) and channels (`integration-test-ch-api-*`). Authorized and unauthorized JWT tokens are obtained by calling `POST /api/v1/auth/login` with correct and incorrect credentials respectively. Redis is flushed before and after each test to ensure clean revocation state.

**Automated command or CI check:**

```bash
uv run pytest tests/integration/test_api.py -q
```

Executed as part of the full coverage gate in CI:

```bash
uv run pytest --cov=core --cov=services --cov-report=term-missing --cov-fail-under=30 tests/ -q
```

**What is verified:**

| Test | Assertion |
|---|---|
| `test_api_login_success_viewer` | Viewer login returns `200 OK` with `access_token`, `role: viewer`, correct channel scope |
| `test_api_login_success_admin` | Admin login returns `200 OK` with `role: admin`, all channels in scope |
| `test_api_login_invalid_credentials` | Invalid password returns `401 Unauthorized` with `error: invalid_credentials` |
| `test_api_login_wrong_password` | Wrong password returns `401 Unauthorized` (100% rejection rate) |
| `test_api_token_refresh_lifecycle` | Refresh token cookie issues new access token; logout clears cookie and revokes token |
| `test_api_logout_malformed_cookie` | Malformed refresh cookie does not crash logout (idempotent) |
| `test_api_channels_scope_filtering` | Viewer sees only channels in their scope; admin sees all channels |
| `test_api_channel_status_access_control` | Viewer receives `403 Forbidden` for out-of-scope channel; `200 OK` for in-scope |

**Expected measurable result:** Authorized admin requests succeed; invalid credentials return `401 Unauthorized` with 100% rejection rate; `viewer` scope is strictly limited to authorized channel IDs only; revoked tokens are rejected by the `jwt:revoked` Redis set check.

**Evidence link:** Latest protected-branch CI run → CnSS Check → "Run coverage gate" step.

---

## QRT-003: Critical module unit coverage

**Linked quality requirement:** QR-003

**Verification method:** Automated coverage gate.

**Test data, setup, or environment:** Standard CI environment: Python 3.11, `uv` package manager, live TimescaleDB and Redis instances started via `docker compose -f docker-compose.dev.yml up -d`. Database migrations applied via `alembic upgrade head` before the test run. The full test suite of 253 tests (17 unit modules + 5 integration modules) is executed.

**Automated command or CI check:**

```bash
uv run pytest --cov=core --cov=services --cov-report=term-missing --cov-fail-under=30 tests/ -q
```

**What is verified:**

- The backend test suite (253 tests) completes successfully with zero failures.
- Combined line coverage for `core/` and `services/` packages meets or exceeds the 30% threshold. If coverage drops below 30%, the CI step fails and blocks the merge.
- The 17 unit test modules cover: buffer management, DB helpers, background flusher, WebSocket GC, logging/token masking, Pub/Sub consumer, SQL query builder, subscription hash computation, reporting poller, sequence tracker, session lifecycle, Redis state manager, subscription manager, telemetry SQL handler, UDP server, WebSocket auth, and WebSocket server message handling.
- The 5 integration test modules cover: REST API auth flows, UDP ingestion pipeline, Reporting Worker (all 5 subscription targets), and WebSocket subscription lifecycle end-to-end.

**Expected measurable result:** The backend test suite completes successfully and the coverage gate enforces at least 30% line coverage for the combined `core` and `services` packages.

**Evidence link:** Latest protected-branch CI run → CnSS Check → "Run coverage gate" step.

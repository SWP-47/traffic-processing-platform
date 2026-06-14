# MVP v0 Report

## Overview

*ADD: Purpose and description of MVP v0 foundation*

### Deployment link

[PLACEHOLDER: deployment link or to runnable artifact]()

### Video demonstration

[PLACEHOLDER: video link]()

### Covered User Stories

### Current limitations

*ADD: any current limitations, placeholders or mocks*

## Local setup instructions

[Local setup instructions link](../../README.md#local-setup-instructions)


## Smoke-Check Scenario

### CnSS validation

To validate that the MVP v0 foundation is correctly deployed and operational, perform the following repeatable smoke-check. This applies to both Dev and Prod environments.

### Step 1: Send a Health Check Request
Execute the following `curl` command against the running service:
```bash
curl -v http://localhost:8000/health
```

### Step 2: Verify Expected Results
The request must return an HTTP `200 OK` status and a JSON payload matching the following structure:
```json
{
  "status": "healthy",
  "message": "CnSS server is running",
  "timestamp": "2026-06-13T12:00:00Z"
}
```
*(Note: The `timestamp` will reflect the current UTC time of the server.)*

### Step 3: Verify Logs (Prod Only)
Check the container logs to ensure no startup errors occurred:
```bash
docker-compose -f docker-compose.prod.yml logs cnss
```
*Expected: Logs should show Uvicorn starting successfully on `0.0.0.0:8000` without `ERROR` or `WARNING` levels.*

---
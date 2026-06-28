# MVP v0 Report

## Overview

The purpoes of this MVP is to provide a technical foundation to show that our product is deployable.

### Deployment links

> Demonstration only accessible on local Innopolis University network (*UniversityStudent*).

* [Deployed backend link](http://10.93.26.186:8000/health)
* [Deployed frontend link](http://10.93.26.186/)

### Video demonstration

[Public video demonstration link](https://disk.yandex.ru/i/E_LcHKsMMonegg)

### Covered User Stories

* US-001: Channel Activity Indicator
* US-002: Basic Network Usage Statistics
* US-004: Modular Platform Integration
* US-014: Remote MUI Access
* US-015: Real-time MUI Dashboard Updates

### Current limitations

* API endpoints are currently only placeholders
* MUI Rx/Tx Rate chart shows random numbers, not actual satistics
* MUI Chanel Activity Indicator shows hardcoded status

## Local setup instructions

[Local setup instructions link](../../README.md#local-setup-instructions)

## Smoke-Check Scenario

### Traffic Processor (TP) validation

#### Step 1: Preparation and Execution

Install dependencies using the command:

```bash
pip install -r requirements.txt
```

 run the main script as administrator:

```bash
sudo python3 demo_1/tp_packet_counter.py
```

*Expected: The script starts without errors (e.g., no ModuleNotFoundError). Initidependenciesal initialization messages appear in the console.*

#### Step 2: Packet Transmission and Logging Verification

Observe the terminal output while the script is running.

*Expected: The console regularly displays messages confirming successful network packet transmission. For each sent packet, a brief summary of its contents is printed, allowing for visual verification of the generated data integrity.*

### CnSS validation

To validate that the MVP v0 foundation is correctly deployed and operational, perform the following repeatable smoke-check. This applies to both Dev and Prod environments.

#### Step 1: Send a Health Check Request

Execute the following `curl` command against the running service:

```bash
curl -v http://localhost:8000/health
```

#### Step 2: Verify Expected Results

The request must return an HTTP `200 OK` status and a JSON payload matching the following structure:

```json
{
  "status": "healthy",
  "message": "CnSS server is running",
  "timestamp": "2026-06-13T12:00:00Z"
}
```

*(Note: The `timestamp` will reflect the current UTC time of the server.)*

#### Step 3: Verify Logs (Prod Only)

Check the container logs to ensure no startup errors occurred:

```bash
docker-compose -f docker-compose.prod.yml logs cnss
```

*Expected: Logs should show Uvicorn starting successfully on `0.0.0.0:8000` without `ERROR` or `WARNING` levels.*

### MUI Validation

#### Step 1: Open the URL in any modern browser

*Expected: Dashboard loads without critical console errors.*

#### Step 2: Locate the Channel Activity Indicator and Rx/Tx Rate chart

*Expected: Channel Activity Indicator shows status "Online" and two distinct metric displays are clearly visible on the screen.*

#### Step 3: Observe the dashboard for 5–10 seconds

*Expected: Numerical values or chart bars for Rx/Tx Rate automatically update. This confirms that the interactive data-flow simulation (with random data generated every second) is functioning correctly.*

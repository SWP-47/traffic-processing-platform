# Communication Node

## Setup instructions 

note: The whole CN code was containerised using Docker. The `docket-compose.yml` file for it builds both TP and CN systems simultaniously. 

1. Create a file of environment using command `cp .env.example .env` for bash or `copy .env.example .env` for PowerShell. Edit `.env` file if necessary
2. Navigate to `./cn-tp-deployment` directory
3. Run `docket-compose up --build` command

## Communication Node (CN) Smoke Check
Step 1: Preparation and Execution.
Create .env file and run the Docker
- Expected: The script starts without errors. Initial initialization messages appear in the console.

Step 2: Packet Transmission and Logging Verification.
Observe the terminal output while the script is running.
- Expected: The console regularly displays messages confirming successful network packet transmission from CN


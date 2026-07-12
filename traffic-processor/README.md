# Traffic Processor

This module contains:
- hardware part (`hardware-part` folder) - FPGA source code for transparent packet processing (top module is `top.sv`).
- software part (`software-part` folder) - containerised Python scripts for collecting telemetry and sending data to the Communication Node.

## Local setup instructions 
### Software part:

note: The whole TP code was containerised using Docker. The `docker-compose.yml` file for it builds both TP and CN systems simultaneously. 

1. Create a file of environment using command `cp .env.example .env` for bash or `copy .env.example .env` for PowerShell. Edit `.env` file if necessary
2. Navigate to `./cn-tp-deployment` directory
3. Run `docker-compose up --build` command


### Hardware part:
note: Ensure you have AMD Vivado Design Suite installed on your system. The folder contains `*.sv` and `*.xdc` files which are expected to be used to program ARTIX-7 FPGA Development Board AX7201.

1. Run Vivado IDE and create new project for board ARTIX-7 FPGA Development Board AX7201.
2. Add all `*.sv` files from the `./hardware-part/` folder to project as source code files.
3. Add `top.xdc` file from the `./hardware-part/` folder to project as constraint file.
4. Run synthesis and Implementation process. Then generate bitstream. 
5. Connect FPGA board to your computer using JTAG programmer.
6. Open "Hardware manager" and program connected device using the corresponding button

## Traffic Processor (TP) Smoke Check
Step 1: Preparation and Execution.
Create .env file and run the Docker
- Expected: The script starts without errors. Initial initialization messages appear in the console.

Step 2: Packet Transmission and Logging Verification.
Observe the terminal output while the script is running.
- Expected: The console regularly displays messages confirming successful network packet transmission from TP

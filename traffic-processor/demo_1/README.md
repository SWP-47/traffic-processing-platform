# Traffic Processor

This module contains:
- FPGA source code for transparent packet processing (`top.sv`).
- Python scripts for collecting telemetry and sending data to the Communication Node.

## Local setup instructions 
### Software part:
note: Ensure you have Python 3.8 or higher and pip (Python package installer) installed on your system. Create and activate a virtual environment. 

1. Install dependencies  using command `pip install -r requirements.txt`
2. Create a file of environment using command `cp .env.example .env` for bash or `copy .env.example .env` for PowerShell. Edit `.env` file if necessary
3. Run the main script as administrator using command `sudo python3 .\demo_1\tp_packet_counter.py` for bash or `python3 .\demo_1\tp_packet_counter.py` as administrator for PowerShell


### Hardware part:
note: Ensure you have AMD Vivado Design Suite installed on your system. The folder contains `top.sv` and `top.xdc` files which are expected to be used to program ARTIX-7 FPGA Development Board AX7201.

1. Run Vivado IDE and add `top.sv` as a source file and `top.xdc` as a file with constraints. 
2. Run synthesis and Implementation process. Than generate bitstream. 
3. Connect FPGA board to your computer using JTAG programmer.
4. Open "Hardware manager" and program connected device using the corresponding button

## Traffic Processor (TP) Smoke Check
Step 1: Preparation and Execution.
Install dependencies  using command `pip install -r requirements.txt` and run the main script as administrator (e.g., `sudo python3 .\demo_1\tp_packet_counter.py`).
- Expected: The script starts without errors (e.g., no ModuleNotFoundError). Initial initialization messages appear in the console.

Step 2: Packet Transmission and Logging Verification.
Observe the terminal output while the script is running.
- Expected: The console regularly displays messages confirming successful network packet transmission. For each sent packet, a brief summary of its contents is printed, allowing for visual verification of the generated data integrity.
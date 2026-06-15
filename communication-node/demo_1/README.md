# Communication Node

## Setup instructions 

note: Ensure you have Python 3.8 or higher and pip (Python package installer) installed on your system. Create and activate a virtual environment. 

1. Install dependencies  using command 
```bash
pip install -r requirements.txt 
```
2. Create a file of environment using command 
```bash
cp .env.example .env
```
for bash or 
```PowerShell
copy .env.example .env
```
for PowerShell. Edit `.env` file if necessary

3. Run the main script as administrator using command 
```bash
sudo python3 .\demo_1\cn_packet_counter.py
```
for bash or 
```PowerShell
python3 .\demo_1\cn_packet_counter.py
```
 as administrator for PowerShell

## Communication Node (CN) Smoke Check
Step 1: Preparation and Execution.
Install dependencies  using command `pip install -r requirements.txt` and run the main script as administrator (e.g., `sudo python3 .\demo_1\cn_packet_counter.py`). Then Simulate packet transmission from the TP (or run the TP component in parallel if already configured).
- Expected: The script starts without errors (e.g., no ModuleNotFoundError). Initial initialization messages appear in the console.

Step 2: Batching and Forwarding Verification.
Observe the terminal output while the script is running.
- Expected: 
    1) The console regularly displays messages confirming successful network packet receiving. For each sent packet, a brief summary of its contents is printed. 
    2) The CN accumulates received packets, and approximately once per second, a log message appears confirming the successful transmission of the special management packet to the Control and Status Server (CnSS).


# Traffic Processing Platform

[![Release](https://img.shields.io/github/v/release/SWP-47/traffic-processing-platform?label=MVP%20v1)](https://github.com/SWP-47/traffic-processing-platform/releases/tag/v1.0.0)

## Project Overview

This is a monorepo containing minimally intrusive network traffic monitoring system. It consists of four distinct components designed to capture, process, forward, and visualize network telemetry in real-time without degrading network performance:

- **`traffic-processor/`**: Core packet counting and telemetry engine (transparent inline bridge).
- **`communication-node/`**: Local data forwarding node.
- **`cnss/`**: Control and Status Server (Backend) aggregating data via API/WebSocket.
- **`mui/`**: Management User Interface (Frontend) for real-time visualization.

## Local Setup Instructions

### Prerequisites

- **Git**
- **Python** (3.8+)
- **Node.js** (18+) and **npm**

### 1. Clone the Repository

```bash
git clone https://github.com/<your-org>/traffic-processing-platform.git
cd traffic-processing-platform
```

### 2. Component Setup & Execution

*Note: Run each component in a separate terminal window. Work strictly within your assigned directory.*

#### **Traffic Processor**

##### Software part:
note: Ensure you have Python 3.8 or higher and pip (Python package installer) installed on your system. Create and activate a virtual environment. 

1. Install dependencies  using command `pip install -r requirements.txt`
2. Create a file of environment using command `cp .env.example .env` for bash or `copy .env.example .env` for PowerShell. Edit `.env` file if necessary
3. Run the main script as administrator using command `sudo python3 .\software-part\tp_packet_counter.py` for bash or `python3 .\software-part\tp_packet_counter.py` as administrator for PowerShell


##### Hardware part:
note: Ensure you have AMD Vivado Design Suite installed on your system. The folder contains `top.sv` and `top.xdc` files which are expected to be used to program ARTIX-7 FPGA Development Board AX7201.

1. Run Vivado IDE and add open `ax7201-ethernet-loopback.xpr` project.
2. Run synthesis and Implementation process. Than generate bitstream. 
3. Connect FPGA board to your computer using JTAG programmer.
4. Open "Hardware manager" and program connected device using the corresponding button

#### **Communication node**

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
sudo python3 .\cn_packet_counter.py
```
for bash or 
```PowerShell
python3 .\cn_packet_counter.py
```
 as administrator for PowerShell

#### **Control and Status Server (CnSS)**

##### Local Development (Dev Build)

Use this configuration for active local development. It includes hot-reload capabilities to reflect code changes instantly.

1. Navigate to the `cnss/` directory:

   ```bash
   cd cnss/
   ```

2. (Optional) Create a local `.env` file based on the example:

   ```bash
   cp .env.example .env
   ```

3. Start the development environment:

   ```bash
   docker-compose up --build
   ```

   *The server will be available at `http://localhost:8000`.*

---

##### Production Deployment (VM Build)

Use this configuration for deploying the service on a production Virtual Machine. It is optimized for security (non-root user) and performance (multiple Uvicorn workers).

1. Copy the `cnss/` directory to your target VM.
2. Ensure a `.env` file is present with production-appropriate values (do not use default dev tokens).
3. Start the production environment in detached mode:
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```
4. Verify the container is running and healthy:
   ```bash
   docker-compose -f docker-compose.prod.yml ps
  

#### **Management User Interface (MUI)**

```bash
# Navigate to the MUI directory
cd mui/

# Run Docker with development server (Vite + Hot reload)
# Access at http://localhost:5173 by default
make dev

# Run Docker with production server (Nginx)
# Access at http://localhost:80 by default
make prod

# Follow Docker logs
make logs

# Stop MUI containers
make stop
```

## Links and Reports

- **System Documentation**: [System Documentation](docs/system-documentation.md)
- **API Documentation**: [API Documentation](api/README.md)
- **Current Deployment / Runnable Artifacts**: http://10.93.26.186
- **Week 2 Reports**:
  - [Week 2 Report](reports/week2/README.md)
  - [MVP v0 Report](reports/week2/mvp-v0-report.md)
- **Week 3 Reports:**
  - [Week 3 Report](reports/week3/README.md)

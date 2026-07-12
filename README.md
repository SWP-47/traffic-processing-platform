# Traffic Processing Platform

[![Release](https://img.shields.io/badge/release-v2.0.1-orange)](https://github.com/SWP-47/traffic-processing-platform/releases/tag/v2.0.1)

## Project Overview

This is a monorepo containing a minimally intrusive network traffic monitoring system. It consists of four distinct components designed to capture, process, forward, and visualize network telemetry in real-time without degrading network performance:

- **`traffic-processor/`**: Core packet counting and telemetry engine (transparent inline bridge).
- **`communication-node/`**: Local data forwarding node.
- **`cnss/`**: Control and Status Server (Backend) aggregating data via API/WebSocket.
- **`mui/`**: Management User Interface (Frontend) for real-time visualization.

## Product Access & Handover

- **Live Deployment**: [http://10.93.26.186](http://10.93.26.186) *(Accessible via Innopolis University "UniversityStudent" Network)*
- **Customer Handover Guide**: [docs/customer-handover.md](docs/customer-handover.md) *(Full installation, deployment, and operational instructions)*
- **Hosted Documentation Site**: [https://swp-47.github.io/traffic-processing-platform/](https://swp-47.github.io/traffic-processing-platform/)

## Local Setup Instructions

### Prerequisites

- **Git**
- **Python** (3.8+)
- **Node.js** (18+) and **npm**

### 1. Clone the Repository

```bash
git clone https://github.com/SWP-47/traffic-processing-platform.git
cd traffic-processing-platform
```

### 2. Component Setup & Execution

*Note: Run each component in a separate terminal window. Work strictly within your assigned directory.*

#### **Traffic Processor**

##### Software part

note: Ensure you have Python 3.8 or higher and pip (Python package installer) installed on your system. Create and activate a virtual environment.

1. Navigate to the Traffic Processor software directory:

```bash
cd traffic-processor/software-part
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create an environment file:

```bash
cp .env.example .env
```

or on Windows PowerShell:

```powershell
copy .env.example .env
```

4. Run the main script:

```bash
sudo python3 tp_packet_counter.py
```

or on Windows PowerShell:

```powershell
python3 .\tp_packet_counter.py
```

##### Hardware part

note: Ensure you have AMD Vivado Design Suite installed on your system. The folder contains `*.sv` and `top.xdc` files which are expected to be used to program ARTIX-7 FPGA Development Board AX7201.

1. Run Vivado IDE and create a new project for board ARTIX-7 FPGA Development Board AX7201.
2. Add all `*.sv` files from the `traffic-processor/hardware-part/` folder to the project as source code files.
3. Add `top.xdc` file from the `traffic-processor/hardware-part/` folder to the project as constraint file.
4. Run synthesis and Implementation process. Then generate bitstream.
5. Connect FPGA board to your computer using JTAG programmer.
6. Open "Hardware manager" and program connected device using the corresponding button.

#### **Communication node**

note: Ensure you have Python 3.8 or higher and pip (Python package installer) installed on your system. Create and activate a virtual environment.

1. Navigate to the Communication Node directory:

```bash
cd communication-node/
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create an environment file:

```bash
cp .env.example .env
```

or on PowerShell:

```powershell
copy .env.example .env
```

4. Run the Communication Node script (the actual demo script is `cn_demo_1.py`):

```bash
sudo python3 cn_demo_1.py
```

or on Windows PowerShell:

```powershell
python3 .\cn_demo_1.py
```

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
   make dev-all
   ```

   *The server will be available at `http://localhost:8000`.*

---

##### Production Deployment (VM Build)

Use this configuration for deploying the service on a production Virtual Machine. It is optimized for security (non-root user) and performance (multiple Uvicorn workers).

1. Copy the `cnss/` directory to your target VM.
2. Ensure a `.env` file is present with production-appropriate values (do not use default dev tokens).
3. Start the production environment in detached mode:

   ```bash
   make prod
   ```

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
make down
```

## Maintained Documentation

- **Architecture**: [docs/architecture/README.md](docs/architecture/README.md)
- **System & API Docs**: [docs/system-documentation.md](docs/system-documentation.md) | [api/README.md](api/README.md)
- **Development Process**: [docs/development-process.md](docs/development-process.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Agent Guidance**: [AGENTS.md](AGENTS.md)

## Reports & Changelog

- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Weekly Reports**:
  - [Week 5](reports/week5/README.md) | [Week 4](reports/week4/README.md) | [Week 3](reports/week3/README.md) | [Week 2](reports/week2/README.md)

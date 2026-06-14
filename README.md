# Traffic Processing Platform

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

```bash
# Traffic Processor instructions
```

#### **Communication node**

```bash
# Communication node instructions
```

#### **Control and Status Server (CnSS)**

#### Local Development (Dev Build)

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

#### Production Deployment (VM Build)

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

- **Main Documentation**: [View Main Documentation](docs/README.md) *(Placeholder)*
- **Current Deployment / Runnable Artifacts**: [View Deployment] *(Placeholder)*
- **Week 2 Reports**:
  - [Week 2 Report](reports/week2/README.md)
  - [MVP v0 Report](reports/week2/mvp-v0-report.md)
# Customer Handover Document

## 1. Current Product Status and Handover Scope
**Product Status:** 
The Traffic Processing Platform is fully functional and has been successfully validated in a live testing environment. The core telemetry pipeline (Traffic Processor → Communication Node → Control and Status Server → Management User Interface) is fully operational. The system currently supports transparent inline packet forwarding, real-time bidirectional packet counting, historical data retention via TimescaleDB, and real-time host table visualization.

**Handover Scope:**
This handover includes the complete monorepo source code, Dockerized deployment configurations for all software components (CnSS, MUI, Infrastructure), and comprehensive instructions for deploying the Traffic Processor (TP) and Communication Node (CN) on your hardware. 
* **Note on Physical Hardware:** The physical FPGA development board is currently retained by the development team to finalize remaining software tasks. The full hardware programming guide and bitstream generation instructions are included in this document so you can independently deploy and program the FPGA on your own monitoring device upon final handover.

## 2. How the Customer Accesses and Uses the Product
**Web Interface (MUI):** 
The Management User Interface is accessed via any modern web browser.
* **URL:** `https://<your-domain-or-ip>` (routed through the Edge Nginx reverse proxy, which handles TLS termination).
* **Authentication:** Log in using the provisioned administrative credentials.
* **Usage:** 
  1. Select a monitored channel from the dropdown menu in the header.
  2. View real-time RX/TX packet rates via the column chart or numerical display.
  3. Analyze historical trends using the interactive line chart (supports 1h, 24h, 7d, and 30d views).
  4. Inspect network activity via the Top LAN and Top WAN host tables, which can be expanded to a full paginated view.

**Current Access Method:** 
Currently, you are accessing the deployed Web UI via the university network to test the latest sprint increment. Because the development team retains the physical FPGA hardware for ongoing work, the live channel monitoring is simulated via our test stand. After handover, you will access the UI hosted on your own infrastructure.

## 3. Installation and Deployment Instructions
The platform is designed to be deployed using Docker and Docker Compose. 

### 3.1. Prerequisites
* Docker and Docker Compose installed on the host machine(s).
* Python 3.11+ and [uv](https://github.com/astral-sh/uv) (for local CnSS development/migrations).
* AMD Vivado Design Suite installed on the machine that will program the FPGA.

### 3.2. Backend Deployment (CnSS)

**Getting Started (Setup & Infrastructure):**

1. **Installation**: Install all dependencies (including dev extras for linting and testing) using `uv`:
   ```bash
   make install
   ```
2. **Environment Setup**: Copy the example environment file and adjust the variables if necessary. 
   *Note: For production, ensure you change the `JWT_SECRET_KEY` to a secure, random string.*
   ```bash
   cp .env.example .env
   ```
3. **Running Infrastructure**: Start the required infrastructure services (TimescaleDB, Redis, pgAdmin) in detached mode using Docker Compose:
   ```bash
   make dev
   ```
4. **Database Migrations**: Apply the initial database schema, TimescaleDB hypertables, and continuous aggregates:
   ```bash
   make migrate
   ```

**Production Deployment:**

For production deployment, all services run in Docker containers. Run the following command to build and start the complete stack (including all 4 microservices, TimescaleDB, Redis, and Nginx):
```bash
make prod
```

### 3.3. Frontend Deployment (MUI)
1. Navigate to the frontend directory: `cd mui/`
2. Create the environment file: `cp .env.example .env`
3. Ensure `CNSS_API_BASE_URL` and `CNSS_WS_BASE_URL` point to the correct CnSS backend addresses.
4. Start the production environment: `make prod`

### 3.4. Infrastructure Layer (Edge Nginx)
1. Navigate to the infrastructure directory: `cd infrastructure/`
2. Generate self-signed TLS certificates: `make certs`
3. Start the reverse proxy: `make up`
   * *This connects to the `cnss-network` and `mui-network` Docker networks created in the previous steps.*

### 3.5. Traffic Processor (TP) & Communication Node (CN) Deployment

**Software Part:**
*Note: The whole TP and CN code is containerized using Docker. The `docker-compose.yml` file builds both TP and CN systems simultaneously.*
1. Navigate to the joint deployment directory: `cd cn-tp-deployment/`
2. Create the environment files for both components using the command `cp .env.example .env` (for bash) or `copy .env.example .env` (for PowerShell). Edit the `.env` files if necessary to configure network interfaces and IP addresses.
3. Build and run the containers using the command: `docker-compose up --build`

**Hardware Part (FPGA Programming):**
*Note: Ensure you have AMD Vivado Design Suite installed on your system. The folder `viva.zip` contains compiled Vivado project which is expected to be used to program the ARTIX-7 FPGA Development Board AX7201.*
0. Download `viva.zip` file and extract all files from it into `viva` (for example) folder.
1. Run Vivado IDE and open project. Navigate to `viva` folder and choose `ax7201-ethernet-loopback.xpr` file.
2. Connect the FPGA board to your computer using a JTAG programmer.
3. Open "Hardware Manager" and program the connected device using the corresponding button.
4. Connect LAN to Ethernet1, OUT sniffering interface of TP-CN device to Ethernet2, IN sniffering interface of TP-CN device to Ethernet3, WAN to Ethernet4. These Ethernets are phisical Ethernet chips on FPGA board, their names are printed on the board

## 4. Required Configuration and Secrets Handling
* **Environment Variables:** All components use `.env` files (which are strictly ignored by Git). Templates are provided as `.env.example`.
* **Secrets Management:** 
  * `JWT_SECRET_KEY` (CnSS): Must be changed from the default development value before production deployment to prevent token forgery.
  * Database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`): Configured in `cnss/.env`.
* **Network Configuration:** The TP and CN require precise mapping to the physical Ethernet interfaces of the host machine (e.g., `eth1`, `eth2`). These must be verified using `ip a` or `ifconfig` on the target hardware before launching the containers to ensure packets are captured correctly.

## 5. Operational Notes for Normal Use
* **Channel Activity:** The MUI dynamically discovers active channels. A channel is marked "active" if telemetry is received within a 5-second window.
* **Data Retention:** Raw packet metadata is stored in TimescaleDB with a default retention policy of 7 days. Older data is automatically purged to prevent disk exhaustion.
* **Redis Ephemeral Mode:** Redis is configured without persistence (no RDB/AOF) to maximize IOPS. If the Redis container restarts, unflushed UDP buffers and sequence states are lost. The system is designed to gracefully reset sequence baselines and resume ingestion automatically without manual intervention.

## 6. Troubleshooting and Support Guidance
* **502 Bad Gateway on `/` or `/api/`**: Ensure the MUI and CnSS containers are running and healthy (`docker ps`). The Edge Nginx proxy requires the `mui-network` and `cnss-network` Docker networks to be active.
* **WebSocket Disconnects / Auth Errors (4001)**: Check if the JWT token has expired (default 24h) or if the `jwt:revoked` set in Redis contains the token's `jti` (e.g., after a logout).
* **No Telemetry Data:** Verify that the TP and CN are correctly capturing packets on the specified network interfaces. Check CnSS Ingestion Worker logs (`docker logs cnss-ingestion`) for UDP reception errors.

## 7. Known Limitations, Unfinished Areas, and Important Risks
* **FPGA Hardware Retention:** The physical FPGA board is currently retained by the development team. You will need to program and set up the hardware on your own device using the Vivado instructions provided in Section 3.5.
* **Hardware Button Debounce:** The physical button (Key1) on the FPGA board used for hardware traffic blocking currently suffers from contact bounce (debounce issue), which may trigger multiple unintended state toggles.
* **System Crash on Interface Disconnect:** If the physical Ethernet cable connected to the FPGA/TP is unplugged and reconnected, the system may experience state corruption or stop transmitting data, requiring a manual container restart.
* **Docker/Ubuntu Compatibility:** The Dockerized TP and CN containers have known compatibility issues with the specific Ubuntu version currently running on the physical monitoring stand. (Currently bypassed by running scripts directly on the host, but Docker is the intended deployment method for your new hardware).
* **UI Filtering:** The host table filtering in the MUI currently relies on strict text-based syntax (e.g., `location: LAN`), which is not user-friendly. Structured UI controls (dropdowns/sidebars) are planned for a future update.

## 8. Current Handover Status
**Handover Level:** `Deployed or operated on customer side`

*Context:* The customer has tested the deployed setup and accessed the Web UI to validate the previous sprint increment. However, because the development team retains the physical FPGA hardware to finalize software tasks, the customer has not yet completely set up the hardware to monitor their own live channel activity. Upon final handover, the customer will independently deploy the FPGA on their own device.

## 9. Remaining Actions
* **Customer Action:** Program the ARTIX-7 FPGA board using the provided Vivado instructions and deploy the TP/CN software on the target monitoring hardware.
* **Team Action:** Provide final support for any Vivado compilation or network interface mapping issues during your independent hardware setup.
* **Blockers:** None. The software is fully ready; the remaining action is purely the physical hardware deployment on the customer's side.

## 10. Links to Related Documentation
* [System Architecture & Data Flow Specification](../docs/system-documentation.md)
* [API Documentation](../cnss/docs/api.md)
* [Project Roadmap](../docs/roadmap.md)
* [User Acceptance Tests & Known Issues](../docs/user-acceptance-tests.md)
* [Local Setup & Deployment Guide](../README.md)

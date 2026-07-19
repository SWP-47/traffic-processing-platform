# Customer Handover Document

## 1. Current Product Status and Handover Scope

**Product Status:**  
The Traffic Processing Platform is fully functional, stable, and has been successfully validated in a live testing environment. The core telemetry pipeline (Traffic Processor → Communication Node → Control and Status Server → Management User Interface) is fully operational. The system supports transparent inline packet forwarding, real-time bidirectional packet and byte-volume counting, historical data retention via TimescaleDB, dynamic IP-based traffic blocking, and real-time host table visualization. Recent stress testing has verified system stability at sustained throughput up to 588 Mbps.

**Handover Scope:**  
This handover includes the complete monorepo source code, automated Dockerized deployment configurations for all software components, and comprehensive instructions for deploying and programming the Traffic Processor (TP) and Communication Node (CN) on your hardware. The product is now ready for independent customer use.

## 2. How the Customer Accesses and Uses the Product

**Web Interface (MUI):**  
The Management User Interface is accessed via any modern web browser.

* **URL:** `https://<your-domain-or-ip>` (routed through the Edge Nginx reverse proxy, which handles TLS termination).
* **Authentication:** Log in using the provisioned administrative credentials. *Note: The system now features automatic session persistence; refreshing the page will maintain your authenticated session without requiring re-login.*
* **Usage:**
  1. Select a monitored channel from the dropdown menu in the header.
  2. View real-time RX/TX rates via the column chart or numerical display. Use the new toggle to switch between **packets per second** and **bytes per second** (bps, Kbps, Mbps) for more accurate asymmetric traffic analysis.
  3. Analyze historical trends using the interactive line chart.
  4. Inspect network activity via the Top LAN and Top WAN host tables. Click on any specific host to view detailed statistics, including Top Destinations and Top Ports.

## 3. Installation and Deployment Instructions

The platform is designed for streamlined deployment using Docker, Docker Compose, and automated helper scripts.

### 3.1. Prerequisites

* Docker and Docker Compose installed on the host machine(s).
* Python 3.11+ and [uv](https://github.com/astral-sh/uv) (for local CnSS development/migrations).
* AMD Vivado Design Suite installed on the machine that will program the FPGA.

### 3.2. Backend Deployment (CnSS)

We have introduced an **interactive deployment script** to eliminate manual database migrations and environment setup.

1. Navigate to the `cnss/` directory.
2. Run the interactive deployment command:

   ```bash
   make deploy
   ```

3. Follow the on-screen prompts. The script will automatically:
   * Warn and safely stop any existing containers, removing old networks and volumes.
   * Start the required infrastructure services (TimescaleDB, Redis, pgAdmin).
   * Copy the `.env.example` to `.env` and generate a secure, random `JWT_SECRET_KEY`.
   * Automatically wait for the database to be ready and execute all necessary schema migrations and TimescaleDB hypertable setups.
   * Prompt you to optionally seed the database with default test users (`admin` and `viewer`).
4. Select your deployment type (`development` or `production`) when prompted to start the complete stack.

*(Optional) CLI User Management:* You can add or manage users directly via the CLI tool provided in the CnSS directory, which securely hashes passwords and updates the database.

### 3.3. Frontend Deployment (MUI)

1. Navigate to the frontend directory: `cd mui/`
2. Start the production environment: `make prod`

### 3.4. Infrastructure Layer (Edge Nginx)

1. Navigate to the infrastructure directory: `cd infrastructure/`
2. Generate self-signed TLS certificates: `make certs`
3. Start the reverse proxy: `make up`  
   *(This connects to the `cnss-network` and `mui-network` Docker networks created in the previous steps.)*

### 3.5. Traffic Processor (TP) & Communication Node (CN) Deployment

**Software Part:**  
The TP and CN code is fully containerized.

1. Navigate to the joint deployment directory: `cd cn-tp-deployment/`
2. Create the environment files: `cp .env.example .env` (bash) or `copy .env.example .env` (PowerShell). Edit the `.env` files to configure the correct physical network interfaces (e.g., `eth1`, `eth2`) for your specific hardware.
3. Build and run the containers: `docker-compose up --build`

**Hardware Part (FPGA Programming & Dynamic Blocking):**  

1. Download and extract the `viva.zip` file containing the compiled Vivado project for the ARTIX-7 FPGA Development Board AX7201.
2. Run Vivado IDE and open the `ax7201-ethernet-loopback.xpr` project.
3. Connect the FPGA board to your computer using a JTAG programmer.
4. Open "Hardware Manager" and program the connected device.
5. **Cable Mapping:** Connect LAN to Ethernet1, OUT sniffing interface to Ethernet2, IN sniffing interface to Ethernet3, and WAN to Ethernet4 (names are printed on the board).
6. **Dynamic IP Blocking:** A script is now available on the FPGA environment to dynamically set the target IP for traffic blocking. By default, it is set to `0.0.0.0` (no blocking). You can input any specific IP address (e.g., a laptop or proxy IP) to instantly block its traffic, which will be reflected as a drop to zero packets in the MUI.

## 4. Required Configuration and Secrets Handling

* **Environment Variables:** All components use `.env` files (strictly ignored by Git). Templates are provided as `.env.example`.
* **Secrets Management:**
  * The `make deploy` script now auto-generates a secure `JWT_SECRET_KEY`. Do not use the default development value in production.
  * Database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`) are managed securely within `cnss/.env`.
* **Network Configuration:** The TP and CN require precise mapping to the physical Ethernet interfaces of the host machine. Verify interface names using `ip a` or `ifconfig` on the target hardware before launching the containers to ensure packets are captured correctly.

## 5. Operational Notes for Normal Use

* **Channel Activity:** The MUI dynamically discovers active channels. A channel is marked "active" if telemetry is received within a 5-second window.
* **Data Retention:** Raw packet metadata is stored in TimescaleDB with a default retention policy of 7 days. Older data is automatically purged to prevent disk exhaustion.
* **Redis Ephemeral Mode:** Redis is configured without persistence (no RDB/AOF) to maximize IOPS. If the Redis container restarts, unflushed UDP buffers and sequence states are lost. The system is designed to gracefully reset sequence baselines and resume ingestion automatically without manual intervention.

## 6. Troubleshooting and Support Guidance

* **502 Bad Gateway on `/` or `/api/`**: Ensure the MUI and CnSS containers are running and healthy (`docker ps`). The Edge Nginx proxy requires the `mui-network` and `cnss-network` Docker networks to be active.
* **WebSocket Disconnects / Auth Errors (4001)**: Check if the JWT token has expired (default 24h) or if the `jwt:revoked` set in Redis contains the token's `jti` (e.g., after a logout).
* **No Telemetry Data**: Verify that the TP and CN are correctly capturing packets on the specified network interfaces. Check CnSS Ingestion Worker logs (`docker logs cnss-ingestion`) for UDP reception errors.
* **Missing ICMP Data in Port Stats**: ICMP (ping) packets do not contain source or destination port information. Due to strict typing in the current telemetry pipeline, these packets are intentionally excluded from port-specific statistics, though they are still counted in overall packet/byte volumes.

## 7. Known Limitations and Important Risks

* **Hardware Button Debounce**: The physical button (Key1) on the FPGA board used for hardware traffic blocking may occasionally experience contact bounce, which can trigger multiple unintended state toggles. Using the dynamic IP blocking script is the recommended method for precise control.
* **UI Filtering**: The host table filtering in the MUI currently relies on text-based syntax (e.g., `location: LAN`). While functional, structured UI controls (dropdowns/sidebars) are planned for a future post-course update to improve user experience.
* **Extreme Load Thresholds**: The system has been stress-tested and verified stable up to **588 Mbps**. Sustained traffic significantly beyond this threshold may require monitoring of the CN/CnSS queue limits, though normal enterprise network loads are well within safe operating margins.

## 8. Current Handover Status

**Handover Level:** `Ready for independent use`  
**Customer Confirmation Status:** `Accepted`

*Context:* The customer has reviewed the final `MVP v3` increment, tested the deployed setup, and validated the updated customer-facing documentation. The customer has explicitly confirmed that the product is ready for independent use and accepts the current handover scope. All core software components, deployment automation, and hardware programming guides have been transferred.

## 9. Remaining Actions

* **Customer Action:** Independently deploy the TP/CN software and program the ARTIX-7 FPGA board on your target monitoring hardware using the provided instructions.
* **Team Action:** The development team remains available to provide final, time-bound support for any Vivado compilation or network interface mapping issues encountered during your independent hardware setup.
* **Blockers:** None. The software and documentation are fully complete and handed over.

## 10. Links to Related Documentation

* [System Architecture & Data Flow Specification](../docs/system-documentation.md)
* [API Documentation](../api/README.md)
* [Project Roadmap](../docs/roadmap.md)
* [User Acceptance Tests & Known Issues](../docs/user-acceptance-tests.md)
* [Local Setup & Deployment Guide](../README.md)
* [Contributor Guide](../CONTRIBUTING.md)
* [Agent Guide](../AGENTS.md)

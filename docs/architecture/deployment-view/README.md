# Deployment View — Infrastructure Topology

## Diagram

The deployment diagram ([deployment-diagram.puml](deployment-diagram.puml)) illustrates the physical and logical deployment topology of the Traffic Processing Platform on a production Virtual Machine (VM) hosted at Innopolis University.

## What the Diagram Shows

### Deployment Node

The entire platform is deployed on a **single production VM** with the following characteristics:

- **Public IP**: `10.93.26.186` (accessible only within the Innopolis University "UniversityStudent" network)
- **Operating System**: Linux (Ubuntu/Debian-based)
- **Container Runtime**: Docker + Docker Compose
- **Network Mode**: Mixed (bridge for CnSS/MUI, host for TP/CN)

### Layered Architecture

The deployment is organized into **four distinct layers**, each with its own Docker network and responsibilities:

#### 1. Infrastructure Layer (Edge Nginx)

- **Component**: `edge-nginx` (Nginx Alpine)
- **Ports**: 80 (HTTP redirect), 443 (HTTPS/WSS)
- **Networks**: `cnss-network`, `mui-network` (external)
- **Responsibilities**:
  - **TLS Termination**: Single entry point for all encrypted traffic. Uses self-signed certificates for development (generated via `make certs`) or CA-signed certificates for production.
  - **Routing**: Routes `/` to MUI, `/api/` to CnSS REST API, `/api/v1/ws/` to CnSS WebSocket Service.
  - **Security**: Masks tokens in access logs using a custom `log_format` that logs `$uri` instead of `$request_uri`. Adds HSTS, X-Frame-Options, and X-Content-Type-Options headers.
  - **Error Handling**: Returns 503 with a custom JSON message if MUI or CnSS is unavailable.

#### 2. CnSS Backend Layer (cnss-network)

- **Components**: `cnss-api`, `cnss-websocket`, `cnss-ingestion`, `cnss-reporting`, `timescaledb`, `redis`, `pgadmin`
- **Network**: `cnss-network` (bridge, internal)
- **Restart Policy**: `always` (Docker automatically restarts crashed containers)

**Service Details**:

| Service | Image | Ports | Volumes | Description |
|---------|-------|-------|---------|-------------|
| `cnss-api` | Custom (FastAPI) | 8000 (internal) | — | REST API, authentication, channel discovery, history |
| `cnss-websocket` | Custom (websockets) | 8001 (internal) | — | WebSocket gateway, session management, subscriptions |
| `cnss-ingestion` | Custom (asyncio) | 5140/udp (host) | — | UDP telemetry ingestion, buffering, flushing |
| `cnss-reporting` | Custom (asyncio) | — | — | 1Hz polling, SQL execution, Pub/Sub publishing |
| `timescaledb` | `timescale/timescaledb:latest-pg15` | 5432 (internal) | `timescaledb_data` (persistent) | Time-series database, continuous aggregates |
| `redis` | `redis:7-alpine` | 6379 (internal) | — | Ephemeral state, buffering, pub/sub (no persistence) |
| `pgadmin` | `dpage/pgadmin4:latest` | 5050 (internal) | — | Database management UI (dev/debug only) |

#### 3. MUI Frontend Layer (mui-network)

- **Component**: `mui` (Nginx + React SPA)
- **Network**: `mui-network` (bridge, internal)
- **Port**: 80 (internal)
- **Responsibilities**: Serves the React single-page application. In production, Edge Nginx handles all routing, so the MUI container only serves static files.

#### 4. Traffic Processor + Communication Node Layer (host network)

This layer implements a **two-tier architecture** for minimally intrusive network monitoring:

##### Hardware Data Plane (FPGA)

- **Component**: ARTIX-7 AX7201 FPGA
- **Role**: Transparent inline bridge operating at wire speed
- **Responsibilities**:
  - **Packet Forwarding**: Receives network packets from LAN interface and forwards them to WAN interface (and vice versa) with negligible latency
  - **Traffic Mirroring**: Duplicates all passing packets and sends them to the software TP component for metadata extraction
  - **Zero-Impact Operation**: Operates independently of all software components; failure in monitoring software has **no impact** on core packet forwarding (US-005, US-007, US-009)

##### Software Telemetry Plane (TP)

- **Component**: `tp` (Python + Scapy)
- **Network Mode**: `host` (direct access to physical network interfaces)
- **Privileged**: `true` (required for raw socket access and packet sniffing)
- **Responsibilities**:
  - **Metadata Extraction**: Receives mirrored traffic from FPGA, extracts packet metadata (source/destination IPs, ports, direction)
  - **Local Dispatch**: Forwards extracted metadata to the Communication Node (CN) via local UDP/IPC
  - **Non-Blocking**: Operates asynchronously; if TP crashes, FPGA continues forwarding packets uninterrupted

##### Communication Node (CN)

- **Component**: `cn` (Python + Scapy)
- **Network Mode**: `host` (direct access to physical network interfaces)
- **Privileged**: `true` (required for raw socket access)
- **Responsibilities**:
  - **Telemetry Batching**: Receives raw packet metadata from TP and aggregates it into `TelemetryBatch` payloads
  - **Window Management**: Groups packets into fixed time windows (configurable via `TIME_WINDOW`, default 500ms)
  - **MTU Enforcement**: Ensures serialized JSON payloads do not exceed 1400 bytes to prevent IP fragmentation and silent UDP drops
  - **Remote Dispatch**: Sends `TelemetryBatch` to CnSS Ingestion Worker via UDP (port 5140)
  - **Sequence Tracking**: Maintains monotonically increasing 64-bit sequence counters per channel for drop detection

### Data Flow

```
User Traffic → FPGA (Hardware Data Plane)
                ↓ (wire-speed forwarding)
               WAN (Internet)
                ↓ (mirrored traffic)
         Software TP (Metadata Extraction)
                ↓ (raw packet metadata)
         CN (Batching + Sequence Tracking)
                ↓ (UDP 5140)
         CnSS Ingestion (Redis buffer)
                ↓ (batch flush)
         TimescaleDB (persistent storage)
                ↓ (1Hz polling)
         CnSS Reporting (SQL → Pub/Sub)
                ↓ (Redis Pub/Sub)
         CnSS WebSocket (push to client)
                ↓ (WSS via Nginx)
         MUI (real-time dashboard)
```

## Why This Deployment Model Was Chosen

### 1. Single VM Deployment

**Rationale**: The platform is deployed on a single VM to simplify operations, reduce infrastructure costs, and meet the course requirements (Innopolis University provides a single VM for the project).

**Trade-offs**:
- **Pros**: Simple to manage, low cost, easy to debug.
- **Cons**: Single point of failure. If the VM crashes, the entire platform is unavailable. No horizontal scaling across multiple nodes.

**Mitigation**: Docker's `restart: always` policy ensures that individual containers are automatically restarted if they crash. TimescaleDB data is persisted on a Docker volume, so it survives container restarts. The FPGA hardware data plane operates independently, so even if all software components fail, user internet connectivity remains unaffected.

### 2. Two-Tier TP Architecture (Hardware + Software)

**Rationale**: The separation of the Traffic Processor into hardware (FPGA) and software (Python + Scapy) components is the foundational architectural decision that enables **zero-impact monitoring**.

**Trade-offs**:
- **Pros**: 
  - Wire-speed packet forwarding with negligible latency
  - Complete fault isolation: software failures cannot disrupt user traffic
  - Hardware-accelerated processing for high-throughput scenarios
- **Cons**: 
  - Requires specialized FPGA hardware (ARTIX-7 AX7201)
  - More complex deployment and debugging (hardware + software stack)
  - Limited flexibility compared to pure software solutions (FPGA logic is harder to modify)

**Mitigation**: The software TP component is designed to be stateless and restartable. If it crashes, the FPGA continues forwarding packets, and the TP can be restarted without any manual intervention. The CN component handles sequence tracking to detect and report any telemetry gaps.

### 3. Docker Compose Orchestration

**Rationale**: Docker Compose provides a declarative way to define and manage multi-container applications. It simplifies deployment, ensures reproducibility, and enables easy rollback.

**Trade-offs**:
- **Pros**: Easy to deploy, version-controlled configuration, automatic dependency management.
- **Cons**: Not suitable for large-scale production deployments (Kubernetes would be better for that). Limited orchestration capabilities (no auto-scaling, no service mesh).

### 4. Separate Docker Networks

**Rationale**: The CnSS and MUI services are deployed on separate Docker networks (`cnss-network` and `mui-network`) to enforce network isolation. Edge Nginx connects to both networks, acting as the only bridge between them.

**Trade-offs**:
- **Pros**: Enhanced security (MUI cannot directly access CnSS internal services), clear separation of concerns.
- **Cons**: Slightly more complex networking setup. Requires careful management of network dependencies.

### 5. Host Network Mode for TP/CN

**Rationale**: The Traffic Processor and Communication Node require direct access to physical network interfaces for packet sniffing and forwarding. Docker's bridge network mode would add unnecessary overhead and complexity.

**Trade-offs**:
- **Pros**: Zero network overhead, direct access to physical interfaces, simplified configuration.
- **Cons**: Less isolation (TP/CN share the host's network stack), potential security risks if TP/CN are compromised.

**Mitigation**: TP and CN run in privileged containers with minimal attack surface. They only expose local UDP/IPC interfaces and do not listen on external ports. Network-level ACLs should restrict access to the VM.

### 6. Ephemeral Redis

**Rationale**: Redis is explicitly configured without persistence (no RDB snapshots, no AOF) to maximize IOPS and prevent disk-write bottlenecks. TimescaleDB is the single source of truth for persistent data.

**Trade-offs**:
- **Pros**: Maximum performance, no disk I/O overhead, simple configuration.
- **Cons**: If Redis restarts, unflushed UDP buffers and sequence states are lost. This is an accepted trade-off for performance.

**Mitigation**: The Ingestion Worker uses capped Redis lists (`LTRIM` at 100,000 items) to prevent OOM crashes. Sequence tracking is designed to gracefully handle resets (CN reboot detection when `last_sequence - incoming_sequence > 1,000,000`).

## Operational Considerations

### 1. FPGA Hardware Management

- **Firmware Updates**: FPGA firmware updates require careful planning and testing. Always have a rollback plan.
- **Hardware Monitoring**: Monitor FPGA temperature, power consumption, and error rates via hardware-specific tools.
- **Traffic Mirroring**: Ensure the FPGA is correctly configured to mirror all traffic (both directions) to the software TP. Misconfiguration can lead to incomplete telemetry data.

### 2. TLS Certificate Management

- **Development**: Self-signed certificates are generated via `make certs` and distributed to LAN clients via `make serve-certs`. Clients must install the certificate into their system's trust store to avoid browser security warnings.
- **Production**: Certificates from a trusted Certificate Authority (e.g., Let's Encrypt, internal corporate CA) must be used. Self-signed certificates are **never** acceptable in production.

### 3. Database Growth Monitoring

- TimescaleDB data is automatically retained for 7 days (configurable via `RETENTION_DAYS` in `.env`).
- The customer advised monitoring Docker volume statistics to build intuition about disk usage (e.g., how many megabytes 100k+ rows consume).
- **Action**: Regularly check `docker volume ls` and `docker system df` to monitor storage consumption.

### 4. Redis Memory Management

- Redis is configured with `maxmemory 2gb` and `maxmemory-policy noeviction`.
- The Ingestion Worker explicitly caps the UDP buffer lists using `LTRIM` (max 100,000 items per channel).
- If Redis reaches the memory limit, new writes will fail with an OOM error. The Ingestion Worker will log the error and drop new packets.
- **Action**: Monitor Redis memory usage via `redis-cli INFO memory` and adjust `maxmemory` if necessary.

### 5. Container Health Checks

- TimescaleDB and Redis have Docker health checks configured to ensure they are ready before dependent services start.
- **Action**: Use `docker-compose ps` to verify that all containers are healthy before accessing the platform.

### 6. Log Management

- All containers log to stdout/stderr, which Docker captures and makes available via `docker-compose logs`.
- Edge Nginx uses a custom `log_format` that masks tokens in access logs.
- CnSS services use a custom `TokenMaskingFilter` to redact tokens in application logs.
- **Action**: Regularly review logs for errors, warnings, and security incidents. Consider integrating with a log aggregation system (e.g., ELK Stack, Grafana Loki) for production deployments.

### 7. Backup and Recovery

- **TimescaleDB**: The `timescaledb_data` volume is persistent and survives container restarts. However, it is not automatically backed up.
- **Action**: Implement a backup strategy (e.g., `pg_dump` cron job, TimescaleDB continuous backups) to prevent data loss in case of VM failure.
- **Redis**: No backup is needed, as Redis is ephemeral. If Redis restarts, the system gracefully resets sequence baselines and resumes ingestion.
- **FPGA Configuration**: Document FPGA firmware version and configuration settings. Maintain a backup of the FPGA bitstream for quick recovery.

### 8. Scaling Considerations

- **Current Limitation**: The single-VM deployment does not support horizontal scaling. If the CnSS becomes a bottleneck, the only option is to vertically scale the VM (add more CPU/RAM).
- **Future Improvement**: Migrate to Kubernetes or Docker Swarm to enable horizontal scaling of CnSS microservices. Use a load balancer (e.g., HAProxy, AWS ALB) to distribute WebSocket connections across multiple WebSocket Service instances.
- **FPGA Scaling**: If traffic volume exceeds FPGA capacity, consider deploying multiple FPGA instances with load balancing at the network level.

### 9. Security Hardening

- **Firewall**: Restrict access to port 443 (HTTPS/WSS) and port 5140/udp (CN → CnSS) to known IP addresses.
- **SSH Access**: Disable password-based SSH authentication. Use SSH keys only.
- **Docker Security**: Run containers as non-root users where possible. Use Docker's `--read-only` flag for containers that don't need to write to the filesystem.
- **Secrets Management**: Move sensitive configuration (e.g., `JWT_SECRET_KEY`, database passwords) to a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager) instead of `.env` files.
- **FPGA Access**: Restrict physical and logical access to the FPGA hardware. Use hardware security modules (HSM) for firmware signing if available.

### 10. Network Performance Monitoring

- **FPGA Throughput**: Monitor the FPGA's packet forwarding rate and latency. Ensure it meets wire-speed requirements for the deployed network.
- **TP Extraction Rate**: Monitor the software TP's metadata extraction rate. If it falls behind the FPGA's forwarding rate, telemetry data will be incomplete.
- **CN Batching Efficiency**: Monitor the CN's batching window (`TIME_WINDOW`) and payload size. Adjust the window size to balance between latency and payload efficiency.
- **UDP Packet Loss**: Monitor the `dropped_batches` metric in `telemetry_update` payloads to detect UDP datagram losses between CN and CnSS.

## Failure Modes and Recovery

| Failure Mode | Impact | Recovery Mechanism |
|--------------|--------|-------------------|
| **FPGA hardware failure** | Complete network disruption | Hardware replacement required; FPGA should be configured with redundant power supplies and monitoring |
| **FPGA firmware crash** | Network disruption until reboot | Automatic hardware watchdog should reboot FPGA; manual intervention may be required |
| **TP software crash** | Telemetry stops; traffic continues | FPGA continues forwarding; Docker restart policy restarts TP container; CN detects sequence gap |
| **CN crash** | Telemetry stops for that channel | Reporting Worker detects 5s timeout, broadcasts `is_active: false`; Docker restarts CN; CnSS detects sequence reset on recovery |
| **CnSS Ingestion crash** | UDP packets dropped | Docker `restart: always`; Redis buffers persist (if Redis is up); CN continues sending, packets silently lost during downtime |
| **Redis crash** | All buffering, state, Pub/Sub lost | Redis restarts; sequence baselines reset; Ingestion resumes; accepted trade-off for performance |
| **TimescaleDB crash** | Persistence and aggregation fail | Ingestion continues buffering in Redis (capped at 100k); Reporting Worker skips SQL queries; WebSocket pushes last known state |
| **WebSocket Service crash** | Active connections dropped | Session keys expire (TTL 10s); Ghost Cleaner removes stale listeners; clients reconnect and re-subscribe |
| **Reporting Worker crash** | No real-time updates for 1s intervals | Docker restart policy; clients continue receiving last known state; MUI fallback timeout triggers `is_active: false` |
| **Network partition (CN → CnSS)** | UDP packets lost | Sequence tracking makes losses visible via `dropped_batches` metric; no retry mechanism (fire-and-forget design) |
| **MUI browser crash** | Client disconnects | WebSocket session expires via TTL; Garbage Collector cleans up subscriptions; no server-side state leak |

## Conclusion

This deployment topology demonstrates how the Traffic Processing Platform achieves its core design goals through a carefully orchestrated combination of hardware and software components:

- **Zero-Impact Monitoring**: The FPGA hardware data plane ensures that user traffic flows uninterrupted, even if all software monitoring components fail.
- **High-Performance Telemetry**: The two-tier TP architecture (FPGA + software) enables wire-speed packet forwarding while extracting detailed metadata for analysis.
- **Scalable Backend**: The CnSS microservices architecture, backed by Redis and TimescaleDB, provides high-throughput ingestion and real-time aggregation.
- **Operational Resilience**: Docker's restart policies, TTL-based session management, and sequence tracking ensure graceful degradation under failure conditions.
- **Security by Design**: JWT authentication, scope-based authorization, TLS termination, and log sanitization protect sensitive data and prevent unauthorized access.

The single-VM deployment model is appropriate for the current scale and course requirements, but the architecture is designed to support future scaling through container orchestration and horizontal expansion of CnSS microservices.
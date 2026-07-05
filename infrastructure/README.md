# Infrastructure Layer (Edge Nginx)

The `infrastructure/` directory contains the **Edge Reverse Proxy** — a single, unified entry point for the entire platform. It handles TLS termination and routes traffic to MUI (frontend) and CnSS (backend).

## Architecture

```
Client (Browser)
        │
        │  HTTPS / WSS (port 443)
        ▼
┌─────────────────────────────────┐
│   Edge Nginx                    │
│   - TLS Termination             │
│   - Token Masking               │
└─────────────────────────────────┘
        │            │
        ▼            ▼
   ┌────────┐  ┌──────────┐
   │  MUI   │  │ CnSS API │
   │ (80)   │  │ (8000)   │
   └────────┘  └──────────┘
```

## Prerequisites

**Before starting the Infrastructure layer, you MUST run:**

1. **CnSS Backend:**
   ```bash
   cd cnss
   make prod
   ```

2. **MUI Frontend:**
   ```bash
   cd mui
   make prod
   ```

This creates the required Docker networks (`cnss-network` and `mui-network`) that Edge Nginx connects to.

## Quick Start

```bash
# 1. Generate TLS certificates (if not already done)
make certs

# 2. Start Edge Nginx
make up

# 3. Access the platform
#    Open https://localhost in your browser
```

## Available Commands

| Command            | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `make certs`       | Generate self-signed TLS certificate for `localhost` and `127.0.0.1`.       |
| `make serve-certs` | Start HTTP server on port `9000` to distribute the certificate to LAN clients. |
| `make up`          | Start Edge Nginx in detached mode.                                          |
| `make down`        | Stop and remove Edge Nginx container.                                       |
| `make restart`     | Restart Edge Nginx (useful after editing `nginx.conf`).                     |
| `make logs`        | Follow Edge Nginx logs in real-time.                                        |
| `make status`      | Show the status of infrastructure containers.                               |

## Troubleshooting

### Error: `network mui-network not found`

MUI is not running. Start it first:

```bash
cd ../mui
make prod
```

### Error: `network cnss-network not found`

CnSS is not running. Start it first:

```bash
cd ../cnss
make prod
```

### 502 Bad Gateway on `/`

MUI container is not responding. Check its status:

```bash
docker ps | grep mui
```

### 502 Bad Gateway on `/api/` or `/ws/`

CnSS services are not running or not healthy. Check their status:

```bash
docker ps | grep cnss
```
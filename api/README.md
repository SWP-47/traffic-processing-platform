# API Documentation

## Placeholders

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{cnss_host}}` | CnSS server hostname/IP | `cnss.example.com` |
| `{{cnss_udp_port}}` | UDP port for CN ingestion | `5140` |
| `{{cnss_ws_port}}` | WebSocket port for MUI | `8443` |
| `{{access_token}}` | Bearer token for authenticated endpoints | `eyJhbG...` |
| `{{channel_id}}` | Identifier for the monitored bridge | `primary-bridge-01` |

---

## 1. CN to CnSS (UDP)

### Transport

- **Protocol**: UDP
- **Endpoint**: `{{cnss_host}}:{{cnss_udp_port}}`
- **Direction**: CN → CnSS (unidirectional)
- **Reliability**: Best-effort. No ACK required. CN must handle silent drops by simply sending the next batch.
- **Encoding**: JSON, UTF-8, single datagram per batch.

### Payload Schema: `TelemetryBatch`

```json
{
  "channel_id": "{{channel_id}}",
  "sequence": 1042,
  "window_ms": 500,
  "direction_a": {
    "packets": 150
  },
  "direction_b": {
    "packets": 140
  },
  "timestamp": "2026-06-13T12:00:00Z"
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `channel_id` | string | Identifier of the monitored channel/bridge. |
| `sequence` | integer | Monotonically increasing sequence number. Allows CnSS to detect dropped datagrams. |
| `window_ms` | integer | Duration of the aggregation window in milliseconds. Used for rate normalization. |
| `direction_a.packets` | integer | Packet count A→B in this window. |
| `direction_b.packets` | integer | Packet count B→A in this window. |
| `timestamp` | string (ISO 8601) | Timestamp when the CN received the telemetry data from the TP. |

---

## 2. CnSS to MUI

### 2.1 REST Endpoints

#### `GET /api/v1/health`

**Purpose:** Verify operational status of all modular components.  
**Auth:** `Authorization: Bearer {{access_token}}`

**Response 200:**
```json
{
  "status": "healthy",
  "components": {
    "traffic_processor": "active",
    "communication_node": "active",
    "cnss": "active"
  },
  "timestamp": "2026-06-13T12:00:00Z"
}
```

**Response 503:**
```json
{
  "status": "unhealthy",
  "components": { 
    "traffic_processor": "error", 
    "communication_node": "active", 
    "cnss": "active" 
  },
  "timestamp": "2026-06-13T12:00:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall system status: `healthy`, `degraded`, `unhealthy`. |
| `components.traffic_processor` | string | `active`, `inactive`, `error`. |
| `components.communication_node` | string | `active`, `inactive`, `error`. |
| `components.cnss` | string | `active`, `inactive`, `error`. |
| `timestamp` | string (ISO 8601) | Server time at response generation. |

#### `GET /api/v1/channel/status`

**Purpose:** REST fallback for channel activity indicator. The MUI should primarily use the WebSocket stream.  
**Auth:** `Authorization: Bearer {{access_token}}`

**Response 200:**
```json
{
  "channel_id": "{{channel_id}}",
  "is_active": true,
  "last_activity_timestamp": "2026-06-13T12:00:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `channel_id` | string | Identifier of the monitored channel. |
| `is_active` | boolean | `true` if packets were observed within the last activity timeout window (default: 5 seconds). |
| `last_activity_timestamp` | string (ISO 8601) | Timestamp of the most recent telemetry batch with `packets > 0`. |

---

### 2.2 WebSocket Endpoint

#### `WS /api/v1/ws/telemetry`

**Purpose:** Real-time push stream for the MUI dashboard.  
**Auth:** Query parameter or subprotocol header. Recommended: `?token={{access_token}}` or `Sec-WebSocket-Protocol: bearer.{{access_token}}`.

**Connection Lifecycle:**
1. MUI opens WebSocket to `wss://{{cnss_host}}:{{cnss_ws_port}}/api/v1/ws/telemetry`.
2. CnSS validates `{{access_token}}`. On failure, closes with code `4001` and reason `invalid_token`.
3. On success, CnSS begins pushing `telemetry_update` frames at the same frequency as CN ingestion (2–10 Hz).
4. MUI may send a `ping` frame; CnSS responds with `pong`.
5. If no telemetry is received from CN for `activity_timeout_ms` (default: 5000), CnSS sends an `is_active: false` update.

**Payload Schema: `telemetry_update`**

```json
{
  "type": "telemetry_update",
  "channel_id": "{{channel_id}}",
  "is_active": true,
  "window_ms": 500,
  "metrics": {
    "direction_a": {
      "packets_per_sec": 300,
      "packets": 150
    },
    "direction_b": {
      "packets_per_sec": 280,
      "packets": 140
    }
  },
  "timestamp": "2026-06-13T12:00:00Z"
}
```

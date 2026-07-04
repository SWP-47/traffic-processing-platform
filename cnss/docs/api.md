# API Documentation

## 1. Overview & Architectural Principles

The Control and Status Server (CnSS) provides a decoupled API for the Management User Interface (MUI).

- **REST API** is used for authentication, state discovery, and historical data retrieval (Line Charts).
- **WebSocket API** is used for real-time telemetry and host table updates via a **Unified Subscription Engine**.
- **UDP Ingestion** is used by Communication Nodes (CN) to push raw packet metadata.

### Placeholders

| Placeholder | Description | Example |
| :--- | :--- | :--- |
| `{{cnss_host}}` | CnSS server hostname/IP | `cnss.example.com` |
| `{{cnss_http_port}}` | HTTP/WS port (routed via Edge Nginx) | `443` |
| `{{cnss_udp_port}}` | UDP port for CN ingestion | `5140` |
| `{{access_token}}` | Bearer token for authenticated endpoints | `eyJhbG...` |
| `{{channel_id}}` | Identifier for the monitored bridge | `primary-bridge-01` |

---

## 2. CN to CnSS (UDP Ingestion)

**Transport**: UDP (Best-effort, unidirectional).

**Endpoint**: `{{cnss_host}}:{{cnss_udp_port}}`

### Payload Schema: `TelemetryBatch`

```json
{
    "channel_id": "{{channel_id}}",
    "timestamp": 1718625600,
    "sequence": 1042,
    "window_ms": 50,
    "packets": [
        {
            "direction": 0,
            "src_ip": "192.168.1.100",
            "dst_ip": "8.8.8.8",
            "src_port": 12345,
            "dst_port": 53
        }
    ]
}
```

**Constraints**:

- **MTU Limit**: CN must ensure the serialized JSON payload does not exceed **1400 bytes** to prevent IP fragmentation.
- **Sequence Data Type**: CN **MUST** implement the `sequence` field as a **64-bit integer**. Using 32-bit integers will lead to silent data loss and incorrect drop calculations once the counter wraps around.

---

## 3. REST API

### 3.1 Authentication

#### `POST /api/v1/auth/login`

**Auth**: None (public endpoint).

**Request Body**:

```json
{
  "username": "admin",
  "password": "secretpassword"
}
```

**Response 200**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "issued_at": "2026-06-18T12:00:00Z",
  "role": "admin",
  "scope": ["bridge-berlin-01", "bridge-prague-01"]
}
```

**Response Headers**:

```http
Set-Cookie: refresh_token=eyJhbG...; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh; Max-Age=604800
```

*Note: The `refresh_token` is **never** returned in the JSON response body. It is strictly set as an `HttpOnly` cookie to mitigate XSS attacks. The `Path` attribute is restricted to the refresh endpoint for additional security.*

#### `POST /api/v1/auth/refresh`

**Description**: Issues a new short-lived `access_token` using the long-lived `refresh_token` stored in the `HttpOnly` cookie.

**Auth**: None (relies on the `refresh_token` cookie).

**Request**:
The browser automatically attaches the cookie. No request body is required.

```http
POST /api/v1/auth/refresh HTTP/1.1
Cookie: refresh_token=eyJhbG...
```

**Response 200**:

```json
{
  "access_token": "new_access_token_eyJhbG...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "issued_at": "2026-06-19T12:00:00Z"
}
```

**Response 401**:

```json
{
  "error": "unauthorized",
  "message": "Refresh token is missing, invalid, expired, or revoked."
}
```

#### `POST /api/v1/auth/logout`

**Description**: Invalidates the current session by revoking the `refresh_token` in Redis and clearing the cookie from the client.

**Auth**: None (relies on the `refresh_token` cookie).

**Response 200**:

```json
{
  "message": "Successfully logged out."
}
```

**Response Headers**:

```http
Set-Cookie: refresh_token=; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh; Max-Age=0
```

### 3.2 System Health & Discovery

#### `GET /api/v1/health`

**Auth**: `Bearer {{access_token}}`

**Response 200**:

```json
{
  "status": "healthy",
  "components": { "cnss": "active" },
  "channels_active": 3,
  "channels_total": 4,
  "timestamp": "2026-06-17T12:00:00Z"
}
```

#### `GET /api/v1/channels`

**Auth**: `Bearer {{access_token}}`

**Description**: Lists all channels accessible to the user. Filtered by JWT `scope` for `viewer` role.

**Response 200**:

```json
{
  "channels": [
    {
      "channel_id": "bridge-berlin-01",
      "is_active": true,
      "last_activity_timestamp": "2026-06-17T12:00:00Z"
    }
  ],
  "total": 1
}
```

#### `GET /api/v1/channel/{channel_id}/status`

**Auth**: `Bearer {{access_token}}`

**Description**: REST fallback for a specific channel's activity indicator.

**Response 200**:

```json
{
  "channel_id": "{{channel_id}}",
  "is_active": true,
  "last_activity_timestamp": "2026-06-17T12:00:00Z"
}
```

### 3.3 Historical Data (Line Charts)

#### `GET /api/v1/channel/{channel_id}/history`

**Description**: Lazy-loads historical telemetry data for the Channel Line Chart. CnSS dynamically calculates the optimal `time_bucket` interval (approximately 1400 point).

**Path Parameters**:

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `channel_id` | string | Identifier of the channel to query. |

**Query Parameters**:

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `period` | string | Yes | Duration of the time window. Enum: `1h`, `24h`, `7d`, `30d`. |
| `start_time` | string (ISO 8601) | No | Start of the time range. If omitted, defaults to `now - period`. |

**Response 200**:

```json
{
    "channel_id": "bridge-berlin-01",
    "period": "24h",
    "start_time": "2026-06-16T12:00:00Z",
    "end_time": "2026-06-17T12:00:00Z",
    "interval_sec": 60,
    "points": [
        {
            "timestamp": "2026-06-16T12:00:00Z",
            "packets_in_per_sec": 280.5,
            "packets_out_per_sec": 300.0,
            "is_active": true
        }
    ]
}
```

**Response Fields**:

| Field | Type | Description |
| :--- | :--- | :--- |
| `channel_id` | string | Identifier of the channel. |
| `period` | string | Requested period duration. |
| `start_time` | string (ISO 8601) | Actual start of the returned time range. |
| `end_time` | string (ISO 8601) | Actual end of the returned time range. |
| `interval_sec` | integer | The calculated time bucket size in seconds. |
| `points` | array | Array of aggregated data points. |

**Error Responses**:

| HTTP Status | Error Code | When |
| :--- | :--- | :--- |
| `400` | `bad_request` | Invalid `start_time` format, or `start_time` is in the future. |
| `400` | `bad_request` | `start_time + period` exceeds data retention |
| `403` | `forbidden` | User lacks access to this channel. |
| `404` | `not_found` | Channel not found. |

**Examples**:

```bash
# Last 24 hours (default behavior)
GET /api/v1/channel/bridge-berlin-01/history?period=24h

# Specific 24h window starting from a given timestamp
GET /api/v1/channel/bridge-berlin-01/history?period=24h&start_time=2026-06-16T12:00:00Z
# → Returns data for [2026-06-16T12:00:00Z, 2026-06-17T12:00:00Z]
```

#### `GET /api/v1/channel/{channel_id}/hosts/{host_ip}/history`

**Description**: Lazy-loads historical Rx/Tx rate data for a specific Host Line Chart.

**Path Parameters**:

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `channel_id` | string | Identifier of the channel to query. |
| `host_ip` | string | IP address of the host (IPv4/IPv6). |

**Query Parameters**:

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `period` | string | Yes | Duration of the time window. Enum: `1h`, `24h`, `7d`, `30d`. |
| `start_time` | string (ISO 8601) | No | Start of the time range. If omitted, defaults to `now - period`. |

**Response 200**:

```json
{
    "channel_id": "bridge-berlin-01",
    "host_ip": "192.168.1.100",
    "period": "1h",
    "start_time": "2026-06-17T10:00:00Z",
    "end_time": "2026-06-17T11:00:00Z",
    "interval_sec": 10,
    "points": [
        {
            "timestamp": "2026-06-17T10:00:00Z",
            "packets_in_per_sec": 15.0,
            "packets_out_per_sec": 5.5
        }
    ]
}
```

**Response Fields**:

| Field | Type | Description |
| :--- | :--- | :--- |
| `channel_id` | string | Identifier of the channel. |
| `host_ip` | string | IP address of the host. |
| `period` | string | Requested period duration. |
| `start_time` | string (ISO 8601) | Actual start of the returned time range. |
| `end_time` | string (ISO 8601) | Actual end of the returned time range. |
| `interval_sec` | integer | The calculated time bucket size in seconds. |
| `points` | array | Array of aggregated data points. |

**Error Responses**:

| HTTP Status | Error Code | When |
| :--- | :--- | :--- |
| `400` | `bad_request` | Invalid `start_time` format, or `start_time` is in the future. |
| `400` | `bad_request` | `start_time + period` exceeds data retention (7 days). |
| `403` | `forbidden` | User lacks access to this channel. |
| `404` | `not_found` | Channel or host not found. |

**Examples**:

```bash
# Last 1 hour (default behavior)
GET /api/v1/channel/bridge-berlin-01/hosts/192.168.1.100/history?period=1h

# Specific 1h window starting from a given timestamp
GET /api/v1/channel/bridge-berlin-01/hosts/192.168.1.100/history?period=1h&start_time=2026-06-17T10:00:00Z
# → Returns data for [2026-06-17T10:00:00Z, 2026-06-17T11:00:00Z]
```

---

## 4. WebSocket API (Real-Time Push)

### 4.1 Connection Lifecycle

**Endpoint**: `wss://{{cnss_host}}:{{cnss_http_port}}/api/v1/ws/telemetry?token={{access_token}}&channel_id={{channel_id}}`

**Lifecycle Steps**:

1. MUI opens WebSocket with `token` and `channel_id` query parameters.
2. CnSS validates JWT (signature, expiration, revocation). On failure, closes with `4001`.
3. CnSS checks `channel_id` presence. On failure, closes with `4002`.
4. CnSS verifies JWT `scope` against `channel_id`. On failure, closes with `4003`.
5. CnSS confirms channel existence in registry. On failure, closes with `4004`.
6. **CRITICAL**: CnSS **DOES NOT** push data automatically. MUI **MUST** send a `subscribe` control message to start receiving updates.

**WebSocket Close Codes**:

| Code | Reason | Meaning |
| :--- | :--- | :--- |
| `4001` | `invalid_token` | JWT missing, malformed, expired, or revoked. |
| `4002` | `missing_channel` | `channel_id` query parameter is absent. |
| `4003` | `channel_forbidden` | Scope mismatch, or subscription `channel_id` differs from URL. |
| `4004` | `channel_not_found` | Channel or Target does not exist. |
| `1011` | `internal_error` | Unexpected server error. |

### 4.2 Unified Subscription Engine

All real-time data streams are treated as subscriptions.

- **Deduplication**: CnSS generates a deterministic `query_hash` (SHA-256) based on `channel_id`, `target`, and `params`. **The client-provided `id` is strictly excluded from the hash calculation.** This ensures that identical requests from multiple users or parallel client subscriptions share the same backend DB query.
- **Initial Snapshot**: Upon subscription, CnSS immediately executes a read-only DB query and pushes the current state to the client, preventing the "cold start" gap before the first 1Hz Reporting Worker tick.

### 4.3 Control Messages (Client -> Server)

#### Subscribe

```json
{
    "action": "subscribe",
    "id": "sub-abc-123",
    "channel_id": "{{channel_id}}",
    "target": "<TARGET_NAME>",
    "params": { ... }
}
```

*Note: The `id` field is a **required** client-generated unique identifier. It allows the MUI to distinguish between multiple identical parallel subscriptions. This field is ignored by the backend when calculating the `query_hash`.*

#### Unsubscribe

```json
{
    "action": "unsubscribe",
    "id": "sub-abc-123",
    "channel_id": "{{channel_id}}",
    "target": "<TARGET_NAME>",
    "params": { ... } 
}
```

*(Note: `params` must match the original subscribe request to correctly compute the `query_hash` for unregistration.*

---

### 4.4 Subscription Targets & Parameters

#### Target: `telemetry`

Real-time channel packet rates.

**Params**:

```json
{
    "window_sec": 5.0 // Aggregation time window in seconds. Defines the rolling window for `packets_per_sec` calculation
}
```

**Push Payload**: `telemetry_update`

```json
{
   "type": "telemetry_update",
   "id": "sub-abc-123",
   "channel_id": "{{channel_id}}",
   "is_active": true,
   "window_ms": 5000,
   "dropped_batches": 0,
   "metrics": {
     "direction_out": { "packets_per_sec": 300.0, "packets": 1500 },
     "direction_in": { "packets_per_sec": 280.0, "packets": 1400 }
   },
   "timestamp": "2026-06-17T12:00:00Z",
   "received_at": "2026-06-17T12:00:05Z"
}
```

#### Target: `hosts_table`

Aggregated table of all observed hosts with pagination and filtering.
**Params**:

```json
{
    "period": "5m",             // Enum: "5m", "15m", "1h", "24h", "7d", "30d"
    "location": "LAN",          // Enum: "LAN", "WAN", or null (all)
    "ip": "192.168.1.100",      // Exact match filter, or null
    "sort_by": "rx",            // Enum: "location", "ip", "unique_destinations", "tx", "rx", "last_activity"
    "sort_order": "desc",       // Enum: "asc", "desc"
    "limit": 50,                // Integer (Page size)
    "offset": 0                 // Integer (Pagination offset)
}
```

**Push Payload**: `hosts_table_update`

```json
{
    "type": "hosts_table_update",
    "id": "sub-abc-123",
    "channel_id": "{{channel_id}}",
    "target": "hosts_table",
    "timestamp": "2026-06-17T12:00:05Z",
    "total_count": 145,
    "hosts": [
        {
            "location": "LAN",
            "ip": "192.168.1.100",
            "unique_destinations": 12,
            "tx_per_sec": 15.5,
            "rx_per_sec": 120.0,
            "last_activity": "2026-06-17T12:00:04Z"
        }
    ]
}
```

#### Target: `host_details`

Real-time Rx/Tx rate for a specific host (for the Host Details page header).
**Params**:

```json
{
    "host_ip": "192.168.1.100",
    "period": "5m"              // Aggregation window for real-time rate
}
```

**Push Payload**: `host_details_update`

```json
{
    "type": "host_details_update",
    "id": "sub-abc-123",
    "channel_id": "{{channel_id}}",
    "host_ip": "192.168.1.100",
    "timestamp": "2026-06-17T12:00:05Z",
    "tx_per_sec": 15.5,
    "rx_per_sec": 120.0
}
```

#### Target: `host_top_destinations`

Top destinations for a specific host.
**Params**:

```json
{
    "host_ip": "192.168.1.100",
    "period": "5m",
    "sort_by": "received",      // Enum: "ip", "location", "received", "last_seen"
    "sort_order": "desc",
    "limit": 10,
    "offset": 0
}
```

**Push Payload**: `host_top_destinations_update`

```json
{
    "type": "host_top_destinations_update",
    "id": "sub-abc-123",
    "channel_id": "{{channel_id}}",
    "host_ip": "192.168.1.100",
    "timestamp": "2026-06-17T12:00:05Z",
    "total_count": 45,
    "destinations": [
        {
            "ip": "8.8.8.8",
            "location": "WAN",
            "received_per_sec": 10.5,
            "last_seen": "2026-06-17T12:00:04Z"
        }
    ]
}
```

#### Target: `host_top_ports`

Top ports and protocols for a specific host.

**Params**:

```json
{
    "host_ip": "192.168.1.100",
    "period": "5m",
    "sort_by": "pps",           // Enum: "port", "protocol", "pps"
    "sort_order": "desc",
    "limit": 10,
    "offset": 0
}
```

**Push Payload**: `host_top_ports_update`

```json
{
    "type": "host_top_ports_update",
    "id": "sub-abc-123",
    "channel_id": "{{channel_id}}",
    "host_ip": "192.168.1.100",
    "timestamp": "2026-06-17T12:00:05Z",
    "total_count": 20,
    "ports": [
        {
            "port": 443,
            "protocol": "TCP",
            "packets_per_sec": 50.0
        }
    ]
}
```

> **Backend Note for `host_top_ports`**: To accurately provide the `protocol` field, the `packet_flows` schema and CN `TelemetryBatch` payload must be extended to include a `protocol` (e.g., TCP/UDP) field, or the backend must rely on well-known port mappings.

---

### 5. Security & JWT Specification

#### 5.1 JWT Claims

**Access Token Claims** (Short-lived, stored in MUI memory):

| Claim | Type | Description |
| :--- | :--- | :--- |
| `sub` | string | User identifier. |
| `jti` | string | Unique JWT ID (used for immediate revocation via Redis). |
| `iat` | integer | Issued At (Unix timestamp). |
| `exp` | integer | Expiration Time (Default: 24h). |
| `role` | string | `admin` or `viewer`. |
| `scope` | array | List of accessible `channel_id`. Ignored for `admin`. |

**Refresh Token Claims** (Long-lived, stored in HttpOnly Cookie):

| Claim | Type | Description |
| :--- | :--- | :--- |
| `sub` | string | User identifier. |
| `jti` | string | Unique JWT ID (used for revocation on logout). |
| `iat` | integer | Issued At (Unix timestamp). |
| `exp` | integer | Expiration Time (Default: 7 days). |
| `type` | string | Hardcoded to `"refresh"` to prevent misuse as an access token. |

#### 5.2 Authorization Matrix

| Role | Access |
| :--- | :--- |
| `admin` | Unrestricted access to all channels. |
| `viewer` | Strictly limited to `channel_id`s present in the `scope` array. |

#### 5.3 Security Constraints

- **Access Token Storage**: MUI **MUST** store the `access_token` exclusively in memory (JavaScript variable). Usage of `localStorage` or `sessionStorage` is strictly prohibited to mitigate XSS token theft.
- **Refresh Token Storage**: The `refresh_token` **MUST** be stored exclusively in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie. This prevents client-side scripts from accessing the token, providing robust protection against XSS.
- **Cookie Path Restriction**: The `refresh_token` cookie `Path` must be strictly limited to `/api/v1/auth/refresh` to prevent it from being sent to other endpoints unnecessarily.
- **Transport Security**: All external communication is secured via `wss://` and `https://` through the Edge Nginx reverse proxy (Centralized TLS). The `Secure` flag on the cookie ensures it is never transmitted over unencrypted HTTP.
- **Logging**: CnSS sanitizes all access logs. Tokens in query parameters, headers, or cookies are replaced with `[REDACTED]`.
- **Revocation Flow**: Both `access_token` and `refresh_token` contain a `jti` claim. Upon `POST /api/v1/auth/logout`, the backend extracts the `jti` from the refresh token and adds it to the Redis `jwt:revoked` set. The `/refresh` endpoint must verify the `jti` against this set before issuing a new `access_token`.

---

## 6. Error Responses

All REST API errors follow a consistent JSON response format:

```json
{
  "error": "<error_code>",
  "message": "<human-readable description>"
}
```

| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| `400` | `bad_request` | Malformed request payload or missing required fields. |
| `401` | `unauthorized` | Bearer token missing, invalid, expired, or revoked. |
| `401` | `invalid_credentials` | Invalid username/password during login. |
| `403` | `forbidden` | Valid token, but user lacks scope permission. |
| `404` | `not_found` | Requested channel or host does not exist. |
| `500` | `internal_error` | Unexpected server-side failure. |
| `503` | `unhealthy` | Returned by `/health` when CnSS is degraded. |

# API Documentation (MVP v1)

## Placeholders

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{cnss_host}}` | CnSS server hostname/IP | `cnss.example.com` |
| `{{cnss_udp_port}}` | UDP port for CN ingestion | `5140` |
| `{{cnss_http_port}}` | WebSocket port for MUI | `8000` |
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
- **Routing**: CnSS uses `channel_id` from the payload to route the batch to the correct per-channel state. If the channel does not exist, CnSS creates it on first receipt.
- **UDP MTU Constraint**: CN is strictly responsible for ensuring the serialized JSON payload does not exceed the network MTU (recommended `< 1400 bytes`). CN must dynamically or statically adjust `window_ms` to prevent IP fragmentation and silent UDP drops.

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
     },
     {
       "direction": 1,
       "src_ip": "8.8.8.8",
       "dst_ip": "192.168.1.100",
       "src_port": 53,
       "dst_port": 12345
     }
   ]
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `channel_id` | string | Identifier of the monitored channel/bridge. Used by CnSS to route the batch to the correct per-channel state. |
| `timestamp` | integer | Unix timestamp (seconds) of the window start. |
| `sequence` | integer | Monotonically increasing sequence number per channel. Allows CnSS to detect dropped datagrams for this specific channel. |
| `window_ms` | integer | Duration of the batching window in milliseconds. Must be kept small enough to ensure the JSON fits within the UDP MTU (< 1400 bytes). |
| `packets` | array | Array of raw packet metadata objects captured during the window. |
| `packets[].direction` | integer | `0` for IN, `1` for OUT. |
| `packets[].src_ip` | string | Source IP address (IPv4/IPv6). |
| `packets[].dst_ip` | string | Destination IP address (IPv4/IPv6). |
| `packets[].src_port` | integer | Source port. |
| `packets[].dst_port` | integer | Destination port. |

---

## 2. CnSS to MUI

### 2.1 Authentication

#### `POST /api/v1/auth/login`

**Purpose:** Authenticate user and issue JWT token with role and scope information.  
**Auth:** None (public endpoint).  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "username": "admin",
  "password": "secretpassword"
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | User identifier. |
| `password` | string | Yes | User password in plaintext. |

**Response 200:**
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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT token for authenticated requests. |
| `token_type` | string | Always `"Bearer"`. |
| `expires_in` | integer | Token lifetime in seconds (default: 86400 = 24 hours). |
| `issued_at` | string (ISO 8601) | Token issuance timestamp. |
| `role` | string | User role: `admin` or `viewer`. |
| `scope` | array[string] | List of accessible `channel_id`. For `admin`, contains all known channels. For `viewer`, contains only permitted channels. |

**Response 400:**
```json
{
  "error": "bad_request",
  "message": "Fields 'username' and 'password' are required."
}
```

**Response 401:**
```json
{
  "error": "invalid_credentials",
  "message": "Invalid username or password."
}
```

**Response 500:**
```json
{
  "error": "internal_error",
  "message": "Authentication service unavailable."
}
```

---

### 2.2 REST Endpoints

#### `GET /api/v1/health`

**Purpose:** Verify operational status of the CnSS and aggregate channel statistics.  
**Auth:** `Authorization: Bearer {{access_token}}`

**Response 200:**
```json
{
  "status": "healthy",
  "components": {
    "cnss": "active"
  },
  "channels_active": 3,
  "channels_total": 4,
  "timestamp": "2026-06-17T12:00:00Z"
}
```

**Response 503:**
```json
{
  "status": "unhealthy",
  "components": { 
    "cnss": "error"
  },
  "channels_active": 0,
  "channels_total": 0,
  "timestamp": "2026-06-17T12:00:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall CnSS status: `healthy`, `degraded`, `unhealthy`. |
| `components.cnss` | string | `active`, `inactive`, `error`. |
| `channels_active` | integer | Number of channels currently reporting telemetry (`is_active=true`). |
| `channels_total` | integer | Total number of channels known to CnSS. |
| `timestamp` | string (ISO 8601) | Server time at response generation. |

**Response 401:**
```json
{
  "error": "unauthorized",
  "message": "Invalid or expired token."
}
```

---

#### `GET /api/v1/channels`

**Purpose:** List all channels accessible to the authenticated user. For `viewer`, the list is filtered by JWT `scope`. For `admin`, all known channels are returned.  
**Auth:** `Authorization: Bearer {{access_token}}`

**Response 200:**
```json
{
  "channels": [
    {
      "channel_id": "bridge-berlin-01",
      "is_active": true,
      "last_activity_timestamp": "2026-06-17T12:00:00Z"
    },
    {
      "channel_id": "bridge-prague-01",
      "is_active": false,
      "last_activity_timestamp": "2026-06-17T11:55:00Z"
    }
  ],
  "total": 2
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `channels` | array | List of channel objects accessible to the user. |
| `channels[].channel_id` | string | Identifier of the channel. |
| `channels[].is_active` | boolean | `true` if telemetry was received within the activity timeout window (default: 5 seconds). |
| `channels[].last_activity_timestamp` | string (ISO 8601) | Timestamp of the most recent telemetry batch with `packets > 0`. |
| `total` | integer | Number of channels returned. |

**Response 401:**
```json
{
  "error": "unauthorized",
  "message": "Invalid or expired token."
}
```

**Response 403:**
```json
{
  "error": "forbidden",
  "message": "User has no channel access."
}
```

---

#### `GET /api/v1/channel/{channel_id}/status`

**Purpose:** REST fallback for a specific channel's activity indicator. The MUI should primarily use the WebSocket stream.  
**Auth:** `Authorization: Bearer {{access_token}}`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `channel_id` | string | Identifier of the channel to query. |

**Response 200:**
```json
{
  "channel_id": "{{channel_id}}",
  "is_active": true,
  "last_activity_timestamp": "2026-06-17T12:00:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `channel_id` | string | Identifier of the monitored channel. |
| `is_active` | boolean | `true` if packets were observed within the last activity timeout window (default: 5 seconds). |
| `last_activity_timestamp` | string (ISO 8601) | Timestamp of the most recent telemetry batch with `packets > 0`. |

**Response 401:**
```json
{
  "error": "unauthorized",
  "message": "Invalid or expired token."
}
```

**Response 403:**
```json
{
  "error": "forbidden",
  "message": "You do not have access to this channel."
}
```

**Response 404:**
```json
{
  "error": "not_found",
  "message": "Channel not found."
}
```

---

### 2.3 WebSocket Endpoint

#### `WS /api/v1/ws/telemetry`

**Purpose:** Real-time push stream for the MUI dashboard, scoped to a specific channel.  
**Auth:** Query parameters. Required: `token={{access_token}}` AND `channel_id={{channel_id}}`.

**URL Format:**
```
wss://{{cnss_host}}:{{cnss_http_port}}/api/v1/ws/telemetry?token={{access_token}}&channel_id={{channel_id}}
```

**Connection Lifecycle:**
1. MUI opens WebSocket with both `token` and `channel_id` query parameters.
2. CnSS validates `{{access_token}}` (signature, expiration). On failure, closes with code `4001` and reason `invalid_token`.
3. CnSS checks that the `{{channel_id}}` query parameter is present in the URL. On failure, closes with code `4002` and reason `missing_channel`.
4. CnSS checks that the JWT's `scope` permits access to `{{channel_id}}` (or user is `admin`). On failure, closes with code `4003` and reason `channel_forbidden`.
5. CnSS checks that the provided `{{channel_id}}` value exists in its channel registry. On failure, closes with code `4004` and reason `channel_not_found`.
6. On success, the WebSocket is added to `channels[channel_id].listeners`, and CnSS begins pushing `telemetry_update` frames for that channel only at a fixed frequency (e.g 1 Hz), aggregated by the Reporting Worker from TimescaleDB.
7. MUI may send a `ping` frame; CnSS responds with `pong`.
8. If no telemetry is received from the CN for this channel for `activity_timeout_ms` (default: 5000), CnSS sends an `is_active: false` update to all listeners of that channel.

**WebSocket Close Codes:**

| Code | Reason | Meaning |
| --- | --- | --- |
| 4001 | invalid_token | Token is missing, malformed, expired, or has invalid signature. |
| 4002 | missing_channel | The `channel_id` query parameter is entirely absent from the WebSocket request URL. |
| 4003 | channel_forbidden | Token is valid, but the user does not have access to the requested channel. |
| 4004 | channel_not_found | The `channel_id` query parameter is present, but its value does not match any known or active channel in the CnSS registry. |
| 1011 | internal_error | Unexpected server error. |

*Security Note: CnSS **MUST NOT** log the full request URL to prevent `access_token` leakage.*

**Payload Schema: `telemetry_update`**

```json
{
  "type": "telemetry_update",
  "channel_id": "{{channel_id}}",
  "is_active": true,
  "window_ms": 500,
  "dropped_batches": 0,
  "metrics": {
    "direction_out": {
      "packets_per_sec": 300,
      "packets": 150
    },
    "direction_in": {
      "packets_per_sec": 280,
      "packets": 140
    }
  },
  "timestamp": "2026-06-17T12:00:00Z",
  "received_at": "2026-06-17T12:00:00.050Z"
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Event type, always `telemetry_update`. |
| `channel_id` | string | Identifier of the monitored channel. Matches the `channel_id` the client subscribed to. |
| `is_active` | boolean | `true` if the channel is active, `false` if timeout detected. |
| `window_ms` | integer | Duration of the aggregation window in milliseconds. |
| `dropped_batches` | integer | Number of lost UDP datagrams between the previous and current batch **for this channel**. `0` means no losses. Allows MUI to visualize transport stability between CN and CnSS. |
| `metrics` | object | Contains `direction_out` and `direction_in` metrics. |
| `metrics.direction_out.packets_per_sec` | float | Normalized packet rate for OUT direction. |
| `metrics.direction_out.packets` | integer | Raw packet count for OUT direction in this window. |
| `metrics.direction_in.packets_per_sec` | float | Normalized packet rate for IN direction. |
| `metrics.direction_in.packets` | integer | Raw packet count for IN direction in this window. |
| `timestamp` | string (ISO 8601) | Original timestamp from the CN batch. |
| `received_at` | string (ISO 8601) | Server time at CnSS when the UDP datagram was received. Used internally for accurate timeout calculation, independent of CN clock skew. |

---

## 3. JWT Token Specification

### 3.1. Token Format

Tokens are issued via `POST /api/v1/auth/login` and follow the JWT (RFC 7519) standard with HS256 signature.

**Header:**
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload:**
```json
{
  "sub": "admin_01",
  "iat": 1750248000,
  "exp": 1750334400,
  "role": "admin",
  "scope": ["bridge-berlin-01", "bridge-prague-01"]
}
```

**Claims:**

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | string | Subject — user identifier. |
| `iat` | integer | Issued At — Unix timestamp of token issuance. |
| `exp` | integer | Expiration Time — Unix timestamp of token expiration. |
| `role` | string | User role: `admin` or `viewer`. |
| `scope` | array[string] | List of accessible `channel_id`. For `admin`, contains all known channels at issuance time. For `viewer`, contains only permitted channels. |

**Signature:**
```
HMACSHA256(base64(header) + "." + base64(payload), SECRET_KEY)
```

### 3.2. Authorization Matrix

| Role | `scope` | Access |
|------|---------|--------|
| `admin` | any value | All channels (including dynamically added ones). The `scope` claim is ignored for authorization checks. |
| `viewer` | specified | Only channels listed in the `scope` array. |

### 3.3. Token Usage

**REST Requests:**
```http
GET /api/v1/channels HTTP/1.1
Host: {{cnss_host}}
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**WebSocket Connection:**
```
wss://{{cnss_host}}:{{cnss_http_port}}/api/v1/ws/telemetry?token=eyJhbG...&channel_id=bridge-berlin-01
```

### 3.4. Token Storage (MUI)

The MUI must store the JWT token **exclusively in memory** (JavaScript variable). Do not use `localStorage` or `sessionStorage` — these are vulnerable to XSS attacks. On page reload, the user must re-authenticate.

---

## 4. Error Responses

All REST endpoints return errors in a consistent format:

```json
{
  "error": "<error_code>",
  "message": "<human-readable description>"
}
```

**Common Error Codes:**

| HTTP Status | `error` | When |
|:-----------:|---------|------|
| 400 | `bad_request` | Malformed request or missing required fields. |
| 401 | `unauthorized` | Missing, invalid, or expired token. |
| 401 | `invalid_credentials` | Invalid username or password during login. |
| 403 | `forbidden` | Token valid but user lacks permission for the requested resource. |
| 404 | `not_found` | Requested channel does not exist. |
| 500 | `internal_error` | Server-side failure. |

---

## 5. Security Considerations

### 5.1. Transport Security

WebSocket connections should use `wss://` (TLS) to protect telemetry data and tokens in transit, especially for remote MUI access. HTTP is permitted as a conscious trade-off for simplicity, but this introduces risks (token interception via MITM).

### 5.2. Logging

CnSS must sanitize logs. Query parameters containing tokens must be masked or omitted from access logs (e.g., replace `?token=eyJhbG...` with `?token=[REDACTED]`).

### 5.3. CN Trust Model
In MVP v1, CNs are not authenticated — the `channel_id` is a trusted assertion. CnSS accepts UDP datagrams from any source. Mitigations:
- **Network-level ACLs**: CnSS should only accept UDP from known CN IP addresses.
- **MTU Enforcement**: CN must strictly enforce the `< 1400 bytes` payload limit to prevent network-level fragmentation and drops.
- **Future versions**: mTLS / DTLS with client certificates, with `channel_id` embedded in the certificate's Subject Alternative Name.

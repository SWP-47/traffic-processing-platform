# CnSS Architecture

## 1. Overview & Architectural Principles

The Control and Status Server (CnSS) is the backend core of the traffic processing platform. The architecture is strictly decoupled into isolated, containerized microservices to ensure horizontal scalability, fault isolation, and high-performance telemetry ingestion.

---

## 2. Component Architecture

The CnSS is deployed as a set of Docker containers. If any container crashes, Docker's `restart: always` policy ensures immediate recovery without affecting the core network forwarding plane.

### 2.1 Ingestion Worker (UDP Listener & Buffer Manager)

**Role**: High-performance telemetry ingestion, sequence tracking, and database buffering.

**Responsibilities**:

1. **UDP Reception**: Listens on `{{cnss_udp_port}}` for `TelemetryBatch` JSON payloads from Communication Nodes (CN). Soft Limit MTU constraints (warn-only) (< 1400 bytes).
2. **Sequence Tracking**: Maintains the `last_sequence` per `channel_id` **in Redis** (`channel:seq:{channel_id}`) to survive container restarts.
   - **Initial State**: If the key does not exist (new channel or post-crash), the first received `sequence` is stored as the baseline without calculating drops.
   - If `incoming_sequence > last_sequence + 1`: Calculates `dropped = incoming_sequence - (last_sequence + 1)`.
   - If `incoming_sequence <= last_sequence`: Ignores (handles out-of-order delivery gracefully).
   - **Constraint**: CN **must** use 64-bit integers for sequence numbers to prevent wrap-around issues.
   - **Sequence Reset Detection**: To handle CN reboots or sequence counter resets, the Ingestion Worker must detect abnormal backward jumps. If last_sequence - incoming_sequence > THRESHOLD (e.g., 1,000,000), the worker treats it as a reset, forcefully updates last_sequence = incoming_sequence, and resets the drop counter for this batch.
3. **Redis State Buffering (Fast Path)**: Updates the channel state in Redis.
   - **Activity Tracking**: Uses `HSET channel:state:{channel_id} last_activity_at <current_timestamp>` **ONLY IF** `len(TelemetryBatch.packets) > 0`. Empty keep-alive batches do not reset the timeout.
   - Uses `HINCRBY channel:state:{channel_id} dropped_delta <calculated_drops>` to accumulate dropped packets.
   - Sets a TTL of 6 seconds on the key. If the CN dies, the key expires, naturally indicating inactivity.
4. **Redis Buffering (Capped List)**: Pushes raw packet metadata into a Redis List (`udp:buffer:{channel_id}`). To prevent Out-Of-Memory (OOM) crashes if the DB flusher lags, the list is strictly capped. Before pushing, the worker checks `LLEN`; if it exceeds a threshold (e.g., 100,000), new packets are dropped, or `LTRIM` is used to discard the oldest entries.
5. **Background Flush**: A background thread within this container periodically flushes the Redis buffer into the `packet_flows` TimescaleDB hypertable using batch `INSERT` operations to minimize network roundtrips.

### 2.2 Reporting Worker (Background Aggregator)

**Role**: Periodic metric aggregation and real-time event publishing.

**Responsibilities**:

1. **Subscription Polling**: Every 1 second, reads the active subscription hashes from a dedicated Redis Set (`SMEMBERS sub:active_hashes`)
2. **Dynamic SQL Execution**: For each discovered `query_hash`, it retrieves the subscription JSON, identifies the `target` (e.g., `telemetry`, `lan_hosts`), and invokes a registered handler. The handler generates safe, parameterized SQL queries against TimescaleDB.
3. **Continuous Aggregate Awareness & Rate Calculation**: The telemetry_1s continuous aggregate is now grouped by protocol in addition to channel_id and bucket. This means multiple rows may exist for the same second (one per active protocol). Handlers querying this aggregate MUST use COUNT(DISTINCT t.bucket) instead of COUNT(t.bucket) when calculating the actual time window for rate calculations (e.g., packets_per_sec). Failure to do so will result in mathematically incorrect, underestimated rates.
4. **History API Compatibility**: Queries to telemetry_1s for historical data (History API) use SUM(t.packets_in) and SUM(t.packets_out). These aggregations remain completely unaffected by the new protocol grouping, as SUM() will correctly aggregate packets across all protocols within each time bucket.
5. **Optimization**: Before executing SQL, it checks `SMEMBERS sub:listeners:{query_hash}`. If no WebSocket clients are listening, the SQL query is skipped to save database resources.
6. **Pub/Sub Publishing**: Formats the aggregated data according to the API schema and publishes it to Redis Pub/Sub on the channel `ws:push:{query_hash}`.
7. **State Synchronization & Timeout Enforcement (Slow Path)**:
   - **Atomic Flush to DB**: Every 1 second, uses a **Lua script** (or `HGETDEL` in Redis 7.4+) to atomically read and reset `dropped_delta` from Redis, preventing race conditions. It then performs a batched `UPDATE` on the `channels` table.
   - **Reactivation**: The SQL `UPDATE` **always sets `is_active = TRUE`** for channels that successfully received a flush, ensuring channels reactivate immediately upon receiving new traffic.
   - **Mass Timeout Calculation**: Executes a single SQL query to mark inactive channels: `UPDATE channels SET is_active = FALSE WHERE is_active = TRUE AND last_activity_at < NOW() - INTERVAL '5 seconds'`.
8. **SQL Injection Prevention**: Since SQL identifiers (like column nam es in ORDER BY) cannot be parameterized, the Reporting Worker must use a strict whitelist mapping for sort_by (e.g., mapping "received" to SUM(direction=0)) and sort_order (strictly "ASC" or "DESC"). Direct string interpolation of user input into SQL queries is strictly prohibited. Additionally, since `period_sec` is strictly validated by Pydantic as a numeric value (`float` or `int`), it is safely formatted directly into SQL `INTERVAL` literals (e.g., `f"{period_sec} seconds"`). This approach is 100% safe from SQL injection and allows the system to support arbitrary custom time ranges without requiring backend code modifications.
9. **Atomic Drop Flushing (Hash-Based):** Dropped packets are accumulated in Redis using `HINCRBY channel:state:{channel_id} dropped_delta <calculated_drops>` by the Ingestion Worker. This approach is significantly more efficient than a List-based alternative (`LPUSH` + `LTRIM`) as it requires only a single atomic Redis operation per batch, avoids memory overhead of list entries, and naturally co-locates drop counters with other channel state fields (`is_active`, `last_activity_at`) in the same Hash key. The Reporting Worker atomically reads and resets the `dropped_delta` counter using a dedicated **Lua script** (`atomic_drop_flush.lua`), which executes `HGET` + `HSET 0` in a single roundtrip. This Lua-based atomicity is critical to prevent race conditions where the Ingestion Worker could increment `dropped_delta` between the Reporting Worker's read and reset operations. The Lua script returns the accumulated delta, which is then applied to the `channels` table via `UPDATE channels SET dropped = dropped + $1`. If the Lua script returns `0` (no drops accumulated), the DB update is skipped entirely to minimize unnecessary writes.
10. **Ghost Subscription Prevention:** If the WebSocket Service container crashes, it may leave stale `client_id`s in `sub:listeners:{hash}`. Before executing the SQL query, the Reporting Worker MUST validate the listeners. It retrieves the set via `SMEMBERS sub:listeners:{hash}` and checks if the corresponding `ws:session:{client_id}` key exists in Redis (`EXISTS`). If the session key is missing (expired or crashed), the worker removes the stale `client_id` from the listener set using `SREM`. If the listener set becomes empty, the SQL query is skipped.
11. **Channel Reactivation Lifecycle:** The Reporting Worker marks channels as `is_active = FALSE` if `last_activity_at < NOW() - 5s`. However, when the Ingestion Worker receives a new valid batch, it immediately updates the Redis state (`HSET channel:state:{channel_id} is_active TRUE`). The Reporting Worker's 1-second flush reads this Redis state and executes `UPDATE channels SET is_active = TRUE, last_activity_at = NOW()`, ensuring channels reactivate instantly upon receiving new traffic.

### 2.3 WebSocket Service (Client Gateway)

**Role**: Persistent client connection management and subscription routing.

**Technologies**: `websockets`, `redis.asyncio`, JWT.

**Responsibilities**:

1. **Connection Lifecycle**: Handles MUI WebSocket upgrades. Validates JWT tokens, checks `channel_id` presence, verifies JWT `scope` against the channel, and confirms channel existence. Returns specific close codes (`4001`-`4004`) on failure. Before accepting the connection, the service checks the token's `jti` (JWT ID) against a Redis revocation set (`jwt:revoked`). If the token has been revoked, the connection is closed with code `4001`.
2. **Subscription Management**: Receives JSON control messages from MUI. Generates a deterministic `query_hash` for the subscription parameters. **The client-provided `id` is strictly excluded from the hash calculation** to ensure database query deduplication remains intact even for parallel identical subscriptions.
3. **Redis State Sync**: Registers the subscription in Redis (`sub:registry:{hash}`) and adds the composite `client_id:sub_id` to the listener set (`sub:listeners:{hash}`).
4. **Initial Snapshot (Race-condition safe):** To prevent missing updates that occur between the DB query and the Pub/Sub subscription, the WebSocket Service MUST follow this strict order:
    - Execute `SUBSCRIBE ws:push:{query_hash}` in Redis.
    - Execute the read-only query against TimescaleDB (Initial Snapshot).
    - Push the Initial Snapshot to the client.
    > *(Note: The client must be designed to handle and deduplicate minor overlaps based on timestamps).*
5. **Pub/Sub Consumption**: Subscribes to the corresponding `ws:push:{query_hash}` Redis channels. Upon receiving messages, it maps the `query_hash` back to the connected `client_id:sub_id` pairs, injects the `sub_id` into the JSON payload as `"id"`, and pushes it to the specific client WebSocket.
6. **Garbage Collection**: On client disconnect, reads the session's tracking set to find all `query_hash:sub_id` pairs. Removes the `client_id:sub_id` from Redis listener sets. If a listener set becomes empty, it deletes the subscription registry key to stop the Reporting Worker from querying the DB.
7. **Session Heartbeat & TTL**: The `ws:session:{ws_client_id}` key in Redis is created with a strict **TTL of 10 seconds**. The WebSocket Service must periodically refresh this TTL (e.g., every 5 seconds) via a background heartbeat task. If the container crashes, the keys automatically expire, preventing orphaned subscriptions and memory leaks.
8. **Subscription Scope Validation**: The channel_id specified in the WebSocket subscription control message must strictly match the channel_id provided in the initial WebSocket connection URL. If they differ, the WebSocket Service must reject the subscription and close the connection with code 4003 (channel_forbidden).

### 2.4 REST API & Auth Service

**Role**: HTTP gateway, identity management, and historical data retrieval.

**Technologies**: FastAPI, asyncpg, passlib, JWT.

**Responsibilities**:

1. **Authentication**: Handles `POST /api/v1/auth/login` and `POST /api/v1/auth/refresh`. Validates credentials using Argon2id password hashes. Issues JWTs containing `role` and `scope`. Crucially, both endpoints must return a `user` object in the JSON response body containing `id`, `username`, `role`, and `scope`. For the `/refresh` endpoint, the service must extract the `sub` (user ID) from the valid `refresh_token`, query the `users` and `user_channel_scopes` tables to fetch the latest profile data, and include it in the response to allow the MUI to restore its UI state upon page reload.
2. **Channel Discovery & Status**: Serves `/channels` and `/status`. Reads directly from the `channels` table for instant, zero-latency status checks (no heavy `MAX(time)` queries required).
3. **History API**: Serves `/history`. Accepts `period_sec` (integer) to support arbitrary time windows. Dynamically calculates optimal `time_bucket` intervals based on the requested seconds to ensure smooth chart rendering.
4. **Health Check**: Serves `/health`, verifying internal component and database connectivity.

---

## 3. Data Storage & State Management

### 3.1 TimescaleDB Schema

The system utilizes TimescaleDB for time-series data and standard PostgreSQL tables for relational state.

#### **`packet_flows` (Hypertable)**

Stores raw packet metadata. Partitioned by time for high-performance aggregation.

```sql
CREATE TABLE packet_flows (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL,
    channel_id TEXT NOT NULL,
    direction SMALLINT NOT NULL, -- 0 = IN, 1 = OUT
    src_ip INET NOT NULL,
    dst_ip INET NOT NULL,
    src_port INTEGER NOT NULL,
    dst_port INTEGER NOT NULL,
    protocol VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN',
    PRIMARY KEY (id, time)
);
SELECT create_hypertable('packet_flows', 'time');
CREATE INDEX idx_channel_time ON packet_flows (channel_id, time DESC);
SELECT add_retention_policy('packet_flows', INTERVAL '7 days');
```

**Performance Optimization (Continuous Aggregates):** To prevent the Reporting Worker from executing heavy `GROUP BY` queries on the raw `packet_flows` table every second, TimescaleDB Continuous Aggregates are used.

```sql
-- 1-second bucket for real-time telemetry and host tables
-- IMPORTANT: Now grouped by protocol. Handlers MUST use COUNT(DISTINCT bucket) for rate calculations.
CREATE MATERIALIZED VIEW telemetry_1s
WITH (timescaledb.continuous) AS
SELECT 
    channel_id, 
    time_bucket('1 second', time) AS bucket,
    protocol,
    COUNT(*) FILTER (WHERE direction = 0) AS packets_in,
    COUNT(*) FILTER (WHERE direction = 1) AS packets_out
FROM packet_flows 
GROUP BY channel_id, bucket, protocol;

-- Add refresh policy to run every 1 second
SELECT add_continuous_aggregate_policy('telemetry_1s', 
    start_offset => INTERVAL '5 seconds', 
    end_offset => INTERVAL '1 second', 
    schedule_interval => INTERVAL '1 second');
```

*Note: The Reporting Worker must query `telemetry_1s` (or a 1-minute equivalent for history) instead of `packet_flows`.*

- **Storage Impact Note**: Grouping by protocol increases the number of rows in telemetry_1s. If a channel has 3 active protocols (TCP, UDP, ICMP), the aggregate will store 3 rows per second instead of 1. This is an acceptable trade-off for protocol-level granularity, and TimescaleDB's native compression will mitigate storage growth.

#### **`channels` (Persistent Registry)**

Acts as the persistent, "cold" registry for channel metadata. While real-time status (`is_active`) is served from the Redis state buffer for sub-millisecond latency by REST/WS services, this table is periodically updated (every 1s) by the Reporting Worker to maintain historical records, audit logs, and state recovery. The Reporting Worker is solely responsible for toggling `is_active` based on the flushed `last_activity_at`.

```sql
CREATE TABLE channels (
    channel_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ,
    dropped INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT FALSE
);
```

#### **`users` & `user_channel_scopes` (Identity & Access)**

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Argon2id via passlib
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_channel_scopes (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    channel_id TEXT NOT NULL,
    PRIMARY KEY (user_id, channel_id)
);
```

### 3.2 Redis Architecture

Redis serves as the central nervous system, handling buffering, state synchronization, and pub/sub messaging.

#### **Subscription Registry**

- `sub:registry:{query_hash}` (String, **No TTL**). Stores the JSON definition. It is explicitly deleted by the WebSocket Service ONLY when the last listener is removed from `sub:listeners:{query_hash}`.
- `sub:listeners:{query_hash}` (Set): Stores the composite IDs of connected WebSocket clients (`client_id:sub_id`) requesting this specific data. This allows a single client to maintain multiple parallel subscriptions to the same `query_hash`.

#### **Session & Buffer Management**

- `ws:session:{ws_client_id}` (Hash): Tracks active subscriptions for a specific WebSocket client to facilitate rapid cleanup on disconnect.
- `ws:session:{ws_client_id}:subs` (Set): Stores the active subscription instances as `query_hash:sub_id` strings for rapid garbage collection.
- `udp:buffer:{channel_id}` (List): High-speed buffer for raw packet metadata. The Ingestion Worker pushes here; the background flusher pops and inserts into TimescaleDB.
- `jwt:session:{token_jti}` (Hash, Optional): Tracks active JWTs to support immediate token revocation.
- `channel:seq:{channel_id}` (String): Stores the `last_sequence` integer per channel to survive Ingestion Worker restarts.
- `channel:state:{channel_id}` (Hash, TTL 6s): Ephemeral channel state buffer containing:
  - `last_activity_at`: Unix timestamp of the last batch with actual packets (not keep-alive).
  - `is_active`: Flag (1/0) indicating if the channel is currently receiving traffic.
  - `dropped_delta`: Accumulated count of dropped packets since last flush to TimescaleDB. Atomically read and reset by the Reporting Worker via Lua script.
- `sub:active_hashes` (Set): Maintains a fast-lookup index of all active `query_hash` values. The WebSocket Service adds/removes hashes here upon subscribe/unsubscribe, replacing the need for the blocking `KEYS` command.
- `jwt:revoked` (Set): Stores the `jti` (JWT ID) of revoked tokens for immediate session termination.

#### **Pub/Sub Channels**

- `ws:push:{query_hash}`: The Reporting Worker publishes aggregated JSON payloads here. The WebSocket Service subscribes to these channels based on active client requests.

#### **Redis Persistence Strategy (Ephemeral Mode)**

Redis is explicitly configured to run **without persistence** (no RDB snapshots, no AOF). It operates purely as an in-memory, ephemeral buffer and state cache. TimescaleDB is the single source of truth for persistent data. If Redis restarts, unflushed UDP buffers and sequence states are lost, which is an accepted trade-off to maximize IOPS and prevent disk-write bottlenecks. Upon restart, the system gracefully resets sequence baselines (see 2.1) and resumes ingestion.

---

## 4. WebSocket Subscription Mechanic

The simplistic subscription model is replaced by a highly flexible, parameterized subscription engine. Every real-time data stream (including the core telemetry metrics) is treated as a subscription.

### 4.1 Subscription Payload Structure

Clients send JSON control messages to subscribe or unsubscribe. The `id` field is a **required** client-generated unique identifier used to distinguish between multiple identical parallel subscriptions.

#### *Example for format*

```json
{
  "action": "subscribe",
  "id": "sub-abc-123",
  "channel_id": "bridge-01",
  "target": "lan_hosts",
  "params": {
    "ip_subnet": "192.168.1.0/24",
    "rx_min": 10.0,
    "rx_max": 100.0,
    "sort_by": "received",
    "sort_order": "desc",
    "limit": 50,
    "window_sec": 5.0
  }
}

> **Note on Time Parameters:** To ensure scalability and avoid the limitations of hardcoded Enums, all time-based parameters (e.g., `window_sec`, `period_sec`) are strictly defined in **seconds** as numeric values. This allows the frontend to request custom aggregation windows (e.g., 45 minutes, 3 hours) without requiring backend code changes or schema updates.

```

### 4.2 Query Hash Generation

To optimize database queries and deduplicate identical requests from multiple users, the WebSocket Service generates a deterministic `query_hash`. **The `id` field is explicitly excluded from this calculation.**

```python
import hashlib, json

def compute_query_hash(channel_id: str, target: str, params: dict) -> str:
    # 'id' is intentionally omitted to ensure identical queries share the same DB execution
    normalized = {"channel_id": channel_id, "target": target, "params": params}
    raw = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

### 4.3 Telemetry Update as a Subscription

The core `telemetry_update` stream is now unified under this mechanic.

1. When a client connects to `wss://.../telemetry?token=...&channel_id=...`, the client should send subscription:
   `{"channel_id": "...", "target": "telemetry", "params": {}}`
2. The `query_hash` is generated and registered in Redis.
3. The Reporting Worker fetches the `dropped` count and aggregated packet rates from the `channels` table and `packet_flows`, then publishes the `telemetry_update` payload to Redis Pub/Sub.

### 4.4 Lifecycle Flow

1. **Subscribe**: WS Service computes `query_hash` (excluding `id`), writes to `sub:registry:{hash}`, adds `client_id:sub_id` to `sub:listeners:{hash}`, fetches Initial Snapshot via direct DB read, injects `"id": sub_id` into the snapshot, and pushes it to the client.
2. **Update**: Reporting Worker ticks (1Hz), reads registry, executes SQL, publishes to `ws:push:{hash}`. WS Service receives Pub/Sub message, iterates over `client_id:sub_id` pairs in the listener set, injects `"id": sub_id` into the payload for each, and broadcasts to the specific clients.
3. **Unsubscribe**: WS Service removes `client_id:sub_id` from `sub:listeners:{hash}`. If the set is empty, it deletes `sub:registry:{hash}`.
4. **Disconnect**: WS Service reads `ws:session:{client_id}:subs`, parses all `query_hash:sub_id` pairs, removes the `client_id:sub_id` from all associated listener sets, and cleans up empty registry keys.

> The `sub:registry:{query_hash}` key must not rely on a short TTL for cleanup. Instead, it should have a long TTL (e.g., 1 hour) or no TTL, and be explicitly deleted by the WebSocket Service only when the last listener is removed from `sub:listeners:{query_hash}`.

---

## 5. Security & Access Control

### 5.1 Authentication & Authorization

- **Password Storage**: Plaintext passwords are never stored. The Auth module uses `passlib` with the `argon2` backend to generate and verify `password_hash`.

- **JWT Specification**: Tokens are signed using HS256.
  - Claims : `sub` (user ID), `iat`, `exp` (default 24h), `role` (`admin` or `viewer`), `scope` (array of `channel_id`).

> *Note: While `role` and `scope` are embedded in the JWT for backend authorization checks, the REST API `/login` and `/refresh` endpoints explicitly return them (along with `id` and `username`) in the JSON response body. This provides the MUI with the necessary context for UI state restoration without requiring client-side JWT parsing or additional `/me` requests.*

- **Authorization Matrix**:
  - `admin`: The `scope` claim is ignored; unrestricted access to all channels.
  - `viewer`: Access is strictly limited to the `channel_id` values present in the `scope` array (populated from `user_channel_scopes` at login).

### 5.2 CN Trust Model

Communication Nodes (CN) are not cryptographically authenticated. The `channel_id` in the UDP payload is a trusted assertion.

- **Mitigation**: CnSS must be deployed behind network-level ACLs, accepting UDP traffic only from known CN IP addresses.
- **Sequence Data Type**: CN **must** implement the `sequence` field as a 64-bit integer. Using 32-bit integers will lead to silent data loss and incorrect drop calculations once the counter wraps around (approx. every 50 days at high traffic).
- **Protocol Field Backward Compatibility**: The protocol field in TelemetryBatch is treated as optional at the ingestion boundary. If an older CN does not provide this field, the Ingestion Worker's Pydantic model will default it to "UNKNOWN". This ensures backward compatibility and prevents batch rejections during rolling upgrades.

### 5.3 Logging & Transport Security

- **Token Masking**: CnSS must sanitize all access logs. A custom Python logging filter replaces `?token=eyJhbG...` with `?token=[REDACTED]` to prevent credential leakage in log aggregators. Additionally, the Edge Nginx (see Section 2.5) uses a custom `log_format` that logs `$uri` instead of `$request_uri`, ensuring tokens in query parameters are never written to the reverse proxy's access logs.
- **Transport Security (Centralized TLS)**: All external communication is secured via `wss://` and `https://` through the **Infrastructure Layer (Edge Nginx, this is different component of project)**, which serves as the single TLS termination point for the entire platform. This architecture ensures:
  - A single certificate covers both the MUI frontend and CnSS backend.
  - Backend microservices never handle TLS directly, simplifying their implementation.
  - Internal Docker-network traffic remains isolated and unencrypted, avoiding unnecessary CPU overhead.
- **Client-Side Storage**: The MUI must store the JWT exclusively in memory (JavaScript variable). Usage of `localStorage` or `sessionStorage` is strictly prohibited to mitigate XSS token theft.
- **Certificate Lifecycle**:
  - **Development**: Self-signed certificates are generated via `make certs` and distributed to LAN clients via `make serve-certs`. Clients must install the certificate into their system's trust store to avoid browser security warnings.
  - **Production**: Certificates from a trusted Certificate Authority (e.g., Let's Encrypt, internal corporate CA) must be used. Self-signed certificates are **never** acceptable in production.

---

## 6. Error Codes and WebSocket Close Codes Summary

All REST API errors follow a consistent JSON response format:

```json
{
  "error": "<error_code>",
  "message": "<human-readable description>"
}
```

### 6.1. REST API HTTP Error Codes

These codes are returned by the CnSS REST API endpoints (Authentication, Channels, History, Health) when a request fails.

| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| **400** | `bad_request` | Malformed request payload or missing required fields. |
| **401** | `unauthorized` | The Bearer token is missing, invalid, expired, or has been revoked (found in `jwt:revoked`). |
| **401** | `invalid_credentials` | Invalid username or password provided during the `POST /api/v1/auth/login` attempt. |
| **403** | `forbidden` | The token is valid, but the user lacks permission for the requested resource (e.g., a `viewer` accessing a channel outside their `scope`). |
| **404** | `not_found` | The requested channel or specific resource does not exist in the CnSS registry. |
| **500** | `internal_error` | Unexpected server-side failure or database connectivity issue. |
| **503** | `unhealthy` | Returned by the `/health` endpoint when the CnSS or its core components are in an error/degraded state. |

### 6.2. WebSocket Connection Close Codes

These codes are sent by the CnSS WebSocket Service to the MUI (Management User Interface) to terminate a connection or reject a subscription request.

| Close Code | Reason | Description |
| :--- | :--- | :--- |
| **4001** | `invalid_token` | The JWT is missing, malformed, expired, has an invalid signature, or has been explicitly revoked. |
| **4002** | `missing_channel` | The `channel_id` query parameter is entirely absent from the initial WebSocket connection URL. |
| **4003** | `channel_forbidden` | The user does not have access to the requested channel (scope mismatch), OR the `channel_id` specified in a subsequent subscription control message differs from the one in the connection URL. |
| **4004** | `channel_not_found` *(or `target_not_found`)* | The `channel_id` does not match any known/active channel in the registry, OR the `target` specified in a subscription control message is invalid/unknown. |
| **1011** | `internal_error` | An unexpected internal server error occurred during the WebSocket session. |

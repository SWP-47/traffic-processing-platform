# CnSS Architecture

## 1. Overview & Architectural Principles

The Control and Status Server (CnSS) is the backend core of the traffic processing platform. The architecture is strictly decoupled into isolated, containerized microservices to ensure horizontal scalability, fault isolation, and high-performance telemetry ingestion.

---

## 2. Component Architecture

The CnSS is deployed as a set of Docker containers. If any container crashes, Docker's `restart: always` policy ensures immediate recovery without affecting the core network forwarding plane.

### 2.1 Ingestion Worker (UDP Listener & Buffer Manager)

**Role**: High-performance telemetry ingestion, sequence tracking, and database buffering.

**Responsibilities**:

1. **UDP Reception**: Listens on `{{cnss_udp_port}}` for `TelemetryBatch` JSON payloads from Communication Nodes (CN). Enforces MTU constraints (< 1400 bytes).
2. **Sequence Tracking**: Maintains an in-memory dictionary of `last_sequence` per `channel_id`.
   - If `incoming_sequence > last_sequence + 1`: Calculates `dropped = incoming_sequence - (last_sequence + 1)`.
   - If `incoming_sequence <= last_sequence`: Ignores (handles out-of-order delivery gracefully).
3. **Redis State Buffering (Fast Path)**: Updates the channel state in Redis.
   - Uses `HSET channel:state:{channel_id} last_activity_at <current_timestamp>` to track activity. Activity is true if the TelemetryBatch contain non zero packets.
   - Uses `HINCRBY channel:state:{channel_id} dropped_delta <calculated_drops>` to accumulate dropped packets.
   - Sets a TTL of 6 seconds on the key. If the CN dies, the key expires, naturally indicating inactivity.
4. **Redis Buffering**: Pushes raw packet metadata into a Redis List (`udp:buffer:{channel_id}`) for fast, non-blocking writes.
5. **Background Flush**: A background thread within this container periodically flushes the Redis buffer into the `packet_flows` TimescaleDB hypertable using batch `INSERT` operations to minimize network roundtrips.

### 2.2 Reporting Worker (Background Aggregator)

**Role**: Periodic metric aggregation and real-time event publishing.

**Responsibilities**:

1. **Subscription Polling**: Every 1 second, executes `KEYS sub:registry:*` in Redis to discover active client subscriptions.
2. **Dynamic SQL Execution**: For each discovered `query_hash`, it retrieves the subscription JSON, identifies the `target` (e.g., `telemetry`, `lan_hosts`), and invokes a registered handler. The handler generates safe, parameterized SQL queries against TimescaleDB.
3. **Optimization**: Before executing SQL, it checks `SMEMBERS sub:listeners:{query_hash}`. If no WebSocket clients are listening, the SQL query is skipped to save database resources.
4. **Pub/Sub Publishing**: Formats the aggregated data according to the API schema and publishes it to Redis Pub/Sub on the channel `ws:push:{query_hash}`.
5. **State Synchronization & Timeout Enforcement (Slow Path)**:
   - **Flush to DB**: Every 1 second, reads the accumulated `dropped_delta` and `last_activity_at` from Redis (`channel:state:*`) and performs a single batched `UPDATE` on the `channels` table in TimescaleDB. Resets the `dropped_delta` in Redis after flushing.
   - **Mass Timeout Calculation**: Executes a single, highly efficient SQL query to mark inactive channels: `UPDATE channels SET is_active = FALSE WHERE is_active = TRUE AND last_activity_at < NOW() - INTERVAL '5 seconds'`. This eliminates the need to iterate over channels in application code.

### 2.3 WebSocket Service (Client Gateway)

**Role**: Persistent client connection management and subscription routing.

**Technologies**: `websockets`, `redis.asyncio`, JWT.

**Responsibilities**:

1. **Connection Lifecycle**: Handles MUI WebSocket upgrades. Validates JWT tokens, checks `channel_id` presence, verifies JWT `scope` against the channel, and confirms channel existence. Returns specific close codes (`4001`-`4004`) on failure.
2. **Subscription Management**: Receives JSON control messages from MUI. Generates a deterministic `query_hash` for the subscription parameters.
3. **Redis State Sync**: Registers the subscription in Redis (`sub:registry:{hash}`) and adds the client ID to the listener set (`sub:listeners:{hash}`).
4. **Initial Snapshot**: Executes an immediate, lightweight read-only query against TimescaleDB to provide the client with an initial data snapshot without waiting for the 1-second Reporting Worker tick.
5. **Pub/Sub Consumption**: Subscribes to the corresponding `ws:push:{query_hash}` Redis channels. Upon receiving messages, it maps the `query_hash` back to the connected WebSocket client IDs and pushes the JSON payload.
6. **Garbage Collection**: On client disconnect, removes the client ID from Redis listener sets. If a listener set becomes empty, it deletes the subscription registry key to stop the Reporting Worker from querying the DB.

### 2.4 REST API & Auth Service

**Role**: HTTP gateway, identity management, and historical data retrieval.

**Technologies**: FastAPI, asyncpg, passlib, JWT.

**Responsibilities**:

1. **Authentication**: Handles `POST /api/v1/auth/login`. Validates credentials using Argon2id password hashes. Issues JWTs containing `role` and `scope`.
2. **Channel Discovery & Status**: Serves `/channels` and `/status`. Reads directly from the `channels` table for instant, zero-latency status checks (no heavy `MAX(time)` queries required).
3. **History API**: Serves `/history`. Calculates optimal `time_bucket` intervals and queries TimescaleDB for historical line chart data.
4. **Health Check**: Serves `/health`, verifying internal component and database connectivity.

---

## 3. Data Storage & State Management

### 3.1 TimescaleDB Schema

The system utilizes TimescaleDB for time-series data and standard PostgreSQL tables for relational state.

**`packet_flows` (Hypertable)**
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
    PRIMARY KEY (id, time)
);
SELECT create_hypertable('packet_flows', 'time');
CREATE INDEX idx_channel_time ON packet_flows (channel_id, time DESC);
SELECT add_retention_policy('packet_flows', INTERVAL '7 days');
```

**`channels` (State Table)**
Acts as the single source of truth for channel status. Updated by the Ingestion Worker.

```sql
CREATE TABLE channels (
    channel_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ,
    dropped INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT FALSE
);
```

**`users` & `user_channel_scopes` (Identity & Access)**

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

**Subscription Registry**
- `sub:registry:{query_hash}` (String, TTL 10s): Stores the JSON definition of the subscription.
- `sub:listeners:{query_hash}` (Set): Stores the IDs of connected WebSocket clients requesting this specific data.

**Session & Buffer Management**
- `ws:session:{ws_client_id}` (Hash): Tracks active subscriptions for a specific WebSocket client to facilitate rapid cleanup on disconnect.
- `udp:buffer:{channel_id}` (List): High-speed buffer for raw packet metadata. The Ingestion Worker pushes here; the background flusher pops and inserts into TimescaleDB.
- `jwt:session:{token_jti}` (Hash, Optional): Tracks active JWTs to support immediate token revocation.

**Pub/Sub Channels**
- `ws:push:{query_hash}`: The Reporting Worker publishes aggregated JSON payloads here. The WebSocket Service subscribes to these channels based on active client requests.

---

## 4. WebSocket Subscription Mechanic

The simplistic subscription model is replaced by a highly flexible, parameterized subscription engine. Every real-time data stream (including the core telemetry metrics) is treated as a subscription.

### 4.1 Subscription Payload Structure

Clients send JSON control messages to subscribe or unsubscribe.

```json
{
  "action": "subscribe",
  "channel_id": "bridge-01",
  "target": "lan_hosts",
  "params": {
    "ip_subnet": "192.168.1.0/24",
    "rx_min": 10.0,
    "rx_max": 100.0
    "sort_by": "received",
    "sort_order": "desc",
    "limit": 50,
    "window_sec": 5.0
  }
}
```

### 4.2 Query Hash Generation

To optimize database queries and deduplicate identical requests from multiple users, the WebSocket Service generates a deterministic `query_hash`.

```python
import hashlib, json

def compute_query_hash(channel_id: str, target: str, params: dict) -> str:
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

1. **Subscribe**: WS Service computes `query_hash`, writes to `sub:registry:{hash}`, adds client to `sub:listeners:{hash}`, fetches Initial Snapshot via direct DB read, and subscribes to `ws:push:{hash}`.
2. **Update**: Reporting Worker ticks (1Hz), reads registry, executes SQL, publishes to `ws:push:{hash}`. WS Service receives Pub/Sub message and broadcasts to all clients in `sub:listeners:{hash}`.
3. **Unsubscribe**: WS Service removes client from `sub:listeners:{hash}`. If the set is empty, it deletes `sub:registry:{hash}`.
4. **Disconnect**: WS Service reads `ws:session:{client_id}`, removes the client from all associated listener sets, and cleans up empty registry keys.

---

## 5. Security & Access Control

### 5.1 Authentication & Authorization

- **Password Storage**: Plaintext passwords are never stored. The Auth module uses `passlib` with the `argon2` backend to generate and verify `password_hash`.

- **JWT Specification**: Tokens are signed using HS256.
  - **Claims**: `sub` (user ID), `iat`, `exp` (default 24h), `role` (`admin` or `viewer`), `scope` (array of `channel_id`).

- **Authorization Matrix**:
  - `admin`: The `scope` claim is ignored; unrestricted access to all channels.
  - `viewer`: Access is strictly limited to the `channel_id` values present in the `scope` array (populated from `user_channel_scopes` at login).

### 5.2 CN Trust Model

Communication Nodes (CN) are not cryptographically authenticated. The `channel_id` in the UDP payload is a trusted assertion.

- **Mitigation**: CnSS must be deployed behind network-level ACLs, accepting UDP traffic only from known CN IP addresses.

### 5.3 Logging & Transport Security

- **Token Masking**: CnSS must sanitize all access logs. A custom Python logging filter replaces `?token=eyJhbG...` with `?token=[REDACTED]` to prevent credential leakage in log aggregators.
- **Transport**: WebSocket and REST endpoints should be exposed via `wss://` and `https://` (TLS) in production to prevent Man-in-the-Middle (MITM) token interception.
- **Client-Side Storage**: The MUI must store the JWT exclusively in memory (JavaScript variable). Usage of `localStorage` or `sessionStorage` is strictly prohibited to mitigate XSS token theft.

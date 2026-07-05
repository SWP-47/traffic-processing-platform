# Dynamic View — End-to-End Telemetry Pipeline

## Diagram

The sequence diagram ([end-to-end-telemetry.puml](end-to-end-telemetry.puml)) illustrates the **complete lifecycle of telemetry data** flowing through the entire Traffic Processing Platform — from physical network packets traversing the hardware data plane, through batching, ingestion, persistence, aggregation, and finally real-time delivery to the administrator's dashboard.

## Scenario Description

This scenario captures a **full system workflow** involving **all 10 major components** of the platform and crossing **multiple integration boundaries**:

1. **System Administrator** authenticates and discovers accessible channels via the REST API.
2. **Management UI (MUI)** establishes a persistent WebSocket connection scoped to a specific channel and subscribes to real-time telemetry.
3. **Traffic Processor (TP)** operates as a transparent inline bridge, forwarding user traffic at wire speed on the FPGA data plane while independently extracting packet metadata on the software telemetry plane.
4. **Communication Node (CN)** batches raw metadata into time-windowed `TelemetryBatch` payloads, enforcing strict UDP MTU constraints (< 1400 bytes).
5. **CnSS Ingestion Worker** receives UDP datagrams, tracks 64-bit sequences per channel (with CN reboot detection), and buffers raw metadata in Redis capped lists (preventing OOM).
6. **Background Flusher** atomically drains the Redis buffer and batch-inserts raw packet flows into the TimescaleDB hypertable.
7. **CnSS Reporting Worker** runs a 1Hz polling loop, discovers active subscriptions, executes parameterized SQL against continuous aggregates, and publishes results to Redis Pub/Sub.
8. **CnSS WebSocket Service** consumes Pub/Sub messages, injects client-specific subscription IDs, and pushes `telemetry_update` payloads to connected MUI clients.
9. **Channel Timeout Mechanism**: When telemetry stops flowing, the Reporting Worker detects inactivity (5-second threshold) and broadcasts `is_active: false` to all subscribers.
10. **Session Heartbeat**: The WebSocket Service refreshes Redis session TTLs every 5 seconds, ensuring orphaned subscriptions are automatically cleaned up if a client disconnects abruptly.

## Why This Scenario Is Important

### Product Significance

This end-to-end flow directly fulfills the platform's core value proposition and supports the following user stories:

- **US-001 (Channel Activity Indicator)**: The `is_active` boolean in `telemetry_update` payloads drives the binary Red/Green visual cue on the MUI dashboard.
- **US-002 (Basic Network Usage Statistics)**: The `metrics.direction_in` and `metrics.direction_out` fields provide real-time bidirectional packet rates for the line chart.
- **US-005, US-007, US-009 (Uninterrupted Traffic Flow)**: The strict decoupling of the FPGA data plane from the software telemetry plane ensures that any failure in monitoring components (CN crash, CnSS outage, Redis failure) has **zero impact** on user internet connectivity.
- **US-014 (Remote MUI Access)**: JWT-based authentication and scope-based authorization ensure that only authorized administrators can access specific channels from remote locations.
- **US-015 (Real-time Dashboard Updates)**: The 1Hz aggregation loop combined with Redis Pub/Sub ensures the dashboard updates continuously without manual refreshes.

### Architectural Decisions Illustrated

This scenario highlights several critical architectural decisions that shape the entire platform:

#### 1. Strict Data Plane / Control Plane Decoupling

The TP's FPGA forwards packets at wire speed **independently** of the telemetry extraction software. Even if the CN crashes, the CnSS is unreachable, or TimescaleDB is down, user traffic continues to flow uninterrupted. This is the foundational non-functional requirement of the entire system.

#### 2. Race-Condition-Safe Initial Snapshot

When a client subscribes, the WebSocket Service follows a **strict ordering**:
1. **SUBSCRIBE** to Redis Pub/Sub channel `ws:push:{hash}` first.
2. **THEN** query TimescaleDB for the current aggregated state.
3. **THEN** push the snapshot to the client.

This prevents the client from missing any updates that might be published between the DB query and the Pub/Sub subscription. The client must be designed to handle and deduplicate minor timestamp overlaps.

#### 3. Deterministic Query Hash for Deduplication

The WebSocket Service computes a `query_hash` (SHA-256, truncated to 16 chars) based on `channel_id`, `target`, and `params`. The client-provided subscription `id` is **explicitly excluded** from the hash. This means:
- Multiple clients subscribing to identical telemetry streams share the same `query_hash`.
- The Reporting Worker executes the expensive SQL query **only once per hash**.
- Results are broadcast to all listeners via a single Redis Pub/Sub publish.

This prevents redundant database queries and ensures data consistency across clients.

#### 4. Redis as Ephemeral Nervous System (No Persistence)

Redis is explicitly configured **without RDB/AOF persistence** to maximize IOPS. It serves as:
- A high-speed buffer for UDP ingestion (`udp:buffer:{channel_id}`)
- A state tracker for sequences and activity (`channel:seq`, `channel:state`)
- A Pub/Sub message bus for real-time delivery (`ws:push:{hash}`)
- A session registry with TTL-based auto-expiry (`ws:session:{client_id}`)

**Trade-off**: If Redis restarts, unflushed UDP buffers and sequence baselines are lost. The system gracefully resets and resumes — an accepted trade-off for performance.

#### 5. UDP MTU Constraint Enforcement

The CN is strictly responsible for ensuring serialized `TelemetryBatch` payloads do not exceed 1400 bytes. It dynamically adjusts the `window_ms` batching window to prevent IP fragmentation and silent UDP drops, which would otherwise cause invisible telemetry loss.

#### 6. 64-bit Sequence Tracking with Reboot Detection

Each CN maintains a monotonically increasing 64-bit sequence counter per channel. The Ingestion Worker:
- Calculates `dropped_batches` when `incoming > last + 1`
- Gracefully ignores out-of-order packets (`incoming <= last`)
- Detects CN reboots when `last - incoming > 1,000,000` and force-resets the baseline

This provides end-to-end visibility into UDP datagram loss without requiring TCP's reliability overhead.

#### 7. Capped Redis Buffers (OOM Protection)

The Ingestion Worker uses `LTRIM` to cap `udp:buffer:{channel_id}` lists at 100,000 items. If the background flusher lags behind a traffic spike, new packets are dropped rather than allowing Redis to consume unbounded memory and trigger an OOM kill.

#### 8. Lazy SQL Execution via Active Hash Index

The Reporting Worker checks `sub:active_hashes` every second. If a hash has no listeners (SCARD == 0), the SQL query is **skipped entirely**. This is a form of lazy evaluation — the system only computes data that someone is actively observing, saving database resources when dashboards are closed.

#### 9. Dual-Path Timeout Detection

Channel inactivity is detected through two complementary mechanisms:
- **Server-side**: The Reporting Worker runs `UPDATE channels SET is_active = FALSE WHERE last_activity_at < NOW() - 5s` every second and broadcasts the state change via Pub/Sub.
- **Client-side fallback**: If MUI receives no `telemetry_update` within 6000ms, it locally assumes `is_active = false` as a defensive measure against network partitions.

#### 10. Session TTL-Based Garbage Collection

WebSocket sessions are tracked in Redis with a 10-second TTL, refreshed every 5 seconds via heartbeat. If the WebSocket Service crashes:
- Session keys auto-expire after 10 seconds.
- The Ghost Cleaner (in Reporting Worker) detects stale listeners via `EXISTS ws:session:{client_id}` and removes them.
- Clients reconnect and re-subscribe, with no manual intervention required.

## Integration Boundaries Crossed

This scenario crosses the following integration boundaries, each with distinct protocols and failure modes:

| Boundary | Protocol | Direction | Failure Impact |
|----------|----------|-----------|----------------|
| User Network ↔ TP | Ethernet/IP | Bidirectional | None (data plane independent) |
| TP ↔ CN | Local UDP/IPC | Unidirectional | Telemetry loss only, traffic unaffected |
| CN ↔ CnSS Ingestion | UDP (port 5140) | Unidirectional | Telemetry loss tracked via sequence gaps |
| CnSS ↔ Redis | RESP (async) | Bidirectional | Ingestion buffering stalls, Pub/Sub stops |
| CnSS ↔ TimescaleDB | PostgreSQL (asyncpg) | Bidirectional | Persistence fails, but Redis buffering continues |
| MUI ↔ CnSS REST | HTTPS | Bidirectional | Authentication/discovery fails |
| MUI ↔ CnSS WebSocket | WSS | Bidirectional | Real-time updates stop, fallback timeout kicks in |

## Failure Modes and Recovery

| Failure Mode | Impact | Recovery Mechanism |
|--------------|--------|-------------------|
| **TP software crash** | Telemetry stops; traffic continues | FPGA continues forwarding; Docker restart policy restarts TP container |
| **CN crash** | Telemetry stops for that channel | Reporting Worker detects 5s timeout, broadcasts `is_active: false`; Docker restarts CN; Ingestion detects sequence reset on recovery |
| **CnSS Ingestion crash** | UDP packets dropped | Docker `restart: always`; Redis buffers persist (if Redis is up); CN continues sending, packets silently lost during downtime |
| **Redis crash** | All buffering, state, Pub/Sub lost | Redis restarts; sequence baselines reset; Ingestion resumes; accepted trade-off for performance |
| **TimescaleDB crash** | Persistence and aggregation fail | Ingestion continues buffering in Redis (capped at 100k); Reporting Worker skips SQL queries; WebSocket pushes last known state |
| **WebSocket Service crash** | Active connections dropped | Session keys expire (TTL 10s); Ghost Cleaner removes stale listeners; clients reconnect and re-subscribe |
| **Reporting Worker crash** | No real-time updates for 1s intervals | Docker restart policy; clients continue receiving last known state; MUI fallback timeout triggers `is_active: false` |
| **Network partition (CN → CnSS)** | UDP packets lost | Sequence tracking makes losses visible via `dropped_batches` metric; no retry mechanism (fire-and-forget design) |
| **MUI browser crash** | Client disconnects | WebSocket session expires via TTL; Garbage Collector cleans up subscriptions; no server-side state leak |

## Observability Points

The architecture exposes several key observability signals along this pipeline:

- **`dropped_batches`**: Counter in `telemetry_update` payload showing UDP datagram losses between CN and CnSS.
- **`is_active`**: Boolean flag derived from 5-second inactivity threshold, propagated to MUI in real-time.
- **`last_activity_at`**: Persisted in `channels` table, updated every second by Reporting Worker.
- **Redis memory usage**: Must be monitored to prevent OOM (configured `maxmemory 2gb`, `noeviction` policy).
- **TimescaleDB chunk count**: Retention policy (7 days) must be verified to prevent unbounded disk growth.
- **WebSocket connection count**: Tracked via `ws:session:*` keys; sudden spikes may indicate DDoS or client bugs.

## Conclusion

This end-to-end dynamic view demonstrates how the Traffic Processing Platform achieves its core design goals: **zero-impact monitoring** (data plane independence), **high-performance telemetry ingestion** (Redis buffering + batched DB writes), **real-time visualization** (1Hz aggregation + Pub/Sub push), and **operational resilience** (TTL-based cleanup, sequence tracking, dual-path timeout detection). Each component plays a specific, well-bounded role, and the system gracefully degrades under failure rather than catastrophically collapsing.
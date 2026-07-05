# ADR-002: Ephemeral Redis Buffering for High-Performance Telemetry Ingestion

## Status

**Accepted** — Implemented in MVP v2 and validated under production load.

## Context

The CnSS Ingestion Worker must handle high-frequency telemetry data from multiple Communication Nodes (CNs) via UDP. The system must:
- Ingest telemetry batches at high throughput (1000+ batches/second)
- Buffer data temporarily before persisting to TimescaleDB
- Handle traffic spikes without losing data or crashing
- Minimize latency between data reception and persistence

**Key constraints:**
- UDP is inherently unreliable (no delivery guarantees)
- TimescaleDB batch inserts are slower than UDP reception rate
- System must prevent Out-Of-Memory (OOM) crashes during traffic spikes
- Sequence tracking must survive container restarts

**Quality Requirements addressed:**
- **QR-001 (Time Behaviour)**: Minimize ingestion latency and maximize throughput
- **QR-002 (Fault Tolerance)**: Handle traffic spikes and component failures gracefully

## Decision

We use Redis as an ephemeral, in-memory buffer with the following configuration:

### Redis Configuration
- **Persistence**: Explicitly disabled (`save ""`, `appendonly no`)
- **Memory Limit**: 2GB (`maxmemory 2gb`)
- **Eviction Policy**: `noeviction` (reject writes when full)
- **Network**: Docker bridge network, internal only

### Buffering Strategy
1. **Capped Lists**: Each channel has a Redis list (`udp:buffer:{channel_id}`) capped at 100,000 items via `LTRIM`
2. **Atomic Operations**: Background flusher uses Lua scripts for atomic `LPOP` operations
3. **Sequence Tracking**: Per-channel sequence numbers stored in Redis (`channel:seq:{channel_id}`)
4. **State Management**: Channel activity state with 6-second TTL (`channel:state:{channel_id}`)

### Data Flow
```
CN → UDP → Ingestion Worker → Redis Buffer (capped list) → Background Flusher → TimescaleDB
```

### Failure Handling
- **Buffer Full**: New packets are dropped (logged) rather than causing OOM
- **Redis Crash**: Unflushed buffers lost, sequence baselines reset, system resumes gracefully
- **TimescaleDB Down**: Ingestion continues buffering in Redis (up to cap), flusher retries

## Consequences

### Positive
- **High Throughput**: Redis in-memory operations provide sub-millisecond buffering latency
- **No Disk I/O**: Ephemeral mode eliminates disk-write bottlenecks, maximizing IOPS
- **OOM Protection**: Capped lists prevent unbounded memory growth during traffic spikes
- **Atomic Operations**: Lua scripts ensure consistent state during concurrent access
- **Simple Recovery**: Redis restart is non-catastrophic; system resets and resumes
- **Sequence Tracking**: Survives container restarts (unlike in-memory state)

### Negative
- **Data Loss on Redis Restart**: Unflushed buffers and sequence states are lost
- **No Persistence**: Cannot recover buffered data after Redis failure
- **Memory Limit**: 2GB cap may be insufficient for very high-throughput scenarios
- **Single Point of Coordination**: All CnSS microservices depend on Redis availability
- **Noeviction Policy**: Writes fail when memory limit reached (must monitor closely)

### Risks
- **Redis OOM**: If cap is reached, new telemetry is dropped until flusher catches up
- **Redis Crash**: Temporary loss of buffering capacity; system degrades but doesn't fail
- **Network Partition**: If Redis becomes unreachable, ingestion stalls completely

## Quality Requirements Traceability

| Quality Requirement | How This Decision Addresses It |
|---------------------|-------------------------------|
| **QR-001 (Time Behaviour)** | Redis in-memory buffering provides sub-millisecond latency. Ephemeral mode (no persistence) maximizes IOPS. Capped lists prevent OOM-induced latency spikes. |
| **QR-002 (Fault Tolerance)** | Capped buffers prevent OOM crashes. Graceful degradation on Redis failure (system resets and resumes). Sequence tracking survives container restarts. |

## Alternatives Considered

### Alternative 1: Direct TimescaleDB Insert
- **Pros**: No buffering layer, simpler architecture
- **Cons**: UDP reception rate exceeds DB insert rate, causes backpressure and packet loss
- **Rejected because**: Cannot handle traffic spikes, higher latency

### Alternative 2: Persistent Redis (RDB/AOF)
- **Pros**: Data survives Redis restart
- **Cons**: Disk I/O reduces throughput, increases latency, complex recovery
- **Rejected because**: Performance trade-off unacceptable for real-time telemetry

### Alternative 3: Apache Kafka / Message Queue
- **Pros**: Durable, high-throughput, distributed
- **Cons**: Overkill for single-VM deployment, higher operational complexity, more resources
- **Rejected because**: Project scope and infrastructure constraints (single VM)

### Alternative 4: In-Memory Buffer (Python dict/list)
- **Pros**: Simple, no external dependency
- **Cons**: Lost on container restart, no sequence tracking persistence, harder to share across services
- **Rejected because**: Cannot survive container restarts, limits microservice decomposition

## References

- **System Architecture**: [docs/system-documentation.md](../../system-documentation.md) §2.3.1 Ingestion Worker
- **Redis Configuration**: [cnss/docker-compose.yml](../../../cnss/docker-compose.yml)
- **Lua Scripts**: [cnss/core/redis/lua/](../../../cnss/core/redis/lua/)
- **User Stories**: US-002 (Basic Network Usage Statistics)
# ADR-001: Hardware-Software Separation for Zero-Impact Monitoring

## Status

**Accepted** — Implemented in MVP v1 and validated in production deployment.

## Context

The Traffic Processing Platform must monitor network traffic in real-time without degrading network performance or causing service interruptions. The system operates as an inline bridge between LAN and WAN, meaning any failure in monitoring components must not disrupt user internet connectivity.

**Key constraints:**
- The system must forward packets at wire speed (Gigabit Ethernet)
- Monitoring failures must have zero impact on data plane operations
- The platform must extract detailed packet metadata for analysis
- Latency introduced by monitoring must be negligible (< 1ms)

**Quality Requirements addressed:**
- **QR-002 (Fault Tolerance)**: System must continue operating under component failures
- **QR-001 (Time Behaviour)**: Packet forwarding must meet wire-speed requirements

## Decision

We separate the Traffic Processor into two independent planes:

### Hardware Data Plane (FPGA)
- **Technology**: ARTIX-7 AX7201 FPGA programmed with SystemVerilog
- **Role**: Transparent inline bridge operating at wire speed
- **Responsibilities**:
  - Receive packets from LAN interface
  - Forward packets to WAN interface (and vice versa) with negligible latency
  - Mirror all passing traffic to the software telemetry plane
- **Independence**: Operates completely independently of all software components

### Software Telemetry Plane (TP + CN)
- **Technology**: Python + Scapy running in Docker containers
- **Role**: Extract packet metadata and forward to CnSS
- **Responsibilities**:
  - Receive mirrored traffic from FPGA
  - Extract metadata (IPs, ports, direction)
  - Batch and forward to CnSS via UDP
- **Failure Impact**: If TP/CN crash, telemetry stops but packet forwarding continues uninterrupted

## Consequences

### Positive
- **Zero-Impact Monitoring**: User traffic flows uninterrupted even if all software components fail
- **Wire-Speed Performance**: FPGA handles packet forwarding at hardware speed (no software overhead)
- **Fault Isolation**: Software failures are contained to monitoring functionality only
- **Independent Scaling**: Software components can be restarted/updated without affecting network connectivity
- **Hardware Acceleration**: FPGA provides deterministic latency for critical path operations

### Negative
- **Hardware Dependency**: Requires specialized FPGA hardware (ARTIX-7 AX7201)
- **Increased Complexity**: Two-tier architecture requires hardware + software stack management
- **Limited Flexibility**: FPGA logic is harder to modify compared to pure software solutions
- **Higher Cost**: FPGA development boards are more expensive than standard servers
- **Debugging Difficulty**: Hardware issues require specialized tools (Vivado, oscilloscopes)

### Risks
- **FPGA Firmware Bugs**: Could cause packet forwarding failures (mitigated by hardware watchdog)
- **Traffic Mirroring Overhead**: Must ensure mirroring doesn't exceed FPGA capacity
- **Single Point of Failure**: If FPGA fails, entire network connectivity is lost (mitigated by redundant hardware in production)

## Quality Requirements Traceability

| Quality Requirement | How This Decision Addresses It |
|---------------------|-------------------------------|
| **QR-002 (Fault Tolerance)** | Complete fault isolation between data plane (FPGA) and control plane (software). Software failures have zero impact on packet forwarding. |
| **QR-001 (Time Behaviour)** | FPGA provides wire-speed packet forwarding with deterministic latency (< 1μs), meeting Gigabit Ethernet requirements. |

## Alternatives Considered

### Alternative 1: Pure Software Solution (DPDK/AF_PACKET)
- **Pros**: No hardware dependency, easier to develop and debug
- **Cons**: Software packet forwarding introduces latency (10-100μs), cannot guarantee wire-speed performance, higher CPU utilization
- **Rejected because**: Cannot meet wire-speed requirements for high-throughput channels (1 Gbps+)

### Alternative 2: Network Tap + Separate Monitoring
- **Pros**: Complete isolation, no risk to production traffic
- **Cons**: Cannot operate as inline bridge, requires network topology changes, more expensive
- **Rejected because**: Customer requirement for inline deployment without network changes

### Alternative 3: Smart NIC with Monitoring
- **Pros**: Integrated solution, good performance
- **Cons**: Limited flexibility, vendor lock-in, higher cost
- **Rejected because**: FPGA provides more flexibility for custom telemetry extraction logic

## References

- **System Architecture**: [docs/system-documentation.md](../../system-documentation.md) §2.1 Traffic Processor
- **Deployment Diagram**: [docs/architecture/deployment-view/deployment-diagram.puml](../deployment-view/deployment-diagram.puml)
- **User Stories**: US-005, US-007, US-009 (Uninterrupted Traffic Flow)

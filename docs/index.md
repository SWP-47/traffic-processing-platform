# Traffic Processing Platform Documentation

Welcome to the official documentation for the Traffic Processing Platform — a minimally intrusive network traffic monitoring system.

## Overview

This platform consists of four distinct components designed to capture, process, forward, and visualize network telemetry in real-time without degrading network performance:

- **Traffic Processor (TP)**: Core packet counting and telemetry engine (transparent inline bridge)
- **Communication Node (CN)**: Local data forwarding node
- **Control and Status Server (CnSS)**: Backend aggregating data via API/WebSocket
- **Management User Interface (MUI)**: Frontend for real-time visualization

## Quick Links

| Resource | Link |
|----------|------|
| **Live Dashboard** | [http://10.93.26.186](http://10.93.26.186) |
| **Architecture** | [Architecture Overview](architecture/README.md) |
| **Development Process** | [Git Workflow](development-process.md) |
| **Quality Requirements** | [Quality Gates](quality-requirements.md) |

## Documentation Sections

### Architecture

- [**Static View**](architecture/static-view/README.md) — Component structure and data flows
- [**Dynamic View**](architecture/dynamic-view/README.md) — Runtime behavior and sequences
- [**Deployment View**](architecture/deployment-view/README.md) — Infrastructure topology
- [**Architectural Decision Record 1**](architecture/adr/adr-001-hardware-software-separation.md) — Key design decision 1
- [**Architectural Decision Record 2**](architecture/adr/adr-002-ephemeral-redis-buffering.md) — Key design decision 2
- [**Architectural Decision Record 3**](architecture/adr/adr-003-microservice-decomposition.md) — Key design decision 3


### Development

- [**Development Process**](development-process.md) — Git workflow and team roles
- [**Quality Requirements**](quality-requirements.md) — Measurable quality gates
- [**Definition of Done**](definition-of-done.md) — Completion criteria
- [**Testing Strategy**](testing.md) — Test coverage and approach


## Repository

- **Source Code**: [GitHub Repository](https://github.com/SWP-47/traffic-processing-platform)
- **Issues**: [Issue Tracker](https://github.com/SWP-47/traffic-processing-platform/issues)
- **Releases**: [SemVer Releases](https://github.com/SWP-47/traffic-processing-platform/releases)
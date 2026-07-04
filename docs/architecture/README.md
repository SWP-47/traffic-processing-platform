# Architecture Documentation

This directory contains the architectural documentation for the Traffic Processing Platform, following a **diagrams-as-code** approach using PlantUML. All diagrams are stored as source files within the repository to ensure they evolve alongside the codebase.

## Table of Contents

1. [Static View](static-view/) — Component structure, interfaces, and data flows
2. [Dynamic View](dynamic-view/) — Runtime behavior and interaction sequences
3. [Deployment View](deployment-view/) — Infrastructure topology and deployment topology

## How to Render Diagrams

All diagrams are stored as `.puml` (PlantUML) source files. You can render them using:

- **VS Code Extension**: [PlantUML](https://marketplace.visualstudio.com/items?itemName=jebbs.plantuml)

Pre-rendered PNG/SVG versions are also provided alongside the source files for convenience.

## Architecture Principles

The platform is built on the following core principles:

1. **Separation of Data Plane and Control Plane**: The Traffic Processor forwards packets at wire speed (data plane) while independently extracting telemetry (control plane). Failure in monitoring must never disrupt traffic flow.
2. **Modular Monorepo**: Four loosely coupled components (`traffic-processor`, `communication-node`, `cnss`, `mui`) communicate via well-defined protocols (UDP, WebSocket, REST).
3. **Ephemeral State, Persistent Storage**: Redis handles high-speed ephemeral buffering and state tracking; TimescaleDB serves as the single source of truth for persistent time-series data.
4. **Horizontal Scalability**: The CnSS is decomposed into four independent microservices that can be scaled independently based on load.
5. **Security by Design**: JWT-based authentication, scope-based authorization, centralized TLS termination, and token masking in logs.
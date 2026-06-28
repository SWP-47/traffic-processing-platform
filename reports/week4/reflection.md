# Week 4 Reflection

**Team**: Team 47\
**Sprint**: Sprint 2\
**Date**: June 28, 2026

---

## Learning points

* **Responding to Customer Feedback**: We learned that system administrators prefer "rigid", data-dense, and highly readable interfaces over heavily smoothed, "beautiful" charts. The customer's feedback on removing curve smoothing and adding a toggle for raw RX/TX numbers highlighted a crucial UX principle for monitoring tools: accuracy and quick readability must take precedence over visual aesthetics.
* **Defining and Automating Quality Requirements**: Initially, we struggled definining measurable non-functional requirements for our specific architecture. The customer's advice to "just pick three measurable things you can automate in CI" helped us take action. We learned how to translate abstract concepts (like "handling high-throughput channels" and "security") into concrete, automatable CI gates (e.g., Health API response time limits, JWT scope enforcement, and strict coverage thresholds).
* **Configuring CI and Additional QA Checks**: We learned the critical importance of dependency vulnerability scanning for a system that ingests untrusted network payloads. Implementing `pip-audit` in our CI pipeline highlighted how easily transitive vulnerabilities can slip into Python projects and reinforced the need for automated security gates before merging.

## Validated assumptions

* **TimescaleDB Ingestion Capacity**:
  * *Assumption*: TimescaleDB and our `asyncpg` batch-insert pipeline could handle the ingestion rate of raw packet metadata for a 100 Mbps channel without bottlenecking.
  * *Validation*: Confirmed during manual testing. We successfully stress-tested the backend to 6,000 packets/sec in one direction (~72-150 Mbps bidirectional). The server handled the load, wrote to the hypertable efficiently, and maintained the 1Hz Reporting Worker without dropping batches.
* **WebSocket Delta Updates vs. Full State**:
  * *Assumption*: Pushing only delta updates for the real-time host tables via WebSocket, rather than recalculating and pushing the entire chart state, would optimize database load and frontend rendering.
  * *Validation*: The customer approved this approach, and our implementation of the `WSClientSession` subscription model proved that skipping heavy DB queries when no clients are listening significantly reduced CPU and I/O overhead.
* **In-Memory State Store Limitations**:
  * *Assumption*: The legacy in-memory state store used in MVP v1 was insufficient for historical data retention and posed a memory leak risk over long uptimes.
  * *Validation*: Transitioning to TimescaleDB successfully enabled the historical line charts and resolved the memory constraints, validating the need to shift from `InMemoryStateStore` to a persistent, time-series-optimized database.

## Friction and gaps

* **Legacy Code Technical Debt**: While we migrated the core functionality to TimescaleDB, legacy in-memory storage code and fallback logic still exist in the Python CnSS backend.
* **Database Growth Monitoring**: The customer pointed out the need to track Docker volume growth relative to row counts to build "intuition" about disk usage.
* **Deferred UX Improvements**: Due to sprint capacity constraints, the customer's request for a toggle switch between the RX/TX column chart and raw numbers was deferred.

## Planned response

* **Backend Cleanup**: We will create a PBI in Sprint 3 to completely remove the legacy `InMemoryStateStore` and associated fallback logic from the CnSS backend, ensuring a single source of truth (TimescaleDB).
* **Implement Deferred UX**: We will implement the RX/TX raw number toggle switch and finalize the "View all" pagination for the Top-5 host tables based on the customer's exact specifications.
* **Maintain Quality Gates**: The QRTs defined this week (QR-001, QR-002, QR-003) and the `pip-audit` CI check will be strictly enforced in Sprint 3. Any new PBIs touching the CnSS authentication or telemetry ingestion modules will be required to maintain the ≥30% coverage threshold.

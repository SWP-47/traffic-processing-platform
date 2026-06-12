# User stories

## US-001: Channel Activity Indicator

**Requirement Status:** Active
**MoSCoW priority:** Must Have

As a system administrator,
I want to see a simple indicator of channel activity
so that I can quickly see if a connection is active.

### US-001 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-002: Basic Network Usage Statistics

**Requirement Status:** Active
**MoSCoW priority:** Must Have

As a system administrator,
I want to see how many packets and bytes are passing through the channel,
so that I can gather basic network usage statistics.

### US-002 Notes and constraints

* How important is the accuracy (what timing error is acceptable)?
* Regarding the question of whether it is possible to assign a single timestamp to a burst of packets for CN and transmit them with it.

---

## US-004: Modular Platform Integration

**Requirement Status:** Active
**MoSCoW priority:** Must Have

As a system administrator,
I want to integrate the platform to existing network by parts
so each component can be easily deployed in any place.

### Us-004 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-005: Invisible Traffic Analyzer Deployment

**Requirement Status:** Active
**MoSCoW priority:** Must Have

As a network end user,
I want the deployment of the traffic analyzer to be completely invisible to both me and my router,
so that my internet access is not disrupted.

### US-005 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-007: No Noticeable Network Slowdown

**Requirement Status:** Active
**MoSCoW priority:** Must Have

As an end user,
I want the traffic analyzer to operate without noticeably slowing down my network speed,
so that my internet access isn't disrupted.

### US-007 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-009: Seamless Bidirectional Packet Passing

**Requirement Status:** Active
**MoSCoW priority:** Must Have

As a system administrator,
I want the Traffic Processor to seamlessly pass network packets in both directions,
so that the primary internet connection remains fully functional.

### US-009 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-014: Remote MUI Access

**Requirement Status:** Active
**MoSCoW priority:** Must Have

As a system administrator,
I want to access the MUI from anywhere via the internet,
so that I can monitor a closed local network remotely.

### US-014 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-015: Real-time MUI Dashboard Updates

**Requirement Status:** Active
**MoSCoW priority:** Must Have

As a system administrator,
I want the MUI dashboard to update automatically in real-time without manual refreshing,
so that I always see the current state of the channel.

### US-015 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-006: Specific IP Traffic Analysis

**Requirement Status:** Active
**MoSCoW priority:** Should Have

As an Information Security specialist,
I want to be able to select a specific IP address and view all its traffic,
so that I can quickly understand what a particular computer on the network is doing and detect any suspicious activity originating from it.

### US-006 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-013: Historical Traffic Statistics Storage

**Requirement Status:** Active
**MoSCoW priority:** Should Have

As a system administrator,
I want the server to save traffic statistics to a database,
so that I can view historical data and not just the current real-time state.

### US-013 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-003: Traffic Information Export

**Requirement Status:** Active
**MoSCoW priority:** Could Have

As a system administrator,
I want to export all brief information which the system got from the traffic as a single file
so that I can analyse it and find critical network vulnerabilities.

### US-003 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]

---

## US-008: SYN Flood Attack Detection

**Requirement Status:** Active
**MoSCoW priority:** Could Have

As an Information Security specialist,
I want the system to count how many SYN packets (handshake requests) arrive and how many of them actually receive responses,
so that I can detect attempts to overwhelm the network with thousands of empty requests (SYN flood attacks).

### US-008 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-010: Protocol Type Traffic Filtering

**Requirement Status:** Active
**MoSCoW priority:** Could Have

As a system administrator,
I want to filter traffic by protocol type (TCP, UDP, ICMP),
so that I can focus analysis on specific communication types.

### US-010 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-011: Throughput Values Display

**Requirement Status:** Active
**MoSCoW priority:** Could Have

As a system administrator,
I want the interface to show average, minimum, and maximum throughput values,
so that I can understand network capacity utilization.

### US-011 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

---

## US-012: Basic Password Protection for MUI

**Requirement Status:** Active
**MoSCoW priority:** Could Have

As a system administrator,
I want the web interface (MUI) to be protected by a basic password,
so that unauthorized users cannot view the network statistics.

### US-012 Notes and constraints

_[Add any relevant notes, constraints, assumptions, or open questions here]_

## Initial proposed MVP v1 scope

All "Must Have" user stories: US-001, US-002, US-004, US-005, US-007, US-009, US-014, US-015

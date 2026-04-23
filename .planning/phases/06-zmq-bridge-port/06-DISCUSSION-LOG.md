# Phase 6: ZMQ Bridge Port - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 06-zmq-bridge-port
**Areas discussed:** Deployment Topology, Schema Versioning, Heartbeat + Reconnect Policy, Bar-Close Detection

---

## Deployment Topology

| Option | Description | Selected |
|--------|-------------|----------|
| Windows only (same machine as MT5) | Loopback 127.0.0.1, simplest for spike | |
| Ubuntu only (separate machine) | Cross-machine TCP/WireGuard, matches V1 | |
| Either — bridge must work on both | Configurable host, both OS supported | ✓ |

**User's choice:** Either — bridge must work on both Windows and Ubuntu systems

| Option | Description | Selected |
|--------|-------------|----------|
| V2/bridge/ with same ports as V1 (5556–5559) | Familiar, avoids conflicts | |
| V2/bridge/ with new ports (5600–5603) | Fresh range for V1/V2 coexistence | |
| V2/bridge/ with env-configurable ports | Default 5556–5559, overridable via env vars | ✓ |

**User's choice:** Env-configurable ports

| Option | Description | Selected |
|--------|-------------|----------|
| WireGuard VPN (same as V1) | Encrypted tunnel, 10.200.0.x | ✓ |
| Plain LAN TCP | Direct IP, no VPN overhead | |
| Claude's Discretion | Transport is deployment concern only | |

**User's choice:** WireGuard VPN (same as V1)

| Option | Description | Selected |
|--------|-------------|----------|
| PUB/SUB topology (current V1 design) | MT5 publishes, multiple Python subscribers | ✓ |
| Single consumer only (PUSH/PULL) | Simpler, Phase 6 only needs one consumer | |

**User's choice:** PUB/SUB for market data (optimal — fan-out for free, monitoring scripts can tap same feed). PUSH/PULL retained for orders/fills.

---

## Schema Versioning

| Option | Description | Selected |
|--------|-------------|----------|
| Module-level constant only | SCHEMA_VERSION = 1 in schemas.py, Heartbeat carries version | ✓ |
| Version field in every message | ~3 bytes per message, runtime mismatch detection | |
| Version in filename only (schema_v1.py) | No runtime detection | |

**User's choice:** Module-level constant only

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — Heartbeat carries schema_version field | Version negotiation on low-frequency keepalive | ✓ |
| No — version constant only, no runtime negotiation | Simpler, mismatch detected by failed unpack | |

**User's choice:** Yes — Heartbeat carries schema_version field

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — rename to Fill (matches BRDG-01 spec) | V2 breaks from V1 naming intentionally | ✓ |
| Keep OrderResult (matches V1) | Preserve V1 naming convention | |

**User's choice:** Yes — rename to Fill

---

## Heartbeat + Reconnect Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Keep V1 defaults: 5s interval / 10s stale | Proven in V1, appropriate for daily signals | ✓ |
| Tighter: 2s interval / 5s stale | More network traffic, unnecessary for daily signals | |
| Looser: 15s interval / 30s stale | Lower overhead | |

**User's choice:** Keep V1 defaults: 5s / 10s

| Option | Description | Selected |
|--------|-------------|----------|
| One missed heartbeat = reconnect attempt | 10s without heartbeat triggers reconnect | ✓ |
| Stale flag only — let consumer decide | Pushes responsibility upstream | |
| Hard threshold: 3 missed heartbeats | Reduces spurious reconnects, +15s stale risk | |

**User's choice:** One missed heartbeat = reconnect attempt (matches BRDG-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep V1 backoff exactly (1→2→4→8→16→30s) | Proven in V1 | ✓ |
| Cap lower: 1→2→4→8→10s | Faster recovery ceiling | |
| Claude's Discretion | Implementation detail | |

**User's choice:** Keep V1 backoff exactly

---

## Bar-Close Detection in MQL5

| Option | Description | Selected |
|--------|-------------|----------|
| OnTimer + RATES_TOTAL change detection | Consistent with existing lastBarTime[] tracking | ✓ |
| OnTick + timestamp comparison | More event-driven, fires on every tick | |
| Dedicated OnCalculate in indicator | Cleanest separation, adds second MQL5 file | |

**User's choice:** OnTimer + RATES_TOTAL change detection

| Option | Description | Selected |
|--------|-------------|----------|
| Daily (D1) only | Matches daily signal cadence | |
| D1 + H1 | Daily swing + intraday strategies | |
| All active timeframes (D1, H1, M15) | Future-proofs the bridge for v2.0 router | ✓ |

**User's choice:** All active timeframes (D1, H1, M15)

| Option | Description | Selected |
|--------|-------------|----------|
| Full OHLCV + timeframe tag | Python receives everything without follow-up query | ✓ |
| Bar close price + timestamp + timeframe only | Minimal payload, requires round-trip for OHLC | |

**User's choice:** Full OHLCV + timeframe tag

---

## Claude's Discretion

- Python class structure for consumer (async vs sync API surface)
- Whether to split publisher and consumer into separate files or single bridge module
- MQL5 ZMQ library selection (mql-zmq vs alternatives) — subject to DLL spike results
- Test harness structure for BRDG-03 spike

## Deferred Ideas

None — discussion stayed within phase scope.

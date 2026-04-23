# Phase 6: ZMQ Bridge Port - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a Python↔MT5 ZMQ bridge in V2 from scratch: versioned msgpack schema contract, heartbeat/auto-reconnect, DLL compatibility spike on the IC Markets MT5 terminal, and bar-close event publishing from the MQL5 EA. The bridge is the IPC layer only — signal logic, routing, and order execution are separate phases. Phase 6 success = bridge operational and BRDG-03 go/no-go gate cleared.

</domain>

<decisions>
## Implementation Decisions

### Deployment Topology
- **D-01:** Bridge code lives in `V2/bridge/` — greenfield directory, no V1 code migrated directly
- **D-02:** Python signal engine must run on **both Windows and Ubuntu** — bridge uses configurable host, not hardcoded platform assumptions
- **D-03:** Ports are **env-configurable** via `ZMQ_TICK_PORT`, `ZMQ_BAR_PORT`, `ZMQ_ORDER_PORT`, `ZMQ_FILL_PORT` with defaults matching V1 (5556, 5557, 5558, 5559)
- **D-04:** Cross-machine deployment (Ubuntu Python ↔ Windows MT5) uses **WireGuard VPN** — same as V1 (10.200.0.x addresses)
- **D-05:** **PUB/SUB for market data** (tick/bar streams): MT5 publishes once, multiple Python consumers can subscribe independently. **PUSH/PULL for orders/fills**: one-to-one, only one EA receives each OrderRequest

### Schema Versioning
- **D-06:** Schema versioning uses a **module-level `SCHEMA_VERSION = 1` constant** in `V2/bridge/schemas.py` — no per-message version field on high-frequency Tick/Bar messages (avoids latency overhead)
- **D-07:** **Heartbeat message carries `schema_version` field** — Python consumer checks incoming Heartbeat version on connect and logs a warning if mismatched. Version negotiation happens on the low-frequency keepalive only
- **D-08:** V2 **renames `OrderResult` to `Fill`** to match BRDG-01 spec (Tick, Bar, OrderRequest, Fill, Heartbeat). V1 called it `OrderResult` — V2 breaks from V1 naming intentionally

### Heartbeat + Reconnect Policy
- **D-09:** Heartbeat interval: **5 seconds** (match V1 default)
- **D-10:** Stale threshold: **10 seconds** without heartbeat = data considered stale
- **D-11:** Auto-reconnect triggers on **one missed heartbeat cycle** (10s elapsed without heartbeat received)
- **D-12:** Reconnect uses **V1 exponential backoff schedule**: 1s → 2s → 4s → 8s → 16s → 30s (capped)

### Bar-Close Detection in MQL5
- **D-13:** EA detects bar close via **OnTimer + RATES_TOTAL change** — consistent with existing `lastBarTime[]` tracking in `V2/ea/MultiPairEA.mq5`. On each timer tick, check if RATES_TOTAL increased; if so, previous bar just closed
- **D-14:** Publish bar-close events for **all three active timeframes: D1, H1, M15** — timeframe tag included in every bar message
- **D-15:** Bar-close message payload: **full OHLCV + timeframe tag** — symbol, timestamp, open, high, low, close, volume, spread, timeframe string (e.g. "D1"). Python receives everything it needs without a follow-up MT5 query

### Claude's Discretion
- Exact Python class structure for consumer (async vs sync API surface)
- Whether to split publisher and consumer into separate files or keep as a single bridge module
- MQL5 ZMQ library selection (mql-zmq vs alternatives) — subject to DLL spike results
- Test harness structure for BRDG-03 spike

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — BRDG-01 through BRDG-04 definitions (schema contract, heartbeat, DLL spike, bar-close publishing)
- `.planning/ROADMAP.md` — Phase 6 goal, success criteria, and dependency on Phase 5 foundation

### V1 Bridge Source (port reference)
- `V1/helix/src/execution/bridge/message_schemas.py` — V1 msgpack pack/unpack for all message types; V2 schema is based on this with Fill rename and schema_version in Heartbeat
- `V1/helix/src/execution/bridge/linux_consumer.py` — V1 async consumer with reconnect logic and stale detection; V2 consumer mirrors this architecture
- `V1/helix/src/execution/bridge/windows_publisher.py` — V1 publisher with heartbeat loop and order handling; V2 publisher mirrors this
- `V1/helix/src/execution/abstract.py` — V1 dataclass definitions (Tick, Bar, OrderRequest, OrderResult) — V2 redefines these in bridge/types.py with Fill rename

### V2 EA (to modify for BRDG-04)
- `V2/ea/MultiPairEA.mq5` — EA skeleton with existing OnTimer, lastBarTime[], CCircuitBreaker; bar-close ZMQ publishing wired here
- `V2/ea/include/CCircuitBreaker.mqh` — Risk layer that OrderRequest execution routes through (must not be broken by ZMQ additions)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `V1/helix/src/execution/bridge/message_schemas.py`: Full msgpack schema — copy into V2/bridge/schemas.py with modifications (Fill rename, schema_version in Heartbeat). All pack/unpack logic is reusable.
- `V1/helix/src/execution/bridge/linux_consumer.py`: `LinuxConsumer` class with async ZMQ, RECONNECT_DELAYS, STALE_THRESHOLD, `is_stale` property — port directly to V2/bridge/consumer.py
- `V1/helix/src/execution/bridge/windows_publisher.py`: `WindowsPublisher` with heartbeat loop — port to V2/bridge/publisher.py
- `V2/ea/MultiPairEA.mq5`: Has `lastBarTime[5]` array and OnTimer(1s) — bar-close detection hooks here, no structural rewrite needed

### Established Patterns
- V1 bridge uses async/await throughout (zmq.asyncio) — V2 should follow the same async pattern
- ZMQ multipart messages: `[symbol_bytes, payload_bytes]` for PUB sockets (enables topic filtering on subscribers)
- Heartbeat sent as single-frame on the tick PUB socket (no symbol prefix) — Python consumer distinguishes heartbeat vs tick by frame count

### Integration Points
- `V2/bridge/` → connects to `V2/v3_intelligence/` (signal engine will subscribe to bar-close events in Phase 10)
- `V2/ea/MultiPairEA.mq5` → ZMQ PUSH socket added alongside existing CCircuitBreaker/CLogger/CScalingManager calls
- Port config → shared via env vars between Python bridge and MQL5 EA (EA reads from input params, Python reads from env)

</code_context>

<specifics>
## Specific Ideas

- The V1 `RECONNECT_DELAYS = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]` list should be copied verbatim into V2 consumer
- Heartbeat pack function should add `"schema_version": SCHEMA_VERSION` field: `{"type": "heartbeat", "ts": ns, "schema_version": 1}`
- MQL5 bar-close message should use the `Bar` msgpack schema extended with a `tf` (timeframe) string field: `{"ts": ..., "sym": ..., "tf": "D1", "o": ..., "h": ..., "l": ..., "c": ..., "v": ..., "sp": ...}`
- BRDG-03 spike: test mql-zmq DLL load + single test message send on IC Markets terminal — pass/fail gate, not a full integration test

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-zmq-bridge-port*
*Context gathered: 2026-04-23*

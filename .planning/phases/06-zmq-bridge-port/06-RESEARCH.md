# Phase 6: ZMQ Bridge Port - Research

**Researched:** 2026-04-23
**Domain:** ZeroMQ IPC bridge — Python async consumer/publisher, msgpack schema versioning, MQL5 DLL integration, bar-close event publishing
**Confidence:** HIGH (V1 source is authoritative; pyzmq/msgpack versions verified from live environment; mql-zmq confirmed via GitHub)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Deployment Topology**
- D-01: Bridge code lives in `V2/bridge/` — greenfield directory, no V1 code migrated directly
- D-02: Python signal engine must run on both Windows and Ubuntu — bridge uses configurable host, not hardcoded platform assumptions
- D-03: Ports are env-configurable via `ZMQ_TICK_PORT`, `ZMQ_BAR_PORT`, `ZMQ_ORDER_PORT`, `ZMQ_FILL_PORT` with defaults matching V1 (5556, 5557, 5558, 5559)
- D-04: Cross-machine deployment (Ubuntu Python <-> Windows MT5) uses WireGuard VPN — same as V1 (10.200.0.x addresses)
- D-05: PUB/SUB for market data (tick/bar streams); PUSH/PULL for orders/fills

**Schema Versioning**
- D-06: Schema versioning uses a module-level `SCHEMA_VERSION = 1` constant in `V2/bridge/schemas.py` — no per-message version field on high-frequency Tick/Bar messages
- D-07: Heartbeat message carries `schema_version` field — Python consumer checks on connect and logs warning if mismatched
- D-08: V2 renames `OrderResult` to `Fill` — intentional break from V1 naming

**Heartbeat + Reconnect Policy**
- D-09: Heartbeat interval: 5 seconds
- D-10: Stale threshold: 10 seconds without heartbeat = data considered stale
- D-11: Auto-reconnect triggers on one missed heartbeat cycle (10s elapsed)
- D-12: Reconnect uses V1 exponential backoff: 1s -> 2s -> 4s -> 8s -> 16s -> 30s (capped)

**Bar-Close Detection in MQL5**
- D-13: EA detects bar close via OnTimer + RATES_TOTAL change — matches existing `lastBarTime[]` pattern in MultiPairEA.mq5
- D-14: Publish bar-close events for all three active timeframes: D1, H1, M15
- D-15: Bar-close message payload: full OHLCV + timeframe tag (symbol, timestamp, open, high, low, close, volume, spread, timeframe string)

### Claude's Discretion
- Exact Python class structure for consumer (async vs sync API surface)
- Whether to split publisher and consumer into separate files or keep as a single bridge module
- MQL5 ZMQ library selection (mql-zmq vs alternatives) — subject to DLL spike results
- Test harness structure for BRDG-03 spike

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BRDG-01 | Versioned msgpack schema contract file defines Tick, Bar, OrderRequest, Fill, Heartbeat types before any bridge code is written | V1 `message_schemas.py` is the direct port base; Fill rename and schema_version addition are small deltas documented below |
| BRDG-02 | ZMQ bridge has heartbeat + auto-reconnect | V1 `linux_consumer.py` and `windows_publisher.py` implement this exactly; V2 ports with configurable host and env-driven ports |
| BRDG-03 | mql-zmq DLL compatibility confirmed on IC Markets MT5 terminal (go/no-go spike) | DLL installation procedure, "Allow DLL imports" setting location, known failure modes documented below |
| BRDG-04 | MT5 EA publishes completed bars per pair with timeframe tag; Python reacts on bar close | OnTimer + RATES_TOTAL pattern is validated MQL5 idiom; multipart PUB send with `sendMore()` is the wire format |
</phase_requirements>

---

## Summary

Phase 6 is a port-and-extend operation, not a greenfield build. The V1 bridge (`V1/helix/src/execution/bridge/`) is a fully functional, tested ZMQ bridge that covers everything except: (1) Fill rename, (2) `schema_version` field on Heartbeat, (3) env-configurable ports, and (4) the MQL5 EA bar-close publisher. All Python-side code adapts directly from V1. The MQL5 side requires integrating the mql-zmq DLL library and adding a PUSH socket to the existing `OnTimer` bar-close detection loop in `MultiPairEA.mq5`.

The BRDG-03 DLL spike is the only genuine unknowable — IC Markets may restrict DLL imports at the broker level (separate from the terminal "Allow DLL imports" checkbox). The spike must be run on the live IC Markets MT5 terminal before any downstream EA work begins. If the DLL loads and sends one message without crash, Phase 10 is unblocked.

**Primary recommendation:** Port V1 Python bridge files verbatim into `V2/bridge/`, apply the three schema deltas (Fill rename, schema_version, env ports), then implement the MQL5 bar-close publisher in `MultiPairEA.mq5`. Run BRDG-03 spike immediately after DLL installation.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyzmq | 27.1.0 | ZeroMQ Python bindings with asyncio support | Already installed in project venv; matches V1 |
| msgpack | 1.1.2 | Binary serialization for bridge messages | Already installed in project venv; matches V1 |
| zmq.asyncio | (bundled with pyzmq) | Async-compatible ZMQ context and sockets | Required for async consumer pattern from V1 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 1.26.3 | `datetime64[ns]` timestamp encoding/decoding | Required for ns-precision timestamps in schema |
| mql-zmq (dingmaotu) | ZMQ 4.2.0 DLL | ZeroMQ binding for MQL5 EA | Primary DLL candidate for BRDG-03 spike |
| coke5151/mql5-zmq (fork) | ZMQ 4.2.0 DLL | MQL5-only fork fixing type errors | Fallback if original dingmaotu build fails compilation on modern MQL5 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mql-zmq (dingmaotu) | ding9736/MQL5-ZeroMQ | ding9736 is a more modern rewrite (3.0) but is newer and less battle-tested; dingmaotu is the original and most referenced |
| mql-zmq (dingmaotu) | coke5151/mql5-zmq | coke5151 is a targeted fix fork for modern MQL5 type errors — use as fallback if dingmaotu fails compilation |
| pyzmq + asyncio | aiozmq | aiozmq is deprecated and unmaintained; pyzmq asyncio support is native since v14 |

**Installation (Python — already installed, verify before use):**
```bash
# Verify current installed versions in project venv
pip show pyzmq msgpack numpy
# Expected: pyzmq 27.1.0, msgpack 1.1.2, numpy 1.26.3
```

**MQL5 DLL installation:**
```
1. Clone dingmaotu/mql-zmq or download release
2. Copy Library/MT5/libzmq.dll      -> MT5_DATA_DIR/MQL5/Libraries/
3. Copy Library/MT5/libsodium.dll   -> MT5_DATA_DIR/MQL5/Libraries/
4. Copy Include/Zmq/               -> MT5_DATA_DIR/MQL5/Include/Zmq/
5. Copy Include/Mql/               -> MT5_DATA_DIR/MQL5/Include/Mql/
6. Install Visual C++ 2015 Runtime (x64) if not present
7. MT5 terminal: Tools > Options > Expert Advisors > "Allow DLL imports" = ON
```

**Version verification:**
```bash
pip show pyzmq  # Verified: 27.1.0 (latest as of 2026-04-23)
pip show msgpack  # Verified: 1.1.2 (latest as of 2026-04-23)
```

---

## Architecture Patterns

### Recommended Project Structure
```
V2/
└── bridge/
    ├── __init__.py          # exports BridgeConsumer, BridgePublisher
    ├── types.py             # Tick, Bar, OrderRequest, Fill dataclasses (V2 definitions)
    ├── schemas.py           # SCHEMA_VERSION=1; pack_*/unpack_* functions
    ├── consumer.py          # BridgeConsumer (async, env-configurable host/ports)
    ├── publisher.py         # BridgePublisher (async, env-configurable ports)
    └── spike/
        └── brdg03_spike.py  # Standalone spike: DLL load test + single message send
```

```
V2/
└── ea/
    ├── MultiPairEA.mq5      # MODIFIED: add ZMQ context, PUB socket, bar-close send
    └── include/
        └── (existing .mqh files unchanged)
```

```
V2/
└── tests/
    └── unit_tests/
        └── bridge/
            ├── test_schemas.py     # Pack/unpack round-trips for all 5 types
            ├── test_consumer.py    # Stale detection, reconnect backoff, receive_loop
            └── test_publisher.py   # Heartbeat loop, publish_tick, publish_bar
```

### Pattern 1: Schema Contract File (BRDG-01)

**What:** A single `V2/bridge/schemas.py` file defines `SCHEMA_VERSION = 1` as a module constant, then provides `pack_*` / `unpack_*` functions for all five message types. No bridge code creates message dicts ad-hoc — all serialization routes through this file.

**When to use:** Every cross-bridge message send/receive.

**V2 schema deltas from V1:**

```python
# V2/bridge/schemas.py — key changes from V1

SCHEMA_VERSION = 1  # D-06: module-level constant

# 1. Heartbeat gains schema_version field (D-07)
def pack_heartbeat() -> bytes:
    ns = int(time.time_ns())
    return msgpack.packb({"type": "heartbeat", "ts": ns, "schema_version": SCHEMA_VERSION})

def unpack_heartbeat(data: bytes) -> dict:
    return msgpack.unpackb(data)  # caller checks ["schema_version"]

# 2. Fill replaces OrderResult (D-08)
def pack_fill(fill: Fill) -> bytes:  # was pack_order_result
    return msgpack.packb({
        "oid": fill.order_id,
        "fp": fill.fill_price,
        "fq": fill.fill_quantity,
        "slip": fill.slippage,
        "comm": fill.commission,
        "ok": fill.success,
        "err": fill.error_message,
    })

# 3. Bar gains timeframe tag for bar-close messages (D-15)
def pack_bar(bar: Bar, timeframe: str = "") -> bytes:
    payload = {
        "ts": _dt64_to_ns(bar.timestamp),
        "sym": bar.symbol,
        "o": bar.open, "h": bar.high, "l": bar.low, "c": bar.close,
        "v": bar.volume, "sp": bar.spread,
    }
    if timeframe:
        payload["tf"] = timeframe  # e.g. "D1", "H1", "M15"
    return msgpack.packb(payload)
```

**Source:** V1 `message_schemas.py` + CONTEXT.md D-06/D-07/D-08/D-15

### Pattern 2: Env-Configurable Ports (BRDG-02, D-03)

**What:** Python publisher reads port values from environment variables with fallback defaults.

**Example:**
```python
# V2/bridge/publisher.py
import os

TICK_PORT:     int = int(os.getenv("ZMQ_TICK_PORT",  "5556"))
BAR_PORT:      int = int(os.getenv("ZMQ_BAR_PORT",   "5557"))
ORDER_PORT:    int = int(os.getenv("ZMQ_ORDER_PORT", "5558"))
FILL_PORT:     int = int(os.getenv("ZMQ_FILL_PORT",  "5559"))
```

MQL5 EA reads ports from input parameters (not env vars — MQL5 has no env API):
```mql5
input int InpTickPort  = 5556;
input int InpBarPort   = 5557;
input int InpOrderPort = 5558;
input int InpFillPort  = 5559;
input string InpPythonHost = "10.200.0.1";  // WireGuard VPN address
```

### Pattern 3: Async Consumer with Heartbeat Guard (BRDG-02)

**What:** `BridgeConsumer` is a direct port of `LinuxConsumer` from V1, with `_host` defaulting to `os.getenv("BRIDGE_HOST", "10.200.0.1")` and ports from env vars.

**Reconnect trigger:** Consumer tracks `_last_heartbeat` via `time.monotonic()`. Any caller that detects `is_stale` (10s threshold) must call `await consumer._reconnect()` or wrap the receive loop with a supervisor task that checks staleness and reconnects.

**Critical pattern — heartbeat vs tick disambiguation:**
```python
# Heartbeats arrive on tick socket as single-frame messages.
# Ticks arrive as two-frame [symbol_bytes, payload_bytes].
# The V1 pattern (frame count check) is the correct discriminator — use it verbatim.
frames = await self._tick_sub.recv_multipart()
if len(frames) == 1:
    # heartbeat
    d = unpack_heartbeat(frames[0])
    if d.get("schema_version") != SCHEMA_VERSION:
        logger.warning("Schema version mismatch: remote=%s", d.get("schema_version"))
    self._last_heartbeat = time.monotonic()
elif len(frames) == 2:
    bar_or_tick = unpack_tick(frames[1])
    await on_tick(bar_or_tick)
```

**Source:** V1 `linux_consumer.py` + CONTEXT.md D-07

### Pattern 4: MQL5 Bar-Close Publisher (BRDG-04)

**What:** In `MultiPairEA.mq5`, wire a ZMQ PUSH socket to the existing `OnTimer` + `lastBarTime[]` pattern. On each timer tick, for each symbol and each active timeframe (D1, H1, M15), check if a new bar has formed; if so, pack OHLCV + timeframe tag into a `uchar` array and send via the ZMQ PUB socket.

**MQL5 serialization approach:** mql-zmq `Socket.send(const uchar &buf[])` sends raw bytes. The bar-close payload must be manually packed as msgpack bytes in MQL5. Two options:
- **Option A (recommended):** Build a simple JSON string and send as UTF-8 bytes — avoids needing a msgpack encoder in MQL5. Python consumer parses JSON instead of msgpack for bar-close events on the bar socket.
- **Option B:** Encode msgpack manually in MQL5 (feasible but error-prone). Prefer Option A for simplicity of spike.

**Concrete MQL5 bar-close send pattern:**
```mql5
// In OnTimer(), for each symbol+timeframe:
int barsTotal = Bars(sym, tf);
if(barsTotal != lastBarsTotal[i][j]) {
    lastBarsTotal[i][j] = barsTotal;
    // bar just closed — send bar-close event
    MqlRates rates[];
    if(CopyRates(sym, tf, 1, 1, rates) == 1) {
        string payload = StringFormat(
            "{\"ts\":%I64d,\"sym\":\"%s\",\"tf\":\"%s\","
            "\"o\":%.5f,\"h\":%.5f,\"l\":%.5f,\"c\":%.5f,"
            "\"v\":%d,\"sp\":%d}",
            rates[0].time * 1000000000LL,  // seconds -> nanoseconds
            sym, tf_str,
            rates[0].open, rates[0].high, rates[0].low, rates[0].close,
            rates[0].tick_volume, rates[0].spread
        );
        uchar msgBytes[];
        StringToCharArray(payload, msgBytes, 0, StringLen(payload));
        // Send as multipart: [symbol_topic, payload]
        string topicStr = sym;
        uchar topicBytes[];
        StringToCharArray(topicStr, topicBytes, 0, StringLen(topicStr));
        barSocket.sendMore(topicBytes);
        barSocket.send(msgBytes);
    }
}
```

**Source:** CONTEXT.md D-13/D-14/D-15, mql-zmq Socket.mqh API

### Anti-Patterns to Avoid

- **Ad-hoc dict construction in bridge code:** All message construction goes through `schemas.py`. Never build `{"ts": ..., "sym": ...}` inline outside the schema module.
- **Hardcoding `10.200.0.1` in Python code:** Always read from `os.getenv("BRIDGE_HOST", "10.200.0.1")` — D-02 requires Windows/Ubuntu portability.
- **Polling MT5 on bar close:** Python must NOT poll MT5 — it subscribes to the ZMQ PUB socket and reacts to bar-close events pushed from the EA (BRDG-04).
- **Skipping the staleness check:** Signal engine (Phase 10) must call `consumer.is_stale` before generating signals. A stale bridge must gate all signal generation.
- **Blocking asyncio with synchronous zmq calls:** Always use `zmq.asyncio.Context()`, never `zmq.Context()` in async code.
- **Forgetting the heartbeat on reconnect:** After reconnect, `_last_heartbeat` must NOT be reset to `time.monotonic()` — it should remain stale until a real heartbeat arrives from the publisher.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Binary serialization | Custom byte packing | msgpack (already installed) | msgpack handles nil, int64, float64, str natively; hand-rolled packing will miss edge cases |
| ZMQ topic filtering | Manual symbol prefix parse | `socket.setsockopt(zmq.SUBSCRIBE, symbol.encode())` | ZMQ handles prefix matching in C; Python-side filtering adds latency and bugs |
| Reconnect backoff | Custom sleep loop | V1 `RECONNECT_DELAYS` list (copy verbatim) | Already tested, capped at 30s, proven pattern |
| Async ZMQ integration | Thread-based ZMQ in asyncio | `zmq.asyncio.Poller` with `await poller.poll()` | Mixing sync ZMQ with asyncio without the asyncio context causes event loop blocking |
| MQL5 msgpack encoding | Hand-rolled msgpack in MQL5 | JSON string via `StringFormat` + `StringToCharArray` | MQL5 has no native msgpack; JSON is safe and Python can decode either format |

**Key insight:** The V1 bridge already solved all reconnect and message framing problems. The only new code is the schema deltas (Fill, schema_version, timeframe field) and env-driven configuration.

---

## Common Pitfalls

### Pitfall 1: MT5 "Allow DLL imports" is a Two-Layer Setting
**What goes wrong:** DLL loads on developer terminal but fails on IC Markets terminal because broker restricts DLL imports at the broker-profile level.
**Why it happens:** MT5 has both a terminal-level setting (Tools > Options > Expert Advisors > Allow DLL imports) AND a broker-level restriction that can override the terminal setting. IC Markets may have DLL restrictions on certain account types.
**How to avoid:** BRDG-03 spike must be run on the actual IC Markets MT5 terminal (not a local terminal). If DLL fails to load even with terminal setting ON, the approach requires a different IPC mechanism.
**Warning signs:** Error code 998 (access violation) or error 126 (missing Visual C++ runtime) in MT5 journal when EA initializes.

### Pitfall 2: libzmq.dll Version Mismatch with libsodium.dll
**What goes wrong:** `Cannot load libzmq.dll` error even when DLL is in the correct directory.
**Why it happens:** libzmq.dll and libsodium.dll must be compiled together — mixing versions from different sources causes load failures.
**How to avoid:** Always take both DLLs from the same mql-zmq release. Do not substitute a newer libzmq.dll without the matching libsodium.dll.
**Warning signs:** MT5 journal shows error 126 (DLL dependency not found) or error 998 at DLL load time.

### Pitfall 3: MQL5 Compilation Failure on Modern Build
**What goes wrong:** `#include <Zmq/Zmq.mqh>` compiles but socket operations fail because MQL5 type system rejects `char[]` vs `uchar[]` implicit conversion.
**Why it happens:** dingmaotu/mql-zmq was written for older MQL5 — newer builds enforce strict array type separation.
**How to avoid:** Use coke5151/mql5-zmq fork as first choice if dingmaotu fails compilation. This fork specifically fixes the char/uchar type errors.
**Warning signs:** Compiler errors mentioning `char[]` to `uchar[]` conversion in ZMQ include files.

### Pitfall 4: RATES_TOTAL vs iTime for Bar-Close Detection
**What goes wrong:** Bar-close detection fires spuriously or misses bars when using `iTime(sym, tf, 0)` comparison.
**Why it happens:** `iTime(sym, tf, 0)` returns the current (open) bar's time, which changes on bar open. For multi-pair/multi-timeframe EAs called from `OnTimer(1s)`, comparing against `lastBarTime[i]` via iTime works but RATES_TOTAL comparison (comparing bar count) is equally reliable and is what the CONTEXT.md specifies.
**How to avoid:** Use `Bars(sym, tf)` count comparison (RATES_TOTAL equivalent) as specified in D-13. When count increases, the previous bar closed. Read the completed bar at index 1, not 0.
**Warning signs:** Duplicate bar-close events or missed bars at session boundaries.

### Pitfall 5: Heartbeat Discrimination Frame Count
**What goes wrong:** Heartbeat bytes are passed to `unpack_tick()` causing a decode error or silent data corruption.
**Why it happens:** Both heartbeats and ticks arrive on the tick PUB socket. Heartbeats are single-frame; ticks are two-frame `[topic, payload]`. If the frame count check is missing, the code crashes or misroutes.
**How to avoid:** Always check `len(frames)` before deciding message type. V1 implementation does this correctly — copy verbatim.
**Warning signs:** `msgpack.UnpackValueError` in the receive loop, or `is_stale` never becoming False even when publisher is running.

### Pitfall 6: Schema Version Mismatch Silent Failure
**What goes wrong:** A Python consumer connects to a publisher running a different schema version; messages decode without error but fields have wrong semantics.
**Why it happens:** V1 heartbeats have no `schema_version` field. If V1 publisher somehow connects to V2 consumer, `d.get("schema_version")` returns `None`.
**How to avoid:** Consumer must log a WARNING (not raise) when `schema_version` is None or != SCHEMA_VERSION. The D-07 decision is log-only, not rejection — but the log must be visible.

---

## Code Examples

Verified patterns from V1 source and mql-zmq API:

### V2 Schema Module Structure (BRDG-01)
```python
# V2/bridge/schemas.py
# Source: V1/helix/src/execution/bridge/message_schemas.py + CONTEXT.md D-06/D-07/D-08

from __future__ import annotations
import time
from typing import Any
import msgpack
import numpy as np
from .types import Bar, Fill, OrderRequest, Tick

SCHEMA_VERSION: int = 1

def _dt64_to_ns(dt: np.datetime64) -> int:
    return int(dt.astype("datetime64[ns]").astype(np.int64))

def _ns_to_dt64(ns: int) -> np.datetime64:
    return np.datetime64(ns, "ns")

def pack_heartbeat() -> bytes:
    return msgpack.packb({"type": "heartbeat", "ts": int(time.time_ns()), "schema_version": SCHEMA_VERSION})

def unpack_heartbeat(data: bytes) -> dict[str, Any]:
    return msgpack.unpackb(data)

# pack_tick, unpack_tick, pack_bar, unpack_bar, pack_order_request, unpack_order_request
# — identical to V1 except pack_bar gains optional 'tf' field
# pack_fill / unpack_fill — renamed from pack_order_result / unpack_order_result
```

### V2 Consumer Constructor (env-configurable, BRDG-02)
```python
# V2/bridge/consumer.py
import os
import zmq
import zmq.asyncio

class BridgeConsumer:
    RECONNECT_DELAYS: list[float] = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
    STALE_THRESHOLD: float = 10.0

    def __init__(self) -> None:
        self._host = os.getenv("BRIDGE_HOST", "10.200.0.1")
        self._tick_port = int(os.getenv("ZMQ_TICK_PORT", "5556"))
        self._bar_port  = int(os.getenv("ZMQ_BAR_PORT",  "5557"))
        self._order_port = int(os.getenv("ZMQ_ORDER_PORT", "5558"))
        self._fill_port  = int(os.getenv("ZMQ_FILL_PORT",  "5559"))
        # ... rest same as V1 LinuxConsumer
```

### BRDG-03 Spike Script Structure
```python
# V2/bridge/spike/brdg03_spike.py
"""BRDG-03 DLL compatibility spike.
Run on the IC Markets MT5 terminal Windows machine ONLY.
Pass: DLL loads, one test message sends, no crash.
Fail: Any exception or MT5 journal DLL error.
"""
# This is a documentation placeholder — the actual spike is an MQL5 Script,
# not a Python script. The MQL5 Script:
# 1. #include <Zmq/Zmq.mqh>
# 2. Creates Context, creates PUB socket
# 3. Binds to tcp://127.0.0.1:5599 (test port, not production)
# 4. Sends one uchar[] message: "BRDG03_SPIKE_OK"
# 5. Prints "SPIKE PASS" to MT5 journal
# 6. Python listener on test port confirms receipt
```

### MQL5 ZMQ Initialization in EA
```mql5
// At top of MultiPairEA.mq5
#include <Zmq/Zmq.mqh>

// Global declarations
Context zmqContext;
Socket  barPubSocket(zmqContext, ZMQ_PUB);  // PUB for bar-close events

// In OnInit():
string bindAddr = StringFormat("tcp://*:%d", InpBarPort);
barPubSocket.bind(bindAddr);

// In OnDeinit():
barPubSocket.unbind(bindAddr);
zmqContext.destroy(0);
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| V1 `OrderResult` type name | V2 `Fill` type name | Phase 6 (now) | Breaking change — V1 and V2 schemas are incompatible by design (D-08) |
| V1 heartbeat: `{"type": "heartbeat", "ts": ns}` | V2 heartbeat: adds `"schema_version": 1` | Phase 6 (now) | Backward-compatible if consumer uses `.get()` |
| V1 Bar: no timeframe field | V2 Bar: optional `"tf"` field added | Phase 6 (now) | V2 bar-close events carry timeframe; V1 bar messages do not |
| Port constants in class body | Env-variable-driven ports with class defaults | Phase 6 (now) | Enables cross-platform deployment without code changes |

**Deprecated/outdated:**
- `V1/helix/src/execution/bridge/`: Do NOT modify V1 bridge files — V2 lives in `V2/bridge/` (D-01). V1 is read-only reference.
- `OrderResult` type name: Replaced by `Fill` in V2. Any V2 code importing `OrderResult` is wrong.

---

## Open Questions

1. **IC Markets DLL restriction policy**
   - What we know: MT5 terminal "Allow DLL imports" setting exists and works on standard terminals
   - What's unclear: Whether IC Markets broker profile restricts DLL loading independently of the terminal setting
   - Recommendation: BRDG-03 spike is the only resolution. If DLL fails, fallback options are: (a) named pipe IPC (Windows-only, breaks D-02), (b) file-based IPC (polling, breaks performance target), (c) MT5 Python API via MetaTrader5 pip package (Windows-only, but avoids DLL). Document spike outcome in STATE.md.

2. **MQL5 JSON vs msgpack for bar-close payload**
   - What we know: MQL5 has no native msgpack encoder; JSON is straightforward via `StringFormat`
   - What's unclear: Whether the Python consumer should expect JSON or msgpack on the bar socket (mixing formats adds complexity)
   - Recommendation: Use JSON string encoding for MQL5-originated bar-close events. Python consumer uses `json.loads()` on bar socket frames instead of `msgpack.unpackb()`. Document this asymmetry in `V2/bridge/schemas.py` header comment.

3. **V2 pyproject.toml / pytest config**
   - What we know: V2/tests/unit_tests/ directory exists but is empty; no pyproject.toml found outside vectorbtpro
   - What's unclear: Whether V2 has its own pytest config or shares V1's
   - Recommendation: Wave 0 must create `V2/pyproject.toml` with pytest config pointing at `V2/tests/` and `V2/bridge/` as source. Mirror V1's `pyproject.toml` `[tool.pytest.ini_options]` block.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (from V1 pyproject.toml) |
| Config file | `V2/pyproject.toml` — does not yet exist (Wave 0 gap) |
| Quick run command | `cd V2 && pytest tests/unit_tests/bridge/ -x -q` |
| Full suite command | `cd V2 && pytest tests/unit_tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BRDG-01 | All 5 types round-trip through pack/unpack without data loss | unit | `pytest V2/tests/unit_tests/bridge/test_schemas.py -x` | Wave 0 |
| BRDG-01 | Heartbeat includes `schema_version=1` field | unit | `pytest V2/tests/unit_tests/bridge/test_schemas.py::test_heartbeat_schema_version -x` | Wave 0 |
| BRDG-01 | Fill (not OrderResult) round-trips correctly | unit | `pytest V2/tests/unit_tests/bridge/test_schemas.py::TestFillRoundTrip -x` | Wave 0 |
| BRDG-02 | `is_stale` returns True initially and after 10s without heartbeat | unit | `pytest V2/tests/unit_tests/bridge/test_consumer.py::TestStaleDetection -x` | Wave 0 |
| BRDG-02 | Reconnect delays follow [1,2,4,8,16,30] schedule and cap at 30s | unit | `pytest V2/tests/unit_tests/bridge/test_consumer.py::TestReconnectBackoff -x` | Wave 0 |
| BRDG-02 | Heartbeat loop fires at configured interval | unit | `pytest V2/tests/unit_tests/bridge/test_publisher.py::TestHeartbeatLoop -x` | Wave 0 |
| BRDG-02 | Consumer auto-reconnects on heartbeat timeout | unit | `pytest V2/tests/unit_tests/bridge/test_consumer.py::TestAutoReconnect -x` | Wave 0 |
| BRDG-03 | DLL loads and sends one message on IC Markets MT5 | manual/spike | Run `V2/ea/spike/brdg03_spike.mq5` on IC Markets terminal | Wave 0 (MQL5 script) |
| BRDG-04 | Bar-close events received with correct symbol+timeframe+OHLCV | unit | `pytest V2/tests/unit_tests/bridge/test_consumer.py::TestBarCloseReceive -x` | Wave 0 |
| BRDG-04 | All three timeframes (D1, H1, M15) are tagged correctly | unit | `pytest V2/tests/unit_tests/bridge/test_schemas.py::TestBarTimeframeTag -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix && pytest V2/tests/unit_tests/bridge/ -x -q`
- **Per wave merge:** `cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix && pytest V2/tests/unit_tests/ -v`
- **Phase gate:** Full suite green + BRDG-03 spike PASS before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `V2/pyproject.toml` — pytest config for V2 package
- [ ] `V2/tests/unit_tests/bridge/__init__.py` — package marker
- [ ] `V2/tests/unit_tests/bridge/test_schemas.py` — covers BRDG-01
- [ ] `V2/tests/unit_tests/bridge/test_consumer.py` — covers BRDG-02 + BRDG-04 consumer side
- [ ] `V2/tests/unit_tests/bridge/test_publisher.py` — covers BRDG-02 publisher side
- [ ] `V2/ea/spike/brdg03_spike.mq5` — MQL5 script for BRDG-03 go/no-go gate
- [ ] `V2/bridge/__init__.py`, `V2/bridge/types.py` — package scaffolding

---

## Sources

### Primary (HIGH confidence)
- `V1/helix/src/execution/bridge/message_schemas.py` — exact V1 schema; V2 diffs documented above
- `V1/helix/src/execution/bridge/linux_consumer.py` — exact V1 consumer; V2 adds env config
- `V1/helix/src/execution/bridge/windows_publisher.py` — exact V1 publisher; V2 adds env config
- `V1/helix/tests/execution/bridge/test_bridge.py` — test patterns to mirror in V2
- `V1/helix/src/execution/abstract.py` — V1 type definitions; V2 redefines in `bridge/types.py`
- `V2/ea/MultiPairEA.mq5` — existing EA skeleton; bar-close hook wired into `OnTimer`/`lastBarTime[]`
- `pip show pyzmq msgpack` — verified 27.1.0 and 1.1.2 installed (2026-04-23)

### Secondary (MEDIUM confidence)
- [dingmaotu/mql-zmq GitHub](https://github.com/dingmaotu/mql-zmq) — DLL installation procedure, Socket API (`sendMore`, `send(uchar[])`)
- [coke5151/mql5-zmq GitHub](https://github.com/coke5151/mql5-zmq) — char/uchar type fix for modern MQL5; same DLL files
- [MT5 Help: Platform Settings](https://www.metatrader5.com/en/terminal/help/startworking/settings) — "Allow DLL imports" location confirmed at Tools > Options > Expert Advisors

### Tertiary (LOW confidence — flag for BRDG-03 spike validation)
- [mql-zmq Issue #49](https://github.com/dingmaotu/mql-zmq/issues/49) — error 998 after MT5 build 2450 update (WINE env); risk flagged but unresolved upstream
- WebSearch: IC Markets broker-level DLL restriction — no official documentation found; assume standard MT5 terminal settings apply until spike result

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pyzmq 27.1.0 and msgpack 1.1.2 verified from live venv
- Architecture: HIGH — V1 source is fully readable and directly portable; schema deltas are small and explicit
- MQL5 DLL (BRDG-03): MEDIUM — dingmaotu/mql-zmq is the de-facto standard, but IC Markets broker-level DLL policy is unknown until spike runs
- Pitfalls: HIGH — error 998, char/uchar issue, and staleness discriminator are all confirmed from GitHub issues and V1 code review

**Research date:** 2026-04-23
**Valid until:** 2026-07-23 (stable stack; mql-zmq DLL versions have been unchanged for years)

---
phase: 06-zmq-bridge-port
plan: "04"
subsystem: bridge+ea
tags: [zmq, bar-close, tdd, brdg-04, mql5, consumer, msgpack, json-fallback]
dependency_graph:
  requires: [V2/bridge/schemas.py, V2/bridge/consumer.py, V2/ea/MultiPairEA.mq5, BRDG-03-PASS]
  provides: [V2/bridge/consumer.py, V2/ea/MultiPairEA.mq5, V2/tests/unit_tests/bridge/test_bar_close.py, V2/tests/unit_tests/bridge/test_consumer.py]
  affects: [Phase 10 LiveSignalEngine bar-close subscription]
tech_stack:
  added: []
  patterns: [tdd-red-green, zmq-pub-uchar-multipart, json-msgpack-dual-decoder, fail-open-zmq-bind, bars-count-change-detection]
key_files:
  created:
    - V2/tests/unit_tests/bridge/test_bar_close.py
  modified:
    - V2/bridge/consumer.py
    - V2/tests/unit_tests/bridge/test_consumer.py
    - V2/ea/MultiPairEA.mq5
decisions:
  - "zmqContext.destroy(0) omitted from OnDeinit — coke5151 RAII handles cleanup on scope exit (confirmed from brdg03_spike.mq5 pattern)"
  - "_handle_bar_frame tries msgpack first (V2 native), falls back to JSON (MQL5 Option A) — dual-decoder pattern makes consumer resilient to both payload formats"
  - "JSON fallback path uses np.datetime64(int(obj['ts']), 'ns') to convert integer nanoseconds from MQL5 %I64d format"
  - "lastBarsCount initialised in OnInit bind block to avoid 15 spurious bar-close events on first OnTimer tick"
  - "Fail-open bind: zmqBarsActive stays false if barPub.bind() fails — EA trades normally without ZMQ"
metrics:
  duration_seconds: 230
  completed_date: "2026-04-24"
  tasks_completed: 3
  files_created: 1
  files_modified: 3
---

# Phase 06 Plan 04: MT5 EA Bar-Close Publisher + Consumer Bar Routing (BRDG-04) Summary

**One-liner:** MultiPairEA.mq5 extended with ZMQ PUB bar-close publisher emitting D1/H1/M15 JSON frames for 5 pairs; BridgeConsumer extended with `_handle_bar_frame` accepting msgpack or JSON and dispatching `on_bar_close(Bar, tf)` — BRDG-04 Python side complete, EA side awaiting MetaEditor compile verification (Task 4).

---

## What Was Built

### Task 0: Gate check — BRDG-03 PASS confirmed
`V2/bridge/spike/BRDG03-RESULT.md` — Outcome: PASS. coke5151/mql5-zmq, MT5 Build 5800, Ubuntu+Wine 11.7. Plan 04 cleared to proceed with all three tasks.

### Task 1: Bar-close consumer tests (RED)
`V2/tests/unit_tests/bridge/test_bar_close.py` — 9 tests across 4 classes:
- `TestHandleBarFrameMsgpack` (4 tests): D1, H1, M15 tag round-trip + no-tf fallback
- `TestHandleBarFrameJson` (2 tests): JSON D1 frame, JSON without tf field
- `TestMalformedFrames` (1 test): random bytes raise Exception
- `TestReceiveLoopDispatch` (2 tests): `_receive_loop` dispatches `(bar, tf)` to callback, both args verified

RED confirmed: `AttributeError: 'BridgeConsumer' object has no attribute '_handle_bar_frame'`

### Task 2: BridgeConsumer extension (GREEN)
`V2/bridge/consumer.py` — 293 lines (was 251):
- `import json` and `import numpy as np` added at top
- `unpack_bar_with_timeframe` added to imports from `.schemas`
- `_handle_bar_frame(data: bytes) -> tuple[Bar, str]`: tries `unpack_bar_with_timeframe(data)` first (msgpack); on any exception, falls back to `json.loads(data.decode("utf-8"))` using the `{"ts","sym","o","h","l","c","v","sp","tf"}` JSON schema that MQL5 EA emits
- `_receive_loop` signature updated: `on_bar` renamed to `on_bar_close` with type `Callable[[Bar, str], Awaitable[None]]`; bar decode errors now caught and logged as WARNING without killing the loop
- `test_consumer.py` `TestBarCloseReceive`: `pytest.skip` placeholder replaced with live `test_receive_loop_passes_timeframe_to_callback` test

Full bridge suite: **53 passed** (9 bar_close + 19 consumer + 10 publisher + 15 schemas)

### Task 3: MultiPairEA.mq5 extension
`V2/ea/MultiPairEA.mq5` — 375 lines (was 291, +84 ZMQ additions):

**Includes added:**
```mql5
#include <Zmq/Zmq.mqh>
```

**Inputs added (BRDG-04):**
```mql5
input int    InpBarPort       = 5557;
input string InpBarBindAddr   = "tcp://*";
input bool   InpEnableZmqBars = true;
```

**Globals added (BRDG-04):**
```mql5
Context        zmqContext;
Socket         barPub(zmqContext, ZMQ_PUB);
bool           zmqBarsActive = false;
ENUM_TIMEFRAMES activeTimeframes[3] = {PERIOD_D1, PERIOD_H1, PERIOD_M15};
string         timeframeTags[3]    = {"D1", "H1", "M15"};
int            lastBarsCount[5][3];
```

**OnInit Step 7 (fail-open):**
- Binds `barPub` to `tcp://*:5557`; on success sets `zmqBarsActive=true` and seeds `lastBarsCount[5][3]` with current Bars() counts
- On bind failure: logs `[BRIDGE] WARNING: Bar-close PUB bind failed` and leaves `zmqBarsActive=false` — EA continues trading normally

**OnDeinit (RAII-safe):**
- If `zmqBarsActive`: calls `barPub.unbind()`, clears flag, logs `[BRIDGE] Bar-close PUB unbound`
- No `zmqContext.destroy(0)` call — coke5151 RAII destructor handles context cleanup on scope exit

**OnTimer BRDG-04 block (at end, after all existing steps):**
- Iterates 5 pairs × 3 timeframes = 15 streams per 1s tick
- Bar detection: `Bars(sym, tf) > lastBarsCount[p][t]` (count-change pattern, D-13)
- On new bar: `CopyRates(sym, tf, 1, 1, rates)` reads index 1 (just-closed bar)
- JSON payload: `StringFormat("{\"ts\":%I64d,...}", (long)rates[0].time * 1000000000, ...)` — timestamps as nanoseconds
- ZMQ send: `StringToCharArray → topicBytes/payloadBytes → barPub.sendMore(topicBytes) → barPub.send(payloadBytes)` (uchar[] pattern from brdg03_spike.mq5)
- Log: `[BRIDGE] Bar close: EURUSD D1 @ <timestamp>` on every emission
- All existing risk/signal/scaling logic untouched

### Task 4: Human verification — CHECKPOINT (not yet executed)
Awaiting user to compile `V2/ea/MultiPairEA.mq5` in MetaEditor (F7), attach to MT5 chart, and confirm bar-close events appear in both MT5 Experts tab and Python listener. See checkpoint details below.

---

## BRDG-04 Satisfaction Status

| Component | Status | Verified by |
|-----------|--------|-------------|
| Python: `_handle_bar_frame` accepts msgpack | PASS | test_handle_bar_frame_msgpack_d1/h1/m15 |
| Python: `_handle_bar_frame` falls back to JSON | PASS | test_handle_bar_frame_json_d1 |
| Python: `_receive_loop` dispatches `on_bar_close(bar, tf)` | PASS | test_receive_loop_dispatches_bar_with_timeframe |
| Python: malformed frames don't kill loop | PASS | test_malformed_bytes_raises_or_returns_none + WARNING catch |
| EA: publishes D1/H1/M15 per 5 pairs on Bars() count change | CODE READY | Task 4 human compile+live verify |
| EA: JSON payload includes tf tag | CODE READY | grep confirmed in file |
| EA: fail-open on bind failure | CODE READY | zmqBarsActive gate pattern |
| EA: existing logic untouched | CODE READY | grep CCircuitBreaker/CScalingManager/lastBarTime all present |
| MetaEditor compile 0 errors | PENDING | Task 4 |
| Live bar-close event received by Python | PENDING | Task 4 |

---

## Phase 6 Gate Status

| Requirement | Status | Plan |
|-------------|--------|------|
| BRDG-01: msgpack schema contract | PASS | 06-01 |
| BRDG-02: heartbeat + auto-reconnect | PASS | 06-03 |
| BRDG-03: DLL compatibility spike | PASS | 06-02 |
| BRDG-04: bar-close publisher + consumer routing | PYTHON PASS / EA PENDING COMPILE | 06-04 |

**Phase 6 is functionally complete on the Python side.** BRDG-04 EA-side verification (Task 4) is the final gate before `/gsd:verify-work 6`.

---

## Test Results

```
53 passed in 0.34s
```

- Schemas (from Plan 01): 15 PASSED
- Consumer (from Plan 03 + Plan 04): 19 PASSED
- Publisher (from Plan 03): 10 PASSED
- Bar-close (Plan 04 new): 9 PASSED
- Total: **53 PASSED, 0 SKIPPED** (the 1 skip from Plan 03 is now a live test)

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Constraint Compliance] Omitted zmqContext.destroy(0) from OnDeinit**
- **Found during:** Task 3, implementing OnDeinit block
- **Issue:** Plan template included `zmqContext.destroy(0)` but prompt explicitly stated this must be omitted for coke5151 RAII safety
- **Fix:** OnDeinit only calls `barPub.unbind()` — context cleanup handled by destructor on scope exit
- **Files modified:** `V2/ea/MultiPairEA.mq5`
- **Commit:** 013e3a6

No other deviations — plan executed as written for all other items.

---

## Known Stubs

None — all implemented methods are fully wired. No hardcoded empty values, placeholder returns, or TODO comments in the implementation files. The EA bar-close emission is real production code awaiting compile verification, not a stub.

---

## Task 4 Checkpoint Details

**What was built:** Tasks 1-3 complete. `_handle_bar_frame` + `on_bar_close` routing in consumer, ZMQ PUB bar-close publisher in EA across D1/H1/M15 for all 5 pairs.

**Human steps required:**
1. Open `V2/ea/MultiPairEA.mq5` in MetaEditor → press F7 → confirm 0 errors
2. Start Python listener: `cd V2 && python3 -c "import asyncio, os; os.environ.setdefault('BRIDGE_HOST','127.0.0.1'); from bridge.consumer import BridgeConsumer; ..."`
3. Attach EA to any MT5 chart; confirm `InpEnableZmqBars=true, InpBarPort=5557`
4. Wait up to 15 minutes for M15 bar close
5. Confirm `[BRIDGE] Bar close:` appears in MT5 Experts tab and Python listener receives it

**Next step on PASS:** `/gsd:verify-work 6` to run phase gate.

---

## Self-Check: PASSED

Files verified:
- `V2/tests/unit_tests/bridge/test_bar_close.py` — FOUND (142 lines, 9 tests)
- `V2/bridge/consumer.py` — FOUND (293 lines)
- `V2/tests/unit_tests/bridge/test_consumer.py` — FOUND (pytest.skip=0)
- `V2/ea/MultiPairEA.mq5` — FOUND (375 lines)

Commits verified:
- `2dfc961` — test(06-04): add failing bar-close consumer tests RED
- `9eccc36` — feat(06-04): extend BridgeConsumer with _handle_bar_frame + on_bar_close dispatch GREEN
- `013e3a6` — feat(06-04): extend MultiPairEA.mq5 with ZMQ PUB bar-close publisher

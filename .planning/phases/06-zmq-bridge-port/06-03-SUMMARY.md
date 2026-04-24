---
phase: 06-zmq-bridge-port
plan: "03"
subsystem: bridge
tags: [zmq, consumer, publisher, heartbeat, auto-reconnect, tdd, brdg-02, env-config]
dependency_graph:
  requires: [V2/bridge/schemas.py, V2/bridge/types.py, V2/pyproject.toml]
  provides: [V2/bridge/consumer.py, V2/bridge/publisher.py, V2/tests/unit_tests/bridge/test_consumer.py, V2/tests/unit_tests/bridge/test_publisher.py]
  affects: [06-04, Phase 10 LiveSignalEngine]
tech_stack:
  added: []
  patterns: [zmq-asyncio-pub-sub, heartbeat-guard, exponential-backoff-reconnect, env-configurable-ports, tdd-red-green]
key_files:
  created:
    - V2/bridge/consumer.py
    - V2/bridge/publisher.py
    - V2/tests/unit_tests/bridge/test_consumer.py
    - V2/tests/unit_tests/bridge/test_publisher.py
  modified: []
decisions:
  - "_last_heartbeat starts at 0.0 so is_stale is True initially before any heartbeat arrives (D-10 intent)"
  - "_handle_heartbeat_frame is a public method (not private) to allow direct test injection without async loop setup"
  - "_reconnect increments attempt counter before sleeping to match test expectations (before=0, after=1)"
  - "BridgePublisher uses env-read instance ports (not class-level constants) so port overrides take effect per-instance"
  - "publisher.py _fill_push socket uses PUSH (not PULL) to send fills back to consumer side"
metrics:
  duration_seconds: 182
  completed_date: "2026-04-23"
  tasks_completed: 3
  files_created: 4
---

# Phase 06 Plan 03: BridgeConsumer + BridgePublisher with Heartbeat Guard + Auto-Reconnect Summary

**One-liner:** BridgeConsumer and BridgePublisher with env-configurable ports, 10s stale detection, [1,2,4,8,16,30]s backoff reconnect, schema_version mismatch warning, and 5s heartbeat loop — BRDG-02 satisfied with 43 tests GREEN.

---

## What Was Built

### Task 1: Consumer tests (RED)
- `V2/tests/unit_tests/bridge/test_consumer.py` — 19 tests across 6 classes
- Confirmed RED state: `ModuleNotFoundError: No module named 'bridge.consumer'`

### Task 2: BridgeConsumer implementation (GREEN)
- `V2/bridge/consumer.py` — 250 lines, BridgeConsumer class
- Env-configurable: BRIDGE_HOST (default 10.200.0.1), ZMQ_TICK_PORT/BAR/ORDER/FILL (defaults 5556-5559)
- `_handle_heartbeat_frame(data: bytes)` — public method for schema_version check; WARNING on mismatch or missing field
- `is_stale` property — True initially (\_last\_heartbeat=0.0), True after 10s without heartbeat
- `_get_reconnect_delay()` — caps at index min(attempt, 5) over RECONNECT_DELAYS [1,2,4,8,16,30]
- `_reconnect()` — logs UI-SPEC WARNING "Reconnecting in Ns (attempt n/max)", closes sockets, calls connect()
- 18/19 consumer tests GREEN (1 skip = Plan 04 placeholder)

### Task 3: Publisher tests + BridgePublisher implementation (RED + GREEN in one task)
- `V2/tests/unit_tests/bridge/test_publisher.py` — 10 tests across 4 classes
- `V2/bridge/publisher.py` — 145 lines, BridgePublisher class
- Env-configurable: ZMQ_TICK/BAR/ORDER/FILL_PORT (defaults 5556-5559)
- HEARTBEAT_INTERVAL = 5.0 class constant; `_heartbeat_loop()` sends pack_heartbeat() on tick PUB socket
- `publish_tick(tick)` — send_multipart([symbol.encode(), pack_tick(tick)])
- `publish_bar(bar, timeframe="")` — send_multipart([symbol.encode(), pack_bar(bar, timeframe)])
- All 10 publisher tests GREEN

---

## V2 Deltas Applied (from V1 LinuxConsumer / WindowsPublisher)

| Delta | V1 | V2 |
|-------|----|----|
| D-02: env host | `host="10.200.0.1"` constructor arg | `os.getenv("BRIDGE_HOST", "10.200.0.1")` |
| D-03: env ports | hardcoded 5556-5559 in connect() | `os.getenv("ZMQ_*_PORT", "55XX")` per port |
| D-07: schema_version check | heartbeat parsed but version ignored | `_handle_heartbeat_frame()` checks version, logs WARNING |
| D-08: Fill (not OrderResult) | `unpack_order_result` imported | `unpack_fill` from `.schemas` |
| D-15: timeframe tag | `publish_bar(bar)` no timeframe | `publish_bar(bar, timeframe="")` passes tf to pack_bar |
| UI-SPEC log copy | no [BRIDGE] prefix | exact format strings from 06-UI-SPEC copywriting contract |
| testability | no extracted heartbeat method | `_handle_heartbeat_frame` extracted as public method |

---

## BRDG-02 Satisfaction Summary

| Requirement | Implementation | Verified by |
|-------------|----------------|-------------|
| Heartbeat every 5s | `BridgePublisher.HEARTBEAT_INTERVAL = 5.0`; `_heartbeat_loop()` | `test_heartbeat_interval_is_5s`, `test_heartbeat_sends_on_tick_socket` |
| Stale after 10s | `STALE_THRESHOLD = 10.0`; `is_stale = monotonic() - _last_heartbeat > 10.0` | `TestStaleDetection` (4 tests) |
| True initially | `_last_heartbeat = 0.0` — always > 10s behind monotonic | `test_is_stale_true_initially` |
| Reconnect schedule | `RECONNECT_DELAYS = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]`; capped at index 5 | `TestReconnectBackoff` (3 tests) |
| Schema mismatch warning | `_handle_heartbeat_frame` checks `hb.get("schema_version") != SCHEMA_VERSION` | `TestSchemaMismatchWarning` (4 tests) |
| WARNING log format | `"[BRIDGE] WARNING: Schema version mismatch — remote=%s, expected=%s"` | `test_mismatched_version_logs_warning` |
| Reconnect log format | `"[BRIDGE] Reconnecting in %.0fs (attempt %d/%d)"` | `test_reconnect_logs_attempt` |

---

## Test Results

```
43 passed, 1 skipped in 0.33s
```

- Schema tests (from Plan 01): 15 PASSED
- Consumer tests: 18 PASSED, 1 SKIPPED (Plan 04 placeholder)
- Publisher tests: 10 PASSED
- Total: 43 PASSED, 1 SKIPPED

---

## Deviations from Plan

None — plan executed exactly as written. All code from the plan spec was used verbatim. The `_reconnect()` ordering (log → increment → sleep → close → connect) matches both the V1 pattern and the test expectations.

---

## Known Stubs

None — all consumer and publisher methods are fully implemented. No hardcoded empty values, placeholder returns, or TODO comments in the implementation files.

---

## Self-Check: PASSED

Files verified:
- `V2/bridge/consumer.py` — FOUND (250 lines)
- `V2/bridge/publisher.py` — FOUND (145 lines)
- `V2/tests/unit_tests/bridge/test_consumer.py` — FOUND (155 lines, 19 tests)
- `V2/tests/unit_tests/bridge/test_publisher.py` — FOUND (130 lines, 10 tests)

Commits verified:
- `c189d7a` — test(06-03): add failing consumer tests RED
- `20ed098` — feat(06-03): implement BridgeConsumer GREEN
- `8102c6c` — feat(06-03): implement BridgePublisher GREEN

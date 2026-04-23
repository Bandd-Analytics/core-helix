---
phase: 6
slug: zmq-bridge-port
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `V2/pyproject.toml` — does not yet exist (Wave 0 gap) |
| **Quick run command** | `cd V2 && pytest tests/unit_tests/bridge/ -x -q` |
| **Full suite command** | `cd V2 && pytest tests/unit_tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd V2 && pytest tests/unit_tests/bridge/ -x -q`
- **After every plan wave:** Run `cd V2 && pytest tests/unit_tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green + BRDG-03 spike PASS
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-??-01 | TBD | 0 | BRDG-01 | unit stub | `pytest V2/tests/unit_tests/bridge/test_schemas.py -x` | ❌ W0 | ⬜ pending |
| 6-??-02 | TBD | 0 | BRDG-01 | unit stub | `pytest V2/tests/unit_tests/bridge/test_schemas.py::test_heartbeat_schema_version -x` | ❌ W0 | ⬜ pending |
| 6-??-03 | TBD | 0 | BRDG-01 | unit stub | `pytest V2/tests/unit_tests/bridge/test_schemas.py::TestFillRoundTrip -x` | ❌ W0 | ⬜ pending |
| 6-??-04 | TBD | 0 | BRDG-02 | unit stub | `pytest V2/tests/unit_tests/bridge/test_consumer.py::TestStaleDetection -x` | ❌ W0 | ⬜ pending |
| 6-??-05 | TBD | 0 | BRDG-02 | unit stub | `pytest V2/tests/unit_tests/bridge/test_consumer.py::TestReconnectBackoff -x` | ❌ W0 | ⬜ pending |
| 6-??-06 | TBD | 0 | BRDG-02 | unit stub | `pytest V2/tests/unit_tests/bridge/test_publisher.py::TestHeartbeatLoop -x` | ❌ W0 | ⬜ pending |
| 6-??-07 | TBD | 0 | BRDG-02 | unit stub | `pytest V2/tests/unit_tests/bridge/test_consumer.py::TestAutoReconnect -x` | ❌ W0 | ⬜ pending |
| 6-??-08 | TBD | 0 | BRDG-03 | manual/spike | Run `V2/ea/spike/brdg03_spike.mq5` on IC Markets terminal | ❌ W0 | ⬜ pending |
| 6-??-09 | TBD | 0 | BRDG-04 | unit stub | `pytest V2/tests/unit_tests/bridge/test_consumer.py::TestBarCloseReceive -x` | ❌ W0 | ⬜ pending |
| 6-??-10 | TBD | 0 | BRDG-04 | unit stub | `pytest V2/tests/unit_tests/bridge/test_schemas.py::TestBarTimeframeTag -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `V2/pyproject.toml` — pytest config for V2 package
- [ ] `V2/tests/__init__.py` — package marker
- [ ] `V2/tests/unit_tests/__init__.py` — package marker
- [ ] `V2/tests/unit_tests/bridge/__init__.py` — package marker
- [ ] `V2/tests/unit_tests/bridge/test_schemas.py` — stubs covering BRDG-01 (all 5 types, heartbeat version, Fill rename, Bar timeframe tag)
- [ ] `V2/tests/unit_tests/bridge/test_consumer.py` — stubs covering BRDG-02 + BRDG-04 consumer side (stale detection, reconnect backoff, auto-reconnect, bar-close receive)
- [ ] `V2/tests/unit_tests/bridge/test_publisher.py` — stubs covering BRDG-02 publisher side (heartbeat loop)
- [ ] `V2/ea/spike/brdg03_spike.mq5` — MQL5 script for BRDG-03 go/no-go gate
- [ ] `V2/bridge/__init__.py` — package scaffolding
- [ ] `V2/bridge/types.py` — type definitions

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| mql-zmq DLL loads on IC Markets MT5 terminal | BRDG-03 | Broker-level DLL policy unknown; requires real terminal | Enable DLL imports in Tools > Options > Expert Advisors. Compile and run `V2/ea/spike/brdg03_spike.mq5`. Verify "ZMQ test message sent" appears in Experts log without error 998 or crash. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

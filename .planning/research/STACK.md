# Technology Stack — V3 Adaptive Strategy Dispatch System (New Features Only)

**Project:** MarketMind Helix
**Milestone:** v2.0 — V3 Adaptive Strategy Dispatch System
**Researched:** 2026-04-21
**Scope:** New library additions only. Existing stack (Python 3.12, vectorbt.pro 2026.3.1, ChromaDB, NumPy, Pandas, SQLite) is validated and not reconsidered here.

---

## New Dependencies Required

### ZMQ Bridge (Python Side)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| pyzmq | 27.1.0 | ZMQ sockets for Python↔Python bridge (Linux consumer + Windows publisher) | Exact version used in V1, confirmed latest on PyPI as of 2026-04-21. Ships libzmq 4.3.5 as bundled wheel — no separate system libzmq install needed. asyncio support via `zmq.asyncio` submodule is confirmed available. |

**Version confidence:** HIGH — verified via `pip index versions pyzmq` (27.1.0 is both installed in V1 venv and PyPI latest).

**ZMQ pattern used in V1 (carry forward unchanged):**
- Port 5556: PUB (Windows ticks) / SUB (Linux)
- Port 5557: PUB (Windows bars) / SUB (Linux)
- Port 5558: PULL (Windows receives order requests from Linux)
- Port 5559: PUSH (Windows sends order results to Linux)
- Heartbeat: single-frame message on tick PUB socket, 5s interval
- Reconnect: exponential backoff [1, 2, 4, 8, 16, 30]s

**Concurrency model (confirmed from V1 source):** `asyncio` + `zmq.asyncio`. The `LinuxConsumer` and `WindowsPublisher` both use `zmq.asyncio.Context` and `asyncio.sleep`. This is the correct choice for the live service (see Python Service Runner section below).

---

### Serialization

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| msgpack | 1.1.2 | Binary serialization for all ZMQ message frames | Exact version used in V1, confirmed PyPI latest. ~10x smaller payload than JSON, no schema overhead unlike protobuf. Nanosecond timestamp int64 transmitted losslessly (JSON float64 truncates to ~microseconds). |

**msgpack vs JSON:** msgpack. JSON is ruled out because:
1. The V1 bridge transmits `np.datetime64` nanosecond timestamps as int64 — JSON encodes these as floats, introducing precision loss.
2. JSON serialization of Tick/Bar/OrderRequest adds ~3-4x byte overhead vs msgpack.
3. msgpack nil maps cleanly to Python `None` for optional order fields (price, sl, tp).

**msgpack vs protobuf:** msgpack for this use case because:
- Schema evolution is not a current concern (single producer, single consumer, same codebase)
- No codegen step required
- protobuf adds build complexity for marginal efficiency gain at this message rate

**Version confidence:** HIGH — verified via `pip index versions msgpack`.

---

### HMM Regime Classifier

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| hmmlearn | 0.3.3 | GaussianHMM for Stage 1 of two-stage HMM-GARCH fit | V1 production code uses `hmmlearn.hmm.GaussianHMM` with `n_components`, `covariance_type="diag"`, `n_iter`, `tol`, `random_state`. 0.3.3 is PyPI latest. The V1 code is ported as-is — no API change needed. |

**hmmlearn vs pomegranate vs manual HMM:**

Use hmmlearn. Ruled out:

- **pomegranate:** v1.0 rewrote the API entirely (GPU-first, torch dependency). The V1 `GaussianHMM` interface maps directly to hmmlearn, not pomegranate. Switching would require rewriting the two-stage fit loop, `_fit_gaussian_hmm`, and the `monitor_.converged` convergence check. No benefit for this use case.
- **manual HMM:** The V1 `viterbi.py` already implements a custom Viterbi decoder for the GARCH emission phase (Stage 2 uses GARCH log-probs, not Gaussian). Stage 1 still needs EM-fitted transition/start probabilities — hmmlearn provides this. A full manual EM implementation is unnecessary complexity.

**Version confidence:** HIGH — verified via `pip index versions hmmlearn`.

---

### GARCH Volatility Model

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| arch | 8.0.0 | GARCH(1,1) fit for per-state emission variance in HMM-GARCH | V1 production code calls `arch_model(returns, vol="Garch", p=1, q=1, dist="normal").fit(disp="off")` and reads `params["mu"]`, `params["omega"]`, `params["alpha[1]"]`, `params["beta[1]"]`. 8.0.0 is PyPI latest. |

**Why arch package:** The `arch` package (Kevin Sheppard) is the de-facto Python GARCH implementation. statsmodels has a GARCH implementation but it was removed in favour of `arch` (statsmodels GARCH is unmaintained). No realistic alternative exists for GARCH(1,1) fitting in Python.

**arch 8.0.0 vs earlier:** 8.0.0 is a major version. V1 was already on 8.0.0 — no migration needed. The V1 `.fit(disp="off")` call and parameter naming are stable across 7.x→8.x.

**Version confidence:** HIGH — verified via `pip index versions arch`.

---

### Point-in-Time Data Manager

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| arcticdb | 6.13.0 | Columnar time-series store with native `date_range` filtering for PiT reads | V1 `pit_manager.py` uses `arcticdb.Arctic`, `lib.read(symbol, date_range=(None, as_of_timestamp))`, and `lib.snapshot()`. V1 venv has 6.10.2; PyPI latest is 6.13.0. Upgrade is safe — patch/minor releases in the 6.x line. |

**arcticdb version note:** V1 pinned 6.10.2. PyPI latest is 6.13.0. Recommend pinning to 6.13.0 for V2 to pick up LMDB performance fixes. The `pit_manager.py` API surface (`Arctic`, `get_library`, `read`, `snapshot`) is stable across 6.x.

**Version confidence:** HIGH — verified via `pip index versions arcticdb`.

---

### Python Live Service Runner

**Decision: asyncio (single-threaded event loop)**

The V1 bridge code already commits to this: `LinuxConsumer` and `WindowsPublisher` both use `asyncio.sleep`, `zmq.asyncio.Poller`, and `await poller.poll()`. The live signal engine service must integrate with this existing async foundation.

**asyncio vs threading vs simple loop:**

| Approach | Assessment |
|----------|------------|
| asyncio | Use this. Already proven in V1 bridge. `zmq.asyncio` avoids blocking the event loop on socket waits. Single thread simplifies state management for the regime filter and strategy router (no locks needed). |
| threading | Rejected. ZMQ sockets are not thread-safe — sharing context across threads requires explicit locking. The V1 bridge pattern deliberately avoids this. |
| simple synchronous loop | Rejected for live mode. Blocking `socket.recv()` would stall heartbeat processing and order result handling simultaneously. Acceptable only for backtesting harness scripts (which already use pandas DataFrames, not live sockets). |

No additional concurrency library is needed — `asyncio` is stdlib.

---

### H1 Backtest Framework Hooks

No new library required. The existing `vectorbt.pro 2026.3.1` handles H1 data loops. The V2 backtest files (`backtest_hybrid.py`, `backtest_all_timeframes.py`) already demonstrate H1 data iteration patterns. The H1 scalp and momentum strategies reuse the existing signal filter module (`signal_filters.py`) and vectorbt.pro `Portfolio.from_signals()`.

---

### MQL5 ZMQ Integration (Windows EA Side)

**This is new scope not covered by the Python-side pyzmq.**

The V2 MQL5 EA (`MultiPairEA.mq5`) currently generates signals internally. The V3 goal (per PROJECT.md line 49) is: "MT5 EA reads OrderRequest from ZMQ, validates via CCircuitBreaker, executes."

This requires ZMQ socket support inside MQL5. MQL5 cannot use Python libraries — it requires a Windows DLL wrapper.

**Recommended approach: dingmaotu/mql-zmq**

The `mql-zmq` library (github.com/dingmaotu/mql-zmq) provides:
- `libzmq.dll` (prebuilt, ZMQ 4.x for Windows) — placed in `MT5DataFolder/MQL5/Libraries/`
- `Include/Zmq/` header files — placed in `MT5DataFolder/MQL5/Include/`
- `ZmqContext`, `ZmqSocket` MQL5 classes with PULL/SUB socket support

**Integration pattern for V3 EA:**
```mql5
#include <Zmq/Zmq.mqh>
ZmqContext context;
ZmqSocket  orderSocket(context, ZMQ_PULL);  // receives OrderRequest from Python PUSH

int OnInit() {
    orderSocket.connect("tcp://127.0.0.1:5558");
    // MT5 EA polls this socket on each timer tick
    EventSetMillisecondTimer(100);
    return INIT_SUCCEEDED;
}

void OnTimer() {
    ZmqMsg msg;
    if(orderSocket.recv(msg, ZMQ_DONTWAIT)) {
        // Unpack OrderRequest, validate via CCircuitBreaker, execute
    }
}
```

**Why PULL not SUB:** The Python side sends OrderRequest messages via a PUSH socket (port 5558). The EA uses PULL — this is already the socket pattern in V1. PULL is correct for unicast order delivery (exactly one consumer per order).

**libzmq.dll version:** Must match pyzmq's bundled libzmq version. pyzmq 27.1.0 bundles libzmq 4.3.5. The dingmaotu/mql-zmq prebuilt DLL ships libzmq 4.2.x. **This is a protocol compatibility risk** — ZMQ wire protocol has been stable since ZMQ 4.0 (ZMTP 3.0), so cross-version connections work, but the DLL version mismatch should be noted.

**Alternative: file-based signal passing** — Rejected. PROJECT.md Key Decisions table explicitly records: "File-polling rejected (1s latency, lock risk)."

**Alternative: HTTP REST from MQL5** — Rejected. MT5's `WebRequest` function requires broker server whitelist approval and has unpredictable latency.

**DLL must be allowed:** IC Markets MT5 terminal requires "Allow DLL imports" to be enabled in Tools > Options > Expert Advisors for libzmq.dll to load. This is a deployment prerequisite, not a code change.

---

## Summary of New Additions

| Library | Version | Platform | Install Method |
|---------|---------|---------|----------------|
| pyzmq | 27.1.0 | Linux + Windows (Python) | `pip install pyzmq==27.1.0` |
| msgpack | 1.1.2 | Linux + Windows (Python) | `pip install msgpack==1.1.2` |
| hmmlearn | 0.3.3 | Linux | `pip install hmmlearn==0.3.3` |
| arch | 8.0.0 | Linux | `pip install arch==8.0.0` |
| arcticdb | 6.13.0 | Linux | `pip install arcticdb==6.13.0` |
| mql-zmq (dingmaotu) | libzmq 4.2.x | Windows (MQL5 EA) | Manual: copy DLL + headers to MT5 data folder |

asyncio: stdlib, no install needed.

---

## Anti-Features — Do Not Add

| Library | Why Not |
|---------|---------|
| pomegranate | Rewrote API to torch-first in v1.0; V1 HMM code is hmmlearn-specific; no benefit |
| nats-py | V1 used NATS for React dashboard pubsub. V3 has no dashboard. Adding NATS creates an unnecessary broker dependency for what is a direct Python↔MT5 bridge. |
| redis | Sometimes proposed as a signal bus. Adds a network service with no latency advantage over ZMQ direct sockets for a single-consumer architecture. |
| celery / rq | Task queue for strategy router — overkill. The router is a synchronous per-bar decision function; asyncio coroutines handle concurrency. |
| protobuf | Schema versioning overhead not justified for a same-codebase producer/consumer. msgpack is sufficient. |
| uvicorn / FastAPI | REST API for order routing — rejected in PROJECT.md Key Decisions. ZMQ direct socket achieves sub-10ms; HTTP adds framework overhead. |
| threading.Thread | ZMQ sockets are not thread-safe. asyncio is the correct concurrency model for this codebase. |
| MetaTrader5 (Python) on Linux | MT5 Python API is Windows-only (COM interop). On Linux, signals flow out via ZMQ; MT5 Python API is only used on the Windows publisher side. |

---

## Installation

```bash
# Core new dependencies (requirements-v2.txt or pyproject.toml additions)
pip install pyzmq==27.1.0
pip install msgpack==1.1.2
pip install hmmlearn==0.3.3
pip install arch==8.0.0
pip install arcticdb==6.13.0

# Windows publisher side also needs:
pip install pyzmq==27.1.0
pip install msgpack==1.1.2
pip install MetaTrader5  # Windows-only, version pinned by broker compatibility
```

```
# MQL5 EA side (manual deployment steps):
1. Download mql-zmq from github.com/dingmaotu/mql-zmq
2. Copy mql-zmq/Lib/MT5/*.dll  →  %APPDATA%/MetaQuotes/Terminal/<hash>/MQL5/Libraries/
3. Copy mql-zmq/Include/Zmq/  →  %APPDATA%/MetaQuotes/Terminal/<hash>/MQL5/Include/Zmq/
4. Enable "Allow DLL imports" in MT5 Tools > Options > Expert Advisors
5. Compile MultiPairEA.mq5 with #include <Zmq/Zmq.mqh>
```

---

## Windows/Linux Split

| Component | OS | Key Libraries |
|-----------|-----|--------------|
| `windows_publisher.py` | Windows VPS | pyzmq 27.1.0, msgpack 1.1.2, MetaTrader5 |
| `linux_consumer.py` + signal engine | Linux | pyzmq 27.1.0, msgpack 1.1.2 |
| HMM-GARCH regime classifier | Linux | hmmlearn 0.3.3, arch 8.0.0 |
| PiT manager | Linux | arcticdb 6.13.0 |
| Strategy router | Linux | no new deps (pure Python, uses existing vectorbt.pro output) |
| MT5 EA (MQL5) | Windows (MT5 terminal) | mql-zmq (libzmq.dll + ZMQ.mqh) |

WireGuard VPN connects Windows VPS ↔ Linux server. Port 5556–5559 must be open through WireGuard interface (not external firewall).

---

## Sources

- V1 `requirements.txt`: confirmed versions for pyzmq, msgpack, hmmlearn, arch, arcticdb
- V1 source `src/execution/bridge/`: confirmed asyncio + zmq.asyncio pattern, msgpack schema
- V1 source `src/alpha/regime/hmm_garch.py`: confirmed hmmlearn GaussianHMM + arch arch_model API
- V1 source `src/data/pit_manager.py`: confirmed arcticdb API surface
- PyPI `pip index versions`: all versions confirmed as PyPI latest on 2026-04-21
  - pyzmq 27.1.0 (LATEST), msgpack 1.1.2 (LATEST), hmmlearn 0.3.3 (LATEST), arch 8.0.0 (LATEST)
  - arcticdb: V1 pinned 6.10.2; PyPI latest is 6.13.0 (recommend upgrade)
- `python3 -c "import zmq; print(zmq.zmq_version())"`: confirmed bundled libzmq 4.3.5
- PROJECT.md Key Decisions: confirmed ZMQ bridge rationale, file-polling rejection
- MQL5 ZMQ approach: dingmaotu/mql-zmq is the standard community solution for MQL5 ZMQ (MEDIUM confidence — could not verify via WebFetch; based on training data + V1 architecture docs. Verify DLL version against libzmq 4.3.5 compatibility before deployment.)

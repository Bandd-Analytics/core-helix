# Bridge Components — What Each Piece Does

The bridge is the communication layer between Python and MT5. It lives in `V2/bridge/`.

---

## 1. Message Schema (`bridge/schemas.py` + `bridge/types.py`)

**What it is:** A shared language that both sides agree on.

Before any message is sent across the wire, it is packed into a compact binary format called **msgpack** (think of it as a very small, fast version of JSON). The schema defines the exact structure of every message type so Python and MT5 always understand each other.

**The five message types:**

| Type | Fields | Purpose |
|------|--------|---------|
| `Tick` | symbol, bid, ask, timestamp | Live price update |
| `Bar` | symbol, open, high, low, close, volume, spread, timestamp, timeframe | A completed candle |
| `OrderRequest` | symbol, direction (buy/sell), volume, price, stop loss, take profit | Send a trade to MT5 |
| `Fill` | symbol, direction, volume, fill price, timestamp | MT5 confirms a trade was placed |
| `Heartbeat` | timestamp, schema version | "I'm still alive" ping |

**Why it matters:** Without a schema, a change on one side could silently break the other. The schema version number (`SCHEMA_VERSION = 1`) lets the consumer detect when the two sides are out of sync and warn you before anything goes wrong.

---

## 2. BridgePublisher (`bridge/publisher.py`)

**What it is:** The Python-side broadcaster. It opens ZMQ sockets, binds to ports, and sends messages out.

**What it does:**
- Opens 4 ports (tick stream on 5556, bar stream on 5557, order requests on 5558, fills on 5559)
- Every 5 seconds, sends a **heartbeat** on the tick port so MT5 knows Python is alive
- When called by the trading engine, sends tick data and bar data to MT5
- Receives filled order confirmations back from MT5

**Simple analogy:** The publisher is like a radio station — it broadcasts on specific frequencies (ports). Whoever is tuned in receives the signal.

---

## 3. BridgeConsumer (`bridge/consumer.py`)

**What it is:** The Python-side receiver. It connects to MT5's ZMQ socket and listens for incoming messages.

**What it does:**
- Connects to MT5's bar-close port (5557) and subscribes to all 5 pairs
- Every time MT5 reports a completed bar, the consumer decodes it and calls your `on_bar_close(bar, timeframe)` function — this is what will trigger the strategy router in Phase 10
- Watches the heartbeat: if no heartbeat arrives for 10 seconds, it marks the bridge as **stale** (something is wrong)
- **Auto-reconnects** if the connection drops, with increasing wait times: 1s, 2s, 4s, 8s, 16s, 30s — no manual restart needed
- Accepts bar messages in both msgpack format (Python-to-Python) and JSON format (from the MT5 EA) — whichever arrives, it decodes correctly

**Simple analogy:** The consumer is like a radio receiver — it tunes in to a specific station (port) and translates the incoming signal into something your code can use.

**Stale detection:** If the consumer hasn't heard from MT5 in 10 seconds, `consumer.is_stale` returns `True`. Your code can check this to know whether the bridge is healthy before placing a trade.

---

## 4. MultiPairEA (`ea/MultiPairEA.mq5`)

**What it is:** The MT5 Expert Advisor — the piece of code that runs inside MetaTrader 5 and does the actual trading.

**What it does — original trading logic:**
- Runs every 1 second
- For each of the 5 pairs, checks if a new bar has opened on the pair's primary timeframe
- If yes, asks the signal generator (MeanRev, Trend, or Hybrid depending on the pair) whether to buy, sell, or do nothing
- If the signal is strong enough, calculates the correct position size using ATR (a measure of recent volatility)
- Before placing any order, the **CCircuitBreaker** checks daily loss limits (3%), weekly limits (6%), and max drawdown (15%) — if any limit is hit, trading stops automatically
- **CScalingManager** handles scaling into winning positions

**What it does — new ZMQ bar-close publishing (Phase 6):**
- On the same 1-second timer, checks whether any D1, H1, or M15 bar has just closed across all 5 pairs (that's 15 streams to watch)
- When a bar closes, it reads the completed candle data (open, high, low, close, volume, spread) and sends it to Python over ZMQ as a JSON message
- Python receives this and can then decide whether to trade based on that bar
- If the ZMQ connection fails to start, the EA silently continues trading through its own logic — it never crashes because of the bridge

**The three timeframes it watches:**

| Timeframe | Closes every | Used for |
|-----------|-------------|---------|
| M15 | 15 minutes | Intraday scalping signals |
| H1 | 1 hour | Medium-term signals |
| D1 | 24 hours | Daily swing signals |

---

## 5. Spike Script (`ea/spike/brdg03_spike.mq5`)

**What it is:** A one-shot test script, not a trading tool.

**What it does:** Loads the ZMQ library (libzmq.dll), creates a socket, connects to Python, and sends a single test message. If it completes without errors, the DLL works on this MT5 installation.

This was run once to confirm that the ZMQ library works on the IC Markets MT5 terminal before writing any real bridge code. Result: **PASS** on 2026-04-23.

---

## How the components connect

```
MT5 (Wine)                          Python (Linux)
─────────────────────────────────────────────────────────
MultiPairEA
  │
  │  Bar closes (D1/H1/M15)
  └──────────────────────────────► BridgeConsumer
                                        │
                                        ▼
                                   on_bar_close(bar, tf)
                                        │
                                        ▼
                                   StrategyRouter      ← Phase 9
                                        │
                                        ▼
                                   OrderRequest
                                        │
  ◄──────────────────────────────  BridgePublisher
  │
  ▼
CCircuitBreaker → place order → IC Markets
```

BridgePublisher also sends a **heartbeat every 5 seconds** back to MT5 so the EA knows Python is still running.

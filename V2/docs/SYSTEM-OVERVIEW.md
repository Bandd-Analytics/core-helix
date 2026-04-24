# How the System Works — Big Picture

## What is this system?

MarketMind Helix is an automated forex trading system. It watches the market, decides when to trade, and places orders on your IC Markets account — without you needing to do anything manually once it's running.

It is split into two sides that talk to each other:

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│   Python (the brain)        │◄───────►│   MT5 (the hands)            │
│                             │  ZMQ    │                              │
│  - Analyses market data     │ bridge  │  - Watches live price feeds  │
│  - Decides trade strategy   │         │  - Places/manages orders     │
│  - Manages risk rules       │         │  - Connected to IC Markets   │
└─────────────────────────────┘         └──────────────────────────────┘
```

**Python** is the decision-maker. It runs on your Linux machine and does all the heavy analysis — regime detection, signal scoring, risk checks.

**MT5** (MetaTrader 5) is the executor. It runs under Wine on the same machine and is the only software IC Markets allows to place orders.

They can't call each other directly, so they communicate through a messaging system called **ZMQ** (ZeroMQ) — think of it as a real-time pipe between the two programs.

---

## Why ZMQ?

Three alternatives were considered:

| Option | Problem |
|--------|---------|
| File polling | 1-second delay minimum; risk of file locks |
| Named pipes | Windows-only; breaks Linux deployment |
| **ZMQ** | Sub-10ms latency; works across Wine/Linux boundary; battle-tested |

ZMQ was chosen. It was confirmed working on the IC Markets terminal in BRDG-03.

---

## What flows through the bridge?

| Message | Direction | What it carries |
|---------|-----------|-----------------|
| Bar close | MT5 → Python | A completed candle (OHLCV + timeframe) for each pair |
| Heartbeat | Python → MT5 | Proof that Python is still alive (sent every 5 seconds) |
| OrderRequest | Python → MT5 | "Buy/Sell X lots of EURUSD at this price" |
| Fill | MT5 → Python | Confirmation that an order was executed |
| Tick | Python → MT5 | Real-time bid/ask prices |

In Phase 6 (just completed), the **bar close** and **heartbeat** flows are wired up. OrderRequest and Fill connect in Phase 10.

---

## The five pairs traded

EURUSD, USDJPY, AUDNZD, EURGBP, GBPJPY

Each pair gets its own signal strategy based on its historical behaviour. USDJPY is the strongest performer (Sharpe 3.09 in backtesting).

---

## Phases of development

| Phase | What it builds | Status |
|-------|---------------|--------|
| 6 — ZMQ Bridge | The communication pipe between Python and MT5 | **COMPLETE** |
| 7 — Backtest Fix | Fixes an entry-price bias in historical testing; re-validates 4 years of data | Next |
| 8 — Regime Filter | Detects market conditions (trending vs ranging) to filter bad signals | Planned |
| 9 — Strategy Router | Picks the right strategy for each pair at each moment | Planned |
| 10 — Live Execution | Wires everything together; 7-day demo run before real money | Planned |

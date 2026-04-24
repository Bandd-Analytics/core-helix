# Running the System — Step by Step

This covers what you need to start the bridge and EA for live or demo trading.

---

## What needs to be running

Two things must be active at the same time:

1. **Python bridge** (on Linux) — listens for bar-close events from MT5
2. **MultiPairEA** (in MT5 under Wine) — watches charts and publishes bar closes

They can be started in either order, but Python should ideally be up first.

---

## Starting the Python bridge

Open a terminal and run:

```bash
cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2
python3 -c "
import asyncio, os
os.environ['BRIDGE_HOST'] = '127.0.0.1'
from bridge.consumer import BridgeConsumer

async def on_tick(t): pass

async def on_bar_close(b, tf):
    print(f'[BRIDGE] Bar close: {b.symbol} {tf} close={b.close}')

async def main():
    c = BridgeConsumer()
    await c.connect()
    for sym in ['EURUSD','USDJPY','AUDNZD','EURGBP','GBPJPY']:
        await c.subscribe(sym)
    print('[BRIDGE] Waiting for bar-close events...')
    await c._receive_loop(on_tick, on_bar_close)

asyncio.run(main())
"
```

**What you should see immediately:**
```
[BRIDGE] Connected to 127.0.0.1:5556 — heartbeat OK
[BRIDGE] Waiting for bar-close events...
```

Then every 15 minutes (M15 bar close), lines like:
```
[BRIDGE] Bar close: EURUSD M15 close=1.16771
[BRIDGE] Bar close: USDJPY M15 close=159.825
...
```

---

## Starting the MT5 EA

1. Launch MT5 (Wine):
   ```bash
   WINEPREFIX=~/.mt5 wine "/home/user/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe" /portable
   ```

2. In MT5: open Navigator (Ctrl+N) → Expert Advisors → drag **MultiPairEA** onto any one chart

3. In the inputs dialog, confirm:
   - `InpEnableZmqBars` = true
   - `InpBarPort` = 5557
   - Click OK

4. Check the **Experts tab** at the bottom — you should see:
   ```
   MultiPairEA Starting
   [BRIDGE] Bar-close PUB bound to tcp://*:5557
   MultiPairEA Initialized Successfully
   ```

**Important:** Only attach the EA to **one chart**. It monitors all 5 pairs internally. Attaching it to multiple charts causes a port conflict (error 5004).

---

## Ports used

| Port | Direction | What it carries |
|------|-----------|-----------------|
| 5556 | Python → MT5 | Heartbeat + tick data |
| 5557 | MT5 → Python | Bar-close events |
| 5558 | Python → MT5 | Order requests (Phase 10) |
| 5559 | MT5 → Python | Fill confirmations (Phase 10) |

All traffic stays on `127.0.0.1` (localhost) — nothing goes over the network.

---

## Environment variables (optional overrides)

| Variable | Default | What it changes |
|----------|---------|-----------------|
| `BRIDGE_HOST` | `10.200.0.1` | Host to connect to (use `127.0.0.1` for local Wine setup) |
| `ZMQ_TICK_PORT` | `5556` | Tick/heartbeat port |
| `ZMQ_BAR_PORT` | `5557` | Bar-close port |
| `ZMQ_ORDER_PORT` | `5558` | Order request port |
| `ZMQ_FILL_PORT` | `5559` | Fill confirmation port |

---

## Checking the bridge is healthy

The consumer has a built-in health check. If no heartbeat arrives from Python for 10 seconds, the bridge is considered **stale**. In the terminal you'll see:

```
[BRIDGE] WARNING: No heartbeat received for 10.0s — bridge may be down
```

This means Python stopped or the connection dropped. The consumer will automatically try to reconnect — first after 1 second, then 2s, 4s, 8s, 16s, 30s. You don't need to restart it manually.

---

## Known issues (pre-existing, not bridge-related)

- `CLogger: Cannot open log file` — the EA's CSV trade logger can't create its file in the Wine environment. Doesn't affect trading or ZMQ.
- `zero divide in MeanRevOscillator.mq5 (162,15)` — the mean-reversion indicator occasionally divides by zero when there's not enough history. The signal is skipped for that bar; the EA continues normally.

---

## What's not wired yet (Phase 10)

The bar-close events are now flowing from MT5 → Python. What's not connected yet:

- Python reading those events and deciding to trade (StrategyRouter — Phase 9)
- Python sending OrderRequest messages back to MT5 (Phase 10)
- MT5 executing those orders through CCircuitBreaker (Phase 10)

Currently the EA still places trades through its own internal signal logic. The ZMQ bridge in Phase 6 only wires up the bar-close feed — the full round-trip (Python decides → MT5 executes) comes in Phase 10.

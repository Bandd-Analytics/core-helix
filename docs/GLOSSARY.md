# Helix Trading System — Glossary

## Sharpe Ratio (Sh)

**Definition:** Risk-adjusted return measure. How much return you get per unit of risk taken.

```
Sharpe = Average Return per Trade / Standard Deviation of Returns
```

| Range | Meaning |
|-------|---------|
| Sh > 1.0 | Strong — returns significantly outpace volatility |
| Sh 0.5–1.0 | Acceptable — positive edge, meaningful drawdown swings |
| Sh 0.0–0.5 | Marginal — easily wiped by spreads/slippage in live trading |
| Sh < 0.0 | Losing — average losses exceed average wins on risk-adjusted basis |

**Project threshold:** `allow_flag = True` requires **Sh ≥ 0.5 AND trade_count ≥ 30**.

**Biased vs corrected:** Pre-Phase 7 Sharpe figures used the current bar's close as entry
price — impossible in live trading (close is only known after the bar ends). Phase 7 corrected
all entry prices to the next bar's open. This deflated every Sharpe figure to realistic levels.
Example: EURGBP momentum Sh 1.57 (biased) → 0.84 (corrected).

---

## Timeframes

| Code | Name | Bar Duration | Typical Use |
|------|------|-------------|-------------|
| M15 | 15-minute | 15 min | Scalp entries, intraday timing |
| H1 | 1-hour | 1 hour | Momentum, scalp (medium-term) |
| D1 | Daily | 1 day | Swing trades, trend filter |

---

## Strategy Types

| Strategy | Timeframe | Entry Logic | Notes |
|----------|-----------|-------------|-------|
| Swing | D1 | Z-score mean reversion on daily closes | Longest hold, widest stops |
| H1 Scalp | H1 | Adaptive ATR bands + z-score | Medium hold |
| H1 Momentum | H1 | Z-score breakout direction | Trend-following |
| M15 Scalp | M15 | Z-score mean reversion, tighter thresholds | Shortest hold, most trades |

---

## Data Acquisition Failover

When `MetaTrader5` Python package fails (Windows COM only, cannot install on Linux):

**A → B → D**

- **A:** MT5 GUI History Center export (F2 in terminal → select pair + H1 → Export)
- **B:** Wine Python execution — `wine <path>/python.exe scripts/download_history.py --4yr`
- **D:** Dukascopy free tick data — `pip install duka`, then resample ticks to H1 OHLCV

See `V2/scripts/download_history.py` module docstring for exact commands.

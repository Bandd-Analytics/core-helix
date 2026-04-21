# Hybrid Multi-Timeframe Trading Methodology

## Strategy Overview
Adaptive trading that selects entry/exit based on available opportunity:
- **Scalp mode** (H1): Quick 1-3 hour trades during high volatility/liquid sessions
- **Swing mode** (Daily): Multi-day trades capturing larger moves
- **Session-aware**: Respects liquidity windows and stop-hunt patterns

---

## Market Regime Detection

### Volatility Assessment
```
Low Vol (ATR_H1 < 20th percentile)  → Scalp bias (H1 entries)
High Vol (ATR_H1 > 80th percentile) → Swing bias (Daily entries)
Normal Vol                            → Both allowed, score each
```

### Trend Direction (Daily)
```
Z-score on daily close determines bias:
  Z < -1.5:  Downtrend (look for shorts)
  Z > 1.5:   Uptrend (look for longs)
  -1.5 to 1.5: Neutral (allow both, require stronger signals)
```

---

## Entry Logic: Multi-Frame Decision Tree

### DAILY SWING (High Conviction)
**Condition:**
- Daily Z-score extreme (< -2.0 or > 2.0)
- H1 does NOT contradict (H1 Z-score < 1.5 in opposite direction)
- Position sizing: 1.0x base (larger, fuller stop)

**Example:** Daily shows oversold (Z=-2.3), H1 overbought (Z=1.2)
→ TAKE daily long entry (H1 noise doesn't contradict trend)

---

### SESSION SCALP (Medium Conviction)
**Condition:**
- High volatility window (London Open 08:00 GMT, NY Open 13:00 GMT)
- H1 Z-score extreme (< -2.0 or > 2.0)
- Daily trend aligned or neutral
- Position sizing: 0.5x base (smaller, tighter stop = lower risk)

**Example:** NY session open, volatility spike, H1 Z=-2.1 + daily neutral
→ TAKE H1 short scalp (quick 1-2hr trade)

---

### INTRADAY MOMENTUM (Lower Conviction)
**Condition:**
- H1 Z-score moderate (< -1.5 or > 1.5, not extreme)
- Daily trend STRONGLY aligned (Z-score > |1.5|)
- High liquidity (within session hours)
- Position sizing: 0.3x base (micro-position, very tight stop)

**Example:** Daily uptrend (Z=2.2), H1 Z=1.8 (not extreme but aligned)
→ TAKE tiny H1 long (ride the wave for 1-2hrs)

---

## Exit Rules by Entry Type

### Daily Swing Trades
- **Profit target:** 4x H1_ATR (hold for days)
- **Stop loss:** 1.5x H1_ATR (wider to avoid session whipsaws)
- **Time stop:** Max 5 days held (reduce overnight risk)

### Session Scalps
- **Profit target:** 2x H1_ATR (quick 1-3hr targets)
- **Stop loss:** 0.75x H1_ATR (tight)
- **Time stop:** Max 4 hours held (exit before session change)

### Intraday Momentum
- **Profit target:** 1x H1_ATR (take quick wins)
- **Stop loss:** 0.5x H1_ATR (micro stops)
- **Time stop:** Max 2 hours held

---

## Position Management

### Max Concurrent Positions
- 1 Daily swing trade (holds days)
- 1 Session scalp (holds hours)
- Total max: 2 positions simultaneously
- Same pair max: Only 1 position (no pyramiding same pair)

### Correlation Filter
- If EURUSD is in swing mode, don't scalp GBPJPY (highly correlated)
- Calculate rolling correlation, skip trades > 0.7 correlation with open position

### Risk Per Trade
- Daily swing: 2% account risk
- Session scalp: 1% account risk
- Intraday momentum: 0.5% account risk

---

## Session Timing (UTC)

```
ASIA (22:00-08:00 UTC): 
  - Low liquidity, high spreads
  - Avoid unless strong daily signal
  - Good for testing signals, not execution

LONDON (08:00-17:00 UTC):
  - HIGH SCALP WINDOW
  - Widest moves, tight spreads
  - Favors session scalp entries

NEW YORK (13:00-22:00 UTC):
  - HIGH SCALP WINDOW
  - Overlap 13:00-17:00 with London = most liquid
  - Favors session scalp + swing setups

OFF-HOURS (17:00-22:00 UTC):
  - Avoid intraday entries
  - Daily swings only if extremely strong setup
```

---

## Example Scenarios

### Scenario 1: EURUSD Daily Oversold
```
Daily Z-score: -2.4 (OVERSOLD)
H1 volatility: High (top 20%)
Time: 15:00 London (high liquidity)

→ ENTER: Daily swing long
→ Size: 1.0x
→ Target: 4x ATR (~400 pips)
→ Stop: 1.5x ATR (~150 pips)
→ Hold: 3-5 days
```

### Scenario 2: USDJPY Scalp During London Open
```
Daily Z-score: 0.2 (NEUTRAL)
H1 Z-score: 2.3 (OVERBOUGHT)
Time: 08:00 London open
Vol spike: 30% above normal

→ ENTER: Session scalp short
→ Size: 0.5x
→ Target: 2x ATR (~50 pips)
→ Stop: 0.75x ATR (~19 pips)
→ Hold: 1-2 hours (exit before noon fade)
```

### Scenario 3: Daily Strong + H1 Aligned
```
Daily Z-score: 1.8 (OVERBOUGHT, trending)
H1 Z-score: 1.6 (ALIGNED, not extreme)
Time: 14:30 NY open
Corr check: No conflicting positions

→ ENTER: Momentum short (tiny)
→ Size: 0.3x
→ Target: 1x ATR (~25 pips)
→ Stop: 0.5x ATR (~13 pips)
→ Hold: 1-2 hours
```

---

## Decision Priority (What to Trade?)

1. **Daily swing if Z-score > |2.0|** (highest conviction)
2. **Session scalp if H1 Z-score > |2.0| during London/NY** (medium conviction)
3. **Momentum if daily Z > |1.5| AND H1 aligned** (lower conviction, only tiny size)

If multiple signals available, take the highest conviction one first, then allow second position if they don't conflict.

---

## Implementation Checklist

- [ ] Calculate daily & H1 indicators simultaneously
- [ ] Implement session-aware timestamps (convert to UTC)
- [ ] Build correlation matrix (rolling 30-day)
- [ ] Volatility percentile ranking (20-day rolling)
- [ ] Multi-timeframe Z-score alignment checker
- [ ] Position sizing calculator (% account risk)
- [ ] Session liquidity filter
- [ ] Backtesting validation

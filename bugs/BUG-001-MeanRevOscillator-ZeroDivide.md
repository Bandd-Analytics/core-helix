# BUG-001 — MeanRevOscillator Zero Divide on Non-Mean-Reversion Pairs

| Field | Value |
|-------|-------|
| **ID** | BUG-001 |
| **Status** | FIXED |
| **Severity** | Medium — periodic log spam, signal skipped, no crash |
| **First seen** | 2026-04-24 06:16:24 UTC+3 (MT5 Experts tab) |
| **Fixed** | 2026-04-24 |
| **Files changed** | `V2/indicators/MeanRevOscillator.mq5`, `V2/ea/include/CSignalManager.mqh` |

---

## Symptom

MT5 Experts tab logged repeatedly on bar close:

```
2026.04.24 06:16:24.123  MeanRevOscillator (EURUSD,M15) zero divide,
  check divider to avoid this error in 'MeanRevOscillator.mq5' (162,15)
```

The signal for that bar was skipped; the EA continued running normally.

---

## Root Cause — Full Chain

### Step 1: CSignalManager loads MeanRevOscillator for every pair

`CSignalManager::LoadIndicators()` (CSignalManager.mqh line 119) calls `LoadMeanRevOscillator()` for **all** signal generators — including USDJPY and GBPJPY which use trend-following strategies, not mean reversion.

```mql5
// CSignalManager.mqh — LoadIndicators (before fix)
indicatorHandles[4] = LoadMeanRevOscillator();  // called for every pair
```

### Step 2: Trend-only pairs have zScorePeriod = 0

In `SymbolConfig.mqh`, pairs that don't use mean reversion mark `zScorePeriod = 0`:

```mql5
// SymbolConfig.mqh — InitUSDJPY (before fix)
config.zScorePeriod = 0;  // Not used
```

### Step 3: MeanRevOscillator loaded with InpPeriod = 0

`LoadMeanRevOscillator()` blindly passed `config.zScorePeriod` as the first input:

```mql5
// CSignalManager.mqh — LoadMeanRevOscillator (before fix)
return iCustom(NULL, 0, "MeanRevOscillator", config.zScorePeriod);
// For USDJPY/GBPJPY: iCustom(..., 0)  ← InpPeriod=0
```

MT5 loads the indicator with `InpPeriod = 0` and immediately begins calculating.

### Step 4: CalcSMA guard fails to protect against period = 0

```mql5
// MeanRevOscillator.mq5 — CalcSMA (before fix)
double CalcSMA(const double &close[], int bar, int period)
{
   if(bar < period - 1) return 0.0;  // bar < -1 → always false → no guard!
   ...
   return sum / period;  // period=0 → ZERO DIVIDE (line 162)
}
```

When `period = 0`, the guard `bar < period - 1` becomes `bar < -1`, which is always false for non-negative `bar`. Execution reaches `return sum / period` with `period = 0`.

The same flaw exists in `CalculateStdDev` (line 170): `if(barIndex < period - 1)` → `barIndex < -1` is also always false.

---

## Why It Didn't Crash the EA

MQL5 treats indicator divide-by-zero as a non-fatal runtime error. The indicator returns `EMPTY_VALUE` for that bar and logs the warning. The EA's signal generator receives 0 from `GetZScore()`, which is below the entry threshold, so no trade is placed and execution continues.

---

## Before (broken)

### CSignalManager.mqh
```mql5
int CSignalManager::LoadMeanRevOscillator()
{
   return iCustom(NULL, 0, "MeanRevOscillator", config.zScorePeriod);
   // Passes 0 for trend-only pairs — loads indicator with InpPeriod=0
}
```

### MeanRevOscillator.mq5 — CalcSMA
```mql5
double CalcSMA(const double &close[], int bar, int period)
{
   if(bar < period - 1) return 0.0;  // guard fails when period=0
   double sum = 0.0;
   for(int k = bar - period + 1; k <= bar; k++)
      sum += close[k];
   return sum / period;  // crashes if period=0
}
```

### MeanRevOscillator.mq5 — CalculateStdDev
```mql5
double CalculateStdDev(const double &close[], int barIndex, int period, double sma)
{
   if(barIndex < period - 1) return 0.0;  // same guard flaw
   ...
   double variance = sumSquaredDiff / period;  // would also crash if period=0
}
```

---

## After (fixed)

### CSignalManager.mqh
```mql5
int CSignalManager::LoadMeanRevOscillator()
{
   int period = config.zScorePeriod > 0 ? config.zScorePeriod : 48;
   return iCustom(NULL, 0, "MeanRevOscillator", period);
   // Falls back to 48 (indicator default) when zScorePeriod is not configured
}
```

### MeanRevOscillator.mq5 — CalcSMA
```mql5
double CalcSMA(const double &close[], int bar, int period)
{
   if(period <= 0 || bar < period - 1) return 0.0;  // period=0 caught first
   double sum = 0.0;
   for(int k = bar - period + 1; k <= bar; k++)
      sum += close[k];
   return sum / period;  // safe
}
```

### MeanRevOscillator.mq5 — CalculateStdDev
```mql5
double CalculateStdDev(const double &close[], int barIndex, int period, double sma)
{
   if(period <= 0 || barIndex < period - 1) return 0.0;  // period=0 caught first
   ...
}
```

---

## Fix Strategy

Two layers of defence applied:

| Layer | Fix | Why |
|-------|-----|-----|
| **Caller** (CSignalManager) | Fall back to `48` when `zScorePeriod = 0` | Prevents loading the indicator with a meaningless period; results are never used for non-mean-rev pairs anyway |
| **Indicator** (MeanRevOscillator) | `period <= 0` guard before any division | Defensive — indicator is correct regardless of how it's loaded |

The indicator fix alone would suppress the error. The caller fix is the semantic correctness fix — non-mean-rev pairs load the indicator with a valid period value rather than `0`.

---

## Verification

After reloading the EA in MT5:
- No more `zero divide` entries in the Experts tab on any pair or timeframe
- AUDNZD and EURGBP Z-score signals unaffected (still use their configured periods: 48 and 30)
- USDJPY/EURUSD/GBPJPY MeanRevOscillator loads with period=48 (harmless — GetZScore is never called for trend pairs)

---

## Related

- This is a pre-existing V1 bug carried into V2 — the indicator was written before `CSignalManager` was extended to load it for all signal types
- `CalculateHalfLife` already has correct denominator guards (`if(MathAbs(denominator) < 1e-10) return 0.0`) — no change needed there
- `InpHalfLifePeriod` defaults to 100 and is not configurable via `iCustom` in the current call — cannot be 0 from the caller side

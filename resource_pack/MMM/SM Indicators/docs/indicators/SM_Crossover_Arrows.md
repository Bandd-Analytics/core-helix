# SM_Crossover_Arrows

## Header

| Field | Value |
|-------|-------|
| Name | SM_Crossover_Arrows |
| Source filename | `!SM_Crossover_Arrows.ex4` |
| Source platform | MT4 (MQL4) |
| Source binary size | 5,508 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 1 — Atomic (no SM dependencies beyond Tier 0) |
| Confidence | Confidence: Medium |

**Confidence rationale:** The EMA-crossover arrow indicator pattern is a well-understood and widely-implemented MT4 indicator class. The specific MA periods — EMA 5 and EMA 13 — are HIGH confidence, confirmed by MMM Book p. 47 ("Confluence of Signals" lists EMA 5/13 as a primary entry signal in the MMM methodology). The cross-detection algorithm (`fast > slow AND fast[1] <= slow[1]`) is HIGH confidence as the standard definition of a bullish crossover. Arrow placement, style, offset, and the presence or absence of alert/email features are `[INFER]`. A community note from Forex Factory BTMM threads reports that Steve Mauro's original BTMM crossover indicator had a known off-by-one bar bug where arrows appeared on the wrong bar; the SM_Crossover_Arrows binary (dated 2019) is presumed to incorporate the fix common in later SM releases.

---

## Purpose

SM_Crossover_Arrows draws directional arrows on the main price chart at bars where a fast Exponential Moving Average (EMA) crosses a slow EMA. The **MMM standard EMA pair is EMA 5 / EMA 13** (MMM Book p. 47, "Confluence of Signals" section): "the EMA crossover is one of the three primary confluence factors for MMM entry signals." When EMA(5) crosses above EMA(13), a green UP arrow is placed below the bar's low, signaling a potential bullish entry. When EMA(5) crosses below EMA(13), a red DOWN arrow is placed above the bar's high, signaling a potential bearish entry.

The indicator is purely a visual trigger marker — it does not constitute a complete MMM entry signal by itself. In the MMM methodology (MMM Book pp. 47–49), EMA crossovers are one of three required confluence factors; the others are a session-specific time filter (sm_WorkTime) and confirmation from the SM_TDI indicator. The arrows are best interpreted as "first candidate" signals requiring additional confirmation before acting.

A community note in the BTMM Forex Factory discussion thread (circa 2013–2016) flagged that Steve Mauro's first-generation BTMM crossover indicator placed arrows one bar ahead of the actual cross (a repainting artifact). The SM_Crossover_Arrows binary (2019-dated) is presumed to have corrected this by using the standard `fast[i+1] <= slow[i+1]` previous-bar confirmation.

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| FastMA | int | 5 | 2–100 | Period of the fast Exponential Moving Average | High — MMM Book p. 47 explicitly cites EMA 5 as the fast MA in the MMM entry signal confluence |
| SlowMA | int | 13 | 5–500 | Period of the slow Exponential Moving Average | High — MMM Book p. 47 explicitly cites EMA 13 as the slow MA |
| MAMethod | int | MODE_EMA | MODE_SMA / MODE_EMA / MODE_SMMA / MODE_LWMA | Moving average calculation type | [INFER] — EMA is the MMM standard; the binary may lock this to EMA or expose it as an input |
| AppliedPrice | int | PRICE_CLOSE | enum | Price series used as input to the MA calculation | [INFER] — PRICE_CLOSE is the universal default for EMA |
| UpColor | color | clrLime | any | Color of up (bullish cross) arrows | [INFER] |
| DownColor | color | clrRed | any | Color of down (bearish cross) arrows | [INFER] |
| ArrowSize | int | 2 | 1–5 | Wingdings arrow size (MT4 object property) | [INFER] |
| UpArrowCode | int | 233 | 1–255 (Wingdings) | Wingdings character code for the up arrow (233 = standard MT4 up arrow) | [INFER] |
| DownArrowCode | int | 234 | 1–255 (Wingdings) | Wingdings character code for the down arrow | [INFER] |
| AlertOnCross | bool | false | true / false | Fire a popup alert when a new cross is detected on the current live bar | [INFER] |
| AlertEmail | bool | false | true / false | Send email alert via MT4 email settings | [INFER] |
| AlertPush | bool | false | true / false | Send push notification to MT4 mobile app | [INFER] |
| ObjectPrefix | string | "smXO_" | any valid string | Chart object name prefix for arrow objects and bulk cleanup | [INFER] |

---

## Outputs

### Indicator buffers

[INFER] Two indicator buffer arrays may be used if the implementation draws arrows via the buffer-style `DRAW_ARROW` method:
- Buffer 0: `UpArrows[]` — contains arrow Y-price at cross bars; `EMPTY_VALUE` at non-cross bars
- Buffer 1: `DownArrows[]` — contains arrow Y-price at bearish-cross bars; `EMPTY_VALUE` elsewhere

Alternatively, the indicator may use direct `OBJ_ARROW_UP` / `OBJ_ARROW_DOWN` chart objects rather than buffer drawing. The 5,508-byte binary size is consistent with either approach; the ObjectCreate approach is more common in older MQL4 indicator codebases.

### Chart objects

When using the ObjectCreate approach [INFER]:
- `smXO_up_{i}` — `OBJ_ARROW_UP` at bullish-cross bar `i`, placed below `low[i]` by an offset of ~3 points
- `smXO_dn_{i}` — `OBJ_ARROW_DOWN` at bearish-cross bar `i`, placed above `high[i]` by an offset of ~3 points

When using the buffer approach, no explicit chart objects are created — the indicator system handles arrow rendering.

### Alerts

Fired when a fresh cross is detected on the most recently completed bar (bar 1, not bar 0) to avoid live-bar repainting:
- `Alert()` popup if `AlertOnCross = true` [INFER]
- `SendMail()` if `AlertEmail = true` [INFER]
- `SendNotification()` if `AlertPush = true` [INFER]

Alert text example: "Bullish EMA 5/13 cross on EURUSD H1" [INFER — exact format]

---

## Calculation logic

1. **For each bar i** (using the `prev_calculated` optimization to process only new/changed bars):

   a. Compute `fast_i  = iMA(symbol, period, FastMA, 0, MAMethod, AppliedPrice, i)` — the EMA(5) value at bar i.
   b. Compute `fast_i1 = iMA(symbol, period, FastMA, 0, MAMethod, AppliedPrice, i+1)` — EMA(5) at bar i+1 (one bar earlier).
   c. Compute `slow_i  = iMA(symbol, period, SlowMA, 0, MAMethod, AppliedPrice, i)` — EMA(13) at bar i.
   d. Compute `slow_i1 = iMA(symbol, period, SlowMA, 0, MAMethod, AppliedPrice, i+1)` — EMA(13) at bar i+1.

2. **Bullish cross detection:** If `fast_i > slow_i AND fast_i1 <= slow_i1`:
   - Arrow position: `arrow_y = low[i] − arrow_offset` where `arrow_offset = 3 × Point` (adapted for JPY/index — see Edge cases) [INFER — exact offset multiplier]
   - Create/update arrow object or set buffer value at bar i.

3. **Bearish cross detection:** If `fast_i < slow_i AND fast_i1 >= slow_i1`:
   - Arrow position: `arrow_y = high[i] + arrow_offset`
   - Create/update arrow object or set buffer value at bar i.

4. **Alert condition** (when `AlertOnCross = true`): If the cross is detected at bar i = 1 (the bar immediately before the current live bar) AND this cross is newly detected in this call (not detected in the previous `OnCalculate` call), fire the alert functions.

5. **Bar-iteration model:** `prev_calculated` optimization — only bars from `max(prev_calculated - 1, SlowMA + 1)` to `rates_total - 1` are processed. This is the standard MQL4 recalculation pattern.

---

## Pseudocode

```
# SM_Crossover_Arrows — language-neutral imperative pseudocode
# FastMA=5, SlowMA=13 per MMM Book p. 47 (EMA 5/13 standard pair)

GLOBAL: last_cross_bar = -1   # for alert deduplication [INFER]

function on_calculate(rates_total, prev_calculated):
    start = max(prev_calculated - 1, SlowMA + 1)

    for i in start..rates_total - 1:
        fast_i  = ema(close, FastMA, i)
        fast_i1 = ema(close, FastMA, i + 1)
        slow_i  = ema(close, SlowMA, i)
        slow_i1 = ema(close, SlowMA, i + 1)

        # Bullish cross: fast crosses ABOVE slow at bar i
        if fast_i > slow_i and fast_i1 <= slow_i1:
            arrow_y = low[i] - 3 * symbol_point()    # [INFER] offset = 3 * Point
            upsert_arrow(ObjectPrefix + "up_" + i,
                         time[i], arrow_y,
                         UpArrowCode, UpColor, ArrowSize)

            if AlertOnCross and i == rates_total - 2 and last_cross_bar != i:
                last_cross_bar = i
                fire_alert("Bullish EMA " + FastMA + "/" + SlowMA + " cross")
                if AlertEmail: send_email("EMA cross signal", detail_string)
                if AlertPush:  send_push("EMA cross signal")

        # Bearish cross: fast crosses BELOW slow at bar i
        elif fast_i < slow_i and fast_i1 >= slow_i1:
            arrow_y = high[i] + 3 * symbol_point()   # [INFER] offset = 3 * Point
            upsert_arrow(ObjectPrefix + "dn_" + i,
                         time[i], arrow_y,
                         DownArrowCode, DownColor, ArrowSize)

            if AlertOnCross and i == rates_total - 2 and last_cross_bar != i:
                last_cross_bar = i
                fire_alert("Bearish EMA " + FastMA + "/" + SlowMA + " cross")
                if AlertEmail: send_email("EMA cross signal", detail_string)
                if AlertPush:  send_push("EMA cross signal")
```

---

## Visual elements

Wingdings arrows drawn on the **main price chart** (not a subwindow):

- **Bullish cross (EMA 5 crosses above EMA 13):** Lime/green up-pointing Wingdings arrow (code 233) [INFER], placed below the candle low at `low[i] − 3 × Point` offset. Z-order: above candles.
- **Bearish cross (EMA 5 crosses below EMA 13):** Red down-pointing Wingdings arrow (code 234) [INFER], placed above the candle high at `high[i] + 3 × Point`. Z-order: above candles.
- Arrow size: MT4 ArrowSize property 2 [INFER] — visible but not overwhelming.
- No subwindow. The EMA lines themselves are NOT drawn by this indicator — they are implicit in the crossover detection but the indicator may not visualize them (the trader is expected to have EMA(5) and EMA(13) drawn separately or via SM_TDI). [INFER]

---

## Dependencies

None. SM_Crossover_Arrows is self-contained: it calls `iMA()` internally to compute the two EMA series and creates chart objects. No dependency on `sm_gmtoffset`, `sm_WorkTime`, or other SM indicators for its core operation.

**Complementary indicators** (not dependencies): In the MMM workflow, EMA crossover arrows gain significance when combined with:
- `sm_WorkTime` — to confirm the cross occurs within an active trading session
- `SM_TDI` — for RSI/signal-line confluence confirmation
- `SM_ADR_Marker` — to confirm the cross does not occur at ADR exhaustion (would be a lower-quality signal)

These are workflow relationships, not code dependencies.

---

## Edge cases

- **Insufficient history for SlowMA:** For bars i where `i + 1 < SlowMA`, the EMA(13) at bar i+1 is undefined (insufficient lookback). These bars must be skipped — the `start = max(prev_calculated - 1, SlowMA + 1)` guard handles this.

- **Arrow off-by-one bar (repainting / non-repainting):** This is the historically significant edge case for crossover indicators. Using `fast_i1 <= slow_i1` (comparing to the previous bar i+1) correctly identifies a cross that is already confirmed by bar close at bar i. If instead the code used bar 0 (current live bar), the arrow would appear and then potentially disappear if the bar reverses — a repainting artifact. The 2019 SM binary is presumed to use the non-repainting pattern (compare against i and i+1, never against bar 0 directly).

- **Multiple consecutive crosses in a choppy market:** Short EMA periods (5/13) frequently produce whipsaw signals in low-volatility consolidation. The indicator simply draws all detected crosses without filtering. High arrow density during consolidation is expected behavior, not a bug.

- **JPY pairs — arrow offset:** `3 × Point` offset for USDJPY produces an arrow at `±0.003` from the bar high/low, which at price 152.50 is approximately 0.3 pips — barely visible. A pip-based offset (`3 × pip_size`) would be `±0.030`, which is more appropriate. [INFER — whether JPY-aware offset adaptation is implemented]

- **Repeated cross on the same bar (fast oscillation on very short EMA):** If the EMA values are recalculated on every tick and the comparison is applied to partially-completed bars, it is possible to detect multiple sign changes on the same bar index. The `last_cross_bar != i` deduplication guard prevents multiple alerts; the `prev_calculated - 1` restart prevents multiple objects on the same bar.

- **Symbol/timeframe change:** `prev_calculated = 0` triggers a full recompute. All arrow objects from the previous symbol must be cleaned up via the `ObjectPrefix`-based loop before new arrows are placed.

- **Live last-bar behavior:** The current bar (bar 0) may briefly show a cross condition during a tick, then reverse. The indicator should NOT place arrows or fire alerts based on bar 0 — only on bar 1 (confirmed closed bar) and earlier. [INFER — whether this guard is robustly implemented]

---

## Test cases

1. **EURUSD H1 transitioning from downtrend to uptrend.** At bar i where EMA(5) crosses above EMA(13): `fast[i] = 1.08342 > slow[i] = 1.08297` and `fast[i+1] = 1.08180 ≤ slow[i+1] = 1.08240`. Expected: a lime up-arrow object placed at `y = low[i] − 3 × 0.00001` below the bar's low. No arrow on bars before or after where no cross occurred.

2. **EURUSD H1, later bearish cross.** At bar j where EMA(5) crosses below EMA(13): `fast[j] = 1.08050 < slow[j] = 1.08090` and `fast[j+1] = 1.08130 ≥ slow[j+1] = 1.08110`. Expected: a red down-arrow placed at `y = high[j] + 3 × 0.00001` above the bar's high. The prior up-arrow from test case 1 remains on the chart unchanged.

3. **AlertOnCross=true, EURUSD H1, a new bearish cross occurs at bar 1 (the last completed bar).** Expected: `Alert()` fires with a message containing "Bearish EMA 5/13 cross". If `AlertEmail = true`, `SendMail()` is also called. The alert fires only once for this bar, not on subsequent ticks within the same bar.

---

## Port notes

### MQ4 → MQ5

- `iMA(symbol, period, ma_period, ma_shift, ma_method, applied_price, bar_shift)` (MQ4) → MQ5 uses a handle pattern: `int handle = iMA(symbol, period, ma_period, ma_shift, ma_method, applied_price); CopyBuffer(handle, 0, bar_shift, count, buffer_array);`. This is the most significant delta when porting SM_Crossover_Arrows.
- `OBJ_ARROW_UP` / `OBJ_ARROW_DOWN` exist in both. MQ5 `ObjectCreate` requires `chart_id = 0` as the first argument.
- Buffer-style arrow drawing in MQ5: `PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_ARROW); PlotIndexSetInteger(0, PLOT_ARROW, UpArrowCode);` — this is cleaner than the ObjectCreate approach and handles chart synchronization automatically.
- Helix's `V2/indicators/BandD_TradeReplay.mq5` (landed Phase 8.4 Plan 04) demonstrates the modern MQ5 arrow-drawing pattern via `OBJ_ARROW` — use its object-creation code as a reference for the arrow placement API in MQ5.
- `Alert()`, `SendMail()`, `SendNotification()` function signatures are identical in MQ4 and MQ5.

### Python port

```python
import pandas as pd

def compute_ema_crossover(df: pd.DataFrame,
                          fast: int = 5,
                          slow: int = 13) -> pd.DataFrame:
    df = df.copy()
    df['ema_fast'] = df['Close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['Close'].ewm(span=slow, adjust=False).mean()

    # EMA 5 crosses above EMA 13
    df['cross_up'] = (df['ema_fast'] > df['ema_slow']) & \
                     (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
    # EMA 5 crosses below EMA 13
    df['cross_dn'] = (df['ema_fast'] < df['ema_slow']) & \
                     (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))
    return df

# Visualization (matplotlib scatter)
up_bars = df[df['cross_up']]
dn_bars = df[df['cross_dn']]
ax.scatter(up_bars.index, up_bars['Low']  * 0.9999, marker='^', color='lime', s=80)
ax.scatter(dn_bars.index, dn_bars['High'] * 1.0001, marker='v', color='red',  s=80)
```

Alerts become log messages or webhook/push calls depending on the deployment context.

### Backtester integration

EMA(5)/EMA(13) crossover is a foundational signal pattern already validated in Helix v1.0's strategy library. In `backtest_hybrid.py`:

```python
df = compute_ema_crossover(df, fast=5, slow=13)

if df.iloc[-1]['cross_up']:
    long_entry = True
if df.iloc[-1]['cross_dn']:
    short_entry = True
```

The H1 momentum strategy validated in Phase 7 Plan 03 (BKTS-04 GREEN, Sharpe 2.08) uses a Hurst-based regime filter rather than EMA crossover, but the EMA 5/13 cross is conceptually equivalent as an entry trigger for mean-reversion setups. SM_Crossover_Arrows as a backtester input would complement the daily Z-score signal: EMA cross confirms the short-term momentum has turned in favor of the trade direction.

---

## Uncertainty log

- [INFER] `FastMA = 5, SlowMA = 13` defaults — HIGH-confidence for the MMM context per MMM Book p. 47; the specific compiled binary may expose these as adjustable inputs or hard-code them; the assumption is they are exposed as inputs with 5/13 as defaults
- [INFER] `MAMethod = MODE_EMA` default — EMA is the MMM standard but the binary may allow switching to SMA or LWMA via an input
- [INFER] `AppliedPrice = PRICE_CLOSE` default — nearly universal for EMA indicators
- [INFER] Wingdings codes 233 / 234 — standard MT4 up/down arrow codes; could be different Wingdings values
- [INFER] Arrow offset `3 × Point` — the exact multiplier could be 5 or 10; on JPY pairs, Point-based offset may be inadequate
- [INFER] `AlertOnCross = false` default — most indicators default alerts off and let the user opt in
- [INFER] Whether the indicator draws the EMA 5 and EMA 13 lines in addition to the arrows — many crossover indicators in the MT4 community also plot the MAs; the 5,508-byte size is consistent with either approach
- [INFER] Whether the binary uses ObjectCreate-based arrows or buffer-based DRAW_ARROW — buffer approach is cleaner but ObjectCreate was more common in 2019-era MQL4 code
- [INFER] Whether secondary EMA pairs (e.g., EMA 50/200 for trend-shift signals) are supported via additional inputs or require a separate indicator instance
- [INFER] Wait-for-bar-close logic — whether the indicator has an explicit `AlertOnClose` flag or simply fires on bar 1 by design

# SM_TDI

## Header

| Field | Value |
|-------|-------|
| Name | SM_TDI |
| Source filename | `!SM_TDI.ex4` (also present: `!_TDI.ex4` — 27,724 bytes, a more elaborate variant with additional features) |
| Source platform | MT4 (MQL4) |
| Source binary size | 15,880 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 2 — Composite (no SM dependencies; self-contained) |
| Confidence | Confidence: High |

**Confidence rationale:** The Traders Dynamic Index (TDI) was created by Dean Malone and is extensively documented in the MMM TDI Tradestation PDF (in this repo at `resource_pack/MMM/docs/MMM TDI_Tradestation.pdf`). That PDF provides all five line definitions, all parameter values, all three alert types, and the 32/50/68 reference levels. Community sources (earnforex.com, tradersunion.com, Forex Factory BTMM threads) cross-confirm every parameter. The only MEDIUM-confidence claim is the StdDev multiplier: 1.6185 is most commonly cited for the original Malone TDI; some SM variants use 2.0. All other parameters are HIGH confidence. This makes SM_TDI the only Tier 2 indicator with overall **Confidence: High**.

**Primary source:** MMM TDI Tradestation PDF — a Steve Mauro-authored document in this repo presenting the TDI parameters and alert conditions explicitly. Cross-referenced against MMM Book pp. 45-46 for MMM-specific usage patterns.

---

## Purpose

The Traders Dynamic Index (TDI) was created by Dean Malone and adopted wholesale by Steve Mauro as the **sole confirmation indicator** for MMM strategies. It combines RSI, Bollinger Bands, and moving averages into a single subwindow display that simultaneously shows momentum (RSI level), volatility (Bollinger Band width), and trend (Market Base Line slope) in one view. No other indicator is required — MMM entries are confirmed when TDI patterns align with session timing and price structure.

The TDI is composed of **5 lines** and **3 reference levels**:
- **Green line (RSI Price Line / RSI PL)** — the raw RSI(13) smoothed with a 2-period SMA. The fastest-moving line; drives alert logic.
- **Red line (Trade Signal Line / TSL)** — 7-period SMA of the raw RSI(13). The lagging signal; Green crossing Red generates entry alerts.
- **Yellow line (Market Base Line / MBL)** — 34-period SMA of the raw RSI(13). Represents the medium-term RSI trend; Green crossing Yellow generates "Blood in the Water" continuation alerts.
- **Blue lines (Volatility Bands / VB upper + VB lower)** — Bollinger Bands applied to the MBL with period 34 and StdDev multiplier 1.6185. Width contracts during consolidation (VB Squeeze) and expands during momentum; price hooks at the bands generate counter-trend alerts.
- **Reference levels** — horizontal dashed lines at **32** (Selling Exhaustion / oversold), **50** (Sentiment midpoint), and **68** (Buying Exhaustion / overbought). These levels divide the 0-100 RSI scale into actionable zones.

MMM Book pp. 45-46 describe the key TDI patterns in the MMM context: the **Shark Fin** (RSI PL spikes above 68 or below 32 then re-enters the band — stop hunt signal), **Blood in the Water** (RSI PL crosses the MBL with price confirmation — trend continuation entry), and the **VB Squeeze** (band contraction preceding a breakout). These patterns map directly to the three alert types described in the MMM TDI Tradestation PDF.

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| RSI_Period | int | 13 | 5–50 | Period for the underlying RSI calculation | High — MMM TDI Tradestation PDF + all community sources universally confirm 13 |
| RSI_Price | int | PRICE_CLOSE (0) | 0–6 (PRICE_* enum) | Price type fed into the RSI: 0=Close, 1=Open, 2=High, 3=Low, 4=Median, 5=Typical, 6=Weighted | High — Close is the universal convention |
| Volatility_Band | int | 34 | 5–100 | Bollinger Band period applied to the MBL | High — confirmed in PDF and community |
| StdDev | double | 1.6185 | 0.5–3.0 | Bollinger StdDev multiplier for the Volatility Bands | [INFER] — 1.6185 is the most-cited value for the original Malone TDI; some SM variants may use 2.0; exact value in this binary unverifiable |
| RSI_Price_Line | int | 2 | 1–10 | Green line: SMA period applied to smooth the raw RSI | High — PDF p. 11 confirms 2-period SMA |
| Trade_Signal_Line | int | 7 | 2–30 | Red line: SMA period of the raw RSI | High — PDF p. 11 confirms 7-period SMA |
| Market_Base_Line | int | 34 | 10–100 | Yellow line: SMA period of the raw RSI (same as Volatility_Band by convention) | High — PDF p. 12 confirms 34-period SMA |
| Level_High | double | 68 | 50–90 | Buying Exhaustion reference level — overbought threshold | High — MMM TDI Tradestation PDF p. 10 |
| Level_Mid | double | 50 | 40–60 | Sentiment midpoint reference level | High — MMM TDI Tradestation PDF p. 10 |
| Level_Low | double | 32 | 10–50 | Selling Exhaustion reference level — oversold threshold | High — MMM TDI Tradestation PDF p. 10 |
| GreenColor | color | clrLime | any | RSI Price Line (Green) color | [INFER] |
| RedColor | color | clrRed | any | Trade Signal Line (Red) color | [INFER] |
| YellowColor | color | clrYellow | any | Market Base Line (Yellow) color | [INFER] |
| BlueColor | color | clrDodgerBlue | any | Volatility Band upper and lower line color | [INFER] |
| LevelColor | color | clrDarkGray | any | Horizontal reference level line color at 32, 50, 68 | [INFER] |
| EnableSignalCrossAlert | bool | true | true / false | Fire alert when Green (RSI PL) crosses Red (TSL) | High — PDF p. 15 defines Signal Cross as the primary alert |
| EnableMBLCrossAlert | bool | true | true / false | Fire alert when Green crosses Yellow (MBL) with price confirmation | High — PDF p. 16 defines MBL Cross conditions |
| EnableHookAlert | bool | true | true / false | Fire alert when Green hooks back from 32/68 extreme across the VB | High — PDF p. 17 defines Hook alert conditions |
| AlertEmail | bool | false | true / false | Also send email alert via configured SMTP | [INFER] |
| AlertPush | bool | false | true / false | Also send push notification to mobile | [INFER] |

---

## Outputs

### Indicator buffers

Five indicator buffers exposed in the subwindow. Because TDI is implemented as an indicator (not an EA), these buffers are accessible to other indicators and EAs via `iCustom("SM_TDI", symbol, timeframe, buffer_index, shift)`:

- Buffer 0: `RSI_PL[]` — Green line values (2-period SMA of RSI(13))
- Buffer 1: `TSL[]` — Red line values (7-period SMA of RSI(13))
- Buffer 2: `MBL[]` — Yellow line values (34-period SMA of RSI(13))
- Buffer 3: `VB_upper[]` — Upper Volatility Band values
- Buffer 4: `VB_lower[]` — Lower Volatility Band values

[INFER] Whether SM_TDI (15,880-byte variant) actually exposes all 5 buffers to EAs, vs. the larger `!_TDI.ex4` (27,724 bytes) being the buffer-exposing variant. The SM_TDI binary may be a visual-only version with internal arrays not registered as indicator buffers.

### Chart objects

None directly. All five lines are rendered through the indicator buffer drawing system in a dedicated subwindow (`#property indicator_separate_window`). Three horizontal `OBJ_HLINE` objects drawn at Level_Low (32), Level_Mid (50), Level_High (68) in LevelColor with STYLE_DASH. No chart objects on the main price chart.

### Alerts

Three alert types, each gated by its own enable flag:

1. **TDI Signal Cross** — Green (RSI PL) crosses Red (TSL) in either direction. Bullish: Green crosses above Red. Bearish: Green crosses below Red. (MMM TDI Tradestation PDF p. 15)

2. **MBL Cross** — Green crosses Yellow (MBL) AND Green is above Red (TSL) for bullish, AND `high[1] > average(high[2..N])` for price confirmation. (MMM TDI Tradestation PDF p. 16)

3. **TDI Hook** — Bullish hook: Green is near Level_Low (32), Green was below VB_lower, now crosses back above VB_lower (re-entry into Bollinger Band from below). Bearish hook: inverse. (MMM TDI Tradestation PDF p. 17)

Alerts fire via MT4's `Alert()` function with a message string. If AlertEmail=true, `SendMail()` is also called. If AlertPush=true, `SendNotification()`. [INFER] All three alert methods use the same triggering conditions.

---

## Calculation logic

All calculations use the raw RSI series as the foundation. The smoothing operations (SMA for RSI PL, TSL, MBL) and Bollinger Band operations are applied to that single raw RSI series — NOT to the price series directly.

1. **On `OnInit`:** Register 5 indicator buffers with `SetIndexBuffer`. Set drawing styles (`SetIndexStyle(DRAW_LINE, ..., color)`). Draw the three horizontal reference lines (32, 50, 68) as `OBJ_HLINE` in the subwindow. The subwindow is created automatically because `#property indicator_separate_window` is set.

2. **On `OnCalculate` (per bar, from oldest to newest):** Compute the raw RSI for each bar:
   ```
   RSI_raw[i] = iRSI(symbol, timeframe, RSI_Period, RSI_Price, i)
   ```
   This is the standard 13-period Wilder RSI on closing prices.

3. **Green line (RSI Price Line):** Apply a 2-period Simple Moving Average to the raw RSI series:
   ```
   RSI_PL[i] = SMA(RSI_raw, RSI_Price_Line=2, i)
   ```
   This single bar of smoothing removes the most extreme tick-by-tick noise while keeping the line highly responsive.

4. **Red line (Trade Signal Line):** Apply a 7-period SMA to the same raw RSI series:
   ```
   TSL[i] = SMA(RSI_raw, Trade_Signal_Line=7, i)
   ```
   The TSL lags several bars behind the Green line; crossovers signal directional change.

5. **Yellow line (Market Base Line):** Apply a 34-period SMA to the raw RSI series:
   ```
   MBL[i] = SMA(RSI_raw, Market_Base_Line=34, i)
   ```
   The MBL is the slow-moving midline; when Green crosses Yellow from below with bullish price action, this is "Blood in the Water."

6. **Blue lines (Volatility Bands):** Compute the 34-period standard deviation of the raw RSI series, then apply the StdDev multiplier around the MBL:
   ```
   sigma[i] = StdDev_population(RSI_raw, Volatility_Band=34, i)
   VB_upper[i] = MBL[i] + StdDev * sigma[i]   # 1.6185 × sigma
   VB_lower[i] = MBL[i] - StdDev * sigma[i]   # 1.6185 × sigma
   ```

7. **Alert detection** (on each new completed bar — bar index 1 in MT4 convention):
   - **TDI Signal Cross:** `RSI_PL[1] > TSL[1] AND RSI_PL[2] <= TSL[2]` → Bullish Signal Cross alert. Inverse for Bearish.
   - **MBL Cross (Bullish):** `RSI_PL[1] > MBL[1] AND RSI_PL[2] <= MBL[2] AND RSI_PL[1] > TSL[1] AND high[1] > avg_high(bars=6)`. The price confirmation (`high[1] > avg_high`) is from the MMM TDI PDF p. 16 — ensures price action corroborates the TDI signal.
   - **TDI Hook (Bullish):** `RSI_PL[1] > VB_lower[1] AND RSI_PL[2] <= VB_lower[2] AND RSI_PL[1] < 40` → Green is still near the oversold zone but has crossed back above the lower VB. This is the counter-trend hook entry. Bearish hook is the inverse condition at the upper band near 60+.

8. **Bar-iteration model:** New-bar-only for alert detection (bar[1] transition). Full recalculation uses the `prev_calculated` optimization to avoid recomputing bars that haven't changed: `start = max(prev_calculated - 1, Market_Base_Line + Volatility_Band + 2)`. This ensures sufficient lookback for the 34-period MBL + the 34-period Bollinger on it.

9. **On `OnDeinit`:** Delete the three horizontal level objects (32, 50, 68). Buffer memory freed automatically by MT4.

---

## Pseudocode

```
# SM_TDI — language-neutral imperative pseudocode
# Source: MMM TDI Tradestation PDF (primary) + community cross-confirmation

CONST RSI_PERIOD       = 13
CONST RSI_PRICE_LINE   = 2       # SMA period for Green (RSI PL)
CONST TRADE_SIGNAL     = 7       # SMA period for Red (TSL)
CONST MARKET_BASE      = 34      # SMA period for Yellow (MBL) and VB
CONST STDDEV_MULT      = 1.6185  # Bollinger StdDev multiplier [INFER — may be 2.0]
CONST LEVEL_HIGH       = 68
CONST LEVEL_MID        = 50
CONST LEVEL_LOW        = 32

GLOBAL rsi_raw[MAX_BARS]
GLOBAL rsi_pl[MAX_BARS]   # Green
GLOBAL tsl[MAX_BARS]      # Red
GLOBAL mbl[MAX_BARS]      # Yellow
GLOBAL vb_upper[MAX_BARS] # Blue upper
GLOBAL vb_lower[MAX_BARS] # Blue lower

function on_init():
    register_buffer(rsi_pl,   DRAW_LINE, GREEN)
    register_buffer(tsl,      DRAW_LINE, RED)
    register_buffer(mbl,      DRAW_LINE, YELLOW)
    register_buffer(vb_upper, DRAW_LINE, BLUE)
    register_buffer(vb_lower, DRAW_LINE, BLUE)
    draw_hline("TDI_H68", LEVEL_HIGH, DARKGRAY, STYLE_DASH)
    draw_hline("TDI_H50", LEVEL_MID,  DARKGRAY, STYLE_DASH)
    draw_hline("TDI_H32", LEVEL_LOW,  DARKGRAY, STYLE_DASH)

function on_calculate(rates_total, prev_calculated):
    start = max(prev_calculated - 1, MARKET_BASE + STDDEV_PERIOD + 2)
    for i in start..rates_total - 1:
        rsi_raw[i] = rsi(close, RSI_PERIOD, i)

    for i in start..rates_total - 1:
        rsi_pl[i]   = sma(rsi_raw, RSI_PRICE_LINE, i)
        tsl[i]      = sma(rsi_raw, TRADE_SIGNAL,   i)
        mbl[i]      = sma(rsi_raw, MARKET_BASE,    i)
        sigma       = stddev(rsi_raw, MARKET_BASE, i)
        vb_upper[i] = mbl[i] + STDDEV_MULT * sigma
        vb_lower[i] = mbl[i] - STDDEV_MULT * sigma

    last = rates_total - 2
    prev = rates_total - 3

    if EnableSignalCrossAlert:
        if rsi_pl[last] > tsl[last] and rsi_pl[prev] <= tsl[prev]:
            fire_alert("TDI Signal Cross BULLISH: " + symbol + " " + timeframe)
        elif rsi_pl[last] < tsl[last] and rsi_pl[prev] >= tsl[prev]:
            fire_alert("TDI Signal Cross BEARISH: " + symbol + " " + timeframe)

    if EnableMBLCrossAlert:
        avg_h = mean(high[last-5..last])
        if rsi_pl[last] > mbl[last] and rsi_pl[prev] <= mbl[prev]:
            if rsi_pl[last] > tsl[last] and high[last] > avg_h:
                fire_alert("TDI MBL Cross BULLISH (Blood in the Water)")
        elif rsi_pl[last] < mbl[last] and rsi_pl[prev] >= mbl[prev]:
            if rsi_pl[last] < tsl[last] and low[last] < mean(low[last-5..last]):
                fire_alert("TDI MBL Cross BEARISH")

    if EnableHookAlert:
        if rsi_pl[last] > vb_lower[last] and rsi_pl[prev] <= vb_lower[prev]:
            if rsi_pl[last] < 40:
                fire_alert("TDI Hook BULLISH (counter-trend) near " + LEVEL_LOW)
        elif rsi_pl[last] < vb_upper[last] and rsi_pl[prev] >= vb_upper[prev]:
            if rsi_pl[last] > 60:
                fire_alert("TDI Hook BEARISH (counter-trend) near " + LEVEL_HIGH)

function on_deinit():
    delete_object("TDI_H68")
    delete_object("TDI_H50")
    delete_object("TDI_H32")
```

---

## Visual elements

**Subwindow:** TDI renders in a dedicated subwindow below the main price chart (`#property indicator_separate_window`). Y-axis spans 0 to 100 (the RSI scale). The subwindow height is set by MT4's default auto-scale; no fixed minimum/maximum is expected.

**Line properties (all [INFER] for exact pixel thickness):**
- Green line (RSI PL): `clrLime`, DRAW_LINE, width 1 — fastest-moving, drawn on top
- Red line (TSL): `clrRed`, DRAW_LINE, width 1 — slightly lagging
- Yellow line (MBL): `clrYellow`, DRAW_LINE, width 2 — medium-term baseline; slightly thicker for visual prominence
- Blue upper VB: `clrDodgerBlue`, DRAW_LINE, width 1 — upper band
- Blue lower VB: `clrDodgerBlue`, DRAW_LINE, width 1 — lower band
- Reference levels (32, 50, 68): `clrDarkGray`, STYLE_DASH, width 1 — faint dashed horizontals

**Z-order within subwindow:** Yellow (MBL) rendered first, then Blue bands, then Red (TSL), then Green (RSI PL) on top — so the fast green line is always visible above the slower lines.

**No price-chart objects.** TDI does NOT draw anything on the main price chart (no arrows, no lines, no zones).

---

## Dependencies

None. SM_TDI is entirely self-contained. It does NOT call `sm_gmtoffset`, `sm_WorkTime`, or any other SM helper. Its calculation is purely mathematical (RSI + SMA + Bollinger) on the current chart's price series.

The separate `!_TDI.ex4` (27,724 bytes) may be a version that calls additional SM indicators via `iCustom`, but SM_TDI at 15,880 bytes has no external SM dependencies.

---

## Edge cases

1. **Insufficient history:** The warmup period is `RSI_Period + MARKET_BASE + VOLATILITY_BAND = 13 + 34 + 34 = 81 bars minimum`. For the first 80 bars, `RSI_PL`, `TSL`, `MBL`, `VB_upper`, `VB_lower` should be set to `EMPTY_VALUE` (MT4 constant 2^31 − 1) to suppress drawing. If the chart has fewer than 81 bars, no lines appear.

2. **Symbol or timeframe change:** `prev_calculated` resets to 0 and the full history is recomputed. The `OnInit` handler re-draws the reference level lines.

3. **Alert on forming bar (bar[0]):** MT4's bar[0] is the currently-forming bar; RSI values on bar[0] change every tick. Alerting on bar[0] produces frequent false signals (signal fires, then reverses before bar closes). The spec recommends alerting on bar[1] (most recently closed bar) only — transition from prev state (bar[2]) to current complete state (bar[1]).

4. **Repeated cross within same bar:** If RSI PL whipsaws around TSL multiple times in a single bar's tick stream (only relevant if alerting on bar[0] which this spec discourages), the strict two-bar comparison (`[prev] <= threshold`, `[last] > threshold`) prevents double-firing per bar.

5. **StdDev at low-volatility Bollinger Squeeze:** If RSI_raw is nearly constant for 34 bars (e.g., price completely flat), sigma → 0 and VB_upper ≈ VB_lower ≈ MBL. The bands collapse to a single line. This is not an error — it is the "VB Squeeze" signal that a breakout is imminent.

6. **Alert flooding prevention:** [INFER] The indicator likely implements an internal flag to prevent refiring the same alert on consecutive bars (e.g., store the bar time of last alert per alert type and skip if same bar).

---

## Test cases

1. **Shark Fin Short setup (MMM Book p. 45):**
   - Setup: EURUSD H1, existing down-trend. RSI_PL spikes to 70 (above Level_High=68), then on the next bar closes at 65 (below 68) while VB_upper was at 67.
   - Expected: TDI Hook BEARISH alert fires at the bar where RSI_PL drops below VB_upper near the 68 level. Signal interpretation: "stop hunt complete — resume short."

2. **Blood in the Water Long setup (MMM Book p. 45):**
   - Setup: London open at 07:30 GMT. RSI_PL at 44 (below MBL at 48). On bar close, RSI_PL = 50, MBL = 48. RSI_PL > TSL = 46. The prior 6 bar average high was 1.0865; current bar high is 1.0872.
   - Expected: TDI MBL Cross BULLISH alert fires ("Blood in the Water"). All three conditions met: Green crossed Yellow, Green > Red, price high exceeds average.

3. **VB Squeeze (MMM Book p. 46):**
   - Setup: Asian session, RSI_PL oscillates between 48 and 52 for 20+ bars. sigma drops near 0. VB_upper ≈ VB_lower ≈ MBL ≈ 50.
   - Expected: No alert fires. The spec observes the squeeze state via `VB_upper - VB_lower < 2` (arbitrary threshold). Practitioners watch for the first Signal Cross after a squeeze as a breakout entry.

4. **TDI Hook Bullish at oversold (GBPNZD H1):**
   - Setup: GBPNZD H1 after sharp sell-off. RSI_PL drops to 28 (below Level_Low=32), then on next bar = 34 (above 32) while VB_lower was at 33 on that bar.
   - Expected: TDI Hook BULLISH alert fires. RSI_PL < 40 condition met (34 < 40); VB cross confirmed.

5. **TDI Signal Cross at midline:**
   - Setup: EURUSD M15. RSI_PL = 49, TSL = 51 (prev bar). RSI_PL = 52, TSL = 51 (current bar).
   - Expected: TDI Signal Cross BULLISH alert fires. MMM interpretation: weak mid-zone signal — validate with EMA 5/13 crossover (SM_Crossover_Arrows) before entering.

---

## Port notes

### MQ4 to MQ5 deltas

The MQ5 port of SM_TDI requires these API changes:

- **RSI calculation:** MQ4 `iRSI(symbol, period, length, price, shift)` returns a double directly. MQ5 `iRSI(symbol, period, length, price)` returns a handle; values are read via `CopyBuffer(handle, 0, shift, count, buffer_array)`. The internal RSI_raw array must be populated using `CopyBuffer` calls in `OnCalculate`.
- **Indicator buffers:** `SetIndexBuffer(n, array, INDICATOR_DATA)` in MQ5 vs `SetIndexBuffer(n, array)` in MQ4. Style: MQ4 `SetIndexStyle(n, DRAW_LINE, 0, 1, color)` → MQ5 `PlotIndexSetInteger(n, PLOT_DRAW_TYPE, DRAW_LINE); PlotIndexSetInteger(n, PLOT_COLOR_INDEXES, 1); PlotIndexSetInteger(n, PLOT_LINE_COLOR, 0, color)`.
- **Separate subwindow:** `#property indicator_separate_window` identical in both languages.
- **Alert functions:** `Alert()`, `SendMail()`, `SendNotification()` — identical names in both MQ4 and MQ5.
- **iCustom consumption by EAs:** MQ4 `iCustom("SM_TDI", symbol, period, ..., buffer_index, shift)` → MQ5 requires creating a handle with `iCustom(symbol, period, "SM_TDI", ...)` then reading via `CopyBuffer`.

### Python port

A Python port is trivial using pandas-ta or TA-Lib:

```python
import pandas_ta as ta

df['rsi_raw'] = ta.rsi(df['Close'], length=13)
df['rsi_pl']  = df['rsi_raw'].rolling(2).mean()       # Green
df['tsl']     = df['rsi_raw'].rolling(7).mean()       # Red
df['mbl']     = df['rsi_raw'].rolling(34).mean()      # Yellow
df['sigma']   = df['rsi_raw'].rolling(34).std(ddof=0) # population stddev
df['vb_upper']= df['mbl'] + 1.6185 * df['sigma']     # Blue upper
df['vb_lower']= df['mbl'] - 1.6185 * df['sigma']     # Blue lower
```

Alert detection becomes vectorized pandas `.shift()` comparisons. Plot via matplotlib with five `ax.plot()` calls in a subplots panel below the price chart.

### Backtester integration

TDI maps directly to the Helix signal-filtering layer in `V2/v3_intelligence/`. The Phase 8 RAG learning loop (INFRA-03) records trade-time features; TDI lines (RSI_PL, TSL, MBL, VB position) are primary candidate features for Phase 9 StrategyRouter:

```python
# Signal filter in backtest_hybrid.py:
signal = +1 if (rsi_pl > tsl) and (rsi_pl > 50) else \
         -1 if (rsi_pl < tsl) and (rsi_pl < 50) else 0
```

The TDI Hook pattern (mean-reversion from extreme) maps directly to the daily Z-score mean-reversion strategy validated in Helix v1.0 (Sharpe 2.08 with RAG). The recommended port target is `V2/v3_intelligence/tdi.py` as a Phase 9 router input module. The VB Squeeze condition (`vb_upper - vb_lower < threshold`) is a candidate "low-volatility skip" gate for `backtest_hybrid.py`.

---

## Uncertainty log

- [INFER] StdDev multiplier 1.6185 vs 2.0 — community sources split on this value; the SM binary likely uses one specific value; operator confirmation via MT4 parameter dialog is the definitive resolution
- [INFER] Whether SM_TDI (15,880 bytes) exposes all 5 indicator buffers to EAs via `iCustom` or is visual-only; the larger `!_TDI.ex4` (27,724 bytes) may be the buffer-exposing variant
- [INFER] Whether Green line smooths `iRSI()` output directly (this spec's assumption) or first stores the raw RSI values and applies SMA to that array — community implementations do it both ways; the result is numerically identical
- [INFER] Exact color hex codes for all 5 lines — lime/red/yellow/blue/blue is the universal convention but exact MT4 color constants unverifiable
- [INFER] EnableSignalCrossAlert / EnableMBLCrossAlert / EnableHookAlert default to `true` — could be `false` (alerts off by default); some community TDI releases ship with alerts disabled to avoid noise
- [INFER] Whether the MBL Cross alert requires both (a) Green > Red AND (b) price high confirmation, or just one of them — MMM TDI PDF p. 16 lists both as conditions but the binary may implement only one
- [INFER] Alert repeat prevention logic — whether the indicator guards against refiring the same alert on consecutive bars where the cross condition is still true
- [INFER] Subwindow height / Y-axis minimum-maximum — likely MT4 auto-scale (0 to 100 approximate), but the indicator may set `IndicatorSetDouble(INDICATOR_MINIMUM, 0); IndicatorSetDouble(INDICATOR_MAXIMUM, 100)` explicitly
- [INFER] AlertEmail / AlertPush parameter names — could be `SendEmail`, `SendPush`, or similar
- [INFER] Whether the `!_TDI.ex4` 27,724-byte variant has additional features (e.g., multi-timeframe TDI, additional alert types, or buffer access) — the ~70% size differential implies significant extra code

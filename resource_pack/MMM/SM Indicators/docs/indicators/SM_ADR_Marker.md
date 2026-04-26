# SM_ADR_Marker

## Header

| Field | Value |
|-------|-------|
| Name | SM_ADR_Marker |
| Source filename | `!SM_ADR_Marker.ex4` (also: `!_ADR_Marker.ex4` — 12,720 bytes, identical size, likely the same indicator without the SM_ prefix) |
| Source platform | MT4 (MQL4) |
| Source binary size | 12,720 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 1 — Atomic (no SM dependencies beyond Tier 0) |
| Confidence | Confidence: High |

**Confidence rationale:** The formula `ADR_high = today_open + ADR/2` and `ADR_low = today_open − ADR/2` is confirmed by two independent sources: (1) MMM Book p. 41 ("ADR High and Low — The ADR is normally plotted as an oscillator. It is however difficult to read in this format and Mauro has produced a version which is read on the price chart and provides a high and low value.") and (2) the Helix MQ5 reference implementation `V2/indicators/ADR_Levels.mq5` (landed Phase 8.4 Plan 04 Task 3a, INFRA-04), which implements exactly this formula. Parameter names and cosmetic defaults are `[INFER]` but the formula itself is HIGH confidence.

---

## Purpose

SM_ADR_Marker plots two or three horizontal lines on the main price chart to mark the statistical daily range boundaries for the current trading day. The lines are anchored to the day's opening price: the **ADR-high** line is drawn at `today_open + ADR/2` and the **ADR-low** line at `today_open − ADR/2`, where ADR is the Average Daily Range computed as the mean of (Daily High − Daily Low) over a configurable lookback window (typically 20 days). An optional **midline** is drawn at `today_open` itself.

MMM Book p. 41 explains the rationale: "ADR High and Low — The ADR is normally plotted as an oscillator. It is however difficult to read in this format and Mauro has produced a version which is read on the price chart and provides a high and low value." For MMM practitioners, when price reaches the ADR-high or ADR-low boundary, the day's statistical range has been "used up" — a mean-reversion signal or exhaustion warning. The indicator thus gives traders a concrete, data-grounded expectation of where the day's price action is likely to stall.

The companion indicator `!_ADR_Marker.ex4` (identical 12,720-byte size) is almost certainly the same indicator or an immediate predecessor without the SM_ branding prefix. Both are included in the resource pack.

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| LookbackDays | int | 20 | 5–100 | Number of completed D1 bars to average for the ADR calculation (bar 0 = today's incomplete bar is excluded) | [INFER] — 20 is the MMM-standard ADR lookback; `V2/indicators/ADR_Levels.mq5` also defaults to 20 |
| UseTodayOpen | bool | true | true / false | Anchor lines to today's D1 open price (vs. previous-day midpoint or close) | [INFER] |
| ShowMidline | bool | true | true / false | Whether to draw the today_open midline in addition to the high/low lines | [INFER] — could default false |
| HighColor | color | clrDeepSkyBlue | any | Color of the ADR-high line | [INFER] — MMM-typical palette; `ADR_Levels.mq5` uses cyan/blue |
| LowColor | color | clrOrangeRed | any | Color of the ADR-low line | [INFER] |
| MidColor | color | clrSilver | any | Color of the midline (today_open) | [INFER] |
| LineStyle | int | STYLE_DASH | STYLE_* enum | Line drawing style | [INFER] — could be STYLE_SOLID or STYLE_DOT |
| LineWidth | int | 1 | 1–5 | Line pixel width | [INFER] |
| ShowLabel | bool | true | true / false | Print "ADR(N): X pips" text label at right edge of chart | [INFER] |
| ObjectPrefix | string | "smADR_" | any valid string | Chart object name prefix; all objects created by this indicator share this prefix for bulk-delete on deinit | [INFER] |

---

## Outputs

### Indicator buffers

None. SM_ADR_Marker uses direct `ObjectCreate` calls and exposes no indicator buffer arrays. Per the Helix MQ5 reference: `#property indicator_buffers 0; #property indicator_plots 0` (ADR_Levels.mq5). This means other indicators or EAs cannot read ADR levels via `CopyBuffer` — they must derive the value independently or share it through a GlobalVariable.

### Chart objects

Two or three `OBJ_HLINE` objects on the main price chart:
- `smADR_high` — at price level `today_open + ADR/2` (HighColor)
- `smADR_low` — at price level `today_open − ADR/2` (LowColor)
- `smADR_mid` — at price level `today_open` (MidColor), drawn only when `ShowMidline = true` [INFER]

Plus one optional `OBJ_LABEL` near the right edge or corner of the chart, displaying a formatted string such as "ADR(20): 88 pips". [INFER — exact format]

### Alerts

[INFER] None by default — SM_ADR_Marker is a purely visual marker. Some community variants of the same formula (e.g., ZUP-based ADR indicators) add an alert when price first touches the ADR-high or ADR-low boundary; it is unknown whether this SM variant includes that feature.

---

## Calculation logic

The following steps describe the plausible implementation, consistent with `V2/indicators/ADR_Levels.mq5` (lines 67–84 implement the core ADR formula in MQ5):

1. **On `OnInit` and on each new D1 bar:** Compute `ADR` as the mean of (DailyHigh[i] − DailyLow[i]) for i = 1..LookbackDays, where i = 0 is today's still-open bar (excluded because its range is incomplete).

   ```
   sum_range = 0
   for i = 1 to LookbackDays:
       sum_range += iHigh(symbol, PERIOD_D1, i) - iLow(symbol, PERIOD_D1, i)
   ADR = sum_range / LookbackDays
   ```

2. **Read today's D1 open:** `today_open = iOpen(symbol, PERIOD_D1, 0)`.

3. **Compute ADR boundaries:**
   - `adr_high = today_open + ADR / 2`
   - `adr_low  = today_open − ADR / 2`
   - `adr_mid  = today_open`

4. **Create or update chart objects:** Call `ObjectCreate` (if not existing) or `ObjectMove` (if existing) for each `OBJ_HLINE` at the three price levels. Set color, style, and width per the corresponding inputs.

5. **Refresh trigger:** D1 bar-change OR a periodic 60-second timer. Timer-based refresh ensures the lines redraw promptly if the indicator is applied mid-session after the D1 bar has already opened. `EventSetTimer(60)` is used in the MQ5 idiom (see `ADR_Levels.mq5` line 35). [INFER — exact cadence]

6. **On `OnDeinit`:** Delete all chart objects whose names begin with `ObjectPrefix` to avoid object leakage across indicator loads.

**Bar-iteration model:** Not every-tick. The ADR value changes only on new D1 bars (once per day), so per-tick recomputation would waste CPU and thrash chart objects. D1-bar-change + periodic timer is the expected pattern.

---

## Pseudocode

```
# SM_ADR_Marker — language-neutral imperative pseudocode
# All [INFER] annotations indicate assumptions about exact implementation

function on_init():
    compute_adr_lines()
    set_timer(60)                           # [INFER] 60-second refresh timer

function compute_adr_lines():
    sum_range = 0
    for i in 1..LookbackDays:              # exclude bar[0] (today's open bar)
        sum_range += daily_high(i) - daily_low(i)
    ADR = sum_range / LookbackDays

    today_open = daily_open(0)

    adr_high = today_open + ADR / 2
    adr_low  = today_open - ADR / 2
    adr_mid  = today_open

    upsert_hline(ObjectPrefix + "high", adr_high, HighColor, LineStyle, LineWidth)
    upsert_hline(ObjectPrefix + "low",  adr_low,  LowColor,  LineStyle, LineWidth)

    if ShowMidline:
        upsert_hline(ObjectPrefix + "mid", adr_mid, MidColor, LineStyle, LineWidth)

    if ShowLabel:
        adr_pips = price_to_pips(ADR)      # [INFER] uses SYMBOL_DIGITS to detect 3- vs 5-digit
        label_text = "ADR(" + LookbackDays + "): " + adr_pips + " pips"
        upsert_label(ObjectPrefix + "lbl", label_text)

function on_timer():
    d1_index_now = current_d1_bar_index()
    if d1_index_now != last_d1_index:
        last_d1_index = d1_index_now
        compute_adr_lines()

function on_deinit():
    delete_objects_with_prefix(ObjectPrefix)
    kill_timer()
```

---

## Visual elements

Two (or three) horizontal lines drawn on the **main price chart** (not a subwindow). Default visual style:

- **ADR-high line:** dashed [INFER], deep-sky-blue or cyan, width 1
- **ADR-low line:** dashed [INFER], orange-red, width 1
- **Midline (today_open):** dashed [INFER], silver/gray, width 1 — only when `ShowMidline = true`
- **Right-edge label:** small text such as "ADR(20): 88 pips" anchored to the chart's right margin or top-right corner [INFER — exact position]

Z-order: lines render below price candles (send-to-back). Candles remain readable through the lines. The label renders above all price objects to remain visible.

---

## Dependencies

No mandatory dependencies. The indicator is self-contained for its core calculation.

**Optional dependency:** `sm_gmtoffset` — if the broker's "D1 open" does not align with the calendar midnight the indicator is designed around, reading the `sm_GMTOffset` GlobalVariable from `sm_gmtoffset` allows SM_ADR_Marker to correctly identify "today's" D1 bar regardless of broker server timezone. Without this, on brokers with GMT+3 server time, the D1 bar at `iOpen(symbol, PERIOD_D1, 0)` may represent a different calendar day than the trader expects. [INFER — whether this integration actually exists in the binary]

---

## Edge cases

- **JPY pairs (3-digit symbols):** `Point = 0.001`, not `0.00001`. The pip-conversion in the label must use `SymbolInfoInteger(SYMBOL_DIGITS)` to detect 3-digit vs 5-digit symbols. On USDJPY, 96 pips = 0.960 in price units (not 0.00096). Incorrect pip math produces labels showing "9600 pips" or "0.96 pips" — both wrong.

- **Index symbols (US30, GER40, NAS100):** No concept of "pip". The label should display "ADR(20): X.X points" or suppress the unit label entirely. The `today_open ± ADR/2` formula still produces valid price levels for index instruments. [INFER — whether the indicator handles this case]

- **Insufficient D1 history (first N days after broker history rollover):** If fewer than `LookbackDays` completed D1 bars are available, the indicator should fall back to using however many bars are available. The label may show "ADR(5): X pips — insufficient history" or simply use the available count silently. [INFER — exact fallback behavior]

- **Weekend bar gap:** The D1 bar at index 0 on a Sunday (some brokers open at 22:00 GMT) has an extremely narrow range — often just a few pips. Including it in the ADR lookback artificially deflates the ADR. The indicator should skip "thin" Sunday bars or identify them by day-of-week. [INFER — whether this guard is implemented]

- **Holiday / missing D1 bars (Christmas, New Year):** Some D1 bars in the lookback window may have artificially small ranges. The indicator has no way to distinguish these from genuine narrow-range trading days without an external calendar. Result: ADR is slightly underestimated during holiday-adjacent weeks.

- **Symbol change:** When the chart symbol changes, `OnInit` is called again. Old objects must be deleted first (via `ObjectPrefix`-based cleanup) and the ADR recomputed for the new symbol. If `ObjectPrefix` is the same across symbols, stale objects from the previous symbol may be deleted correctly.

- **Broker server timezone vs trader timezone:** If the broker's "D1 open" is 22:00 GMT but the trader expects 00:00 GMT midnight as the session start, `today_open = iOpen(symbol, PERIOD_D1, 0)` returns the 22:00 GMT open. This can shift the ADR marker zone by up to a few hours of price movement. Reading `sm_gmtoffset` helps align interpretation, but the fix requires mapping to the "correct" D1 start time, which may require reading a custom timeframe or an auxiliary indicator.

---

## Test cases

1. **EURUSD H1, LookbackDays=20, standard 5-digit broker.** Today's D1 open = 1.08500. Mean of last 20 D1 ranges = 88 pips (= 0.00880 in price units). Expected chart objects: `smADR_high` at 1.08940, `smADR_mid` at 1.08500, `smADR_low` at 1.08060. Label: "ADR(20): 88 pips".

2. **USDJPY H1, LookbackDays=20, 3-digit JPY broker.** Today's D1 open = 152.500. Mean of last 20 D1 ranges = 96 pips (= 0.960 in price units, since USDJPY pip = 0.010 and SYMBOL_DIGITS = 3). Expected: `smADR_high` at 153.980, `smADR_low` at 151.020. Label: "ADR(20): 96 pips" (correct pip math via SYMBOL_DIGITS = 3 detection path, not "9600 pips").

3. **GBPNZD H1, first day after broker history rollover (only 5 D1 bars available).** LookbackDays=20 but only 5 bars exist. Expected: ADR computed as mean of 5 bars; lines drawn correctly at `today_open ± ADR/2`; label may show "ADR(5): X pips — insufficient history" or simply "ADR(20): X pips" using 5 bars silently. [INFER — exact fallback label]

---

## Port notes

### MQ4 → MQ5

The MQL4 → MQL5 delta for an indicator that creates chart objects (rather than plotting buffer values) is relatively small:

- `OnInit()` and `OnDeinit()` signatures are identical in name but MQ5 `OnInit` must return `int` (return `INIT_SUCCEEDED`).
- `iHigh`, `iLow`, `iOpen` on `PERIOD_D1` work in both; in MQ5 you must either use the legacy compatibility mode or switch to `CopyHigh`/`CopyLow`/`CopyOpen` with a series handle.
- `ObjectCreate` signature in MQ5 takes an explicit `chart_id` (first argument, pass `0` for the current chart); MQ4 omits it. Example delta: MQ4 `ObjectCreate("smADR_high", OBJ_HLINE, 0, 0, adr_high)` → MQ5 `ObjectCreate(0, "smADR_high", OBJ_HLINE, 0, 0, adr_high)`.
- `EventSetTimer` / `EventKillTimer` are identical in both versions.
- Object cleanup loop: MQ5's `ObjectsTotal(0, 0, -1)` and `ObjectName(0, i, 0, -1)` are the equivalents of MQ4's `ObjectsTotal()` and `ObjectName(i)`. The `ADR_Levels.mq5` cleanup pattern at lines 92–110 of `V2/indicators/ADR_Levels.mq5` is the canonical reference for this indicator — copy its OnInit/OnTimer/OnCalculate skeleton.

**Helix MQ5 reference: `V2/indicators/ADR_Levels.mq5`** (landed Phase 8.4 Plan 04 Task 3a, INFRA-04) implements exactly this formula in MQ5. The OnInit/OnTimer/OnCalculate structure, the ADR formula loop (lines 67–84), and the object prefix–based cleanup (lines 92–110) should be used as the canonical starting point for any MQ5 port of SM_ADR_Marker.

### Python port

Vectorized via pandas. Given a OHLCV DataFrame with D1 resolution:

```python
# Compute ADR
adr = (df_d1['High'] - df_d1['Low']).rolling(LookbackDays).mean().iloc[-1]
today_open = df_d1.iloc[-1]['Open']
adr_high = today_open + adr / 2
adr_low  = today_open - adr / 2

# Visualization (matplotlib)
import matplotlib.pyplot as plt
ax.axhline(adr_high, color='cyan',   linestyle='--', label=f'ADR High ({adr:.5f})')
ax.axhline(adr_low,  color='salmon', linestyle='--', label=f'ADR Low  ({adr:.5f})')
ax.axhline(today_open, color='grey', linestyle='--', label='Today Open')
```

The `compute_adr` helper at `V2/v3_intelligence/adr.py` (landed Phase 8.4 Plan 04, INFRA-03) is the canonical Python implementation — port SM_ADR_Marker against its `compute_adr(pair, timeframe, lookback_days=20) -> float` interface.

### Backtester integration

In `backtest_hybrid.py`, ADR is consumed as a scalar per bar for stop-loss sizing and take-profit anchoring. The existing `compute_adr(pair, timeframe, lookback_days=20) -> float` function already returns the value. A strategy filter derived from SM_ADR_Marker would be:

```python
if (current_price - today_open) > adr / 2:
    signal = "adr_exhaustion_short"  # price has reached statistical daily high
elif (current_price - today_open) < -adr / 2:
    signal = "adr_exhaustion_long"   # price has reached statistical daily low
```

This pattern is consistent with the v1.0 daily Z-score mean-reversion logic already validated in Phase 7.

---

## Uncertainty log

- [INFER] Default `LookbackDays = 20` — MMM-standard ADR lookback convention; `ADR_Levels.mq5` also defaults to 20; the exact binary default is unverifiable
- [INFER] Default `HighColor = clrDeepSkyBlue` — inferred from MMM palette and `ADR_Levels.mq5` color choices; could be clrRed or another color
- [INFER] Default `LowColor = clrOrangeRed` — similarly inferred; could be clrGreen
- [INFER] Default `MidColor = clrSilver` — inferred
- [INFER] `ShowMidline` default true — could default false; midline is optional in some ADR variants
- [INFER] `LineStyle = STYLE_DASH` default — could be STYLE_SOLID or STYLE_DOT
- [INFER] `ObjectPrefix = "smADR_"` — naming convention guess based on other SM indicators' patterns
- [INFER] Refresh cadence (D1-bar-change + 60-second timer) — could be every-tick or every-new-bar-on-current-TF
- [INFER] Label format "ADR(N): X pips" — exact format unverified; could omit the unit, or use "ADR High:" instead
- [INFER] Whether the indicator alerts on ADR-high/low touch — most simple ADR markers don't; some variants do
- [INFER] Whether previous-day ADR markers are also drawn alongside today's
- [INFER] Whether `sm_gmtoffset` GlobalVariable is consumed for D1 boundary alignment
- [INFER] Exact fallback behavior when fewer than LookbackDays D1 bars are available

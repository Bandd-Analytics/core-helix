# SM_Daily_HiLo

## Header

| Field | Value |
|-------|-------|
| Name | SM_Daily_HiLo |
| Source filename | `!SM_Daily_HiLo.ex4` (also: `!_Daily_HiLo.ex4` — 3,004 bytes, a smaller and likely simpler variant) |
| Source platform | MT4 (MQL4) |
| Source binary size | 6,284 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 1 — Atomic (no SM dependencies beyond Tier 0) |
| Confidence | Confidence: High |

**Confidence rationale:** Purpose and calculation are HIGH confidence from MMM Book p. 41 ("Previous HOD/LOD Markers") and the MMM Glossary definition of HOD/LOD. The algorithm — `iHigh(symbol, PERIOD_D1, DaysBack)` and `iLow(symbol, PERIOD_D1, DaysBack)` — is trivially derivable from the indicator's name and is a well-understood pattern used across hundreds of public MT4 indicators. Parameter names, cosmetic defaults, and the ShowCurrentDay optional feature are `[INFER]`. The companion `!_Daily_HiLo.ex4` (3,004 bytes, roughly half the size) is likely an earlier or stripped-down variant of the same concept.

---

## Purpose

SM_Daily_HiLo draws two horizontal lines on the main price chart marking the previous trading day's High (PHOD — Previous High of Day) and Low (PLOD — Previous Low of Day). Optionally, it also tracks and draws the current day's running intraday High and Low as they develop.

MMM Book p. 41 describes the rationale: "The high and low prices from the previous day were used by the market maker to trap volume. It is therefore significant to know how price acts at these levels the following day. These levels will often line up with other support and resistance zones." The MMM Glossary defines HOD and LOD as "the highest and lowest prices within a 24-hour trading period" and notes that identifying the I-HOD (Initial High of Day) and I-LOD (Initial Low of Day) during the first session sweep is central to the MMM market-maker cycle framework.

For MMM traders, when today's price reaches PHOD or PLOD, it triggers evaluation of a potential "stop hunt" scenario: the market maker may be seeking to trigger stops clustered at these visible levels before reversing. The PHOD/PLOD lines provide a persistent, clearly visible reference for this analysis across all timeframes.

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| HighColor | color | clrRed | any | Color of the PHOD (Previous High of Day) line | [INFER] — red is the most common convention for previous high in MT4 indicators |
| LowColor | color | clrLimeGreen | any | Color of the PLOD (Previous Low of Day) line | [INFER] |
| LineStyle | int | STYLE_DASH | STYLE_* enum | Line drawing style | [INFER] |
| LineWidth | int | 1 | 1–5 | Line pixel width | [INFER] |
| ShowLabel | bool | true | true / false | Show "PHOD" / "PLOD" text labels anchored to the right edge of the chart | [INFER] |
| ShowCurrentDay | bool | false | true / false | Additionally draw running HOD / LOD for today's in-progress D1 bar (live tracking) | [INFER] — some variants include this; the size difference between SM_Daily_HiLo (6,284 bytes) and _Daily_HiLo (3,004 bytes) may correspond to this extra feature |
| DaysBack | int | 1 | 1–7 | Which prior day to display (1 = yesterday, 2 = day-before-yesterday, etc.) | [INFER] |
| ObjectPrefix | string | "smHL_" | any valid string | Chart object name prefix for bulk cleanup on deinit | [INFER] |

---

## Outputs

### Indicator buffers

None. SM_Daily_HiLo creates chart objects and has no indicator buffer arrays.

### Chart objects

Static (PHOD/PLOD) objects — redrawn once per D1 bar:
- `smHL_phod` — `OBJ_HLINE` at `iHigh(symbol, PERIOD_D1, DaysBack)` (HighColor)
- `smHL_plod` — `OBJ_HLINE` at `iLow(symbol, PERIOD_D1, DaysBack)` (LowColor)
- `smHL_phod_lbl` — `OBJ_LABEL` at right edge, text "PHOD" (when `ShowLabel = true`) [INFER]
- `smHL_plod_lbl` — `OBJ_LABEL` at right edge, text "PLOD" (when `ShowLabel = true`) [INFER]

Dynamic (current-day running H/L) objects — redrawn on each bar of the active timeframe (when `ShowCurrentDay = true`) [INFER]:
- `smHL_today_h` — `OBJ_HLINE` at today's running high (dotted style to distinguish from PHOD)
- `smHL_today_l` — `OBJ_HLINE` at today's running low (dotted style)

### Alerts

[INFER] None by default. Some variants alert on price-cross of PHOD or PLOD. SM_Daily_HiLo's 6,284-byte size does not suggest a substantial alerting subsystem.

---

## Calculation logic

1. **On `OnInit` and on each new D1 bar change:** Compute the PHOD and PLOD values:
   - `prev_high = iHigh(symbol, PERIOD_D1, DaysBack)`
   - `prev_low  = iLow(symbol, PERIOD_D1, DaysBack)`
   where `DaysBack = 1` selects yesterday's completed D1 bar.

2. **Create or update `OBJ_HLINE`** at `prev_high` and `prev_low`. If the objects already exist (from a previous bar), use `ObjectMove` to update their price coordinates; otherwise call `ObjectCreate`.

3. **Label placement** (when `ShowLabel = true`): Create or update `OBJ_LABEL` objects anchored to the right edge of the chart, with text "PHOD" (HighColor) and "PLOD" (LowColor). [INFER — exact anchor type: ANCHOR_RIGHT or chart-width X coordinate]

4. **Running current-day H/L** (when `ShowCurrentDay = true`): On each new bar of the active timeframe, scan all bars in the current D1 session from session-open to the current bar. Compute `today_high = max(iHigh over those bars)` and `today_low = min(iLow over those bars)`. Upsert two additional dotted `OBJ_HLINE` objects at these levels. These update on every new bar. [INFER — whether this is truly implemented in the binary]

5. **On `OnDeinit`:** Delete all objects with the `ObjectPrefix` prefix.

**Bar-iteration model:** Static PHOD/PLOD — recomputed only on D1 bar change (once per day). Running today H/L — every bar of the active timeframe (e.g., every H1 close). Not every-tick.

---

## Pseudocode

```
# SM_Daily_HiLo — language-neutral imperative pseudocode
# All [INFER] annotations indicate assumptions about the exact implementation

function on_init():
    compute_phod_plod()

function compute_phod_plod():
    prev_high = daily_high(DaysBack)       # iHigh(symbol, PERIOD_D1, DaysBack)
    prev_low  = daily_low(DaysBack)        # iLow(symbol,  PERIOD_D1, DaysBack)

    upsert_hline(ObjectPrefix + "phod", prev_high, HighColor, LineStyle, LineWidth)
    upsert_hline(ObjectPrefix + "plod", prev_low,  LowColor,  LineStyle, LineWidth)

    if ShowLabel:
        upsert_label(ObjectPrefix + "phod_lbl", "PHOD",
                     anchor=right_edge, y_price=prev_high, color=HighColor)
        upsert_label(ObjectPrefix + "plod_lbl", "PLOD",
                     anchor=right_edge, y_price=prev_low,  color=LowColor)

function on_d1_bar_change():
    compute_phod_plod()

function on_new_intratf_bar():                  # fires on each H1/M15/etc. close
    if ShowCurrentDay:
        bars_today = bars_since_d1_open()
        today_high = max(high[0..bars_today])
        today_low  = min(low[0..bars_today])

        upsert_hline(ObjectPrefix + "today_h", today_high,
                     HighColor, STYLE_DOT, 1)   # [INFER] dotted to distinguish from PHOD
        upsert_hline(ObjectPrefix + "today_l", today_low,
                     LowColor,  STYLE_DOT, 1)

function on_deinit():
    delete_objects_with_prefix(ObjectPrefix)
```

---

## Visual elements

Two horizontal dashed lines on the **main price chart** (not a subwindow):

- **PHOD line:** dashed [INFER], red (HighColor), width 1
- **PLOD line:** dashed [INFER], lime-green (LowColor), width 1
- **Today running High/Low (optional):** dotted lines in same colors, visually distinct from the static PHOD/PLOD by the dotted style [INFER]
- **Labels:** small text "PHOD" / "PLOD" at the right edge of the chart, anchored near the respective line Y-coordinates [INFER — exact label anchor]

Z-order: lines are sent to back so candles and other overlays render above them. Labels are sent to front. No subwindow usage.

---

## Dependencies

No mandatory dependencies. The indicator is self-contained for its core calculation.

**Optional dependency:** `sm_gmtoffset` — if the broker's D1 bar boundary does not align with the calendar midnight the indicator assumes, the PHOD/PLOD values may refer to a slightly different date than the trader expects. Reading the `sm_GMTOffset` GlobalVariable from `sm_gmtoffset` allows correct identification of "yesterday" across broker server timezones. [INFER — whether this integration exists in the binary]

---

## Edge cases

- **First trading day after weekend:** `PERIOD_D1[1]` at market open on Monday references Friday's session. Friday's H/L are typically valid references (no unusual weekend behavior), but the lines remain static all of Monday. On some brokers, Sunday's thin open-to-Monday gap generates a very-short D1 bar at index 1 that may not represent "yesterday" the trader intends; using `DaysBack = 2` on Mondays could be a workaround. [INFER — whether the indicator has day-of-week awareness]

- **Holidays (Christmas, New Year, bank holidays):** D1 bars on holiday-adjacent days exist but have very narrow ranges. PHOD/PLOD from a holiday session are unusual reference points. The indicator has no way to detect holidays automatically.

- **JPY pairs and index symbols:** No pip conversion is needed here — PHOD/PLOD are raw price levels used directly as `OBJ_HLINE` price coordinates. The indicator does not compute pip distances, so no SYMBOL_DIGITS adaptation is required for its core function. Labels may optionally show the level in pips from current price, but that is [INFER] and would require JPY-aware pip math if implemented.

- **Broker server timezone vs. trader timezone D1 boundary:** If the broker's D1 bar opens at 22:00 GMT instead of 00:00 GMT midnight, then `iHigh(symbol, PERIOD_D1, 1)` returns the high of the session from 22:00 GMT two evenings ago to 22:00 GMT yesterday evening — not the calendar-day high the trader may expect. The `sm_gmtoffset` helper addresses this but the fix requires identifying the "correct" D1 start time.

- **Sunday open bar (thin bar):** Some brokers generate a very-short D1 bar for Sunday evening (22:00–00:00 GMT). If `DaysBack = 1` on Monday morning, the indicator may refer to this Sunday thin bar as "yesterday." The resulting PHOD/PLOD would be barely above/below the Sunday open. This is a known edge case in all "previous-day high/low" indicator types.

- **Symbol change or timeframe change:** `OnInit` is invoked again. All objects from the previous symbol must be deleted via `ObjectPrefix`-based cleanup before new objects for the new symbol are created.

- **Running HOD/LOD starting time:** For `ShowCurrentDay = true`, the indicator must know when "today" starts in broker time. Without `sm_gmtoffset`, it uses the D1 bar index 0 open time as the session anchor, which may not match the trader's local midnight. [INFER]

---

## Test cases

1. **EURUSD H1 chart, today is Wednesday.** `iHigh(symbol, PERIOD_D1, 1)` = 1.09000, `iLow(symbol, PERIOD_D1, 1)` = 1.08300. Expected chart objects: `smHL_phod` at 1.09000 (red dashed line), `smHL_plod` at 1.08300 (green dashed line). Labels "PHOD" and "PLOD" displayed at the right edge at the respective Y-price anchors.

2. **EURUSD H1 chart, ShowCurrentDay=true.** Today's intraday high (up to the current bar) reaches 1.08950, today's intraday low reaches 1.08550. Two additional dotted lines drawn: `smHL_today_h` at 1.08950, `smHL_today_l` at 1.08550. These update on each new H1 bar close. The dotted style visually distinguishes them from the dashed static PHOD/PLOD.

3. **DaysBack=2 on a Wednesday.** Lines refer to Monday's D1 High and Low (not Tuesday's). `iHigh(symbol, PERIOD_D1, 2)` and `iLow(symbol, PERIOD_D1, 2)` return Monday's values. This allows a trader to compare today to two sessions ago rather than the immediately prior session.

---

## Port notes

### MQ4 → MQ5

The MQ4 → MQ5 delta for SM_Daily_HiLo is minimal:

- `iHigh(symbol, PERIOD_D1, DaysBack)` and `iLow(symbol, PERIOD_D1, DaysBack)` are available in both MQ4 and MQ5 (MQ5 retains these legacy functions under the compatibility layer). In strict MQ5 style, use `CopyHigh` / `CopyLow` with a series handle to fill arrays and index from there.
- `ObjectCreate` in MQ5 requires `chart_id` as the first argument (pass `0` for the current chart). MQ4 omits it: `ObjectCreate("smHL_phod", OBJ_HLINE, 0, 0, prev_high)` → `ObjectCreate(0, "smHL_phod", OBJ_HLINE, 0, 0, prev_high)`.
- `ObjectsTotal()` → `ObjectsTotal(0, 0, -1)` in MQ5 for chart-scoped object count.
- `OnInit` must return `int INIT_SUCCEEDED` in MQ5 vs. `void` in MQ4.
- No timer is needed for this indicator (no periodic refresh required beyond D1 bar-change events), so the MQ5 EventSetTimer / EventKillTimer migration is not relevant here.

### Python port

Trivially vectorized:

```python
# Assuming df_d1 is a DataFrame indexed by date with columns High, Low, Open, Close
prev_high = df_d1.iloc[-2]['High']   # DaysBack=1 → second-to-last completed D1 bar
prev_low  = df_d1.iloc[-2]['Low']

# Visualization
import matplotlib.pyplot as plt
ax.axhline(prev_high, color='red',       linestyle='--', linewidth=1, label='PHOD')
ax.axhline(prev_low,  color='limegreen', linestyle='--', linewidth=1, label='PLOD')
```

For DaysBack > 1, use `df_d1.iloc[-DaysBack - 1]`. For running today H/L, filter the intraday DataFrame to today's date and compute `max(H)` and `min(L)`.

### Backtester integration

PHOD and PLOD are natural breakout and mean-reversion anchors. In `backtest_hybrid.py`:

```python
phod = df_d1.iloc[-2]['High']
plod = df_d1.iloc[-2]['Low']

# Breakout signal
if close > phod and close > prev_close:
    breakout_long_signal = True

# Mean-reversion signal
if close >= phod and rsi > 70:
    fade_short_signal = True
```

Helix's daily Z-score mean-reversion strategy already operates on D1 bars; PHOD/PLOD are derivable from the existing OHLCV data pipeline at zero additional cost. They would be particularly useful as stop-loss anchors (place stop just beyond PHOD when selling) in conjunction with the ADR-based range exhaustion logic from SM_ADR_Marker.

---

## Uncertainty log

- [INFER] Default `HighColor = clrRed` — conventional choice; actual binary may use a different shade
- [INFER] Default `LowColor = clrLimeGreen` — conventional; actual binary unknown
- [INFER] `LineStyle = STYLE_DASH` default — could be STYLE_SOLID
- [INFER] `ShowCurrentDay = false` default — the running intraday H/L feature may or may not exist in the binary; the 6,284-byte size vs 3,004-byte _Daily_HiLo variant hints at the larger binary having extra features, but this is speculative
- [INFER] `ShowLabel = true` default and label text format "PHOD" / "PLOD" vs. "Prev High" / "Prev Low" or numeric price display
- [INFER] `DaysBack = 1` default — most natural choice but some variants default to 2 to skip Sunday thin bars on Monday
- [INFER] `ObjectPrefix = "smHL_"` — naming convention guess
- [INFER] Whether alerts fire on price-cross of PHOD or PLOD
- [INFER] Whether lines extend to the right only (ray) or span the full chart width (both directions)
- [INFER] Whether `sm_gmtoffset` GlobalVariable is consumed for accurate D1 boundary detection

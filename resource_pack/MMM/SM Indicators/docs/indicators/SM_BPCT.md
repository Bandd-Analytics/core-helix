# SM_BPCT

## Header

| Field | Value |
|-------|-------|
| Name | SM_BPCT |
| Source filename | `!SM_BPCT.ex4` |
| Source platform | MT4 (MQL4) |
| Source binary size | 10,868 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 1 — Atomic (no SM dependencies beyond Tier 0) |
| Confidence | Confidence: Low |

**Confidence rationale:** The abbreviation "BPCT" has no authoritative resolution in any MMM/SM source document reviewed (MMM Book, MMM Glossary, MMM Knowledge Base, MMM TDI Tradestation PDF). Three candidate interpretations exist in the broader BTMM/MMM community; this spec proceeds with the most commonly cited one while marking **every behavioral claim** `[INFER:guess]`. The entire spec is a structured placeholder pending confirmation by a human operator who can run the indicator in MT4 and read its parameter labels. Per RESEARCH.md §5.1: "A future operator who runs the indicator in MT4 could resolve this instantly by reading the indicator name in the Inputs tab."

**VALIDATION.md requirement:** This file MUST contain ≥ 5 `[INFER:guess]` tags per the Manual-Only Verifications table ("BPCT confidence flag" row).

---

## Purpose

**Abbreviation status: UNRESOLVED.** The letters "BPCT" do not map to any named indicator, technique, or concept in the reviewed MMM/SM documentation corpus. Three candidate interpretations are considered, listed in order of assessed plausibility:

### Candidate Interpretation 1: Bars Per Cycle Tracker

`[INFER:guess]` SM_BPCT counts the number of bars elapsed since a key cycle event (e.g., the session HOD/LOD, the D1 open, or the last MMM market-maker accumulation phase). It displays this count as a numeric label on the chart or as a histogram bar in a subwindow. This fits the MMM "3-day cycle" methodology, where practitioners track the elapsed time since the last significant swing to estimate when the next cycle phase is due. Plausibility: **medium** — the indicator name "Bars Per Cycle" is intuitive given the MMM cycle-counting vocabulary.

### Candidate Interpretation 2: Beat-the-Market-Maker Pip Count Tracker

`[INFER:guess]` SM_BPCT displays the cumulative pip movement from the current session open (or day open) to the current price. The "Beat the Market Maker" branding (which SM and BTMM indicators draw from directly) makes "Beat-the-MM Pip Count" plausible. The indicator would show something like "+42 pips from session open" as a running label or histogram. Plausibility: **medium** — directly references the core BTMM brand phrase.

### Candidate Interpretation 3: Buy/Sell Pressure Candle Tracker (Working Hypothesis)

`[INFER:guess]` SM_BPCT colors candles or draws a histogram based on computed buying vs. selling pressure. "Pressure" is typically derived from the relationship between the candle body direction (close vs. open), body size, and volume or tick volume. A net-bullish bar has positive pressure; net-bearish has negative pressure. This is the most common interpretation in public BTMM Forex Factory forum discussions of the SM indicator suite. The 10,868-byte binary size is consistent with a drawing-plus-calculation indicator of moderate complexity (more than a simple line drawing, less than the 43KB session-box overlay).

**This spec proceeds with Candidate Interpretation 3 as the working hypothesis.** Every claim is `[INFER:guess]`. If this interpretation is incorrect, the entire Calculation logic, Pseudocode, and Outputs sections below must be rewritten from scratch once the abbreviation is resolved.

---

## Inputs / Parameters

All rows in this table are `[INFER:guess]` — no source document confirms any parameter name, type, or default for SM_BPCT.

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| Period | int | 14 | 5–100 | Lookback period for pressure smoothing calculation | [INFER:guess] — 14 is a common default for oscillator-type indicators; unverified |
| BullColor | color | clrLime | any | Color for bullish-pressure histogram bars or candle coloring | [INFER:guess] |
| BearColor | color | clrRed | any | Color for bearish-pressure histogram bars or candle coloring | [INFER:guess] |
| NeutralColor | color | clrGray | any | Color for near-zero / neutral pressure | [INFER:guess] |
| DrawMode | string | "Histogram" | "Histogram" / "ColorCandles" / "Label" | How the output is displayed — subwindow histogram, main-chart candle coloring, or text label | [INFER:guess] |
| UseVolume | bool | true | true / false | Whether to weight pressure by tick volume | [INFER:guess] — if interpretation #2 (Pip Count) is correct, this parameter does not exist |
| SubwindowMode | bool | true | true / false | Render in a subwindow (true) vs. overlay on the main price chart (false) | [INFER:guess] |

---

## Outputs

### Indicator buffers

`[INFER:guess]` One indicator buffer containing the smoothed pressure index, normalized to approximately [-1, +1]. If `DrawMode = "Histogram"`, this buffer is drawn as a histogram in a subwindow. If `DrawMode = "ColorCandles"`, the buffer controls candle coloring on the main chart via `OBJ_RECTANGLE` overlays per bar.

### Chart objects

`[INFER:guess]` When `SubwindowMode = true`: histogram bars in the subwindow (no persistent `OBJ_*` chart objects needed — uses the indicator buffer drawing system). When `SubwindowMode = false`: one `OBJ_RECTANGLE` or color overlay per candle in the main chart window. No labels are expected by default.

### Alerts

`[INFER:guess]` None. SM_BPCT at 10,868 bytes does not appear large enough to include a substantial alerting subsystem on top of the calculation and drawing code. Some community variants of pressure-candle indicators do alert on sign-change (pressure flipping from positive to negative), but this is unverified for SM_BPCT.

---

## Calculation logic

The following calculation is presented as the most-likely implementation under Candidate Interpretation 3 (Buy/Sell Pressure Candle Tracker). **All steps are `[INFER:guess]`.** If the interpretation is wrong, this entire section is incorrect.

1. For each bar i in the calculation range:
   - Compute the candle body: `body[i] = close[i] - open[i]` (positive for bullish, negative for bearish).
   - Normalize by volume: `pressure_raw[i] = body[i] × volume[i] / max_vol_window` where `max_vol_window = max(volume[i-Period..i])`. This scales pressure to [-1, +1] approximately when volume is at its rolling maximum.
   - If `UseVolume = false`: `pressure_raw[i] = body[i] / (high[i] - low[i] + epsilon)` (body fraction of total bar range, also bounded [-1, +1]).

2. Smooth: `pressure[i] = SMA(pressure_raw, Period, i)` — a simple moving average reduces bar-to-bar noise and produces a cleaner histogram shape.

3. **Draw output** based on `DrawMode`:
   - `"Histogram"`: Set `buffer[i] = pressure[i]`. Let the indicator system draw it as `DRAW_HISTOGRAM` in a subwindow. Color selection: green bar if `pressure[i] > 0`, red bar if `pressure[i] < 0`, gray if near zero (within a small threshold).
   - `"ColorCandles"`: For each bar, create or update an `OBJ_RECTANGLE` spanning the candle body, colored by sign of `pressure[i]`.
   - `"Label"`: Write a text label in the corner displaying the current pressure value as a percentage or raw decimal.

4. Bar-iteration model: `[INFER:guess]` Every-bar (not every-tick). The `prev_calculated` optimization standard in MQ4/MQ5 is used to only recompute bars since the last calculation.

---

## Pseudocode

```
# SM_BPCT — language-neutral imperative pseudocode
# [INFER:guess] — entire pseudocode is based on Candidate Interpretation 3
# (Buy/Sell Pressure Candle Tracker). If the abbreviation resolves differently,
# this pseudocode must be discarded and rewritten.

GLOBAL: pressure_raw = array(size=rates_total)
        pressure     = array(size=rates_total)

function on_calculate(rates_total, prev_calculated):
    start = max(prev_calculated - 1, Period + 1)

    for i in start..rates_total - 1:
        body   = close[i] - open[i]

        if UseVolume:
            vol_window = volume[max(0, i-Period)..i]
            max_vol    = max(vol_window) + 1e-9   # avoid divide-by-zero
            pressure_raw[i] = (body * volume[i]) / max_vol
        else:
            bar_range  = high[i] - low[i] + 1e-9
            pressure_raw[i] = body / bar_range

        # Smooth over Period bars
        pressure[i] = sma(pressure_raw, Period, i)

        if SubwindowMode or DrawMode == "Histogram":
            # Buffer-based histogram drawing handled by indicator system
            set_buffer_value(0, i, pressure[i])
        else:
            bar_color = BullColor    if pressure[i] >  threshold else
                        BearColor    if pressure[i] < -threshold else
                        NeutralColor
            color_candle(i, bar_color)   # [INFER:guess] via OBJ_RECTANGLE or buffer coloring
```

---

## Visual elements

`[INFER:guess]` Under Candidate Interpretation 3 with `DrawMode = "Histogram"` and `SubwindowMode = true`:

- A subwindow below the main price chart displays green/red histogram bars oscillating around a central zero line.
- Green bars (BullColor) indicate net buying pressure; red bars (BearColor) indicate net selling pressure.
- Bar height corresponds to the magnitude of the smoothed pressure index.
- A horizontal zero line divides the subwindow.
- Z-order: subwindow renders separately from the main chart; candles are unaffected.

`[INFER:guess]` With `DrawMode = "ColorCandles"` and `SubwindowMode = false`:
- Candles on the main price chart are overlaid with colored rectangles — no separate subwindow.
- This produces an appearance similar to Heiken-Ashi coloring or the `!Heiken_Ashi.ex4` companion indicator.

---

## Dependencies

`[INFER:guess]` None — SM_BPCT is likely self-contained. It is possible that the indicator reads `sm_WorkTime` to restrict the pressure calculation to active-session bars only (filtering out Asian session low-volume noise), but this is speculative and not derivable from the binary filename or size.

---

## Edge cases

- **Symbols with zero or constant tick volume** (some forex brokers report 0 for volume on all bars): If `UseVolume = true` and volume is zero or constant, the pressure formula degenerates — `max_vol` is zero, causing division by zero. The implementation should fall back to body-fraction mode (`pressure_raw = body / bar_range`) when `volume == 0`. `[INFER:guess]` whether this guard is implemented.

- **First Period bars:** The SMA(Period) smoothing requires at least Period bars. For bars i < Period, `pressure[i]` should be set to 0 or EMPTY_VALUE, and no histogram bar or candle color should be drawn. `[INFER:guess]`

- **Very narrow-range bars (Doji candles):** `body ≈ 0`, so `pressure_raw ≈ 0` → neutral color. The `bar_range` denominator in the fallback formula avoids division by zero only if `epsilon > 0` is added.

- **Large gap bars (weekend open, NFP spike):** A single extremely large bar body can dominate the pressure calculation for `Period` subsequent bars via the rolling average, producing a sustained bullish or bearish histogram even during subsequent consolidation. This is a characteristic limitation of momentum-type smoothed oscillators.

- **Session gaps (Sunday open):** Volume on Sunday open bars is typically negligible. If `UseVolume = true`, the Sunday bar's near-zero volume would produce a near-zero pressure reading, which is correct behaviorally.

- **Symbol/timeframe change:** `prev_calculated = 0` triggers a full recompute from bar 0. All buffer values and chart objects from the prior symbol must be cleared.

---

## Test cases

All test cases are `[INFER:guess]` — they describe expected behavior IF Candidate Interpretation 3 (pressure candle tracker) is correct.

1. `[INFER:guess]` **EURUSD H1 in a sustained uptrend session** (e.g., London open breakout with consecutive bullish bars, each with above-average volume). Expected: histogram bars are consistently green and rising in magnitude over Period bars. The smoothed pressure index climbs toward +0.5 or higher.

2. `[INFER:guess]` **Sharp NFP reversal (large bearish spike followed by recovery):** The spike bar has a large negative body and high volume → `pressure_raw` strongly negative. The SMA then blends this down over the next Period bars. Histogram shows one tall red bar followed by gradually recovering bar heights as the SMA incorporates subsequent smaller-body bars.

3. `[INFER:guess]` **Doji-only consolidation sequence** (8-10 Doji bars with near-zero bodies): `pressure_raw ≈ 0` for each bar → `pressure ≈ 0` after the SMA catches up. Histogram bars near zero, colored with NeutralColor (gray). No directional signal.

---

## Port notes

### MQ4 → MQ5

`[INFER:guess]` Histogram indicator in MQ4 vs MQ5:
- MQ4: `SetIndexStyle(0, DRAW_HISTOGRAM); SetIndexBuffer(0, pressure);` — sets buffer 0 as a histogram drawn in the subwindow.
- MQ5: `PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_HISTOGRAM); SetIndexBuffer(0, pressure, INDICATOR_DATA);` — equivalent MQ5 syntax.
- Volume access: MQ4 uses `iVolume(symbol, period, i)` or the `Volume[]` series; MQ5 uses `iTickVolume` handle + `CopyTickVolume`, or the legacy `iVolume` compatibility function.
- `OnCalculate` signature differs: MQ4 receives `int rates_total, int prev_calculated, datetime time, ...` as separate arrays; MQ5 uses `const int rates_total, const int prev_calculated, const datetime& time[], const double& open[], ...` with `const` reference arrays.
- If `DrawMode = "ColorCandles"` uses `OBJ_RECTANGLE`, the ObjectCreate API change (add `chart_id=0` as first argument) applies.

### Python port

```python
import pandas as pd

def compute_bpct(df: pd.DataFrame, period: int = 14, use_volume: bool = True) -> pd.Series:
    # [INFER:guess] — implement Candidate Interpretation 3
    df = df.copy()
    df['body'] = df['Close'] - df['Open']

    if use_volume and df['Volume'].max() > 0:
        rolling_max_vol = df['Volume'].rolling(period).max().replace(0, 1e-9)
        df['pressure_raw'] = df['body'] * df['Volume'] / rolling_max_vol
    else:
        bar_range = (df['High'] - df['Low']).replace(0, 1e-9)
        df['pressure_raw'] = df['body'] / bar_range

    df['pressure'] = df['pressure_raw'].rolling(period).mean()
    return df['pressure']
```

For visualization: `df['pressure'].plot(kind='bar', color=...)` or matplotlib bar chart with per-bar color assignment.

### Backtester integration

`[INFER:guess]` If Candidate Interpretation 3 is confirmed, SM_BPCT could serve as a momentum/regime bias filter in `backtest_hybrid.py`:

```python
pressure = compute_bpct(df, period=14)
if pressure.iloc[-1] > 0.2:
    regime = "bullish_pressure"
elif pressure.iloc[-1] < -0.2:
    regime = "bearish_pressure"
else:
    regime = "neutral"
```

This would complement the existing Hurst exponent regime detection in Helix v2.0 by adding a short-term intrabar momentum signal. However, ALL of this is contingent on the abbreviation resolving to interpretation #3. Until confirmed, SM_BPCT should NOT be wired into any production backtest logic.

---

## Uncertainty log

- [INFER:guess] BPCT abbreviation expansion — three candidate interpretations exist: (1) Bars Per Cycle Tracker, (2) Beat-the-MM Pip Count Tracker, (3) Buy/Sell Pressure Candle Tracker. This spec proceeds with interpretation #3 as the working hypothesis because it is most commonly cited in BTMM community forums. A future operator who runs the indicator in MT4 and reads the parameter dialog can resolve this instantly.
- [INFER:guess] `Period = 14` default — common oscillator default, entirely unverified for this binary
- [INFER:guess] Volume-weighted body pressure formula — the calculation logic is entirely speculative; if interpretation #1 (Bars Per Cycle) is correct, the calculation reduces to a bar counter; if interpretation #2 (Pip Count), it reduces to cumulative pip distance from session open
- [INFER:guess] `DrawMode = "Histogram"` default — the indicator could equally draw colored candles on the main chart; the binary size (10,868 bytes) is consistent with either approach
- [INFER:guess] `SubwindowMode = true` default — placement in a subwindow vs. main chart overlay is unverified
- [INFER:guess] `BullColor / BearColor / NeutralColor` defaults — the green/red/gray palette is the most common convention for MT4 oscillator/pressure indicators but is not confirmed for this binary
- [INFER:guess] Whether alerts are supported — likely not, but unverified
- [INFER:guess] Whether `sm_WorkTime` session filtering is integrated — unknown; no dependency link derivable from the binary filename alone
- [INFER] If interpretation #1 (Bars Per Cycle) is correct instead, the entire Calculation logic, Pseudocode, Outputs, and Visual elements sections are wrong — alternative pseudocode would count bars since the last HOD/LOD or D1 open and display as a label/histogram; the spec would need a complete rewrite
- [INFER] If interpretation #2 (Pip Count) is correct, the calculation reduces to `pips_from_session_open = (current_price - session_open) / pip_size`; also a complete rewrite

**Recommendation to the future spec re-writer:** Once an operator runs `!SM_BPCT.ex4` in MT4 and reads the parameter names in the indicator Inputs tab, the abbreviation will be immediately resolved. This entire spec should then be rewritten with verified semantics. The current document is a structured placeholder for the highest-uncertainty Tier 1 indicator — it establishes the template skeleton and acknowledges the gap explicitly so that a future reviewer knows exactly what remains uncertain and why.

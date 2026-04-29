# SM_PivotPoints

## Header

| Field | Value |
|-------|-------|
| Name | SM_PivotPoints |
| Source filename | `!SM_PivotPoints.ex4` |
| Source platform | MT4 (MQL4) |
| Source binary size | 15,684 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 2 — Composite (may depend on sm_gmtoffset for day-boundary detection) |
| Confidence | Confidence: High |

**Confidence rationale:** The standard floor pivot formulas (PP, R1-R3, S1-S3) are an industry standard with zero ambiguity — HIGH confidence for the formula layer. Steve Mauro's MMM-specific addition — the M1/M2/M3/M4 mid-pivot system — is documented in MMM Book pp. 42-43 with specific text describing how to use these levels to predict HOD/LOD placement. The mid-pivot formulas ((S2+S1)/2 etc.) are straightforward midpoints — also HIGH confidence for the extension. The MMM-specific behavioral interpretation ("red daily candle → M1/M3 day") is cited from MMM Book pp. 42-43 and is HIGH confidence as a source citation. Parameter names, color defaults, and ancillary features (weekly pivots, label positions) are [INFER]. Overall: **Confidence: High** with [INFER] on cosmetic parameters.

---

## Purpose

SM_PivotPoints is a daily (and optionally weekly) pivot point calculator that draws PP, R1, R2, R3, S1, S2, S3, and the MMM-specific mid-pivot levels M1-M4 as horizontal lines on the main price chart. Pivot levels are the most widely used institutional support/resistance reference in short-term forex trading — market makers place limit orders and stop clusters at these pre-calculated levels, making them structural zones where the MMM "trap move" (stop hunt) often initiates and reverses.

The MMM Book (pp. 42-43) details the M1/M2/M3/M4 system as a Mauro-specific overlay on standard floor pivots: "If the previous day's candle was red then this indicates that today might be an M1/M3 day (HOD likely to land between S2 and S1 / PP or between PP and R1). If the previous day's candle was green then this indicates that today might be an M2/M4 day (HOD likely to land between S1 and PP / between R1 and R2)." This predictive use of mid-pivots to anticipate the day's High/Low is a Mauro-proprietary technique not found in generic pivot indicators.

MMM Book p. 42 also notes: "It can be more accurate if it is coupled with an ADR indicator which tells us the average daily trading range of the last 2 weeks." SM_PivotPoints and SM_ADR_Marker are therefore companion indicators — pivots provide the STRUCTURAL levels, ADR provides the RANGE expectation.

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| ShowDaily | bool | true | true / false | Draw daily pivot levels (PP, R1-R3, S1-S3, M1-M4) | [INFER] — daily pivots are always shown in typical pivot indicators |
| ShowWeekly | bool | false | true / false | Draw weekly pivot levels (additional set of lines) | [INFER] — weekly likely optional/off-by-default |
| ShowMidPivots | bool | true | true / false | Draw the four MMM-specific M1-M4 mid-pivot lines | [INFER] — MMM Book pp. 42-43 confirms MMM's heavy use of mid-pivots; likely on by default |
| PivotColor | color | clrWhite | any | Color of the central PP line | [INFER] |
| R1Color | color | clrRed | any | Color of R1 (first resistance) | [INFER] |
| R2Color | color | clrTomato | any | Color of R2 (second resistance, lighter shade) | [INFER] |
| R3Color | color | clrOrangeRed | any | Color of R3 (third resistance) | [INFER] |
| S1Color | color | clrLime | any | Color of S1 (first support) | [INFER] |
| S2Color | color | clrGreen | any | Color of S2 (second support, darker shade) | [INFER] |
| S3Color | color | clrDarkGreen | any | Color of S3 (third support) | [INFER] |
| MidColor | color | clrYellow | any | Color of M1-M4 mid-pivot lines | [INFER] — yellow-dotted lines are the common MMM mid-pivot convention |
| WeeklyColor | color | clrSilver | any | Color of weekly pivot levels (if ShowWeekly=true) | [INFER] |
| ResetTimeGMT | int | 22 | 0–23 | GMT hour at which the "new day" starts for pivot calculation (17:00 ET = 22:00 GMT per MMM Book convention) | [INFER] — 22 is the standard forex close/open used by MMM; could be 0 for midnight-server brokers |
| LineStyle | int | STYLE_SOLID | STYLE_* enum | Drawing style for standard pivot lines (PP, R, S) | [INFER] |
| MidLineStyle | int | STYLE_DOT | STYLE_* enum | Drawing style for mid-pivot lines M1-M4 | [INFER] — dotted to visually distinguish from solid standard levels |
| LineWidth | int | 1 | 1–3 | Line pixel width for all pivot lines | [INFER] |
| ShowLabels | bool | true | true / false | Print "PP", "R1", "R2", "S1", "M1" etc. labels at the right edge of the chart | [INFER] |
| ObjectPrefix | string | "smPP_" | any valid string | Prefix for all chart objects; used for bulk-delete on deinit | [INFER] |

---

## Outputs

### Indicator buffers

None. SM_PivotPoints uses `ObjectCreate` calls to draw horizontal lines directly on the chart. It exposes no indicator buffer arrays. Other indicators or EAs cannot read pivot levels via `CopyBuffer` — they must compute independently or share via GlobalVariable.

### Chart objects

When `ShowMidPivots = true` and `ShowLabels = true` (default assumption): **up to 22 chart objects** per active period:
- 7 standard pivot `OBJ_HLINE`: `smPP_PP`, `smPP_R1`, `smPP_R2`, `smPP_R3`, `smPP_S1`, `smPP_S2`, `smPP_S3`
- 4 mid-pivot `OBJ_HLINE`: `smPP_M1`, `smPP_M2`, `smPP_M3`, `smPP_M4`
- 11 matching `OBJ_LABEL` at the right chart edge (one label per line)

If `ShowWeekly = true`, an additional 7-11 OBJ_HLINE + labels with weekly prefix.

### Alerts

[INFER] None by default. The indicator is a pure drawing tool. Some community pivot variants add an alert when price crosses through PP or R1/S1; whether SM_PivotPoints includes this is unknown from the binary alone.

---

## Calculation logic

All pivot formulas use the **previous period's** High (H), Low (L), and Close (C). For daily pivots, this is the previous day's OHLC bar on the D1 timeframe, with the day boundary at `ResetTimeGMT` (default 22:00 GMT = 17:00 ET, the standard forex "New York Close").

1. **On `OnInit` and on each D1-bar-change** (detected via timer or new-bar check at ResetTimeGMT):

2. **Read previous day's data:**
   ```
   H = iHigh(symbol, PERIOD_D1, 1)
   L = iLow(symbol, PERIOD_D1, 1)
   C = iClose(symbol, PERIOD_D1, 1)
   ```
   Index 1 refers to the most recently completed D1 bar.

3. **Compute standard pivot levels:**
   ```
   PP = (H + L + C) / 3
   R1 = 2 * PP - L
   R2 = PP + (H - L)
   R3 = H + 2 * (PP - L)
   S1 = 2 * PP - H
   S2 = PP - (H - L)
   S3 = L - 2 * (H - PP)
   ```

4. **Compute MMM-specific mid-pivot levels** (from MMM Book pp. 42-43):
   ```
   M1 = (S2 + S1) / 2    # Between S2 and S1
   M2 = (S1 + PP) / 2    # Between S1 and PP
   M3 = (PP + R1) / 2    # Between PP and R1
   M4 = (R1 + R2) / 2    # Between R1 and R2
   ```
   These mid-points bisect the four primary price zones. Per MMM Book: a red prior-day candle predicts HOD landing near M1 or M3; a green prior-day candle predicts HOD near M2 or M4.

5. **Draw/update chart objects:** For each level, call `ObjectCreate` if the object does not exist, then `ObjectSetDouble(0, name, OBJPROP_PRICE, level)` if it does. Set object color, style, and width per the corresponding inputs.

6. **Draw labels** (if ShowLabels=true): Place `OBJ_LABEL` near the right edge with the level name ("PP", "R1", "M1", etc.) anchored to the corresponding horizontal line price.

7. **Refresh trigger:** D1 bar-change detection OR periodic timer. At minimum, recalculate once per day when the D1 bar advances. [INFER] A 60-second timer may supplement this for mid-day symbol changes.

8. **Weekly pivots** (if ShowWeekly=true): Same formula applied to the previous W1 bar (PERIOD_W1, index 1). Weekly pivot lines are drawn with WeeklyColor and a different prefix (e.g., `smPP_W_PP`).

9. **On `OnDeinit`:** Delete all objects whose names begin with `ObjectPrefix` ("smPP_").

**Bar-iteration model:** Not every-tick. Pivot values only change once per day (at ResetTimeGMT). The indicator recalculates on D1-bar-change and does NOT iterate over current-chart bars — it creates static horizontal lines that persist until the next daily reset.

---

## Pseudocode

```
# SM_PivotPoints — language-neutral imperative pseudocode
# Source: Standard floor pivot formula (industry standard) +
#         MMM Book pp. 42-43 (M1-M4 mid-pivot extension)

CONST RESET_HOUR_GMT = 22     # 17:00 ET = 22:00 GMT (MMM convention) [INFER]
GLOBAL current_pivot_date = 0 # Track last computed date to avoid recompute
GLOBAL prefix = "smPP_"

function on_init():
    set_timer(60)  # 60-second refresh [INFER — could be 30 or 120]
    compute_and_draw_pivots()

function on_timer():
    today_reset = today_date_at_hour(RESET_HOUR_GMT)
    if current_time_utc() >= today_reset and current_pivot_date < today_date():
        compute_and_draw_pivots()
        current_pivot_date = today_date()

function compute_and_draw_pivots():
    H = prev_day_high()
    L = prev_day_low()
    C = prev_day_close()

    PP = (H + L + C) / 3
    R1 = 2 * PP - L
    R2 = PP + (H - L)
    R3 = H + 2 * (PP - L)
    S1 = 2 * PP - H
    S2 = PP - (H - L)
    S3 = L - 2 * (H - PP)

    upsert_hline(prefix + "PP", PP, PivotColor, STYLE_SOLID, 2)
    upsert_hline(prefix + "R1", R1, R1Color,    STYLE_SOLID, 1)
    upsert_hline(prefix + "R2", R2, R2Color,    STYLE_SOLID, 1)
    upsert_hline(prefix + "R3", R3, R3Color,    STYLE_SOLID, 1)
    upsert_hline(prefix + "S1", S1, S1Color,    STYLE_SOLID, 1)
    upsert_hline(prefix + "S2", S2, S2Color,    STYLE_SOLID, 1)
    upsert_hline(prefix + "S3", S3, S3Color,    STYLE_SOLID, 1)

    if ShowMidPivots:
        M1 = (S2 + S1) / 2   # below S1 zone: predicts HOD on red prior-day [MMM Book p.42]
        M2 = (S1 + PP) / 2   # S1-PP zone: predicts HOD on green prior-day
        M3 = (PP + R1) / 2   # PP-R1 zone: mid-pivot for M1/M3 day scenario
        M4 = (R1 + R2) / 2   # R1-R2 zone: upper extension
        upsert_hline(prefix + "M1", M1, MidColor, STYLE_DOT, 1)
        upsert_hline(prefix + "M2", M2, MidColor, STYLE_DOT, 1)
        upsert_hline(prefix + "M3", M3, MidColor, STYLE_DOT, 1)
        upsert_hline(prefix + "M4", M4, MidColor, STYLE_DOT, 1)

    if ShowLabels:
        for each (name, price) in [("PP", PP), ("R1", R1), ("R2", R2), ("R3", R3),
                                    ("S1", S1), ("S2", S2), ("S3", S3),
                                    ("M1", M1), ("M2", M2), ("M3", M3), ("M4", M4)]:
            upsert_label(prefix + name + "_lbl", name, price, anchor=right_edge)

    if ShowWeekly:
        H_w = prev_week_high(); L_w = prev_week_low(); C_w = prev_week_close()
        compute_and_draw_standard_pivots(H_w, L_w, C_w, prefix="smPP_W_", color=WeeklyColor)

function on_deinit():
    delete_all_objects_with_prefix(prefix)
```

---

## Visual elements

**Main price chart (no subwindow).** All pivot lines are horizontal and span the full width of the chart from left to right (infinite extend both directions, consistent with OBJ_HLINE behavior).

**Default visual layout (top to bottom by price, all [INFER] for exact shades):**
- R3 — orange-red solid thin line, faint
- R2 — tomato/orange solid thin line
- R1 — red solid thin line, more prominent
- PP — white solid medium line (widest, as the central reference)
- S1 — lime/bright green solid thin line
- S2 — green darker solid thin line
- S3 — dark green solid thin line, faint
- M1-M4 — yellow dotted fine lines between the standard levels above

**Labels:** Right-side edge labels in matching colors: "R3", "R2", "R1", "PP", "S1", "S2", "S3", "M1"-"M4". Standard labels align with the line price on the Y-axis.

**Z-order:** Price chart. The horizontal lines are drawn at the back of chart objects layer (below candlesticks). Labels are in front.

---

## Dependencies

[INFER] **sm_gmtoffset** (optional) — to align the `ResetTimeGMT` boundary correctly with the broker's server time. If the broker's server time differs from GMT, the indicator needs the GMT offset to correctly identify when the D1 bar changes at 22:00 GMT. Without sm_gmtoffset, the indicator would need `ResetTimeGMT` manually set to the broker-server-time equivalent (e.g., for a GMT+2 broker, set ResetTimeGMT=0 to represent the 00:00 server time that corresponds to 22:00 GMT).

No dependencies on Tier 1 indicators (SM_ADR_Marker, SM_Daily_HiLo). The relationship between these indicators is conceptual (both used together in MMM chart setup), not programmatic.

---

## Edge cases

1. **Broker day boundary mismatch:** Brokers using midnight server time (GMT+0) will produce D1 bars with boundaries at 00:00 GMT, not 22:00 GMT (the MMM/New York Close convention). If ResetTimeGMT is not adjusted, the pivots are computed from a different daily bar than the one traders see. The ResetTimeGMT input is the primary mitigation — users must configure it to match their broker's daily candle close.

2. **Sunday-Monday rollover:** Many brokers open Sunday at 22:00 GMT with a very thin 2-3 hour "Sunday candle." Using this candle as D1[1] would produce incorrect pivot levels. [INFER] The indicator likely skips Sunday bars: if `DayOfWeek(iTime(PERIOD_D1, 1)) == SUNDAY`, fall back to the previous Friday bar (D1[2]).

3. **Holiday / missing daily bar:** Some brokers close at 22:00 and do not produce a bar on certain holidays (e.g., Christmas). If D1[1] has no data, the indicator should use the most recent non-empty D1 bar.

4. **DST transitions:** The 22:00 GMT boundary may shift by ±1 hour depending on US DST (EDT vs EST) and broker DST policy. If ResetTimeGMT is hard-coded to 22, the pivot reset may fire one hour early or late during DST transitions. Users in DST-affected regions should verify ResetTimeGMT seasonally.

5. **Weekly pivots (ShowWeekly=true):** The "previous week" is typically defined as Sunday-to-Friday. W1 bar index 1 captures this. However, brokers that use a Monday-to-Friday week may not have a W1 bar matching this boundary — manual verification recommended.

6. **Symbol change:** `OnInit` fires; all old objects (prefix-based) are deleted and new pivot levels computed for the new symbol.

7. **Zero-range day (H = L):** Theoretical edge case where a currency pair has no intraday range (e.g., a system error day). In this case `R2 = PP + 0 = PP`, `S2 = PP - 0 = PP` — all levels collapse to PP. Not an error; the indicator should draw normally (all overlapping lines).

---

## Test cases

1. **Standard daily pivot calculation (EURUSD H1):**
   - Input: Previous day H=1.0900, L=1.0830, C=1.0870
   - Expected:
     - PP = (1.0900 + 1.0830 + 1.0870) / 3 = **1.0867**
     - R1 = 2 × 1.0867 − 1.0830 = **1.0904**
     - R2 = 1.0867 + (1.0900 − 1.0830) = **1.0937**
     - R3 = 1.0900 + 2 × (1.0867 − 1.0830) = **1.0974**
     - S1 = 2 × 1.0867 − 1.0900 = **1.0834**
     - S2 = 1.0867 − (1.0900 − 1.0830) = **1.0797**
     - S3 = 1.0830 − 2 × (1.0900 − 1.0867) = **1.0764**
     - M1 = (1.0797 + 1.0834) / 2 = **1.0816**
     - M2 = (1.0834 + 1.0867) / 2 = **1.0851**
     - M3 = (1.0867 + 1.0904) / 2 = **1.0886**
     - M4 = (1.0904 + 1.0937) / 2 = **1.0921**
   - Verify: 7 standard OBJ_HLINE + 4 mid-pivot OBJ_HLINE drawn at these exact prices; labels visible at right edge.

2. **MMM M1/M3 day prediction (red prior candle):**
   - Input: Previous day was a red candle (open=1.0885, close=1.0870 < open). Pivots computed as above (M1=1.0816, M3=1.0886).
   - MMM Book pp. 42-43 interpretation: today's HOD is predicted to land near M3 (1.0886) because the prior candle was red. A trader watching price approach 1.0886 watches for a reversal / stop-hunt signal.
   - Verify: Spec describes this interpretation; no algorithmic validation possible (prediction, not calculation).

3. **ResetTimeGMT=0 (midnight-server broker) vs ResetTimeGMT=22 (MMM/NY-close broker):**
   - Input: Both configurations run on EURUSD on the same trading day.
   - Expected: Two different D1[1] bars are used — the midnight-close D1 bar has different H/L/C than the 22:00-GMT-close D1 bar. The resulting pivot levels differ visibly. A ResetTimeGMT=22 config matches what MMM traders see in MMM education materials; ResetTimeGMT=0 matches some ECN/STP broker charts.
   - Verify: This test illustrates why ResetTimeGMT is a critical config setting; both are correct for their broker type.

---

## Port notes

### MQ4 to MQ5 deltas

`iHigh`, `iLow`, `iClose` on `PERIOD_D1` work in both MQ4 and MQ5 (same function names). `EventSetTimer`, `OBJ_HLINE`, `OBJ_LABEL` APIs are identical. The main MQ5 difference: `ObjectCreate` in MQ5 requires `ChartID()` as the first argument (explicit chart reference) instead of the MQ4 implicit-current-chart behavior. Timer handling in `OnTimer` is identical in structure.

### Python port

```python
def compute_pivots(H, L, C):
    PP = (H + L + C) / 3
    R1 = 2*PP - L;  R2 = PP + (H-L);  R3 = H + 2*(PP - L)
    S1 = 2*PP - H;  S2 = PP - (H-L);  S3 = L - 2*(H - PP)
    M1 = (S2 + S1) / 2; M2 = (S1 + PP) / 2
    M3 = (PP + R1) / 2; M4 = (R1 + R2) / 2
    return dict(PP=PP, R1=R1, R2=R2, R3=R3, S1=S1, S2=S2, S3=S3,
                M1=M1, M2=M2, M3=M3, M4=M4)
```

For backtesting: compute from `df_daily.iloc[-1]` at each simulation day. For live visualization: matplotlib `axhline` per level. No chart-object API needed.

### Backtester integration

Pivots are SPATIAL filters (as opposed to TEMPORAL session filters in `temporal_filters.py` / `session_config.py`). In `backtest_hybrid.py`, pivots could feed:

```python
# Distance-from-pivot gate: skip entries where price is mid-zone between PP and R1
distance_to_pp = abs(close - PP)
if distance_to_pp < 10 * pip_size:
    skip_entry("price at PP — indecision zone")
```

Helix's daily Z-score mean-reversion strategy (v1.0, Sharpe 2.08) does not currently use pivots, but they are a candidate Phase 9 StrategyRouter gate: "exit long at R1 unless TDI MBL cross confirms continuation." The M1-M4 mid-pivot prediction system (red-candle → M1/M3 day) could be an input feature to the RAG learning loop (INFRA-03) as a daily-directional prior.

---

## Uncertainty log

- [INFER] ShowMidPivots default true — the indicator may default to false to match generic pivot indicators; the MMM Book usage of M1-M4 makes true the logical default but cannot be confirmed without running the indicator
- [INFER] ResetTimeGMT default 22 — could be 0 (midnight server) if the indicator was calibrated for a midnight-closing broker; 22 is the MMM/NY-close convention
- [INFER] ShowWeekly default false — weekly pivots are a secondary feature; false is the common default for daily-focused indicators
- [INFER] Color palette specifics — white PP, red R-lines, green S-lines, yellow M-lines is the intuitive MMM palette but unverifiable from the binary
- [INFER] MidLineStyle = STYLE_DOT for M1-M4 vs STYLE_SOLID — dotted is used here to visually distinguish mid-pivots from standard levels, but could be any style
- [INFER] ShowLabels default true — most pivot indicators show labels; could be false
- [INFER] ObjectPrefix = "smPP_" — naming is conventional; actual prefix unknown
- [INFER] Whether alerts fire on price crossing a pivot level (most community versions do not alert by default)
- [INFER] Sunday D1 bar skip logic — whether the indicator automatically detects and skips Sunday candles; no confirmation from binary size alone (15,684 bytes is consistent with either including or excluding this logic)
- [INFER] Whether the indicator supports monthly pivots in addition to daily and weekly
- [INFER] sm_gmtoffset dependency — the indicator may use a hard-coded GMT offset parameter instead of calling sm_gmtoffset; the 15,684-byte size doesn't necessitate calling sm_gmtoffset

---

## Implementation status (Phase 12)

| Target | Status | Build date | Notes |
|--------|--------|------------|-------|
| MQ5 | Built ✅ | 2026-04-29 | `resource_pack/MMM/SM Indicators/MT5/indicators/SM_PivotPoints.mq5`; OBJ_HLINE chart objects; Pitfall 5 guard (shift=1); M1-M4 per MMM Book pp. 42-43 |
| MQ4 | Built ✅ | 2026-04-29 | `resource_pack/MMM/SM Indicators/MT4/_helix_built/indicators/SM_PivotPoints.mq4`; MQL4 idioms per D-20; iHigh/iLow/iClose return double directly |
| Python | Built ✅ | 2026-04-29 | `V2/v3_intelligence/sm_indicators/pivot_points.py`; `compute_pivot_points()` + `PivotPointsParams`; shift(1) Pitfall 5 guard; M1-M4 mid-pivots per MMM Book pp. 42-43; 4/4 pytest GREEN |

**Confidence:** High — standard floor pivot formulas zero-ambiguity; M1-M4 documented in MMM Book pp. 42-43; [INFER] on cosmetic parameters only.

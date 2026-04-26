# SM_IlsleyPsychLevels

## Header

| Field | Value |
|-------|-------|
| Name | SM_IlsleyPsychLevels |
| Source filename | `!SM_IlsleyPsychLevels.ex4` |
| Source platform | MT4 (MQL4) |
| Source binary size | 3,540 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 1 — Atomic (no SM dependencies beyond Tier 0) |
| Confidence | Confidence: Medium |

**Confidence rationale:** The algorithm for round-number psychological level indicators is HIGH confidence — it is a well-documented, widely re-implemented indicator class. The public community reference implementation (mql5.com/en/code/55506 "Round Levels MT4") is functionally identical in concept. The "Ilsley" attribution identifies a specific community variant adopted by Steve Mauro into the SM indicator set; the exact parameter names, intervals, and any Ilsley-specific behavior modifications are `[INFER]`. The 3,540-byte binary size is very small and consistent with a simple horizontal-line drawing indicator with no complex calculation. Confidence is Medium rather than High because the Ilsley-specific variant may differ from generic round-level indicators in non-cosmetic ways that cannot be determined from the binary alone.

---

## Purpose

SM_IlsleyPsychLevels draws horizontal lines at round-number **psychological price levels** on the main price chart. These are price points ending in .00 or .50 (in pips) — for example, on EURUSD: 1.0800, 1.0850, 1.0900, 1.0950, 1.1000. The "00" levels (full figures) are considered stronger than the "50" levels (half figures) in institutional order-flow analysis.

The MMM Glossary defines Psychological Levels as "round-number price levels where institutional orders, stop-losses, and take-profits concentrate, attracting significant order flow that may cause price to stall, reverse, or spike through." In the MMM/BTMM framework, psychological levels are used alongside the ADR markers and previous PHOD/PLOD to identify high-probability zones where market-maker price action may accelerate or stall.

The "Ilsley" name refers to a community contributor (likely from UK/European BTMM trading forums) whose version of the round-levels indicator was adopted by Steve Mauro into the SM indicator set. The Ilsley variant is distinguished from generic round-level indicators in the community by its specific visual style — typically faint dotted lines with distinct color differentiation between minor (50-pip) and major (00-pip) levels. Whether the Ilsley version adds any behavioral features beyond cosmetics (e.g., JPY auto-adaptation, symbol-type detection) is uncertain. Community discussion referencing this variant appears on BTMM Forex Factory threads and in the context of the mql5.com/en/code/55506 "Round Levels MT4" public indicator, which is considered a close equivalent.

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| LevelInterval | int | 50 | 5–500 (points) | Spacing between consecutive psychological levels, in points. On 5-digit brokers, 50 points = 50 pips (= 0.0050 in price). | [INFER] — 50 pips is the canonical MMM psychological level spacing; the binary default is unverified |
| MajorInterval | int | 100 | 50–1000 (points) | Spacing for "major" (00-pip / full-figure) levels. Lines at these levels receive heavier weight/distinct color. | [INFER] |
| MinorColor | color | clrDimGray | any | Color for minor (50-pip) level lines | [INFER] — faint gray palette typical of background reference lines |
| MajorColor | color | clrDarkGray | any | Color for major (00-pip) level lines | [INFER] — slightly darker than MinorColor to distinguish the two grades |
| LineStyle | int | STYLE_DOT | STYLE_* enum | Line drawing style | [INFER] — dotted is the most common style for background psychological levels |
| LineWidth | int | 1 | 1–3 | Line pixel width | [INFER] — major levels may use width 2 |
| LevelsAbove | int | 10 | 1–30 | Number of levels to draw above current price | [INFER] |
| LevelsBelow | int | 10 | 1–30 | Number of levels to draw below current price | [INFER] |
| ObjectPrefix | string | "smPsy_" | any valid string | Chart object name prefix for bulk cleanup on deinit | [INFER] |
| AdaptForJPY | bool | true | true / false | Auto-scale level intervals for JPY pairs, where 1 pip = 0.010 (not 0.00010). Without this, the 50-point interval would place lines every 0.5 pips on USDJPY — far too dense. | [INFER] — the JPY adaptation is a critical correctness requirement; the boolean form is assumed |

---

## Outputs

### Indicator buffers

None. SM_IlsleyPsychLevels creates chart objects and has no indicator buffer arrays.

### Chart objects

Between `2 × (LevelsAbove + LevelsBelow)` `OBJ_HLINE` objects, each named with its price level (e.g., `smPsy_1.0850`, `smPsy_1.0900_major`). Major levels (at MajorInterval spacing) may carry a `_major` suffix in the object name. [INFER — exact naming convention]

No labels are drawn by default [INFER]. The price level itself is readable from the `OBJ_HLINE` price coordinate visible in MT4's "Objects List" or via chart crosshair hover.

### Alerts

None. [INFER] SM_IlsleyPsychLevels is a purely visual reference layer.

---

## Calculation logic

1. **On `OnInit` and on price-significant-move** (when current price crosses to a different base level — see bar-iteration model below):

   a. **Determine effective interval in price units:**
   - If `AdaptForJPY = true` and `SymbolInfoInteger(SYMBOL_DIGITS) ∈ {2, 3}` (JPY pair, 3-digit broker):
     - `interval_price = LevelInterval × 0.01` (e.g., 50 points → 0.50 for USDJPY)
     - `major_price = MajorInterval × 0.01`
   - Else (standard 5-digit broker, 5-digit pair like EURUSD):
     - `interval_price = LevelInterval × Point` (e.g., 50 × 0.00001 = 0.00050)
     - `major_price = MajorInterval × Point`

   b. **Find the base level:** Round current price down to the nearest multiple of `interval_price`:
   `base = floor(current_price / interval_price) × interval_price`

   c. **Delete existing objects** with `ObjectPrefix` to avoid accumulation.

   d. **Create or update `OBJ_HLINE` for each level:** For i in `−LevelsBelow` to `+LevelsAbove`:
   `level = base + i × interval_price`
   Determine if `level` is a major level: `is_major = (round(level / major_price) × major_price ≈ level)` within floating-point tolerance.
   Set color, style, and width: major → MajorColor + heavier width [INFER]; minor → MinorColor + LineWidth.

2. **Bar-iteration model:** [INFER] Not every-tick — recompute only when the current price crosses to a new base (i.e., when `|current_price − last_base| > interval_price / 2`). This prevents thrashing chart objects on every tick while keeping the visible window of levels current as price trends away from the initial base. On `OnTick` or `OnCalculate`, check this condition and recompute if triggered.

3. **On `OnDeinit`:** Delete all objects with `ObjectPrefix`.

---

## Pseudocode

```
# SM_IlsleyPsychLevels — language-neutral imperative pseudocode
# JPY-adaptation branch is critical — see Edge cases section

GLOBAL: last_base = 0.0

function on_init():
    recompute_levels(current_price())

function recompute_levels(price):
    # 1. Determine interval in price units
    if AdaptForJPY and digits() in [2, 3]:
        interval = LevelInterval * 0.01     # JPY: pip = 0.01
        major    = MajorInterval * 0.01
    else:
        interval = LevelInterval * symbol_point()   # e.g. 50 * 0.00001 = 0.00050
        major    = MajorInterval * symbol_point()

    # 2. Find base level (nearest multiple of interval below current price)
    base = floor(price / interval) * interval
    last_base = base

    # 3. Redraw all levels
    delete_objects_with_prefix(ObjectPrefix)

    for i in [-LevelsBelow .. +LevelsAbove]:
        level = base + i * interval
        # 4. Classify as major or minor
        remainder = abs(level - round(level / major) * major)
        is_major = (remainder < interval * 0.01)    # floating-point tolerance
        color  = MajorColor if is_major else MinorColor
        width  = 2          if is_major else LineWidth
        upsert_hline(ObjectPrefix + format_price(level), level, color, LineStyle, width)

function on_tick():
    price = current_price()
    if abs(price - last_base) > interval / 2:
        recompute_levels(price)

function on_deinit():
    delete_objects_with_prefix(ObjectPrefix)
```

---

## Visual elements

Multiple faint horizontal lines on the **main price chart** (not a subwindow):

- **Minor (50-pip) levels:** dotted [INFER], dim-gray, width 1 — appear as subtle background grid lines
- **Major (00-pip) levels:** dotted or solid [INFER], darker gray, width 2 [INFER] — visually heavier to signal full-figure round numbers
- Z-order: all lines are sent to back so candles, SM_ADR_Marker lines, and SM_Daily_HiLo lines render above them. Psychological levels are intentionally the lowest visual layer.
- No text labels on the chart [INFER] — the levels are identifiable from their Y-coordinates. If labels are present, they would show the raw price (e.g., "1.0850") at the left or right chart edge.

---

## Dependencies

None. SM_IlsleyPsychLevels is self-contained. It requires only the current symbol's `Point` value and `Digits` count, both available as built-in MQL4 variables. No dependency on `sm_gmtoffset`, `sm_WorkTime`, or any other SM indicator.

---

## Edge cases

- **JPY pairs (3-digit symbols):** This is the most critical edge case for this indicator. `Point = 0.001` on JPY pairs (3-digit broker). A naive `LevelInterval × Point = 50 × 0.001 = 0.050` produces lines every 5 pips — passable but still not the conventional 50-pip / 100-pip standard. On a 5-digit JPY broker (`SYMBOL_DIGITS = 5` in MT4 display mode, but Digits = 3 for the underlying pip), the calculation differs. The `AdaptForJPY` flag with `Digits ∈ {2, 3}` detection path is the required guard. Without it, USDJPY at 152.34 would get lines at 152.30, 152.35, 152.40 (every 5 points / 0.5 pips) — far too dense to be useful.

- **Index symbols (US30, GER40, NAS100, XAUUSD):** `Point` is typically 0.01 or 1.0 for CFD indices. Psychological levels for indices are at 100, 500, 1000 point intervals — very different from forex. `AdaptForJPY` does not cover this case. A user would need to set `LevelInterval` manually (e.g., `LevelInterval = 100` for US30). Without an index-specific auto-detection, the indicator may draw lines at nonsensical frequencies. [INFER — whether any auto-adaptation for non-forex instruments exists]

- **Crypto pairs (BTCUSD, ETHUSD at high price):** Similar to indices — "psychological levels" for Bitcoin are at $1,000, $5,000, $10,000 increments. Manual `LevelInterval` override required.

- **Recompute frequency / object thrashing:** If `on_tick()` recomputes every tick (every few milliseconds on active pairs), it creates and deletes up to `2 × (LevelsAbove + LevelsBelow)` = 40 chart objects per tick — performance impact. The `last_base` cache pattern (recompute only when price crosses a level boundary) is the necessary optimization. Without it, the indicator would be unusable on active 1-minute charts.

- **Very large LevelsAbove / LevelsBelow:** If set to 30 each, up to 60 horizontal lines are drawn. At 60 lines, chart performance may degrade slightly on older MT4 builds. The practical maximum is ~20 levels per side for most setups.

- **Chart zoom-out beyond visible level range:** Lines beyond the chart's visible price range are rendered but invisible. This is not a bug — the lines are there and will become visible if the user scrolls or the price moves far enough.

- **Symbol change:** `OnInit` is invoked again. The `Digits` check re-runs against the new symbol. Old objects from the previous symbol are deleted via the `ObjectPrefix`-based cleanup, and new levels for the new symbol's price range are drawn.

---

## Test cases

1. **EURUSD H1 at current price 1.0867, LevelInterval=50, MajorInterval=100, AdaptForJPY=true (no effect on 5-digit pair), LevelsAbove=5, LevelsBelow=5.** Expected minor lines at: 1.0870 (round to base 1.0850, i=0..+5: 1.0850, 1.0900, 1.0950, 1.1000 (major), 1.1050; below: 1.0800 (major), 1.0750, 1.0700 (major), 1.0650, 1.0600 (major)). Major lines at 00-pip boundaries (1.0800, 1.0900, 1.1000 etc.) are visually heavier/darker than minor 50-pip lines.

2. **USDJPY H1 at 152.34, AdaptForJPY=true:** `interval = 50 × 0.01 = 0.50`, `major = 100 × 0.01 = 1.00`. Expected lines at: 152.00 (major), 152.50, 153.00 (major), 153.50, etc. above; and 152.00 (major), 151.50, 151.00 (major) below. Base = `floor(152.34 / 0.50) × 0.50 = 152.00`.

3. **USDJPY H1 at 152.34, AdaptForJPY=false (intentionally wrong):** `interval = 50 × 0.001 = 0.050`. Lines at 152.300, 152.350, 152.400, 152.450, 152.500 — spaced 5 pips apart, which is clearly too dense for meaningful psychological level analysis. This demonstrates the necessity of the `AdaptForJPY` flag for JPY pairs.

---

## Port notes

### MQ4 → MQ5

- `OBJ_HLINE` API is identical in both. `ObjectCreate` gains a `chart_id = 0` first argument in MQ5.
- `Point` constant is available in both. `SymbolInfoInteger(SYMBOL_DIGITS)` is available in both (this is the MQ5 name; the MQ4 equivalent is the `Digits` global variable).
- `ChartGetDouble(0, CHART_PRICE_MIN)` and `CHART_PRICE_MAX` can be used in MQ5 to determine the visible chart range and skip drawing levels outside it — a performance optimization not available in MQ4.
- No timer or buffer needed for this indicator. The `on_tick()` price-check pattern is the same in both versions.

### Python port

```python
import numpy as np

def get_psych_levels(price: float, digits: int, level_interval: int = 50,
                     major_interval: int = 100,
                     levels_above: int = 10, levels_below: int = 10,
                     adapt_for_jpy: bool = True) -> list:
    if adapt_for_jpy and digits in [2, 3]:
        interval = level_interval * 0.01
        major    = major_interval * 0.01
    else:
        interval = level_interval * (10 ** -(digits - 1))  # Point equivalent

    base = np.floor(price / interval) * interval
    levels = []
    for i in range(-levels_below, levels_above + 1):
        level = round(base + i * interval, digits)
        is_major = abs(level - round(level / major) * major) < (interval * 0.01)
        levels.append({'price': level, 'major': is_major})
    return levels
```

For visualization: `ax.axhline(lv['price'], linestyle=':', color='darkgray' if lv['major'] else 'dimgray', linewidth=2 if lv['major'] else 1)`.

### Backtester integration

Psychological levels are commonly used as "fade" or "breakout" zones in systematic strategies. In `backtest_hybrid.py`:

```python
psych_levels = get_psych_levels(price=current_price, digits=symbol_digits)
nearest = min(psych_levels, key=lambda lv: abs(lv['price'] - current_price))
dist_to_psych = abs(current_price - nearest['price'])

if dist_to_psych < atr * 0.1 and at_session_open:
    psych_fade_signal = True  # price near psych level at session open → fade candidate
```

Helix does not currently use psychological levels as a strategy gate, but they are a candidate for EXPN-style strategy expansion in Phase 9.

---

## Uncertainty log

- [INFER] `LevelInterval = 50` default — 50-pip spacing is the MMM-typical psychological level convention, but the binary default is unverifiable
- [INFER] `MajorInterval = 100` default — the "00 pip" full-figure standard, unverified
- [INFER] `AdaptForJPY = true` default — assumed because the JPY edge case was well-known in 2019 MT4 indicator development and would be a critical bug if absent; unverifiable from the binary
- [INFER] `MinorColor = clrDimGray` and `MajorColor = clrDarkGray` — MMM-typical faint background palette; the Ilsley community variant may use different colors
- [INFER] `LineStyle = STYLE_DOT` default — dotted is most common for background reference lines; could be STYLE_DASH
- [INFER] `LevelsAbove = 10` and `LevelsBelow = 10` defaults — common default for multi-level indicators; unverified
- [INFER] Whether the "Ilsley" variant differs from generic Round Levels MT4 indicators (mql5.com/en/code/55506) in any non-cosmetic way — the small 3,540-byte binary size suggests it may be functionally identical to a standard round-levels indicator
- [INFER] Whether index-symbol auto-adaptation (beyond AdaptForJPY) exists — likely not given the small binary size; manual LevelInterval override would be required for CFD indices
- [INFER] Whether the recompute is triggered on tick crossing vs. price-distance threshold — the exact trigger condition is unverifiable
- [INFER] Whether labels at the price level values are displayed or omitted by default

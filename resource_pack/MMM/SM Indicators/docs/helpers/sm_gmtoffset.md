# sm_gmtoffset

## Header

| Field | Value |
|-------|-------|
| Name | sm_gmtoffset |
| Source filename | `!sm_gmtoffset.ex4` |
| Source platform | MT4 (MQL4) |
| Source binary size | 5,592 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 0 — Helper (bottom of dependency graph) |
| Confidence | Confidence: Medium |

**Confidence rationale:** The function of this helper — detecting broker GMT offset and publishing it for consumption by session-aware indicators — is HIGH confidence from the MMM Glossary "Time Mapping" entry and the MQL5 community forum discussion of broker-time normalization. The exact parameter names, the internal detection algorithm (GlobalVariable vs buffer vs include), and the DST handling logic are all `[INFER]` because the source binary is compiled MQL4 and cannot be decompiled.

---

## Purpose

MQL4's `TimeCurrent()` function returns the broker's server time, which is not UTC/GMT. For a Cyprus-based broker like IC Markets EU, server time runs at GMT+2 in winter and GMT+3 in summer (EEST); for some New Zealand brokers, server time runs at GMT+12 or GMT+13. The Steve Mauro MMM methodology defines its three trading sessions strictly in GMT: Asia 00:30–07:00 GMT, London/Europe 07:30–13:00 GMT, and US/New York 13:30–20:30 GMT (MMM Book p. 8). Any indicator that draws session boxes, labels session transitions, or evaluates whether the current bar is inside a trading window must first normalize broker server time to GMT. The MMM Glossary "Time Mapping" entry states explicitly: "The action of matching your broker's server time to our indicators."

`sm_gmtoffset` is the bottom-of-stack helper that performs this normalization once and publishes the result. It computes the broker's effective GMT offset in integer hours, stores that value where downstream indicators can read it — most likely via a MetaTrader `GlobalVariable` — and refreshes periodically to catch DST transitions. By centralizing broker-time normalization in a single indicator, the entire SM indicator suite (sm_WorkTime, SM_PivotPoints, SM_NewHUD, and others) avoids duplicating the offset-detection logic and avoids the risk of indicators disagreeing about the current offset during a DST switch week.

---

## Inputs / Parameters

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| AutoDetect | bool | true | true / false | When true, derive GMT offset from `TimeCurrent() - TimeGMT()` at runtime; when false, use ManualGMT | [INFER] |
| ManualGMT | int | 0 | -12 .. +14 | Fallback GMT offset in integer hours — used only when AutoDetect = false | [INFER] |
| DSTAdjust | bool | true | true / false | When true, subtract 1 h from the raw auto-detected offset if the broker appears to have already applied DST (see edge cases) | [INFER] |
| GlobalVarName | string | "sm_GMTOffset" | any valid name | Name of the MT4 GlobalVariable into which the detected offset is written; consumed by sm_WorkTime and other helpers | [INFER] |

---

## Outputs

### Indicator buffers

None. sm_gmtoffset is a data-only utility indicator and does not declare any indicator plots or buffer arrays. [INFER]

### Chart objects

None drawn. The indicator renders nothing visible on the chart. It may print a transient `Comment()` to the top-left chart corner showing the detected offset value (e.g., "GMT Offset: +2") for human verification during setup, but this is not a persistent chart object. [INFER]

### Alerts

None. [INFER]

### Side-effect output

GlobalVariable `sm_GMTOffset` (integer, range -12..+14): the broker's effective GMT offset in whole hours. This is the primary output consumed by all downstream session-aware indicators. [INFER — on GlobalVariable as the publication mechanism]

---

## Calculation logic

The following step-by-step describes the most plausible implementation based on MQL5 forum references and general MQL4 broker-time detection patterns. All steps are [INFER] except the stated MQL4 API function names, which are documented MQL4 functions.

1. **OnInit — compute offset:**
   - If `AutoDetect == false`: set `offset_hours = ManualGMT` directly, skip detection.
   - If `AutoDetect == true`:
     a. Call `TimeGMT()` to get the current UTC timestamp as known to the MT4 platform (derived from the local machine clock with OS-level UTC offset applied).
     b. Call `TimeCurrent()` to get the broker server's reported time.
     c. Compute `delta_seconds = TimeCurrent() - TimeGMT()`.
     d. Convert to hours: `offset_hours = MathRound(delta_seconds / 3600)`.
     e. If `DSTAdjust == true` and the broker's DST window is currently active (detected by comparing `offset_hours` to the broker's known base offset, or by checking the calendar date against European DST rules): subtract 1 from `offset_hours` — reasoning is that some brokers report a time that already includes DST, which would inflate the raw delta by 1 h relative to the "standard" winter offset.

2. **Publish:** Call `GlobalVariableSet(GlobalVarName, (double)offset_hours)` to write the result. [INFER — GlobalVariable rather than a buffer or include-file shared variable]

3. **Bar-iteration model:** The indicator recalculates on `OnInit` (at chart load and at symbol/timeframe change). It also refreshes periodically — most likely on every new bar rather than on every tick — to limit CPU load. The refresh check targets the DST transition boundary: every Sunday 22:00 UTC is the weekly bar rollover and a likely refresh trigger. An hourly check (first tick of each hour) is an alternative. [INFER — exact refresh cadence]

4. **OnDeinit:** The GlobalVariable is deliberately NOT deleted on deinit, so that downstream indicators continue to read the last-known offset even after sm_gmtoffset is temporarily removed from a chart. [INFER]

---

## Pseudocode

```
# sm_gmtoffset — language-neutral imperative pseudocode
# Notation: snake_case, read() = MT4 API call, write() = GlobalVariableSet

GLOBAL: offset_hours = 0

function on_init():
    if AutoDetect == false:
        offset_hours = ManualGMT
    else:
        broker_now_utc  = read_time_gmt()          # MT4 TimeGMT()
        broker_server   = read_time_current()       # MT4 TimeCurrent()
        delta_seconds   = broker_server - broker_now_utc
        raw_offset      = round(delta_seconds / 3600.0)

        if DSTAdjust and broker_appears_dst_shifted(raw_offset):
            offset_hours = raw_offset - 1          # strip broker DST from raw delta
        else:
            offset_hours = raw_offset

    write_global_variable(GlobalVarName, offset_hours)
    log_comment("GMT Offset detected: " + str(offset_hours))


function broker_appears_dst_shifted(raw_offset):
    # Heuristic: if raw_offset is 1 h above the known base offset for this broker
    # during months when European DST is active (late March to late October),
    # the broker has already included DST.
    month = current_month()
    return (month >= 3 and month <= 10)            # rough Northern Hemisphere DST window


function on_new_bar():
    # Refresh hourly to catch mid-week DST switches
    if minute_of_current_bar() == 0:
        on_init()


function on_deinit():
    # Deliberately do NOT delete GlobalVarName:
    # downstream indicators must survive sm_gmtoffset chart removal
    pass
```

---

## Visual elements

Nothing is drawn on the chart. sm_gmtoffset has no visible output beyond an optional transient `Comment()` call that prints the detected offset in the chart's comment area. The comment is overwritten on every refresh and disappears when the indicator is removed or when another indicator calls `Comment()`. [INFER on the Comment behavior — the indicator may produce no visible output at all]

Z-order: N/A. Subwindow: N/A (utility indicator; no plot). Main chart: N/A.

---

## Dependencies

None — sm_gmtoffset is the bottom of the SM indicator dependency graph. It does not read any other SM helper's output. It relies only on built-in MQL4 API functions (`TimeCurrent`, `TimeGMT`, `GlobalVariableSet`).

---

## Edge cases

- **Broker DST switch (last Sunday of March / last Sunday of October):** The broker's GMT offset changes by 1 h. The hourly refresh cycle on the next bar should detect this; until that refresh fires, downstream indicators may draw session boxes 1 h off. The `DSTAdjust` logic is the primary mitigation.
- **Brokers that do not observe European DST** (e.g., some South Pacific or Middle Eastern servers): `DSTAdjust = true` would incorrectly subtract 1 h. Users on such brokers must set `DSTAdjust = false` and manage offset manually.
- **First-tick race condition:** If sm_WorkTime or another downstream indicator loads before sm_gmtoffset has published its GlobalVariable, `GlobalVariableGet(GlobalVarName)` returns 0 (the MT4 default for an undefined GlobalVariable). Downstream indicators must handle a 0-offset gracefully (accept one cycle of inaccurate session boxes rather than crashing).
- **Local machine timezone change while MT4 is running:** `TimeGMT()` is derived from the OS clock; if the OS timezone is changed during an active session, the computed delta may shift until the next refresh. Rare in practice.
- **Weekend gap:** The broker server may be offline or reporting Friday's last timestamp. The cached GlobalVariable value persists across the weekend and is re-validated on Monday's first tick. [INFER]
- **Broker offset change (broker server relocation):** Very rare; requires manual refresh or chart re-load for the new offset to be detected.
- **Integer rounding edge case:** Some brokers run at GMT+x:30 (e.g., India IST at UTC+5:30). `MathRound(delta_seconds / 3600)` would produce +6 rather than +5.5. Half-hour offsets are not supported by this integer-offset model. [INFER — integer-only assumption]

---

## Test cases

1. **IC Markets EU (Cyprus), winter weekday:** Broker server time = GMT+2. At 14:00 broker time on a Tuesday in January, `TimeCurrent()` returns a timestamp 7200 seconds (2 h) ahead of `TimeGMT()`. `delta_seconds = 7200`, `raw_offset = round(7200 / 3600) = 2`. `DSTAdjust = true` but month is January (outside DST window) → `broker_appears_dst_shifted` returns false → `offset_hours = 2`. GlobalVariable `sm_GMTOffset` is written as `2`. **Expected:** downstream sm_WorkTime draws Asia session starting at 02:30 broker time (= 00:30 GMT + 2 h).

2. **Same broker after European spring DST switch (last Sunday of March):** Broker server time shifts to GMT+3. At 09:00 broker time on the Monday following the switch, `TimeCurrent()` is now 10800 seconds (3 h) ahead of `TimeGMT()`. `raw_offset = 3`. `DSTAdjust = true` and month = March, within the rough DST window → `broker_appears_dst_shifted` returns true → `offset_hours = 3 - 1 = 2`. GlobalVariable written as `2`. **Expected:** session boxes remain anchored to GMT times — broker DST is stripped, session times in broker clock shift by +1 h vs winter. **Note:** This test highlights the ambiguity in the DSTAdjust algorithm: [INFER] the correct expected value may be `3` (not `2`) if the intent is to report the current raw broker offset rather than the "standard winter" offset. The spec author cannot resolve this without access to the source.

3. **AutoDetect = false, ManualGMT = 2:** Regardless of `TimeCurrent()` / `TimeGMT()` values, `offset_hours = 2` is published immediately. No API calls made for detection. **Expected:** GlobalVariable `sm_GMTOffset = 2` written on OnInit.

---

## Port notes

### MQ4 to MQ5 deltas

`TimeGMT()` and `TimeCurrent()` are available in both MQL4 and MQL5 with identical signatures. `GlobalVariableSet()` and `GlobalVariableGet()` are also identical between platforms. `OnInit()` changes signature in MQL5: it must return `int` (return `INIT_SUCCEEDED` = 0 on success). There are no indicator buffers and no `OnCalculate()` body beyond returning `rates_total`, so the port is minimal. In MQL5, `EventSetTimer(3600)` combined with `OnTimer()` is a cleaner alternative to polling in `OnCalculate` for the hourly refresh cadence; this avoids consuming unnecessary CPU on every new bar. MQ4's `Comment()` API is identical in MQL5.

### Python port

In a Python/Helix context, broker GMT offset detection uses `datetime.utcnow()` alongside the broker's reported server timestamp from a MetaTrader5 Python connection (`mt5.symbol_info_tick(symbol).time` returns a POSIX timestamp in broker server time). The offset is: `offset_hours = round((broker_ts - utcnow_ts) / 3600)`. Publish via a module-level shared dict: `state["gmt_offset"] = offset_hours`, consumed by the Python equivalent of sm_WorkTime. For DST detection, use `pytz` or Python 3.9+ `zoneinfo` with the broker's IANA timezone (e.g., `Europe/Nicosia` for IC Markets EU); calling `tz.utcoffset(datetime.now())` returns the current offset including DST without manual calendar logic.

### Backtester integration

The Helix V2 backtester reads OHLCV data from CSV files that have already been timestamped in UTC (`V2/v3_intelligence/pit.py` enforces UTC-only timestamps — see `PitClock.UNBOUNDED`). In backtesting mode, broker server time does not exist; all timestamps are already UTC. The Python equivalent of sm_gmtoffset is therefore a **no-op** in backtesting mode — the offset is always 0 and no detection logic is needed. This indicator is only relevant in **live / paper-trade mode** where the EA or Python bridge (`V2/bridge/`) pulls real-time ticks directly from a broker server. The session classification logic that would consume this offset belongs in `V2/v3_intelligence/temporal_filters.py` (Phase 8.5 scope).

---

## Uncertainty log

- [INFER] Parameter name `AutoDetect` — typical MQL4 boolean input convention for this class of indicator; exact name in the compiled binary is unverifiable without source
- [INFER] Parameter name `ManualGMT` — could be `FixedGMT`, `ManualOffset`, `GMTOffset`, or similar; chosen as semantically most descriptive
- [INFER] Parameter name `DSTAdjust` — could be `ApplyDST`, `DSTCorrection`, `AdjustDST`, or absent entirely
- [INFER] Default value of `DSTAdjust = true` — most MQL4 GMT-detection indicators default to DST adjustment enabled, but some leave it to the user
- [INFER] Parameter name `GlobalVarName` as a user-configurable string — the GlobalVariable name might be hard-coded in the source rather than exposed as a parameter
- [INFER] GlobalVariable name `"sm_GMTOffset"` as the default string — this is a plausible SM naming convention; the actual name could be `"SM_GMTOffset"`, `"gmtoffset"`, `"broker_gmt"`, or any other string
- [INFER] Publication mechanism is GlobalVariable — alternative implementations use a shared `.mqh` include file with a module-global variable, or an indicator buffer readable by other indicators via `iCustom()`
- [INFER] Hourly refresh via new-bar poll — alternative: `EventSetTimer`-based periodic refresh (cleaner in MQL5 but valid in MQL4 via `OnTimer`)
- [INFER] Sunday 22:00 UTC as the primary DST-switch detection point — the actual refresh trigger may be simpler (every tick, every new bar) or more specific (calendar date comparison)
- [INFER] `Comment()` call for human verification — common pattern in utility indicators; the indicator may produce zero visible output
- [INFER] GlobalVariable is NOT deleted on `OnDeinit` — some implementations do delete it; the downstream "graceful 0-fallback" behavior in sm_WorkTime depends on the non-deletion assumption
- [INFER] Integer-only GMT offset model — half-hour offsets (e.g., India IST UTC+5:30, Iran IRST UTC+3:30) are unsupported; most Forex broker servers run on integer-hour offsets so this is a reasonable constraint

---

## Implementation status (Phase 12)

| Target | Status | File | Version | Commit | Date |
|--------|--------|------|---------|--------|------|
| MQ4 | Built ✅ | `resource_pack/MMM/SM Indicators/MT4/_helix_built/helpers/sm_gmtoffset.mq4` | v2.00 | `<TBD>` | 2026-04-XX |
| MQ5 | Built ✅ | `resource_pack/MMM/SM Indicators/MT5/helpers/sm_gmtoffset.mq5` | v2.00 | `<TBD>` | 2026-04-XX |
| Python | Built ✅ | `V2/v3_intelligence/sm_indicators/helpers/sm_gmtoffset.py` | v1.00 | `<TBD>` | 2026-04-XX |

Tests: `V2/tests/v3_intelligence/sm_indicators/helpers/test_sm_gmtoffset.py` (5 tests GREEN)
Confidence: High (v2.00 corner label confirmed visible during operator smoke-test 2026-04-28).

### v2.00 changes (Phase 12 Plan 01 gap-closure, 2026-04-28)

The original spec stated the indicator "renders nothing visible on the chart" beyond an optional `Comment()` call. Operator smoke-test on 2026-04-28 found that the `Comment()` text in the upper-left corner gets buried by other indicators that call `Comment()` later, leaving sm_gmtoffset apparently invisible.

v2.00 adds a **persistent corner label** (`OBJ_LABEL`) that survives across other indicators' `Comment()` calls:

- New inputs: `InpShowLabel`, `InpLabelColor` (default `clrLightGreen`), `InpLabelFontSize`, `InpLabelCorner` (default upper-right), `InpLabelXOffset`, `InpLabelYOffset`
- The label text reads `"sm_GMTOffset: +X h"` and refreshes hourly along with the underlying offset value
- Object name is `smGMT_<ChartID>` to support multi-chart use
- Removed cleanly on `OnDeinit`

**Python port unchanged** — the helper still returns an integer; the corner-label semantics are MQ4/MQ5-only (Python doesn't draw).

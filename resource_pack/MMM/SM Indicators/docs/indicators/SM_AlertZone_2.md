# SM_AlertZone_2

## Header

| Field | Value |
|-------|-------|
| Name | SM_AlertZone_2 |
| Source filename | `!SM_AlertZone_2.ex4` |
| Source platform | MT4 (MQL4) |
| Source binary size | 12,710 bytes |
| Binary date | Nov 3, 2019 |
| Tier | 2 — Composite (self-contained; no SM dependencies) |
| Confidence | Confidence: Medium |

**Confidence rationale:** Same category as SM_AlertZone_1 (see SM_AlertZone_1.md for full rationale). The two binaries differ by only **148 bytes** (`!SM_AlertZone_1.ex4` = 12,562 bytes; `!SM_AlertZone_2.ex4` = 12,710 bytes). This near-identical size strongly suggests the **same algorithm compiled with different default values** — NOT fundamentally different calculation logic. The 148-byte delta is consistent with a longer string literal (e.g., a different default alert sound filename, object prefix, or color constant). All behavioral claims are [INFER]. Overall: **Confidence: Medium**.

## Differences from AlertZone_1

SM_AlertZone_2 and SM_AlertZone_1 are assumed to be algorithmically identical — same `OBJ_RECTANGLE` drawing, same enter/exit alert state machine, same rate-limiting by `RepeatAlertSeconds`. The only confirmed difference is the file size (12,710 vs 12,562 bytes — 148-byte delta). The inferred interpretation is:

- **SM_AlertZone_1 (12,562 bytes):** Lower zone variant — intended for use near LOD / S1 / ADR-low; alerts for potential LONG setups
- **SM_AlertZone_2 (12,710 bytes):** Upper zone variant — intended for use near HOD / R1 / ADR-high; alerts for potential SHORT setups

This interpretation is based on naming convention only (variant "1" = lower, variant "2" = upper). The 148-byte size difference may reflect:
- A different default `ZoneColor` constant (e.g., `clrIndianRed` vs `clrSteelBlue` — red-tinted for short zone vs blue for long zone)
- A different `AlertSound` string literal (e.g., `"alert2.wav"` vs `"alert.wav"`)
- A different `ObjectPrefix` string constant (`"smAZ2_"` vs `"smAZ1_"`)

An MT4 operator reading the parameter dialog of both indicators simultaneously would immediately resolve this question. Until then, this spec documents AlertZone_2 as the upper-zone / short-setup companion to AlertZone_1.

---

## Purpose

SM_AlertZone_2 draws a rectangular zone on the price chart between two user-defined price levels and fires alerts when price enters or exits that zone — functionally identical to SM_AlertZone_1. In the MMM context, variant 2 is [INFER] the **upper zone** indicator, positioned near HOD / R1 / ADR-high where the market maker is expected to distribute (sell) and trigger SHORT setups.

The MMM "Strike Zone" / "Blue Box" / "Trading Zone" concept (MMM Book p. 55, MMM Glossary "Trading Zone": "area within 15-20 pips of HOD/LOD where setups occur") applies to both the upper and lower structural levels. A typical MMM chart setup has:
- SM_AlertZone_1 monitoring the lower zone (near LOD — long setups)
- SM_AlertZone_2 monitoring the upper zone (near HOD — short setups)

Both loaded simultaneously provide a two-zone alert envelope. When price reaches either zone, the corresponding indicator alerts the trader to watch for a reversal pattern.

The 148-byte delta between the two binaries is the **primary open question** of Tier 2: does it represent different default colors/sounds (same algorithm), or a meaningful behavioral difference (unlikely given the byte count)? This spec documents the hypothesis that the difference is cosmetic/default-only.

---

## Inputs / Parameters

Parameters are the same as SM_AlertZone_1. The following rows are noted where defaults may differ:

| Parameter | Type | Default | Valid range | Meaning | Confidence |
|-----------|------|---------|-------------|---------|------------|
| ZoneHigh | double | 0.0 | any valid price | Upper price boundary of the alert zone | [INFER] — user must configure |
| ZoneLow | double | 0.0 | any valid price | Lower price boundary of the alert zone | [INFER] |
| ZoneColor | color | clrIndianRed | any | Fill color for the zone rectangle | [INFER] — red/orange palette for "short zone" vs AlertZone_1's blue; may differ from AlertZone_1 default |
| ZoneAlpha | int | 30 | 0–100 | Transparency of the zone fill | [INFER] |
| AlertOnEnter | bool | true | true / false | Fire alert when price first enters the zone | [INFER] — same default as AlertZone_1 |
| AlertOnExit | bool | false | true / false | Fire alert when price first exits the zone | [INFER] — same default as AlertZone_1 |
| AlertSound | string | "alert2.wav" | any valid filename | MT4 sound file played on alert | [INFER] — may differ from AlertZone_1's "alert.wav" to provide distinct audio feedback; contributes to the 148-byte size delta |
| RepeatAlertSeconds | int | 300 | 30–3600 | Minimum seconds between repeated alerts | [INFER] |
| EmailAlert | bool | false | true / false | Also send alert via email | [INFER] |
| PushAlert | bool | false | true / false | Also send push notification | [INFER] |
| ObjectPrefix | string | "smAZ2_" | any valid string | Prefix for all chart objects | [INFER] — must differ from AlertZone_1's "smAZ1_" to allow both on the same chart simultaneously |

---

## Outputs

### Indicator buffers

None. Same as AlertZone_1.

### Chart objects

One `OBJ_RECTANGLE` between `ZoneLow` and `ZoneHigh` spanning chart time range:
- Object name: `smAZ2_rect`
- Fill color: ZoneColor (inferred red/orange palette vs AlertZone_1's blue) with ZoneAlpha transparency
- Z-order: background

[INFER] Two optional `OBJ_HLINE` at ZoneHigh and ZoneLow as boundary markers.

### Alerts

Same alert mechanism as AlertZone_1, with alert text "AZ2 ENTER" / "AZ2 EXIT" (vs "AZ1 ENTER" / "AZ1 EXIT") for visual distinction when both indicators are active simultaneously. Rate-limited by RepeatAlertSeconds.

---

## Calculation logic

Identical to SM_AlertZone_1 with the following substitutions:
- `ObjectPrefix` = `"smAZ2_"` (ensures no name collision when both AlertZone_1 and AlertZone_2 are loaded on the same chart)
- Alert text prefix: "AZ2" instead of "AZ1"
- ZoneColor default may be red/orange instead of blue

The enter/exit state machine, tick-driven execution, rate-limiting, and OnDeinit cleanup are functionally identical to AlertZone_1. See SM_AlertZone_1.md for the full step-by-step algorithm.

---

## Pseudocode

```
# SM_AlertZone_2 — language-neutral imperative pseudocode
# AlertZone_2 — likely upper-zone variant for SHORT setups [INFER]
# Algorithm: identical to AlertZone_1; prefix and default color differ

state was_in_zone     = false
state last_alert_time = 0

function on_init():
    if ZoneHigh == 0 and ZoneLow == 0:
        comment("AlertZone_2: set ZoneHigh and ZoneLow inputs to activate")
        return
    if ZoneHigh <= ZoneLow:
        comment("AlertZone_2: ZoneHigh must be > ZoneLow")
        return
    # Note: ObjectPrefix = "smAZ2_" ensures no collision with AlertZone_1's "smAZ1_" objects
    create_rectangle(ObjectPrefix + "rect",
                     time_from=chart_start_time(), time_to=chart_end_time_extended(),
                     price_low=ZoneLow, price_high=ZoneHigh,
                     color=ZoneColor,    # [INFER: clrIndianRed vs AlertZone_1's clrSteelBlue]
                     alpha=ZoneAlpha,
                     z_order=BACK)

function on_tick():
    current_price = current_bid()
    is_in_zone    = (current_price >= ZoneLow and current_price <= ZoneHigh)
    now           = current_server_time()

    if is_in_zone and not was_in_zone and AlertOnEnter:
        if now - last_alert_time >= RepeatAlertSeconds:
            alert("AZ2 ENTER " + symbol() + " @ " + format_price(current_price))
            if EmailAlert:  send_email("SM AlertZone_2", "ENTER " + symbol())
            if PushAlert:   send_push("AZ2 ENTER " + symbol())
            last_alert_time = now

    elif not is_in_zone and was_in_zone and AlertOnExit:
        if now - last_alert_time >= RepeatAlertSeconds:
            alert("AZ2 EXIT " + symbol() + " @ " + format_price(current_price))
            last_alert_time = now

    was_in_zone = is_in_zone

function on_deinit():
    delete_objects_with_prefix(ObjectPrefix)
```

---

## Visual elements

**Main price chart (no subwindow).** Visually identical to AlertZone_1 in structure but [INFER] with a distinct color scheme to differentiate the upper (short) zone from the lower (long) zone:

- **Fill:** Semi-transparent red/orange rectangle (`clrIndianRed` at ~30% opacity) [INFER]. When both AlertZone_1 (blue) and AlertZone_2 (red) are loaded together, the two zones appear as a blue band near LOD and a red band near HOD — giving a visual "buy zone / sell zone" framing for the session.
- **Z-order:** Background — below candlesticks.
- **No labels** on the zone rectangle by default [INFER].

If both AlertZone_1 and AlertZone_2 are active simultaneously with overlapping zones, both rectangles stack (their fills combine). The distinct `ObjectPrefix` values ensure no collision.

---

## Dependencies

None. Same as AlertZone_1. Self-contained; no SM helper dependencies.

---

## Edge cases

Same edge cases as SM_AlertZone_1, with one addition:

1. **Both AlertZone_1 and AlertZone_2 loaded simultaneously with overlapping zones:** If `AlertZone_1.ZoneHigh > AlertZone_2.ZoneLow` (the zones overlap), both rectangles overlap in the price axis. Each indicator fires its own enter/exit alerts independently. Visual stacking shows a mixed color (blue + red overlay). This is not an error — the zones are independently configured.

2. **Zones set symmetrically (by convention):** A typical MMM session setup has `AlertZone_1.ZoneLow ≈ LOD - 5 pips`, `AlertZone_1.ZoneHigh ≈ LOD + 15 pips`, `AlertZone_2.ZoneLow ≈ HOD - 15 pips`, `AlertZone_2.ZoneHigh ≈ HOD + 5 pips`. This gives ~20-pip zones at each structural level per MMM Glossary "Trading Zone: 15-20 pips from HOD/LOD."

3. **Role reversal:** The indicator is symmetric — AlertZone_2 inputs can be set to a lower zone and AlertZone_1 to an upper zone. The "1 = long / 2 = short" interpretation is convention only; the algorithm makes no assumption about zone direction.

---

## Test cases

1. **Standard upper-zone enter alert (EURUSD H1):**
   - Configuration: `ZoneLow = 1.0890`, `ZoneHigh = 1.0900`, `AlertOnEnter = true`, `AlertOnExit = false`.
   - Tick stream: price at 1.0872 (outside zone, below) → rallies to 1.0895 (inside zone).
   - Expected: Alert fires — "AZ2 ENTER EURUSD @ 1.08950". Zone rectangle visible near HOD in red/orange shading.

2. **Dual-zone setup (AlertZone_1 and AlertZone_2 simultaneously):**
   - AlertZone_1: ZoneLow=1.0820, ZoneHigh=1.0830 (blue, near LOD)
   - AlertZone_2: ZoneLow=1.0890, ZoneHigh=1.0900 (red, near HOD)
   - Price oscillates between 1.0825 and 1.0895 over two hours.
   - Expected: Two distinct zones visible on chart. AlertZone_1 fires when price enters 1.0820-1.0830 range. AlertZone_2 fires when price enters 1.0890-1.0900 range. Each indicator's rate-limiting is independent.

3. **Labels-as-convention test — roles reversed:**
   - AlertZone_1 configured as upper zone (ZoneLow=1.0890, ZoneHigh=1.0900)
   - AlertZone_2 configured as lower zone (ZoneLow=1.0820, ZoneHigh=1.0830)
   - Expected: Both indicators draw and alert correctly. Demonstrates that the "1=lower / 2=upper" interpretation is a convention, not a constraint. Alert text shows "AZ1 ENTER" for the (now-upper) zone and "AZ2 ENTER" for the (now-lower) zone.

---

## Port notes

### MQ4 to MQ5 deltas

Identical to SM_AlertZone_1 — same API surface. See SM_AlertZone_1.md Port notes for the full delta list. The only difference is the `ObjectPrefix` ("smAZ2_" vs "smAZ1_") and potentially the default ZoneColor.

### Python port

Identical to SM_AlertZone_1 in code structure. Instantiate two `AlertZone` objects with different parameters for the lower and upper zones:

```python
lower_zone = AlertZone(zone_low=LOD_today - 5*pip, zone_high=LOD_today + 15*pip,
                       color='steelblue', label='AZ1')
upper_zone = AlertZone(zone_low=HOD_today - 15*pip, zone_high=HOD_today + 5*pip,
                       color='indianred', label='AZ2')
```

### Backtester integration

Same as AlertZone_1. Both zones feed into `backtest_hybrid.py` as spatial gates. A typical setup:

```python
# At session start: define lower/upper MMM zones
az1_low = session_lod - 5 * pip_size
az1_high = session_lod + 15 * pip_size
az2_low = session_hod - 15 * pip_size
az2_high = session_hod + 5 * pip_size

# Gate: long entry only when price is in az1, short entry only when in az2
if az1_low <= current_price <= az1_high:
    apply_long_setup()
if az2_low <= current_price <= az2_high:
    apply_short_setup()
```

---

## Uncertainty log

- [INFER] Whether AlertZone_2 differs from AlertZone_1 in algorithm or only in default values — the 148-byte file size delta is the sole objective evidence; this spec assumes default-only difference
- [INFER] If defaults differ: AlertZone_2 = upper zone / short-setup variant is an inference from naming convention only; AlertZone_1 = lower zone / long-setup is the symmetric inference
- [INFER] Default ZoneColor red/orange palette (clrIndianRed or similar) — a red/orange color for the short zone is intuitive but unverifiable from the binary
- [INFER] AlertSound string "alert2.wav" — the extra 148 bytes could be a longer sound filename string literal; could equally be "alert.wav" with the difference elsewhere
- [INFER] All [INFER] entries from AlertZone_1 apply equally to AlertZone_2 (ZoneHigh/ZoneLow defaults, ZoneAlpha, AlertOnEnter/Exit, RepeatAlertSeconds, EmailAlert, PushAlert)
- [INFER] Whether the two indicators are intended to always be loaded as a pair (one per zone) or can be used independently with only one zone active
- [INFER] ObjectPrefix "smAZ2_" — must differ from AlertZone_1's prefix to avoid object collision; "smAZ2_" is the logical choice but unverifiable
- [INFER] Whether the 148-byte difference involves a different `ObjectPrefix` string length (e.g., "smAlertZone2_" vs "smAZ1_") rather than a sound filename difference

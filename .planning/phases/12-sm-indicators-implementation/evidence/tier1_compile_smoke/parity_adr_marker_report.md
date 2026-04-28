# Parity Check — SM_ADR_Marker

**Verdict:** DEFERRED (advisory per CONTEXT D-15)

## Status

The SM_ADR_Marker MQ5 source ships with an optional `#define DUMP_PARITY_CSV`
block at the top of the file, gated off by default. To capture parity
evidence, the operator runs:

1. Edit `resource_pack/MMM/SM Indicators/MT5/indicators/SM_ADR_Marker.mq5`
   to uncomment the `#define DUMP_PARITY_CSV` line at the top.
2. Recompile in MetaEditor (Wine GUI; D-08 advisory-skips CLI compile).
3. Attach the recompiled indicator to an EURUSD H1 chart in IC Markets KE
   MT5 Terminal; allow it to run for ≥1 D1 bar.
4. The MQL5 EA emits per-bar rows to
   `~/.mt5/drive_c/Program Files/IC Markets KE MT5 Terminal/MQL5/Files/parity_SM_ADR_Marker_EURUSD_H1.csv`.
5. Run the parity script:

   ```bash
   python scripts/parity_check_adr_marker.py \
       --csv ~/.mt5/drive_c/Program\ Files/IC\ Markets\ KE\ MT5\ Terminal/MQL5/Files/parity_SM_ADR_Marker_EURUSD_H1.csv \
       --pair EURUSD --tf H1 --tolerance-price 1e-4
   ```
6. The script overwrites this report with a PASS/FAIL verdict + max-abs-diff
   table.

## Tolerance Achievability (RESEARCH Open Question #3)

The 1e-4 price tolerance target presupposes:

- MQ5 ATR(14) on PERIOD_D1 (Wilder smoothing via `iATR()` handle) matches
  Python `_wilder_atr` (ewm with alpha=1/14, adjust=False).
- `today_open = iOpen(_Symbol, PERIOD_D1, 0)` matches Python `df["Open"]`
  for the bar where the chart timestamp aligns with the OHLCV CSV row.

Both are mathematically equivalent in theory. The 1e-4 tolerance accounts
for:

- Float32 vs float64 promotion across the boundary.
- Broker-server timezone vs UTC alignment (V2/data CSVs are UTC; MT5
  broker time depends on `sm_GMTOffset`).

**If the parity diff lands within tolerance:** Plan 12-03 inherits the
parity-check pattern with confidence for SM_TDI / SM_PivotPoints (also
deterministic).

**If it FAILS** (most-likely cause: timezone misalignment): the divergence
is captured here as a Plan-12-03-blocking discovery; the gap-closure plan
addresses both ADR_Marker and downstream.

## Per CONTEXT D-15

Advisory only — non-blocking for Tier 1 review. Operator may approve the
tier with this report in deferred state and capture the parity diff after
Plan 12-03 closes.

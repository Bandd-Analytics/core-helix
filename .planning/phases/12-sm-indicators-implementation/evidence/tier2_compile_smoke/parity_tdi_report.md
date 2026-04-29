# SM_TDI Advisory Parity Report

**Status:** Deferred — requires Wine MT5 execution

**To run:**
1. Add `#define DUMP_PARITY_CSV` to `SM_TDI.mq5` and recompile under Wine MetaEditor
2. Attach to EURUSD H1 chart, let run for ≥1 bar
3. Copy CSV from `~/.mt5/.../MQL5/Files/parity_SM_TDI_EURUSD_H1.csv`
4. Run:
   ```
   cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix
   python3 scripts/parity_check_tdi.py --csv <path> --pair EURUSD --tf H1
   ```

**Expected tolerances:**
- Price-scale buffers (rsi_pl, tsl, mbl, vb_upper, vb_lower): max_abs_diff < 1e-4
- Ratio-scale metrics (RSI normalization): max_abs_diff < 1e-6

**Advisory note (D-15):** SM_TDI is high-confidence composite (Verified Updates confirmed
RSI=21 + Shark_Fin 63/37 + StdDev 1.6185). Python port uses identical Wilder ewm smoothing.
Parity is expected to be near-exact for all 5 output buffers.

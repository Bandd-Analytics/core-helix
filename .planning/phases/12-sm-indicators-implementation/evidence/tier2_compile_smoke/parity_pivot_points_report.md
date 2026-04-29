# SM_PivotPoints Advisory Parity Report

**Status:** Deferred — requires Wine MT5 execution

**To run:**
1. Add `#define DUMP_PARITY_CSV` to `SM_PivotPoints.mq5` (add parity CSV output on each D1 bar close)
2. Attach to EURUSD D1 chart, let run for ≥1 bar
3. Copy CSV from `~/.mt5/.../MQL5/Files/parity_SM_PivotPoints_EURUSD_D1.csv`
4. Run:
   ```
   cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix
   python3 scripts/parity_check_pivot_points.py --csv <path> --pair EURUSD --tf D1
   ```

**Expected tolerances:**
- All price-scale pivot levels (pp, r1, r2, r3, s1, s2, s3, m1, m2, m3, m4): max_abs_diff < 1e-4

**Advisory note (D-15):** SM_PivotPoints is high-confidence composite (standard floor-pivot
formulas zero-ambiguity; M1-M4 confirmed by MMM Book pp. 42-43). Python port uses identical
formulas. Parity is expected to be exact (floating-point tolerance only).

# Shelved Features — Not Discarded, Not Ready

## BEC Partial Close (50% exit at intermediate target)

**What it does:**  
Closes 50% of a swing position when price reaches half the profit target (2x ATR),
then trails the remaining half with a 1.5x ATR trailing stop.

**Why it was shelved:**  
Backtested 2026-04-20 against 8 pairs, 4-way comparison showed:
- Win rate increases (24.1% → 31.2%) — the mechanism works mechanically
- But Sharpe drops -0.68 (from -1.70 to -2.38) and total P&L worsens by 15.5pp
- Root cause: strategy win rate is too low (24%) for partial close to help.
  You need large wins to compensate for 76% loss rate.
  Partial close halves the wins but takes full stops — asymmetry inverts.

**When to revisit:**  
Once daily swing win rate reaches ≥40% consistently in live or walk-forward testing.
The mechanism is sound; the signal quality must come first.

**Code location (stripped from backtest):**  
Reference implementation exists in git history of `backtest_hybrid.py` and in
`ea/include/CExitManager.mqh` (v2.1) where `SPartialCloseState`, `ExecutePartialClose()`,
and `UpdatePartialTrail()` are fully implemented and tested.
MQL5 code is ready to activate — just needs the win rate precondition met.

---

## Notes on Strategy Architecture Decision (2026-04-20)

The H1 scalp and intraday momentum layers were found to destroy the daily Z-score
signal. See `docs/algorithmic-alpha-research.md` for the clean daily baseline results
that confirmed the daily swing signal is the core alpha source.

# Phase 7: Backtest Entry Fix + H1/Momentum 4yr Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 07-backtest-entry-fix-h1-momentum-4yr-validation
**Areas discussed:** Entry Fix Scope, PiT Validator Design, Walk-forward Structure, 4yr Data Sourcing

---

## Entry Fix Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Fix all 3 loops | 2-line change in each: replace px = row['Close'] with h1.iloc[i+1]['Open']. Minimal change, fast, easy to verify Sharpe delta. Keeps existing for-loop engine. | ✓ |
| Fix evaluate_all.py only | Only the scalp + momentum loops matter for the routing matrix. hybrid.py fix deferred. | |
| Migrate to VBT Pro portfolio API | Rewrite loops using vbt.PF.from_signals(price=-np.inf). Cleaner long-term, but full engine refactor. | |

**User's choice:** Fix all 3 loops

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — show old vs new Sharpe | Run both versions and print comparison table per pair/strategy. Satisfies BKTS-01 "demonstrably corrected". | ✓ |
| No — just commit corrected numbers | Fix the code, run once, commit results. Delta is implicit from old values. | |

**User's choice:** Yes — show old vs new Sharpe comparison

---

| Option | Description | Selected |
|--------|-------------|----------|
| Skip last bar silently | Loop bound already handles it — i+1 is always valid. No special guard needed. | ✓ |
| Add explicit guard with comment | Add `if i+1 >= len(h1): continue` before entry. Defensive, self-documenting. | |
| Claude's discretion | Claude decides based on existing loop structure. | |

**User's choice:** Skip last bar silently

---

| Option | Description | Selected |
|--------|-------------|----------|
| Overwrite 730d entries with corrected numbers | Fix bias, re-run on 730d data, update pair_config.py, then add 4yr entries. | ✓ |
| Leave 730d alone — only add 4yr entries | Old 730d numbers stay as-is (biased but labelled). Phase 7 only adds 4yr. | |

**User's choice:** Overwrite 730d entries with corrected numbers

---

## PiT Validator Design

| Option | Description | Selected |
|--------|-------------|----------|
| Port V1 AST validator | Adapt pit_validator.py from V1/helix/src/quality/. Proven logic, minimal new code. | ✓ |
| Write a simpler targeted check | Focused script checking for 'entry_price = row[Close]' patterns. Narrower scope. | |
| Empirical PiT check | Run backtest on future window and verify Sharpe > 0. Behavior-based. | |

**User's choice:** Port V1 AST validator

---

| Option | Description | Selected |
|--------|-------------|----------|
| CLI script gate | Standalone script, exits non-zero on violations. Run manually before pair_config.py update. | ✓ |
| Wired into backtest runner | backtest_evaluate_all.py calls validator at startup. Automatic but slows every run. | |
| Pre-commit hook | Git pre-commit hook blocks commit if violations found. | |

**User's choice:** CLI script gate

---

| Option | Description | Selected |
|--------|-------------|----------|
| Flag only signal-bar price reads | Violations = reading price cols on current bar as entry. Next-bar reads whitelisted. | ✓ |
| Flag all unshifted price reads | Any price access without .shift(1) is a violation. Catches more but over-flags. | |
| Claude's discretion | Claude defines detection rules based on V1 source and fixed code patterns. | |

**User's choice:** Flag only signal-bar price reads (next-bar reads whitelisted)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Run against all backtest files | Validates fixed hybrid.py, evaluate_all.py, and any new 4yr scripts. | ✓ |
| Only against existing fixed files | Validate only the two files being fixed. New 4yr scripts out of scope. | |

**User's choice:** Run against all backtest files

---

## Walk-forward Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Single 4yr in-sample pass | Run full 4yr window once. Simple, interpretable, consistent with 730d methodology. | ✓ |
| Rolling walk-forward (VBT Splitter) | vbt.Splitter.from_rolling(), train/test windows, average OOS Sharpe. More robust but requires VBT API integration. | |
| Train/test split only | First 3yr = training, last 1yr = OOS test. Report both. | |

**User's choice:** Single 4yr in-sample pass

---

| Option | Description | Selected |
|--------|-------------|----------|
| Sharpe ≥ 0.5 | Conservative floor. Filters genuine underperformers. Matches existing pair_config.py pattern. | ✓ |
| Sharpe ≥ 1.0 | Higher bar. Only clearly profitable strategies enabled. May disable more pairs. | |
| No threshold — report all, user decides | Output table of results, user manually enables. More flexible, not automated. | |

**User's choice:** Sharpe ≥ 0.5 minimum threshold

---

| Option | Description | Selected |
|--------|-------------|----------|
| Sharpe + win rate + trade count | Matches existing pair_config.py fields. Trade count guards against sparse strategies. | ✓ |
| Sharpe only | Minimal, consistent with primary BKTS-02/03 requirement. | |
| Full stats: Sharpe, win rate, max drawdown, avg trade duration | Richer but requires new pair_config.py fields. | |

**User's choice:** Sharpe + win rate + trade count

---

| Option | Description | Selected |
|--------|-------------|----------|
| Replace 730d fields | 730d corrected anyway — overwrite with 4yr values. Same dataclass shape, better data. | ✓ |
| Add parallel 4yr fields | Keep 730d_sharpe and add 4yr_sharpe. More data but router complexity increases. | |

**User's choice:** Replace 730d fields with 4yr values

---

## 4yr Data Sourcing

| Option | Description | Selected |
|--------|-------------|----------|
| MT5 terminal via download_history.py | MetaTrader5 Python API. Same broker, same data as live. Consistent with existing 730d source. | ✓ |
| yfinance fallback | Free, no MT5 required. But data differs from broker (timezone, gaps, OHLC mismatch risk). | |
| Use 730d data only | Limit Phase 7 to 730d re-run. 4yr validation deferred to later phase. | |

**User's choice:** MT5 terminal via download_history.py

---

| Option | Description | Selected |
|--------|-------------|----------|
| 4yr H1 for all 5 pairs | Covers full Phase 7 scope. ~175k rows total. | ✓ |
| 4yr H1 for scalp/momentum pairs only | Only currently enabled pairs. Smaller dataset. | |
| 2yr H1 as compromise | More than 730d but less than 4yr. | |

**User's choice:** 4yr H1 for all 5 active pairs (AUDNZD, EURGBP, GBPJPY, EURUSD, USDJPY)

---

| Option | Description | Selected |
|--------|-------------|----------|
| New files with 4yr label | Save as AUDNZD_H1_4yr.csv. Keep 730d files intact. | ✓ |
| Overwrite 730d files | Replace existing files. Simpler but 730d data lost. | |

**User's choice:** New files with 4yr label (e.g., AUDNZD_H1_4yr.csv)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — skip if file exists | Idempotent. Safe to re-run. One download per pair, cached. | ✓ |
| Always re-download | Fresh data every run. Slow if re-running multiple times. | |

**User's choice:** Skip download if 4yr file already exists

---

## Claude's Discretion

- Exact script names for ported pit_validator.py and 4yr download runner
- Comparison report format (console table vs CSV vs both)
- MT5 connectivity failure handling in download_history.py
- Internal loop variable naming in fixed entry loops

## Deferred Ideas

- VBT Pro portfolio API migration — future phase
- Rolling walk-forward validation with VBT Splitter — after router is built
- V1 pit_manager.py (ArcticDB runtime temporal manager) — Phase 8 PiT port

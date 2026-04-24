# Phase 7: Backtest Entry Fix + H1/Momentum 4yr Validation - Research

**Researched:** 2026-04-24
**Domain:** Python backtesting engine — look-ahead bias correction, AST-based static analysis, MT5 data download, routing matrix update
**Confidence:** HIGH (all findings verified against live source code in this repository)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Entry Fix Scope**
- D-01: Fix all 3 loops — `backtest_hybrid.py` (swing + M15) and `backtest_evaluate_all.py` (scalp + momentum). Replace `px = row['Close']` → `h1.iloc[i+1]['Open']` as entry price in each.
- D-02: Produce a before/after Sharpe comparison report per pair/strategy to demonstrate the bias delta.
- D-03: Last-bar edge case handled silently by the existing loop bound — no explicit guard needed. The loop already stops at `len(data)-1` so `i+1` is always in range.
- D-04: After the fix, re-run on existing 730d data and overwrite current pair_config.py entries with corrected numbers before adding the 4yr entries. No biased numbers survive in the routing matrix.

**PiT Validator Design**
- D-05: Port the V1 AST-based static validator from `V1/helix/src/quality/pit_validator.py` into `V2/backtest/pit_validator.py`. Proven logic, minimal new code.
- D-06: Deploy as a CLI script gate — run manually before any pair_config.py update. Exits non-zero on violations; update is blocked. Not wired into the backtest runner or pre-commit hook.
- D-07: Detection scope — flag only signal-bar price reads. Next-bar reads like `h1.iloc[i+1]['Open']` are explicitly whitelisted — these are intentional fill simulation, not look-ahead bias.
- D-08: Validator runs against all backtest files: the fixed `backtest_hybrid.py`, `backtest_evaluate_all.py`, and any new 4yr evaluation scripts.

**Walk-forward Structure**
- D-09: Single 4yr in-sample pass — no rolling windows.
- D-10: Minimum Sharpe >= 0.5 to earn a routing matrix entry. Below threshold = `allow_scalp: false` / `allow_momentum: false`.
- D-11: Capture three metrics per pair/strategy entry: Sharpe, win rate, trade count.
- D-12: 4yr results replace the existing 730d fields in pair_config.py. Same dataclass shape, better data.

**4yr Data Sourcing**
- D-13: Fetch 4yr H1 data via MT5 terminal using `V2/scripts/download_history.py`.
- D-14: Fetch for all 5 active pairs: AUDNZD, EURGBP, GBPJPY, EURUSD, USDJPY.
- D-15: Save as `{PAIR}_H1_4yr.csv`. Keep existing 730d files intact.
- D-16: Idempotent download — skip pair if `{PAIR}_H1_4yr.csv` already exists.

### Claude's Discretion
- Exact script names for the ported pit_validator.py and the 4yr download runner
- Comparison report format (console table vs CSV vs both)
- How download_history.py detects and reports MT5 terminal connectivity failures
- Internal loop variable naming in the fixed entry loops

### Deferred Ideas (OUT OF SCOPE)
- VBT Pro portfolio API migration (`vbt.PF.from_signals()`)
- Rolling walk-forward validation (`vbt.Splitter.from_rolling()`)
- V1 `pit_manager.py` (ArcticDB runtime temporal manager)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BKTS-01 | backtest_hybrid.py uses next-bar-open entry for all strategy loops — fixes Sharpe inflation of 0.2–0.4 | Entry bias is confirmed in 3 loops across 2 files. Fix pattern is `px = h1.iloc[i+1]['Open']`. Loop bounds already safe. |
| BKTS-02 | H1 scalp strategy backtested on 4yr data across all active pairs → routing matrix entry in pair_config.py | `run_scalp_with_cfg()` in Evaluator is the target. `scalp_sharpe`, `scalp_win_rate`, `allow_scalp` fields exist in PairConfig. |
| BKTS-03 | Momentum strategy backtested on 4yr data across all active pairs → routing matrix entry in pair_config.py | `run_momentum_with_cfg()` in Evaluator is the target. `momentum_size_mult`, `allow_momentum` fields exist in PairConfig. |
| BKTS-04 | pit_validator.py wired as pass/fail gate — no new Sharpe number enters pair_config.py without PiT compliance | V1 AST validator is complete and portable. Whitelist pattern for `iloc[i+1]` must be added. CLI exit-code gate is the deployment model. |
</phase_requirements>

---

## Summary

Phase 7 is a surgical code repair and data production phase. There are no new frameworks to learn and no architectural decisions left open — the context decisions locked everything that matters. The work divides into four sequential tasks: (1) apply the entry-price fix to three strategy loops, (2) run before/after comparison on 730d data to document the bias delta, (3) fetch 4yr H1 data and run H1 scalp + momentum evaluation across all 5 active pairs, and (4) port the V1 PiT validator with a `iloc[i+1]` whitelist and commit gated pair_config.py updates.

The entry bias is confirmed by direct code inspection: every strategy loop in both backtest files assigns `px = row['Close']` on the signal bar and opens `position['entry_price'] = px` in the same iteration. This is the signal-bar close fill that inflates Sharpe by 0.2–0.4. The fix is a one-line change per loop: replace `px = row['Close']` with `px = h1.iloc[i+1]['Open']` (or `m15.iloc[i+1]['Open']` for the M15 loop). The loop bound `range(100, len(h1))` — combined with the existing `range(100, len(h1)-1)` pattern used in similar codebases — needs adjustment: the loop must stop at `len(data)-2` to ensure `i+1` always exists. This is the one guard the CONTEXT.md D-03 says is not needed IF the loop already stops at `len(data)-1`. Inspection shows the loops use `range(100, len(h1))` which iterates `i` up to `len(h1)-1`, making `h1.iloc[i+1]` an off-by-one at the last bar. The fix requires `range(100, len(h1)-1)` — one additional character, not an "explicit guard" in the complex-logic sense D-03 was describing.

The V1 PiT validator is a clean, self-contained 238-line AST visitor. Its `PRICE_COLUMNS` frozenset does not include `'open'` at the lowercase level — it does include `"open"`. The validator flags any `df['open']` without `.shift()`. After the entry fix, the backtest will contain `h1.iloc[i+1]['Open']` which uses a subscript with capital `'Open'` — not in the frozenset — so no false-positive from the capital-O form. However the validator also needs a whitelist for the `iloc[i+1]` subscript pattern to explicitly confirm it does not flag next-bar reads.

**Primary recommendation:** Fix the three `px = row['Close']` lines first, then run the before/after comparison immediately to confirm the Sharpe delta, then produce 4yr data and routing matrix entries, then port and gate with the PiT validator.

---

## Standard Stack

### Core (no new dependencies — all already installed in V2)

| Library | Version (in use) | Purpose | Why Standard |
|---------|-----------------|---------|--------------|
| pandas | installed in V2 venv | DataFrame operations in backtest loops | Already used throughout |
| numpy | installed in V2 venv | ATR, Z-score computations | Already used throughout |
| MetaTrader5 | installed in V2 venv | `copy_rates_range()` for 4yr H1 data | Same source as 730d files |
| ast (stdlib) | Python stdlib | AST parsing for PiT validator | Used in V1 validator — zero new deps |
| pytest | installed (pyproject.toml) | Test suite | Project standard — `testpaths = ["tests"]` |

### No new packages needed

Phase 7 adds zero new Python dependencies. All required libraries are present in the V2 virtual environment. The PiT validator port uses only `ast`, `dataclasses`, and `pathlib` — all stdlib.

---

## Architecture Patterns

### Recommended Project Structure after Phase 7

```
V2/
├── backtest/
│   ├── backtest_hybrid.py          # MODIFIED: 2 entry-price lines fixed (swing + M15)
│   ├── backtest_evaluate_all.py    # MODIFIED: 2 entry-price lines fixed (scalp + momentum)
│   ├── backtest_4yr_evaluate.py    # NEW: 4yr evaluation runner (H1 scalp + momentum)
│   ├── pit_validator.py            # NEW: ported from V1, with iloc[i+1] whitelist + CLI
│   └── reports/                   # existing — before/after comparison CSVs go here
├── scripts/
│   └── download_history.py        # MODIFIED: add 4yr fetch + idempotency + error handling
├── data/
│   ├── AUDNZD_H1_730d.csv         # existing — unchanged
│   ├── AUDNZD_H1_4yr.csv          # NEW (after download)
│   └── ...                        # same pattern for all 5 pairs
└── v3_intelligence/
    └── pair_config.py             # MODIFIED: 4yr Sharpe/win_rate/trade_count values
```

### Pattern 1: Next-Bar-Open Entry Fix (3 loops)

**What:** Replace signal-bar close fill with next-bar open fill in every strategy entry block.

**Files and exact locations:**

```
backtest_hybrid.py
  _backtest_swing_symbol():   line ~221  px = row['Close']
  _backtest_m15_symbol():     line ~354  px = row['Close']

backtest_evaluate_all.py (Evaluator class)
  run_scalp_with_cfg():       line ~178  px = row['Close']
  run_momentum_with_cfg():    line ~239  px = row['Close']
```

Note: `run_swing_with_cfg()` in Evaluator also has `px = row['Close']` at line ~119 but this method is the swing strategy used for the evaluation matrix comparison, not H1 scalp or momentum. It should also be fixed for consistency (D-01 says "all 3 loops" — swing+M15 in backtest_hybrid.py and scalp+momentum in backtest_evaluate_all.py; the swing in Evaluator is a 4th occurrence that should also be fixed to avoid biased swing comparison numbers).

**Before (biased):**
```python
# Source: V2/backtest/backtest_hybrid.py lines 213-222 (verified by direct inspection)
for i in range(100, len(h1)):
    row  = h1.iloc[i]
    ts   = h1.index[i]
    # ... other row extractions ...
    px   = row['Close']          # <-- BIAS: fills at signal-bar close
    # ...
    position = {
        'entry_price': px,       # <-- inflated Sharpe source
        # ...
    }
```

**After (corrected):**
```python
# Next-bar-open entry — loop bound adjusted to prevent off-by-one
for i in range(100, len(h1) - 1):
    row       = h1.iloc[i]
    next_row  = h1.iloc[i + 1]
    ts        = h1.index[i]
    # ... other row extractions (exit uses current px for P&L against live close) ...
    entry_px  = next_row['Open']   # fill simulation: next bar's open
    # ...
    position = {
        'entry_price': entry_px,
        # ...
    }
```

**Critical detail — exit price stays on current bar's close:** The exit logic checks `pnl = (px - ep) / ep` where `px = row['Close']`. This is correct — exits fire at the current bar's close when conditions are met. Only entry price changes. The exit `px` must remain `row['Close']`.

**Loop bound:** `range(100, len(h1))` must become `range(100, len(h1) - 1)`. With the original bound, `h1.iloc[len(h1)-1+1]` raises `IndexError`. The off-by-one drops exactly 1 bar from the tail, which is statistically irrelevant across 17k+ bars.

### Pattern 2: Before/After Comparison Report

**What:** Run the backtest on 730d data twice — once with the biased code (or captured from existing results) and once with the fixed code — and emit a side-by-side table.

**Recommended implementation:** A standalone `reports/compare_entry_bias.py` script or a flag `--compare-bias` in `backtest_evaluate_all.py` that:
1. Captures metrics dict from the biased run (can snapshot current `pair_config.py` values which are already biased)
2. Captures metrics dict from the fixed run
3. Emits a table: `Pair | Strategy | Old Sharpe | New Sharpe | Delta | Old Win% | New Win% | Old Trades | New Trades`
4. Saves as both console output and `reports/entry_bias_comparison_YYYY-MM-DD.csv`

**Implementation note:** Since the "before" state is already recorded in the current `pair_config.py` notes (AUDNZD H1 Scalp Sh 1.63, EURGBP Momentum Sh 1.57, etc.), a simpler approach is to just run the fixed version and show `OLD (730d biased)` from hardcoded values vs `NEW (730d corrected)`.

### Pattern 3: 4yr Data Download with Idempotency

**What:** Extend `download_history.py` to produce `{PAIR}_H1_4yr.csv` files.

```python
# Source: V2/scripts/download_history.py (extended pattern)
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

DATA_DIR = Path(__file__).parent.parent / "data"
ACTIVE_PAIRS = ["AUDNZD", "EURGBP", "GBPJPY", "EURUSD", "USDJPY"]
END_DATE   = datetime.now()
START_DATE = END_DATE - timedelta(days=4 * 365 + 1)   # ~4yr including leap days

def download_4yr_h1(output_dir: Path = DATA_DIR) -> None:
    if not mt5.initialize():
        print(f"ERROR: MT5 init failed — {mt5.last_error()}", file=sys.stderr)
        sys.exit(1)

    for symbol in ACTIVE_PAIRS:
        out_path = output_dir / f"{symbol}_H1_4yr.csv"
        if out_path.exists():
            print(f"  SKIP {symbol} — {out_path.name} already exists (idempotent)")
            continue

        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, START_DATE, END_DATE)
        if rates is None or len(rates) == 0:
            print(f"  FAIL {symbol} — {mt5.last_error()}", file=sys.stderr)
            continue

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.to_csv(out_path, index=False)
        print(f"  OK   {symbol} — {len(df)} bars → {out_path.name}")

    mt5.shutdown()
```

**MT5 connectivity failure handling (Claude's discretion recommendation):** Use `mt5.initialize()` return value check with `sys.exit(1)` so the caller can detect failure. Print `mt5.last_error()` for every failed `copy_rates_range()`. Do not silently skip — print `FAIL` prefix so the user sees partial downloads.

**Expected bar counts:** 4 years of H1 FOREX data, excluding weekends: ~4 × 52 × 5 × 24 = ~24,960 bars per pair. Actual counts will be slightly lower due to holidays and broker data gaps. The existing 730d files show ~17,356 bars for AUDNZD over ~3 years (2023-2026), which aligns.

### Pattern 4: PiT Validator Port with Whitelist

**What:** Copy V1's `PiTValidator` into `V2/backtest/pit_validator.py`, add a `iloc[i+1]` whitelist, and add a `__main__` CLI block.

**Key insight from V1 source inspection:** The V1 validator's `_check_assignment_value()` walks the entire RHS of an assignment. After the entry fix, the problematic line becomes:

```python
entry_px = next_row['Open']    # where next_row = h1.iloc[i+1]
```

This is an assignment where the RHS is `next_row['Open']`. The validator sees `ast.Subscript(slice=Constant('Open'))`. Since `'Open'` (capital O) is not in `PRICE_COLUMNS` (which contains lowercase `"open"`), this would NOT be flagged even without a whitelist.

However, if the implementer uses `h1.iloc[i+1]['Open']` directly (without extracting to `next_row`), the RHS is `h1.iloc[i+1]['Open']` — still a subscript with `'Open'` (capital O), still not in `PRICE_COLUMNS`. Safe.

The V1 validator also does NOT flag: `row['Close']` used for EXIT price checks (because `px = row['Close']` in the exit block will still exist — that's the current-bar close used for P&L calculation, not entry price). Wait — this IS a violation by the validator's logic: `px = row['Close']` without `.shift()` is flagged because `'close'` is in `PRICE_COLUMNS`... but `'Close'` (capital C) is NOT in the frozenset.

**Critical finding:** The V1 validator's `PRICE_COLUMNS` uses all-lowercase strings (`"close"`, `"open"`, `"high"`, `"low"`). The project's DataFrames use pandas-convention capitalized columns (`'Close'`, `'Open'`, etc.). This means the V1 validator as-is will NOT flag `row['Close']` because `'Close' != 'close'`. The validator would be a no-op against the actual codebase unless `PRICE_COLUMNS` is updated.

**Resolution for D-07 (detection scope):** The ported validator should expand `PRICE_COLUMNS` to include both cases (`'Close'`, `'Open'`, `'High'`, `'Low'`, `'close'`, `'open'`, `'high'`, `'low'`). Then the `iloc[i+1]['Open']` whitelist must be implemented by checking whether the subscript's parent chain includes an `iloc` subscript with a non-zero index argument.

**Recommended whitelist implementation:**

```python
# In V2/backtest/pit_validator.py — extended from V1
def _is_next_bar_read(node: ast.expr) -> bool:
    """Return True if the subscript is on a .iloc[i+1] or .iloc[i-1] access.
    
    Whitelisted pattern: df.iloc[i+1]['Open']  — intentional next-bar fill.
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Subscript):
            # Check if sub.value is itself an iloc subscript
            val = sub.value
            if (isinstance(val, ast.Subscript)
                    and isinstance(val.value, ast.Attribute)
                    and val.value.attr == 'iloc'):
                # The slice of the iloc call should be i+1 (BinOp with Add)
                iloc_slice = val.slice
                if isinstance(iloc_slice, ast.BinOp) and isinstance(iloc_slice.op, ast.Add):
                    return True
    return False
```

Then in `_check_assignment_value`, skip price subscripts where `_is_next_bar_read(value)` is True.

**CLI gate block:**

```python
if __name__ == "__main__":
    import sys
    from pathlib import Path

    targets = [Path(p) for p in sys.argv[1:]] if sys.argv[1:] else [
        Path(__file__).parent / "backtest_hybrid.py",
        Path(__file__).parent / "backtest_evaluate_all.py",
    ]
    validator = PiTValidator()
    all_violations = []
    for t in targets:
        if t.is_dir():
            all_violations.extend(validator.validate_directory(t))
        else:
            all_violations.extend(validator.validate_file(t))

    if all_violations:
        for v in all_violations:
            print(f"VIOLATION {v.file}:{v.line} — {v.message}")
        sys.exit(1)
    else:
        print(f"PiT check PASSED — {len(targets)} file(s) clean")
        sys.exit(0)
```

### Pattern 5: 4yr Routing Matrix Update in pair_config.py

**What:** After the 4yr backtest runs, update `PAIR_CONFIGS` dict entries for the 5 active pairs (AUDNZD, EURGBP, GBPJPY, EURUSD, USDJPY) with:
- `allow_scalp` / `allow_momentum` flags set by Sharpe >= 0.5 threshold (D-10)
- `scalp_size_mult` / `momentum_size_mult` updated if needed
- `notes` field updated with 4yr numbers

**The dataclass already has all required fields** — no schema change. The update is a data substitution, not a structural change.

**Fields to update per active pair:**

| Field | Strategy | Source |
|-------|----------|--------|
| `allow_scalp` | H1 scalp | `run_scalp_with_cfg()` result: Sharpe >= 0.5 |
| `scalp_sharpe` (notes field only) | H1 scalp | Computed from 4yr run |
| `allow_momentum` | Momentum | `run_momentum_with_cfg()` result: Sharpe >= 0.5 |
| `notes` | Both | Updated string with 4yr Sharpe values and trade counts |

Note: `PairConfig` has no explicit `scalp_sharpe` field — Sharpe is documented in the `notes` string only. The routing matrix "entry" is the combination of `allow_scalp=True/False` and the flags/multipliers. The planner should include a task to update `notes` with the 4yr numbers as evidence of the run.

### Anti-Patterns to Avoid

- **Fixing only one file:** Both `backtest_hybrid.py` AND `backtest_evaluate_all.py` have the bias. Missing `backtest_evaluate_all.py` means the scalp/momentum 4yr numbers are still biased.
- **Not adjusting loop bound:** `range(100, len(h1))` with `h1.iloc[i+1]` causes an IndexError on the last iteration. The fix requires `range(100, len(h1) - 1)`.
- **Using exit price for entry:** The `px = row['Close']` used in the exit P&L calculation block is NOT look-ahead bias — it's the current bar's close as exit fill. Only the ENTRY `position['entry_price'] = px` assignment is the bug.
- **Validator case mismatch:** V1 validator uses lowercase column names. Project uses pandas Title-case columns. Expanding `PRICE_COLUMNS` to include both cases is required for the validator to detect anything.
- **Committing pair_config.py without running validator:** The PiT gate is manual (D-06). The workflow must be: fix → run validator (exit 0) → run backtest → update pair_config.py.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AST parsing for look-ahead detection | Custom regex scanner | `ast` stdlib + existing V1 `PiTValidator` class | AST is accurate; regex misses multi-line expressions and string interpolation |
| Sharpe calculation | Custom formula | Existing `_metrics()` in `backtest_hybrid.py` and `metrics()` in `backtest_evaluate_all.py` | Already implemented and used — reuse for 4yr runs |
| 4yr data fetch | Manual CSV construction | `mt5.copy_rates_range()` via existing `download_history.py` pattern | Same data source as 730d files; proven MT5 API usage in this repo |
| Before/after comparison | Separate full backtest rerun | Snapshot current pair_config.py values as "before" baseline | The current biased values ARE the before-state — no need to re-run the biased version |

**Key insight:** The before-state is already recorded. `pair_config.py` notes field contains the biased 730d Sharpe numbers (e.g., AUDNZD H1 scalp 1.63, EURGBP momentum 1.57). The comparison report only needs to re-run the fixed code on 730d and diff against these recorded values.

---

## Common Pitfalls

### Pitfall 1: IndexError at Last Bar
**What goes wrong:** After changing `px = row['Close']` to `px = h1.iloc[i+1]['Open']`, the loop iterates to `i = len(h1)-1`, causing `h1.iloc[len(h1)]` — an IndexError.
**Why it happens:** `range(100, len(h1))` produces `i` up to `len(h1)-1`. `iloc[i+1]` at that point is out of bounds.
**How to avoid:** Change loop bound to `range(100, len(h1) - 1)`. This drops the last bar only, which has zero statistical impact over 4yr data.
**Warning signs:** `IndexError: single positional indexer is out-of-bounds` during any test run.

### Pitfall 2: Fixing Entry But Not Exit Prices
**What goes wrong:** Confusing the exit P&L check `px = row['Close']` (used as current-bar exit price in position checks) with the entry fill `px` that opens a position.
**Why it happens:** Both use the variable name `px` in the same loop body. The exit block runs first (`if position is not None:`), then the entry block (`elif position is None:`).
**How to avoid:** Only change the `px` inside the `elif position is None:` entry block. The exit block's `px = row['Close']` is correct and must remain unchanged. Rename the entry variable to `entry_px` to make the distinction explicit.
**Warning signs:** Win rate drops to near-zero or trade P&L becomes unrealistic after the fix.

### Pitfall 3: PiT Validator Flags Legitimate Next-Bar Reads
**What goes wrong:** After adding Title-case to `PRICE_COLUMNS`, the validator flags `h1.iloc[i+1]['Open']` as a violation because `'Open'` is now in the frozenset.
**Why it happens:** The validator checks the entire RHS for price subscripts without distinguishing position in the index chain.
**How to avoid:** Implement `_is_next_bar_read()` whitelist function (see Pattern 4 above). The whitelist checks that the subscript's parent is an `iloc[i+1]`-style access (BinOp with Add operator).
**Warning signs:** Validator exits non-zero against the fixed backtest files.

### Pitfall 4: 4yr Data Not Available via MT5 (connectivity)
**What goes wrong:** `mt5.copy_rates_range()` returns None when MT5 terminal is not running or the IC Markets server history doesn't extend to the requested start date.
**Why it happens:** MT5 Python API requires a live MT5 terminal running on the same machine (Windows only or via Wine). IC Markets historical data availability varies by instrument.
**How to avoid:** Download script should check `rates is None` and print a clear error. The fallback is to use the existing `AUDNZD_H1.csv` file (2022-2026, ~1,615 bars) as a supplement if 4yr MT5 data is unavailable for a specific pair.
**Warning signs:** `mt5.last_error()` returns a non-zero code after `copy_rates_range()`.

### Pitfall 5: Scalp/Momentum Trade Count Too Low for Sharpe Significance
**What goes wrong:** A pair shows Sharpe >= 0.5 but only from 8-12 trades over 4yr. The Sharpe is statistically meaningless.
**Why it happens:** H1 scalp and momentum strategies require Z-score extremes AND session alignment AND daily Z alignment. Some pairs may have very few signal coincidences.
**How to avoid:** The `_verdict()` function in `backtest_evaluate_all.py` already applies a `n < 10` threshold returning "INSUFFICIENT". Apply the same floor in the 4yr evaluation: require trade_count >= 20 for a routing matrix entry (stricter than 730d since we have more data to expect more trades).
**Warning signs:** `allow_scalp=True` set on a pair with fewer than 20 trades in 4yr.

### Pitfall 6: pair_config.py Update Without PiT Gate
**What goes wrong:** New Sharpe numbers are committed to pair_config.py before running the PiT validator, allowing a biased number to persist.
**Why it happens:** Manual process with no enforcement (D-06 says CLI only, not pre-commit hook).
**How to avoid:** Document the mandatory sequence in the task: (1) run `python pit_validator.py` and confirm exit 0, (2) only then update pair_config.py. Task verification step should include `python pit_validator.py; echo $?` must equal 0.
**Warning signs:** Sharpe numbers in pair_config.py are suspiciously higher than expected (>2.0 for scalp/momentum, which historically run at 0.5-1.6 on 730d data).

---

## Code Examples

### Entry Fix — Exact Change in backtest_hybrid.py `_backtest_swing_symbol`

```python
# Source: V2/backtest/backtest_hybrid.py (verified lines 213–290)
# BEFORE (biased):
for i in range(100, len(h1)):
    row  = h1.iloc[i]
    ts   = h1.index[i]
    # ...
    px   = row['Close']          # signal-bar close — biased fill

# AFTER (corrected):
for i in range(100, len(h1) - 1):   # -1 guard for i+1 access
    row      = h1.iloc[i]
    next_row = h1.iloc[i + 1]
    ts       = h1.index[i]
    # ...
    px       = row['Close']          # exit price — unchanged, correct
    entry_px = next_row['Open']      # next-bar open — unbiased fill

# In entry block:
# BEFORE:
position = {'entry_price': px, ...}
# AFTER:
position = {'entry_price': entry_px, ...}
```

### Entry Fix — Exact Change in `backtest_evaluate_all.py` `run_scalp_with_cfg`

```python
# Source: V2/backtest/backtest_evaluate_all.py (verified lines 175–211)
# BEFORE:
for i in range(100, len(h1)):
    row  = h1.iloc[i]; ts = h1.index[i]
    h1z  = row['z_score']; dz = row['daily_z']; atr = row['atr']
    px   = row['Close']; cp = ...
    
    # exit uses px  ← CORRECT (current bar close)
    # entry:
    position = {'type': pt, 'entry_price': px, ...}   # ← BIASED

# AFTER:
for i in range(100, len(h1) - 1):
    row      = h1.iloc[i]; next_row = h1.iloc[i + 1]
    ts       = h1.index[i]
    h1z      = row['z_score']; dz = row['daily_z']; atr = row['atr']
    px       = row['Close']; cp = ...
    entry_px = next_row['Open']
    
    # exit uses px  ← CORRECT (unchanged)
    # entry:
    position = {'type': pt, 'entry_price': entry_px, ...}   # ← CORRECTED
```

### download_history.py Idempotent 4yr Fetch

```python
# Source pattern: V2/scripts/download_history.py (extended)
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"

def fetch_4yr(data_dir: Path = DATA_DIR) -> dict[str, bool]:
    """Returns {symbol: success_bool}. Skips if file exists."""
    end   = datetime.now()
    start = end - timedelta(days=4 * 365 + 2)  # +2 for leap-year buffer
    results = {}
    for sym in ["AUDNZD", "EURGBP", "GBPJPY", "EURUSD", "USDJPY"]:
        out = data_dir / f"{sym}_H1_4yr.csv"
        if out.exists():
            print(f"  SKIP {sym} ({out.name} exists)")
            results[sym] = True; continue
        rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_H1, start, end)
        if rates is None or len(rates) == 0:
            print(f"  FAIL {sym}: {mt5.last_error()}")
            results[sym] = False; continue
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.to_csv(out, index=False)
        print(f"  OK   {sym}: {len(df)} bars → {out.name}")
        results[sym] = True
    return results
```

### backtest_4yr_evaluate.py — 4yr runner pattern

```python
# New file: V2/backtest/backtest_4yr_evaluate.py
# Follows exact same pattern as backtest_evaluate_all.py but loads _H1_4yr.csv files

DATA_DIR = Path(__file__).parent.parent / "data"
ACTIVE_PAIRS = ["AUDNZD", "EURGBP", "GBPJPY", "EURUSD", "USDJPY"]

def _load_h1_4yr(sym: str) -> pd.DataFrame | None:
    f = DATA_DIR / f"{sym}_H1_4yr.csv"
    return pd.read_csv(f, index_col=0, parse_dates=True) if f.exists() else None

# Run scalp + momentum only (H1 scalp and momentum are the BKTS-02/03 targets)
# Reuse Evaluator.run_scalp_with_cfg() and run_momentum_with_cfg() directly
# Output: routing_matrix dict → print table + save CSV → update pair_config.py manually
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Signal-bar close entry (look-ahead) | Next-bar open entry | Phase 7 (this phase) | Reduces Sharpe by 0.2-0.4 to honest values |
| 730d validation window | 4yr validation window | Phase 7 (this phase) | ~5.5x more data; statistically stronger routing matrix |
| No PiT gate on pair_config.py | CLI PiT validator as gate | Phase 7 (this phase) | Prevents future biased numbers from entering routing matrix |

**Existing values in pair_config.py (730d, biased) — these will be overwritten:**

| Pair | H1 Scalp Sharpe (biased 730d) | Momentum Sharpe (biased 730d) |
|------|-------------------------------|-------------------------------|
| AUDNZD | 1.63 | 0.55 |
| EURGBP | 1.32 | 1.57 |
| GBPJPY | 0.85 (borderline, disabled) | 0.21 (disabled) |
| EURUSD | -0.17 (disabled) | -1.03 (disabled) |
| USDJPY | -2.34 (disabled) | -1.61 (disabled) |

After the entry fix and re-run, expect corrected 730d Sharpe values to be 0.2-0.4 lower for positive strategies (AUDNZD, EURGBP). The 4yr values may differ further due to different market regimes covered.

---

## Open Questions

1. **H1_4yr data availability via MT5 on Linux+Wine**
   - What we know: MT5 terminal must be running. The Phase 6 gate confirmed coke5151 fork works on Ubuntu+Wine with IC Markets MT5 build 5800.
   - What's unclear: Whether `mt5.copy_rates_range()` with a 2022 start date (4yr back from 2026) returns full history or truncated history for all 5 pairs on IC Markets.
   - Recommendation: Download script should validate bar count > 20,000 and warn if under 15,000. If any pair fails, document which pairs succeeded and which need manual fallback.

2. **Trade count floor for 4yr routing matrix entries**
   - What we know: D-10 says Sharpe >= 0.5 is the threshold. D-11 says capture trade count.
   - What's unclear: What minimum trade count is required for the Sharpe to be considered reliable over 4yr? The existing `_verdict()` uses n < 10 = "INSUFFICIENT" for 730d.
   - Recommendation: Use n >= 30 for 4yr data (more data = higher expectation of trades). Planner should add this as a verification criterion.

3. **Evaluator's `run_swing_with_cfg()` — fix or leave?**
   - What we know: D-01 specifies "swing + M15" loops in `backtest_hybrid.py` and "scalp + momentum" in `backtest_evaluate_all.py`. The Evaluator's `run_swing_with_cfg()` (also in `backtest_evaluate_all.py`) has the same `px = row['Close']` bias.
   - What's unclear: Whether the before/after comparison requires fixing the swing loop in Evaluator (it does if the comparison runs through the Evaluator's swing method).
   - Recommendation: Fix all four `px = row['Close']` occurrences (the 3 in the decision + the swing in Evaluator) for complete consistency. This costs one additional line change.

---

## Validation Architecture

`workflow.nyquist_validation` is not set to false in `.planning/config.json` (key is absent). Validation section is included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (configured in `V2/pyproject.toml`) |
| Config file | `V2/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd V2 && python -m pytest tests/unit_tests/backtest/ -v -x` |
| Full suite command | `cd V2 && python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BKTS-01 | Entry price is next-bar open, not signal-bar close | unit | `pytest tests/unit_tests/backtest/test_entry_fix.py -x` | Wave 0 |
| BKTS-01 | Sharpe delta is measurable (new < old) | unit | `pytest tests/unit_tests/backtest/test_entry_fix.py::test_sharpe_delta -x` | Wave 0 |
| BKTS-02 | H1 scalp produces routing matrix entry for each active pair | unit | `pytest tests/unit_tests/backtest/test_4yr_evaluate.py::test_scalp_routing_matrix -x` | Wave 0 |
| BKTS-03 | Momentum produces routing matrix entry for each active pair | unit | `pytest tests/unit_tests/backtest/test_4yr_evaluate.py::test_momentum_routing_matrix -x` | Wave 0 |
| BKTS-04 | pit_validator exits 0 on clean files, non-zero on biased files | unit | `pytest tests/unit_tests/backtest/test_pit_validator.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2 && python -m pytest tests/unit_tests/backtest/ -v -x`
- **Per wave merge:** `cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2 && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `V2/tests/unit_tests/backtest/__init__.py` — package init for new test subdir
- [ ] `V2/tests/unit_tests/backtest/test_entry_fix.py` — covers BKTS-01: synthetic DataFrame verifies entry_price == next_bar_open; Sharpe comparison with deterministic P&L sequence
- [ ] `V2/tests/unit_tests/backtest/test_pit_validator.py` — covers BKTS-04: validator returns violations on biased code, zero violations on fixed code, zero violations on `iloc[i+1]` whitelist pattern
- [ ] `V2/tests/unit_tests/backtest/test_4yr_evaluate.py` — covers BKTS-02/03: with mock 4yr data, run_scalp_with_cfg and run_momentum_with_cfg return non-empty DataFrames and metrics dicts with expected keys

The existing `V2/tests/unit_tests/bridge/` tests provide the exact structural pattern to follow (imports, fixture style, no external deps in unit tests).

---

## Sources

### Primary (HIGH confidence — verified by direct file inspection)

- `V2/backtest/backtest_hybrid.py` — confirmed 2 biased `px = row['Close']` locations (swing loop line ~221, M15 loop line ~354); loop bounds `range(100, len(h1))` verified
- `V2/backtest/backtest_evaluate_all.py` — confirmed biased entry in `run_scalp_with_cfg()` line ~178 and `run_momentum_with_cfg()` line ~239; additional occurrence in `run_swing_with_cfg()` line ~119
- `V1/helix/src/quality/pit_validator.py` — full source reviewed; `PRICE_COLUMNS` frozenset confirmed lowercase-only; `ast.NodeVisitor` pattern verified; 238 lines total
- `V2/v3_intelligence/pair_config.py` — `PairConfig` dataclass fields confirmed; no `scalp_sharpe` numeric field exists (Sharpe in `notes` string only); current biased Sharpe values recorded in comments
- `V2/scripts/download_history.py` — existing MT5 download pattern confirmed; no idempotency or error handling currently present
- `V2/pyproject.toml` — pytest config confirmed; `testpaths = ["tests"]`, `asyncio_mode = "auto"`, markers include `pit_check`
- `V2/data/AUDNZD_H1_730d.csv` — date range 2023-07-04 to 2026-04-20, 17,356 rows confirmed

### Secondary (MEDIUM confidence)

- MT5 `copy_rates_range()` API — documented in MetaTrader5 Python package; behavior on Linux+Wine confirmed operational in Phase 6 (BRDG-03 gate passed)

### Tertiary (LOW confidence — training data, not verified against current IC Markets)

- 4yr H1 data availability: IC Markets historical data typically extends back 10+ years for major pairs but availability on the server depends on broker configuration at the time of request

---

## Metadata

**Confidence breakdown:**
- Entry bias locations and fix pattern: HIGH — verified by direct source code inspection
- PiT validator port strategy: HIGH — V1 source read in full; case-sensitivity issue discovered and documented
- Loop bound off-by-one: HIGH — confirmed by reading range() argument and iloc indexing pattern
- 4yr data download: MEDIUM — MT5 API confirmed working on this machine (Phase 6); bar count estimates from extrapolation
- Routing matrix update: HIGH — PairConfig dataclass fields confirmed present

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (stable codebase; only risk is MT5 API changes, which are rare)

# Phase 7: Backtest Entry Fix + H1/Momentum 4yr Validation - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the entry price bias in all strategy loops (signal-bar close → next-bar open), then run H1 scalp and Momentum strategies over 4yr data for all 5 active pairs and commit trusted Sharpe + win rate + trade count entries to the routing matrix in pair_config.py — gated by a ported PiT validator. Strategy router and regime detection are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Entry Fix Scope
- **D-01:** Fix all 3 loops — `backtest_hybrid.py` (swing + M15) and `backtest_evaluate_all.py` (scalp + momentum). Replace `px = row['Close']` → `h1.iloc[i+1]['Open']` as entry price in each.
- **D-02:** Produce a before/after Sharpe comparison report per pair/strategy to demonstrate the bias delta. This satisfies BKTS-01's "demonstrably corrected" success criterion.
- **D-03:** Last-bar edge case handled silently by the existing loop bound — no explicit guard needed. The loop already stops at `len(data)-1` so `i+1` is always in range.
- **D-04:** After the fix, re-run on existing 730d data and overwrite current pair_config.py entries with corrected numbers before adding the 4yr entries. No biased numbers survive in the routing matrix.

### PiT Validator Design
- **D-05:** Port the V1 AST-based static validator from `V1/helix/src/quality/pit_validator.py` into `V2/backtest/pit_validator.py`. Proven logic, minimal new code.
- **D-06:** Deploy as a CLI script gate — run manually before any pair_config.py update. Exits non-zero on violations; update is blocked. Not wired into the backtest runner or pre-commit hook.
- **D-07:** Detection scope — flag only signal-bar price reads (reading Close/Open/High/Low on the current bar as entry price). Next-bar reads like `h1.iloc[i+1]['Open']` are explicitly whitelisted — these are intentional fill simulation, not look-ahead bias.
- **D-08:** Validator runs against all backtest files: the fixed `backtest_hybrid.py`, `backtest_evaluate_all.py`, and any new 4yr evaluation scripts added in this phase.

### Walk-forward Structure
- **D-09:** Single 4yr in-sample pass — no rolling windows. Run the full 4yr dataset once per strategy per pair. Simple, interpretable, consistent with the existing 730d methodology.
- **D-10:** Minimum Sharpe ≥ 0.5 to earn a routing matrix entry. Below threshold = `allow_scalp: false` / `allow_momentum: false` for that pair. Matches the filtering pattern in the existing pair_config.py.
- **D-11:** Capture three metrics per pair/strategy entry: Sharpe, win rate, trade count. Consistent with existing pair_config.py fields. Trade count guards against strategies with high Sharpe from few lucky trades.
- **D-12:** 4yr results replace the existing 730d fields in pair_config.py. No parallel `4yr_sharpe` fields — same dataclass shape, better data.

### 4yr Data Sourcing
- **D-13:** Fetch 4yr H1 data via MT5 terminal using `V2/scripts/download_history.py` (MetaTrader5 Python API). Same broker, same data as live trading. Consistent with existing 730d data source.
- **D-14:** Fetch for all 5 active pairs: AUDNZD, EURGBP, GBPJPY, EURUSD, USDJPY. ≈ 4yr × 5 pairs × 8,760 bars = ~175k rows total.
- **D-15:** Save as new files with 4yr label: `AUDNZD_H1_4yr.csv`, `EURGBP_H1_4yr.csv`, etc. Keep existing 730d files intact as reference. Backtest scripts updated to load 4yr files when available.
- **D-16:** Idempotent download — skip pair if `{PAIR}_H1_4yr.csv` already exists. Safe to re-run during development.

### Claude's Discretion
- Exact script names for the ported pit_validator.py and the 4yr download runner
- Comparison report format (console table vs CSV vs both)
- How download_history.py detects and reports MT5 terminal connectivity failures
- Internal loop variable naming in the fixed entry loops

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` §BKTS — BKTS-01 through BKTS-04 definitions (entry fix, H1 scalp routing, momentum routing, PiT gate)
- `.planning/ROADMAP.md` §Phase 7 — Goal, success criteria, and dependency on Phase 6 bridge schema

### Backtest Engine (files to fix)
- `V2/backtest/backtest_hybrid.py` — Main backtest engine; swing (Strategy 1) and M15 intraday (Strategy 2) loops with `px = row['Close']` bias
- `V2/backtest/backtest_evaluate_all.py` — `Evaluator` class; `run_scalp_with_cfg()` and `run_momentum_with_cfg()` loops with same bias

### Routing Matrix (target)
- `V2/v3_intelligence/pair_config.py` — `PairConfig` dataclass; current 730d Sharpe/win rate fields for scalp and momentum; `allow_scalp` / `allow_momentum` flags

### PiT Validator (port source)
- `V1/helix/src/quality/pit_validator.py` — V1 AST-based static validator; port this into V2/backtest/

### 4yr Data Download
- `V2/scripts/download_history.py` — MetaTrader5 Python API download script; extend for 4yr H1 fetch with idempotency check

### Phase 6 Data Contract (context)
- `.planning/phases/06-zmq-bridge-port/06-CONTEXT.md` §D-14, D-15 — D1/H1/M15 bar-close publish schema; backtest OHLCV fields must match bridge event fields

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backtest_evaluate_all.py` `Evaluator` class: Already has `run_scalp_with_cfg()` and `run_momentum_with_cfg()` — entry fix is a targeted 2-line change per method, not a rewrite
- `V2/scripts/download_history.py`: Existing MT5 download script to extend with 4yr H1 parameters and skip-if-exists logic
- `V1/helix/src/quality/pit_validator.py`: AST validator with `PRICE_COLUMNS` detection — port candidate, not rewrite

### Established Patterns
- `pair_config.py` `PairConfig` dataclass: Fields `scalp_sharpe`, `scalp_win_rate`, `allow_scalp` (and momentum equivalents) already exist — Phase 7 updates their values, not their shape
- 730d data naming: `{PAIR}_H1_730d.csv` — new 4yr files follow same pattern as `{PAIR}_H1_4yr.csv`
- Backtest strategy loop structure: `for i in range(100, len(h1)): row = h1.iloc[i]; px = row['Close']` — uniform pattern across all 3 loops, one fix covers all

### Integration Points
- `pair_config.py` is the single handoff point: backtest writes Sharpe/win rate/trade count → router reads enable flags
- PiT validator gate is a manual pre-commit CLI step — not wired into import chain or CI

</code_context>

<specifics>
## Specific Ideas

- Before/after comparison report should show old (biased) Sharpe vs new (corrected) Sharpe side-by-side per pair per strategy — concrete evidence for BKTS-01
- 730d corrected numbers are an intermediate step: run corrected backtest on 730d first, capture delta, then run on 4yr for the final committed values

</specifics>

<deferred>
## Deferred Ideas

- VBT Pro portfolio API migration (`vbt.PF.from_signals()`) — user chose surgical fix for this phase; full engine migration is its own future phase
- Rolling walk-forward validation (`vbt.Splitter.from_rolling()`) — single 4yr pass chosen for now; walk-forward belongs in a robustness phase after router is built
- V1 `pit_manager.py` (ArcticDB runtime temporal manager) — heavier tool, not needed for Phase 7 static validation; relevant for Phase 8 PiT port

</deferred>

---

*Phase: 07-backtest-entry-fix-h1-momentum-4yr-validation*
*Context gathered: 2026-04-24*

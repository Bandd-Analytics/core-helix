---
phase: 7
slug: backtest-entry-fix-h1-momentum-4yr-validation
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-24
---

# Phase 7 — UI Design Contract

> Visual and interaction contract for Phase 7. Phase 7 is a CLI-only phase — no web
> frontend exists and MONI-01 (live dashboard) is explicitly deferred to v3.0+.
> "UI" here means terminal output contracts: console formatting, report structure,
> error copy, and CTA labels for the CLI gate scripts.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | none — CLI/terminal only |
| Icon library | none — ASCII prefix characters used instead (see Copywriting) |
| Font | monospace (terminal default — no prescription needed) |

**Rationale (pre-populated from RESEARCH.md §Standard Stack):** Phase 7 adds zero new
Python dependencies. All outputs are console text or CSV files. No React/Next.js/Vite
stack is present in V2. The `components.json` file does not exist and is not applicable.

**shadcn gate result:** Not applicable — stack is Python CLI, not a web framework.

---

## Spacing Scale

Not applicable as a pixel grid. Equivalent CLI layout rules:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 2 spaces | Indent continuation lines within a log entry |
| sm | 4 spaces | Column alignment padding in tabular console output |
| md | 1 blank line | Separation between output sections |
| lg | 2 blank lines | Separation between major script phases (download → validate → report) |
| xl | ASCII rule (dashes) | Section header dividers in console report (`---`) |

Exceptions: none

---

## Typography

Console output typography is fixed-width by definition. The contract governs
text structure and prefix characters, not font metrics.

| Role | Format | Weight | Usage |
|------|--------|--------|-------|
| Section heading | ALL CAPS prefix line | bold (via print) | Script phase announcements (`ENTRY FIX REPORT`, `PiT VALIDATION`) |
| Status line | `  OK / SKIP / FAIL / WARN` prefix | normal | Per-item download/validation results |
| Data row | `  {PAIR:<8} {value:>8}` aligned columns | normal | Sharpe/win-rate/trade-count table rows |
| Error message | `ERROR: {problem} — {action}` | normal | Terminal errors (see Copywriting) |

Line height: single-spaced (terminal default). No exceptions.

---

## Color

No color rendering is prescribed — the scripts must produce clean output on
terminals with or without ANSI color support (IC Markets server may be headless).

Semantic signal is carried by prefix strings, not color:

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | terminal background (unset) | All standard output lines |
| Secondary (30%) | terminal background (unset) | No distinction from dominant in CLI |
| Accent (10%) | `OK` prefix string | Download success, validator PASS lines |
| Destructive | `FAIL` / `ERROR` prefix string | Download failure, validator VIOLATION lines |

Accent reserved for: `OK` prefix on per-pair download success lines; `PASS` on
pit_validator exit-0 summary. Never used on neutral informational lines.

---

## Copywriting Contract

All copy is for CLI scripts only. Each entry is the exact string to print.

### download_history.py (4yr fetch)

| Element | Copy |
|---------|------|
| Primary CTA | `python scripts/download_history.py --4yr` (the command the developer runs) |
| Skip line | `  SKIP {PAIR} — {filename} already exists (idempotent)` |
| Success line | `  OK   {PAIR} — {N} bars → {filename}` |
| Failure line | `  FAIL {PAIR} — {mt5_error_code}: {mt5_error_message}` |
| Init error | `ERROR: MT5 init failed — {mt5.last_error()}. Ensure MT5 terminal is running.` |
| Low bar count warning | `  WARN {PAIR} — only {N} bars returned (expected ≥ 20,000). Check broker history.` |
| Summary line | `Download complete: {N}/{M} pairs succeeded.` |
| Empty state | `No pairs fetched. Verify MT5 terminal is running and IC Markets is connected.` |

### pit_validator.py (CLI gate)

| Element | Copy |
|---------|------|
| Primary CTA | `python backtest/pit_validator.py` (the command the developer runs) |
| Violation line | `VIOLATION {file}:{line} — {message}` |
| Pass summary | `PiT check PASSED — {N} file(s) clean` |
| Fail summary | `PiT check FAILED — {N} violation(s) found. Fix before updating pair_config.py.` |
| Empty state (no files given) | `Usage: python pit_validator.py [file ...] — defaults to backtest_hybrid.py and backtest_evaluate_all.py` |

### Entry bias comparison report

| Element | Copy |
|---------|------|
| Report heading | `ENTRY BIAS COMPARISON REPORT — {YYYY-MM-DD}` |
| Column headers | `Pair       Strategy    Old Sharpe  New Sharpe  Delta   Old Win%  New Win%  Old Trades  New Trades` |
| Divider | `----  --------  ----------  ----------  -----  --------  --------  ----------  ----------` |
| Footer | `Bias delta range: {min_delta:.2f} to {max_delta:.2f}. All deltas negative = fix applied correctly.` |
| CSV save confirmation | `Report saved: reports/entry_bias_comparison_{YYYY-MM-DD}.csv` |
| Error state | `ERROR: Could not load baseline values from pair_config.py. Ensure file is importable.` |

### pair_config.py routing matrix update

| Element | Copy |
|---------|------|
| Primary CTA | `Run pit_validator.py (exit 0 required), then update pair_config.py entries manually` |
| Update confirmation | `# 4yr corrected — {YYYY-MM-DD}: Sharpe {value:.2f}, win_rate {value:.1%}, trades {N}` (inline comment) |
| Below-threshold note | `# 4yr corrected — {YYYY-MM-DD}: Sharpe {value:.2f} < 0.5 threshold — allow flag set False` |
| Destructive confirmation | None — pair_config.py updates are manual edits; no destructive confirmation prompt needed |

---

## Interaction Contracts

Phase 7 has no interactive UI. The following defines the expected
exit-code and stdout/stderr routing contracts for each script.

| Script | stdin | stdout | stderr | Exit 0 | Exit 1 |
|--------|-------|--------|--------|--------|--------|
| `download_history.py` | none | OK / SKIP / WARN lines + summary | FAIL lines + ERROR | all pairs attempted (some may WARN) | MT5 init failed |
| `pit_validator.py` | none | PASS summary or VIOLATION lines + FAIL summary | none | no violations found | one or more violations found |
| `backtest_4yr_evaluate.py` | none | report table + CSV save confirmation | ERROR lines | report generated | unrecoverable data error |

**Mandatory routing rule:** `FAIL` and `ERROR` lines go to stderr. `OK`, `SKIP`,
`WARN`, and summary lines go to stdout. This allows `2>/dev/null` filtering in
automation and CI without losing pass/fail signal.

---

## Report Format Contract

### Before/After Comparison Report (`reports/entry_bias_comparison_YYYY-MM-DD.csv`)

| Column | Type | Description |
|--------|------|-------------|
| `pair` | string | e.g. `AUDNZD` |
| `strategy` | string | `scalp` or `momentum` or `swing` |
| `old_sharpe` | float (2dp) | Biased 730d Sharpe from pair_config.py snapshot |
| `new_sharpe` | float (2dp) | Corrected 730d Sharpe from fixed backtest run |
| `delta` | float (2dp) | `new_sharpe - old_sharpe` (expected negative) |
| `old_win_pct` | float (1dp %) | Biased win rate |
| `new_win_pct` | float (1dp %) | Corrected win rate |
| `old_trades` | int | Trade count under biased entry |
| `new_trades` | int | Trade count under corrected entry |

### 4yr Routing Matrix Report (`reports/4yr_routing_matrix_YYYY-MM-DD.csv`)

| Column | Type | Description |
|--------|------|-------------|
| `pair` | string | e.g. `USDJPY` |
| `strategy` | string | `scalp` or `momentum` |
| `sharpe` | float (2dp) | 4yr corrected Sharpe |
| `win_rate` | float (1dp %) | 4yr win rate |
| `trade_count` | int | Total trades over 4yr data |
| `min_trades_met` | bool | True if trade_count >= 30 |
| `sharpe_threshold_met` | bool | True if sharpe >= 0.5 |
| `routing_matrix_entry` | bool | True if both thresholds met |
| `allow_flag` | string | `allow_scalp: true/false` or `allow_momentum: true/false` |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| n/a — no component registries | n/a | not applicable — CLI phase |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

---

## Pre-Population Audit

| Field | Source |
|-------|--------|
| No web UI / no shadcn | REQUIREMENTS.md — "Mobile app / web dashboard: Out of Scope"; MONI-01 deferred to v3.0+ |
| No new dependencies | RESEARCH.md §Standard Stack — "Phase 7 adds zero new Python dependencies" |
| Script names (download_history.py, pit_validator.py) | CONTEXT.md Claude's Discretion — chosen by researcher |
| Report format (console table + CSV) | CONTEXT.md Claude's Discretion — "comparison report format (console table vs CSV vs both)" |
| Prefix characters (OK / SKIP / FAIL / WARN) | RESEARCH.md §Pattern 3 — download_history.py pattern uses these prefixes |
| VIOLATION line format | RESEARCH.md §Pattern 4 — `VIOLATION {file}:{line} — {message}` from CLI block |
| CSV column names and types | RESEARCH.md §Pattern 2 and §Pattern 5 — fields named and typed from code analysis |
| Exit-code contract | CONTEXT.md D-06 — "Exits non-zero on violations; update is blocked" |
| Before-state snapshot approach | RESEARCH.md §Don't Hand-Roll — "current biased values ARE the before-state" |
| Min trade count 30 for 4yr | RESEARCH.md §Open Questions #2 — "Use n >= 30 for 4yr data" recommendation |
| Sharpe threshold 0.5 | CONTEXT.md D-10 — "Minimum Sharpe >= 0.5 to earn a routing matrix entry" |
| 5 active pairs | CONTEXT.md D-14 — "AUDNZD, EURGBP, GBPJPY, EURUSD, USDJPY" |
| stderr/stdout routing rule | Default engineering standard — no upstream source; applied as sensible default |

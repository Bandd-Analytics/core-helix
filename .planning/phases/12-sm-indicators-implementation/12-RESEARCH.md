# Phase 12: SM Indicators implementation — Research

**Researched:** 2026-04-27
**Domain:** MQL4 + MQL5 indicator implementation under Wine MT4/MT5; Python `compute_*()` ports of MMM indicator semantics for the Helix v2.0 backtester
**Confidence:** HIGH on Python port shape, MQ5 idioms, test conftest pattern, output paths, and gitignore strategy. MEDIUM on the exact MetaEditor headless-compile workflow (tooling exists but is GUI-launched in this environment) and the spec-footer Implementation-status table format (no pre-existing precedent in the corpus).

## Summary

Phase 12 reconstructs runnable code for all 14 SM indicators (3 helpers + 5 atomic + 6 composite) from the Phase 11 specs into three target languages: MQ4, MQ5, and Python. The contract is the spec set already on disk under `resource_pack/MMM/SM Indicators/docs/`. Section 11 ("Port notes") of every spec is the per-target translation rule and is binding — it is not a suggestion to research alternatives, it is the recipe.

Phase 11 produced specs of varying confidence (4 High, 8 Medium, 2 Low). Four specs already carry `## Verified Updates (2026-04-27 from MT4 Inputs dialog)` footers from operator screenshots (SM_BPCT, SM_ADR_Marker, SM_TDI, SM_NewHUD); these footers OVERRIDE the spec body where they conflict (TDI RSI=21 not 13, ADR ATR-period=14 not 20, BPCT is a mini-HUD not a pressure tracker, NewHUD has 18+ fields including HYADR / weekly-monthly ADR / EMA Av_N row). Phase 12 implementation honors verified-update values; tests regenerate against them.

The Helix codebase already has two production MQ5 indicators (`BandD_TradeReplay.mq5`, `ADR_Levels.mq5`, plus `BandD_WorktimeRibbon.mq5` and `RegimeClassifier.mq5`) that establish the canonical MQ5 idiom — header block, OnInit/OnCalculate/OnDeinit/OnTimer, ObjectCreate with chart-id 0, prefix-based bulk cleanup, indicator-handle composition via iCustom + CopyBuffer for composite indicators. The Python side has `V2/v3_intelligence/adr.py` as the canonical `compute_*()` shape (function-first, lazy import for testability, Title-case OHLC) and `V2/v3_intelligence/regime/` as the precedent for a nested package with submodules and a clean `__init__.py` re-export surface.

**Primary recommendation:** Three plans (12-01 Tier 0, 12-02 Tier 1, 12-03 Tier 2). Within each tier, parallelize one task per spec — each task builds three files (`<name>.mq4`, `<name>.mq5`, `compute_<name>.py`) plus its pytest module and appends the Implementation-status table to the spec footer. Compile + smoke gating uses MetaEditor `/compile:` CLI under Wine for MQ5 (with `/log:` capture); MQ4 compile uses the same MetaEditor (it compiles both languages — see Wine evidence below). Python uses pytest. Tier review gate captures: MetaEditor `/log:filename.log` files showing 0/0, screenshots of the indicators on a chart, and `pytest -v` GREEN output.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Build order & slicing**
- D-01: Tier-then-platform per indicator. Three plans mirroring Phase 11's tier cadence:
  - Plan 12-01: Tier 0 — 3 helpers (`sm_gmtoffset`, `sm_WorkTime`, `sm_WorkTime_no_autogmt`) × MQ4+MQ5+Python → user review
  - Plan 12-02: Tier 1 — 5 atomic indicators (`SM_ADR_Marker`, `SM_Daily_HiLo`, `SM_BPCT`, `SM_IlsleyPsychLevels`, `SM_Crossover_Arrows`) × MQ4+MQ5+Python → user review
  - Plan 12-03: Tier 2 — 6 composite indicators (`SM_TDI`, `SM_PivotPoints`, `SM_AlertZone_1`, `SM_AlertZone_2`, `SM_Alerting+TL`, `SM_NewHUD`) × MQ4+MQ5+Python → user review
- D-02: Within a tier, spec implementations parallelize. Each spec is an independent task per Phase 11's wave model — Tier 1 spawns 5 parallel implementer tasks, each task building 1 spec × 3 targets.
- D-03: Tier review checkpoint requires **compile + smoke** before approval:
  - MQ4: 0 errors / 0 warnings in MetaEditor + loads on ≥1 chart in MT4 (Wine) without runtime error
  - MQ5: 0 errors / 0 warnings in MetaEditor + loads on ≥1 chart in IC Markets KE MT5 (Wine) without runtime error
  - Python: imports cleanly + ≥1 passing pytest per indicator
- D-04: Phase 12 does not build a 4th plan for INDEX-style finalization — Phase 11's existing INDEX.md is updated in-place by each tier plan when specs gain "Implementation status" footers (D-13).

**Output paths**
- D-05: MQ4 sources → `resource_pack/MMM/SM Indicators/MT4/_helix_built/`
- D-06: MQ5 sources → `resource_pack/MMM/SM Indicators/MT5/`
- D-07: Python module → `V2/v3_intelligence/sm_indicators/`

**Done criteria per target (per indicator)**
- D-08 (MQ4): Compile clean (0/0) + indicator loads on ≥1 chart in MT4 under Wine + buffers/objects render visibly. No visual parity vs original `.ex4`.
- D-09 (MQ5): Compile clean + loads on ≥1 chart in IC Markets KE MT5 (Wine) + buffers/objects render. Files copied to `~/.mt5/.../IC Markets KE MT5 Terminal/MQL5/Indicators/`.
- D-10 (Python): Module exposes `compute_<name>(df: DataFrame, params: <Name>Params) -> DataFrame`. Each spec's Section 10 test cases convert into actual pytest test functions in `tests/v3_intelligence/sm_indicators/test_<name>.py`. ≥1 test GREEN per indicator.

**Python module shape**
- D-11: Function-first surface, params as frozen dataclasses. Mirrors `V2/v3_intelligence/adr.py:compute_adr()`. No class-based `Indicator` interface.
- D-12 (Alerts in Python): Log events only — `compute_*()` returns DataFrame with an `alert_signal` column.
- D-12a (Plot helpers): Skipped.
- D-12b (Backtest wiring): Skipped — `backtest_hybrid.py` is NOT modified by Phase 12.

**Spec linkback**
- D-13: Every implementation task ends by appending an "Implementation status" table to the spec at `resource_pack/MMM/SM Indicators/docs/{helpers,indicators}/<name>.md`. Columns: target (MQ4/MQ5/Python), status (Built ✅ / Stubbed ⚠ / Skipped ❌), file path, commit SHA, date.
- D-14: `INDEX.md` gains an "Implementation matrix" section updated at each tier's end.

**Cross-platform parity**
- D-15: Advisory parity check for High-confidence deterministic indicators (`sm_gmtoffset`, `sm_WorkTime`, `SM_TDI`, `SM_ADR_Marker`, `SM_Daily_HiLo`, `SM_PivotPoints`, `SM_IlsleyPsychLevels`). Plan 12-02 / 12-03 add a `scripts/parity_check_<name>.py` that diffs MQ5 buffer CSV vs Python `compute_*()` within tolerance — `1e-4` for prices, `1e-6` for ratios. Captured as evidence; NOT a blocker for tier review.
- D-16: No parity tested for medium/low-confidence indicators.

**Low-confidence indicators**
- D-17: Low-confidence indicators built best-effort. Every guessed branch carries `// [INFER]` (MQ4/MQ5) or `# [INFER]` (Python) source comments with the spec line reference. Tests assert shape, not behavioral parity vs original. Spec footer marks these `Built ⚠`.
- D-18: Stubs and skips not used. Every indicator gets a real implementation.

**MQ4 ↔ MQ5 source code style**
- D-19: MQ5 ports follow MQ5-idiomatic patterns — indicator handles, `OnCalculate(rates_total, prev_calculated, time, open, high, low, close, tick_volume, volume, spread)`, `CopyBuffer` / `CopyRates`, MQL5 `ObjectCreate(0, name, type, sub_window, ...)` signatures. Reference precedent: `V2/indicators/BandD_TradeReplay.mq5`, `V2/indicators/ADR_Levels.mq5`, `V2/indicators/RegimeClassifier.mq5`. No `#ifdef __MQL5__` shims.
- D-20: MQ4 ports use MQL4 idioms — `int init()/start()/deinit()` legacy or `OnInit/OnCalculate(int rates_total, int prev_calculated, ...)` MQL4-style, `iCustom` for inter-indicator calls, MQL4 `ObjectCreate(name, type, sub_window, time, price)` signatures.

### Claude's Discretion

- Exact subfolder structure under `_helix_built/` (flat vs `helpers/` + `indicators/`) — recommend mirroring Phase 11 docs/ layout for traceability
- Pytest fixture organization for spec test cases (one fixture file per indicator vs shared OHLCV fixtures)
- Whether parity-check scripts get unit-tested themselves (recommend: no, advisory tooling)
- MQ4 vs MQ5 alert configuration defaults — pick the MMM-typical (popup + sound on, email/push off) where the spec is silent; tag `[INFER]`
- Whether `resource_pack/MMM/SM Indicators/MT4/_helix_built/` gets its own README — recommend yes

### Deferred Ideas (OUT OF SCOPE)

- Backtest_hybrid wiring of SM_TDI / SM_PivotPoints as alpha sources
- Visual parity vs original `!SM_*.ex4` binaries
- Headless MQ5 export tooling for required-parity gate
- matplotlib/plotly plot helpers for Python compute() results
- Cross-language unit tests across MQ4/MQ5/Python (parity test corpus)
- Re-spec / re-implement the ~40 third-party non-`!SM_*` indicators
- MMM glossary expansion
- Live MT4/MT5 EA integration of SM indicators

## Phase Requirements

Phase 12 has **no formal REQ-IDs** in REQUIREMENTS.md (this phase is implementation of Phase 11 documentation; not a requirement-bearing phase like INFRA-* / SESS-* / ROUT-*). The "must-haves" are derived from CONTEXT.md decisions D-01..D-20 and the 14 spec files. The success criteria are:

| Source | Success Criterion | Research Support |
|--------|------------------|------------------|
| D-01..D-04 | Three plans deliver 14 indicators × 3 targets, tier-gated by user review | Confirmed against Phase 11 plan structure; precedent works |
| D-05..D-07 | Output paths exist & are isolated from non-decompiled originals | Verified — paths confirmed empty/ready: `MT5/` empty, `MT4/_helix_built/` to be created, `V2/v3_intelligence/sm_indicators/` new package |
| D-08..D-10 | Compile-clean + smoke-load + ≥1 pytest per indicator | MetaEditor compile-CLI + pytest pattern (V2/tests/v3_intelligence) verified |
| D-13..D-14 | Implementation-status table appended to each spec; INDEX.md matrix | Spec template established by Phase 11; status table is new but additive — no spec body rewrites |
| D-19..D-20 | Idiomatic MQ4 + idiomatic MQ5, no shims | Precedent files (TradeReplay.mq5, ADR_Levels.mq5) embody this style |

## Standard Stack

### Core (MQ5 implementation)

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| MetaEditor 5 (build 5800+) | shipped with MT5 / IC Markets KE MT5 Terminal | Compiles both `.mq4` → `.ex4` AND `.mq5` → `.ex5` | The only deterministic compiler available in this environment; already used in Phase 8.4 P04 to ship 4 MQ5 indicators |
| MetaTrader 5 (Wine 11.7) | IC Markets KE MT5 Terminal already installed at `/home/user/.mt5/drive_c/Program Files/IC Markets KE MT5 Terminal/` | Smoke-loads compiled `.ex5` on chart | Confirmed running per Phase 8.4 BRDG-03 spike + INFRA-04 acceptance |
| Wine 11.7 Staging | `/home/user/.wine`, `/home/user/.mt5` Wine prefixes | Runs MetaEditor64.exe and terminal64.exe | Phase 6 P02 dispositive evidence |

### Core (Python implementation)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | already installed (V2 stack) | DataFrame operations on OHLCV; rolling windows for SMA/RSI/Bollinger | The Helix V2 convention — every `V2/v3_intelligence/*.py` returns/accepts pandas DataFrames |
| numpy | already installed | Vectorized math (log returns, std dev, EMA accumulators) | Foundation for V2/v3_intelligence/regime/ |
| pytest | already installed | Test runner | Used throughout `V2/tests/v3_intelligence/` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas-ta or TA-Lib | optional | Pre-built RSI / EMA / Bollinger | If we want to avoid hand-rolling SMA/RSI inside `compute_tdi()`. Recommendation: hand-roll inside the package — small, vectorizable, and removes an external dependency. SM_TDI Section 11 Python port shows the trivial pandas-only pattern. |
| pytz / zoneinfo | stdlib (Python 3.9+) | Broker GMT offset detection in `compute_sm_gmtoffset()` | Required for sm_gmtoffset Python port per its Section 11. Use stdlib `zoneinfo`. |
| frozen dataclass `<Name>Params` | stdlib | Per-indicator immutable parameter object | D-11 — frozen dataclass per indicator |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| MetaEditor CLI compile (`/compile:` `/log:`) under Wine | mql-tools (Sublime/VSCode plugins), Neovim mql-compile.nvim | Same underlying compiler; CLI flag is the simplest scriptable form. Recommended unless we hit Wine UI hangs. |
| Hand-rolled RSI/SMA/Bollinger in Python | pandas-ta | pandas-ta adds a 60+ MB dependency just for indicators we'd write in 5 lines each. Decline. |
| Class-based `Indicator` interface | function-first `compute_<name>()` | D-11 explicit: function-first. Decline class hierarchy. |

**Installation:**
- No new Python deps. Existing pandas/numpy/pytest from V2 environment.
- No new Wine deps. MetaEditor already installed at two paths under `/home/user/.mt5/drive_c/Program Files/`.

**Version verification (2026-04-27):**
- MetaEditor compiler: `/home/user/.mt5/drive_c/Program Files/IC Markets KE MT5 Terminal/MetaEditor64.exe` — PE32+ Windows binary; build version embedded in the .exe. The `Phase 6 P02` BRDG-03 spike confirms build 5800 (Wine 11.7 Staging). Sufficient for current MQL4/MQL5 syntax.
- pandas/numpy/pytest: already pinned in V2 environment; no upgrade needed.

## MetaEditor Compile Workflow Under Wine (Linux)

This is the load-bearing operational unknown for D-08 / D-09 acceptance. Findings:

**Mechanism (HIGH confidence, MQL5 docs + community confirmed):**

```
WINEPREFIX=/home/user/.mt5 wine \
  "/home/user/.mt5/drive_c/Program Files/IC Markets KE MT5 Terminal/MetaEditor64.exe" \
  /compile:"<absolute Windows-style path to .mq5 or .mq4>" \
  /inc:"<MQL5 or MQL4 directory>" \
  /log:"<absolute Windows-style path to .log>"
```

**Key facts ([MQL5 community thread](https://www.mql5.com/en/forum/367908), [official MetaEditor Help](https://www.metatrader5.com/en/metaeditor/help/development/compile)):**

- `/compile:` accepts either a single file or a folder. Folder = batch compile every source in that folder.
- `/log:` writes a plain-text log including line-by-line errors and warnings. Final line is the count summary `<n> errors, <m> warnings`.
- MetaEditor 5 (the same binary) compiles BOTH `.mq4` → `.ex4` AND `.mq5` → `.ex5`. The compiler picks language by file extension. This means our Phase 12 toolchain has ONE compiler invocation pattern, not two.
- The MetaEditor binary launches no GUI when invoked with `/compile:` — confirmed exit-on-completion behavior.
- Wine path conversion: pass Windows-style paths (`Z:\\home\\user\\...`) or rely on Wine's `winepath -w` to convert from POSIX. Most reliably: use the path as already mapped through Wine's `Z:` drive letter.

**Determinism check (the "0 errors / 0 warnings" gate for D-08 / D-09):**

Parse the `/log:` output:
```bash
WINEPREFIX=/home/user/.mt5 wine "<MetaEditor>" /compile:"$SRC" /log:"$LOG"
# After Wine exits — parse log
grep -E "^(Result:|errors,)" "$LOG" | tail -1
# Expected on success: "Result: 0 errors, 0 warnings"
```

The summary line format is stable across MT5 builds (verified via [MQL5 forum #394405](https://www.mql5.com/en/forum/394405/30324400) and community plugin [riodelphino/mql-compile.nvim](https://github.com/riodelphino/mql-compile.nvim)).

**Failure modes ([MQL5 forum #491543](https://www.mql5.com/en/forum/491543) — known issue):**

- For very large modular projects (many `#include` files), MetaEditor CLI can fail silently — exit code 0, no output, but `.ex5` not produced. Workaround: confirm the `.ex5` file exists AND has a recent mtime AFTER each compile. Don't trust exit code alone.
- The terminal does not auto-reload the new `.ex5` if MT5 is already running. To smoke-test, the user must "Refresh" the Indicators list in Navigator.

**Recommended Phase 12 helper script (Wave 0 of each plan):**

```bash
# scripts/compile_mq.sh — wraps MetaEditor CLI + log parse + .ex existence + mtime check
# Usage: scripts/compile_mq.sh <src.mq5|src.mq4>
# Exits 0 only on "0 errors, 0 warnings" AND .ex5/.ex4 mtime > src mtime
```

**MQ4 caveat:** The existing Wine prefix only has MT5 (no separate MT4 install at `/home/user/.mt5`). Per `find /home/user -maxdepth 5 -name "MQL4" -type d` — only an MT4 IC Markets shortcut exists, not a full MT4 install. **MQ4 compile in this environment uses the MT5's MetaEditor (which compiles both MQ4 and MQ5 because it is build 5800+).** Output `.ex4` is dropped next to the source. The compiled `.ex4` then needs to be loaded into a real MT4 terminal for D-08 smoke testing — operator must either install MT4 under Wine OR accept that MQ4 D-08 smoke load is deferred to operator with access to MT4. The plan should call this out.

**Sources:**
- [MetaEditor official compile help](https://www.metatrader5.com/en/metaeditor/help/development/compile)
- [MQL5 forum #367908 — metaeditor.exe help](https://www.mql5.com/en/forum/367908)
- [MQL5 forum #394405 — How do I run a console command](https://www.mql5.com/en/forum/394405/30324400)
- [Trading Strategies Academy — How to Convert MQL4 to MQL5 (porting guide)](https://trading-strategies.academy/archives/920)

## Architecture Patterns

### Recommended Project Structure (D-05/D-06/D-07)

```
resource_pack/MMM/SM Indicators/
├── docs/                              # Phase 11 deliverables (already exist)
│   ├── INDEX.md
│   ├── helpers/
│   │   ├── sm_gmtoffset.md
│   │   ├── sm_WorkTime.md
│   │   └── sm_WorkTime_no_autogmt.md
│   └── indicators/
│       ├── SM_ADR_Marker.md
│       └── … (10 more)
├── MT4/
│   ├── !SM.Indicators/                # ORIGINAL .ex4 binaries — DO NOT TOUCH
│   └── _helix_built/                  # Phase 12 D-05 NEW — recommend mirror docs/ structure
│       ├── README.md                  # "These are reconstructions of !SM_*.ex4 originals from docs/ specs"
│       ├── helpers/
│       │   ├── sm_gmtoffset.mq4
│       │   ├── sm_WorkTime.mq4
│       │   └── sm_WorkTime_no_autogmt.mq4
│       └── indicators/
│           ├── SM_ADR_Marker.mq4
│           └── … (10 more)
└── MT5/                               # Phase 12 D-06 — currently empty, this seeds it
    ├── helpers/
    │   ├── sm_gmtoffset.mq5
    │   ├── sm_WorkTime.mq5
    │   └── sm_WorkTime_no_autogmt.mq5
    └── indicators/
        ├── SM_ADR_Marker.mq5
        └── … (10 more)

V2/v3_intelligence/sm_indicators/      # Phase 12 D-07 — NEW package (Python)
├── __init__.py                        # re-export all 14 compute_*() functions + Params dataclasses
├── helpers/                           # NESTED package mirroring docs/helpers/ (precedent: V2/v3_intelligence/regime/)
│   ├── __init__.py                    # re-exports compute_sm_gmtoffset, compute_sm_worktime, compute_sm_worktime_no_autogmt
│   ├── sm_gmtoffset.py
│   ├── sm_worktime.py
│   └── sm_worktime_no_autogmt.py
├── adr_marker.py                      # FLAT — Tier 1 atomic indicators sit at the package root
├── daily_hilo.py
├── bpct.py
├── ilsley_psych_levels.py
├── crossover_arrows.py
├── tdi.py                             # Tier 2 composites also flat (no further nesting needed)
├── pivot_points.py
├── alert_zone_1.py
├── alert_zone_2.py
├── alerting_tl.py
└── new_hud.py

V2/tests/v3_intelligence/sm_indicators/  # NEW test package mirroring sm_indicators/ structure
├── __init__.py
├── conftest.py                        # ohlcv_eurusd_h1, ohlcv_usdjpy_h1, ohlcv_gbpnzd_h1 fixtures
├── helpers/
│   ├── test_sm_gmtoffset.py
│   ├── test_sm_worktime.py
│   └── test_sm_worktime_no_autogmt.py
├── test_adr_marker.py
├── test_daily_hilo.py
├── … (12 more)
```

**Recommendation rationale:**
- MT4 + MT5 directories mirror the docs/ layout (helpers/ + indicators/) so traceability spec → source is one-to-one. A glance at the file path tells you which spec it implements.
- `V2/v3_intelligence/sm_indicators/` uses the **regime/-style nested-with-helpers-subpackage** pattern (precedent: `V2/v3_intelligence/regime/__init__.py` re-exports submodule symbols). Helpers go in their own subpackage because they have a distinct nature (broker-time normalization, no compute() per se); the 11 indicators sit flat at the package root because each is a single function family. This avoids gratuitous depth (no `indicators/` subpackage) while still grouping helpers cleanly.

### Pattern 1: MQ5 Indicator Header + Lifecycle (idiomatic per D-19)

**What:** Standard scaffold every Phase 12 MQ5 file uses.

**When to use:** Every `.mq5` source. Copy from `V2/indicators/ADR_Levels.mq5` skeleton.

**Example:**
```mq5
// Source: V2/indicators/ADR_Levels.mq5 (Phase 8.4 P04 INFRA-04 precedent)
//+------------------------------------------------------------------+
//|  SM_ADR_Marker.mq5 — Phase 12 P02 (D-05/D-06/D-19)                |
//|  Reconstructs !SM_ADR_Marker.ex4 from spec at                     |
//|  resource_pack/MMM/SM Indicators/docs/indicators/SM_ADR_Marker.md |
//|  ATRPeriod = 14 (Verified Updates 2026-04-27)                     |
//+------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_buffers 0           // ObjectCreate, not buffers
#property indicator_plots   0

input int   InpATRPeriod        = 14;       // Verified-Updates: 14 (was claimed 20)
input bool  InpUseManualADR     = false;
input int   InpManualADRValuePips = 0;
input ENUM_LINE_STYLE InpLineStyle  = STYLE_DOT;   // 2 in MT4 inputs
input int   InpLineThickness1   = 1;
input color InpLineColor1       = clrOrange;
// … (rest of Verified-Updates Inputs table)

const string InpObjectPrefix = "smADR_";    // [INFER] convention from spec

int OnInit() { Recompute(); EventSetTimer(60); return(INIT_SUCCEEDED); }

void OnDeinit(const int reason) {
    int total = ObjectsTotal(0);
    for(int i = total - 1; i >= 0; i--) {
        string n = ObjectName(0, i);
        if(StringFind(n, InpObjectPrefix) == 0) ObjectDelete(0, n);
    }
    EventKillTimer();
}

int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[], const long &tv[],
                const long &v[], const int &sp[]) {
    static datetime last_d1_bar = 0;
    datetime cur_d1 = iTime(_Symbol, PERIOD_D1, 0);
    if(cur_d1 != last_d1_bar) { Recompute(); last_d1_bar = cur_d1; }
    return(rates_total);
}

void OnTimer() { Recompute(); }
```

### Pattern 2: MQ5 Indicator-Handle Composition (for composite indicators using sub-indicators)

**What:** Composite indicators (SM_TDI internally uses RSI; SM_NewHUD may iCustom() SM_TDI/SM_PivotPoints) acquire indicator handles in `OnInit`, copy values via `CopyBuffer` in `OnCalculate`, and release handles in `OnDeinit`.

**When to use:** SM_TDI (RSI handle), SM_NewHUD (if it composes via iCustom — `[INFER]` per spec; likely self-contained but composition is the option).

**Example (from V2/indicators/RegimeClassifier.mq5):**
```mq5
// Source: V2/indicators/RegimeClassifier.mq5 lines 31-71

int handleRSI = INVALID_HANDLE;

int OnInit() {
    handleRSI = iRSI(_Symbol, PERIOD_CURRENT, InpRSIPeriod, PRICE_CLOSE);
    if(handleRSI == INVALID_HANDLE) {
        Print("Failed to create RSI handle");
        return INIT_FAILED;
    }
    SetIndexBuffer(0, BufferRSIPL, INDICATOR_DATA);
    return(INIT_SUCCEEDED);
}

int OnCalculate(const int rates_total, const int prev_calculated, …) {
    double rsiBuf[];
    if(CopyBuffer(handleRSI, 0, 0, rates_total, rsiBuf) <= 0) return prev_calculated;
    // … apply 2-bar SMA to rsiBuf to compute RSI_PL (Green) …
    return rates_total;
}

void OnDeinit(const int reason) {
    if(handleRSI != INVALID_HANDLE) IndicatorRelease(handleRSI);
}
```

### Pattern 3: MQ5 ObjectCreate with chart-id 0 + prefix cleanup (D-19)

**What:** Every `ObjectCreate` call uses chart-id 0 (current chart). Bulk cleanup uses prefix-based iteration.

**When to use:** Every indicator that draws OBJ_HLINE, OBJ_RECTANGLE, OBJ_LABEL, OBJ_ARROW_*. (12 of 14 indicators; helpers and TDI exclusive of these are exceptions.)

**Example:**
```mq5
// Source: V2/indicators/BandD_TradeReplay.mq5 lines 117-152
ObjectCreate(0, n_entry, OBJ_ARROW_BUY, 0, e_ts, e_px);
ObjectSetInteger(0, n_entry, OBJPROP_COLOR, side);

// Cleanup pattern (every OnDeinit):
int total = ObjectsTotal(0);
for(int i = total - 1; i >= 0; i--) {
    string name = ObjectName(0, i);
    if(StringFind(name, InpObjectPrefix) == 0) ObjectDelete(0, name);
}
```

### Pattern 4: Python compute_<name>() function shape (D-11)

**What:** Function-first surface, Title-case OHLC input, returns DataFrame with indicator columns.

**When to use:** Every indicator's Python module.

**Example:**
```python
# Source: V2/v3_intelligence/adr.py + Phase 11 SM_TDI.md Section 11
from dataclasses import dataclass

@dataclass(frozen=True)
class TDIParams:
    rsi_period: int = 21          # Verified-Updates: 21 (was claimed 13)
    volatility_band: int = 34
    stddev_mult: float = 1.6185   # [INFER] — could be 2.0
    rsi_price_line: int = 2
    trade_signal_line: int = 7
    market_base_line: int = 34
    shark_fin_upper: float = 63.0  # Verified-Updates: 63 (was claimed 68)
    shark_fin_lower: float = 37.0  # Verified-Updates: 37 (was claimed 32)


def compute_tdi(df: pd.DataFrame, params: TDIParams = TDIParams()) -> pd.DataFrame:
    """SM_TDI — Traders Dynamic Index (Dean Malone variant per MMM TDI Tradestation PDF).

    Args:
        df: OHLCV with Title-case columns ('Open', 'High', 'Low', 'Close', 'Volume').
            Index is a datetime-like sequence.
        params: TDIParams with verified-update defaults.

    Returns:
        DataFrame with original columns + ['rsi_raw', 'rsi_pl', 'tsl', 'mbl',
        'vb_upper', 'vb_lower', 'alert_signal'].
    """
    out = df.copy()  # NEVER mutate input
    out['rsi_raw']  = _compute_rsi(out['Close'], params.rsi_period)
    out['rsi_pl']   = out['rsi_raw'].rolling(params.rsi_price_line).mean()
    out['tsl']      = out['rsi_raw'].rolling(params.trade_signal_line).mean()
    out['mbl']      = out['rsi_raw'].rolling(params.market_base_line).mean()
    sigma           = out['rsi_raw'].rolling(params.volatility_band).std(ddof=0)
    out['vb_upper'] = out['mbl'] + params.stddev_mult * sigma
    out['vb_lower'] = out['mbl'] - params.stddev_mult * sigma
    out['alert_signal'] = _detect_alerts(out, params)  # bool / categorical (D-12)
    return out
```

### Anti-Patterns to Avoid

- **Mutating input df** — Every `compute_*()` MUST start with `df.copy()`. Anything else corrupts upstream callers' data. Recurring beginner trap when porting from MT4 buffer-style code where buffers are global.
- **MQ5 `Period()` global where MQL4 used it** — In MQL5 it is `_Period` (constant) or `PeriodSeconds()` for seconds-of-bar. Use `_Symbol`, `_Period`, `_Digits`, `_Point` consistently.
- **MQ4-style `Bars` / `Bid` / `Ask` globals in MQ5** — These don't exist in MQ5. Use `iBars(_Symbol, _Period)`, `SymbolInfoDouble(_Symbol, SYMBOL_BID)`, `SymbolInfoDouble(_Symbol, SYMBOL_ASK)`.
- **Forgetting `chart_id` arg in MQ5 `ObjectCreate`** — silent failure: object never appears. Always pass `0`.
- **Using `iRSI` directly in MQ5 OnCalculate loop** — that's the MQ4 idiom. In MQ5 it is `iRSI(_Symbol, _Period, period, PRICE_CLOSE)` returning a *handle*, not a value. Use `CopyBuffer(handle, …)` to get values.
- **`OnCalculate` signature mismatch** — MQ4 short form (`int rates_total, int prev_calculated`) vs MQ5 full form (10 args). Compiler accepts both forms loosely in some builds, but the safe MQ5 idiom is the full form (matches `V2/indicators/ADR_Levels.mq5`, `BandD_WorktimeRibbon.mq5`).
- **Missing `#property indicator_buffers N` declaration** — MQ5 throws `cannot allocate buffer` at runtime if `SetIndexBuffer(N-1, …)` is called without the matching `#property` line. SM_TDI declares 5 buffers; SM_Crossover_Arrows declares 2; helpers declare 0.
- **Repainting on bar[0] alerts** — Every spec that fires alerts (TDI, Crossover, AlertZone) MUST gate on bar[1] transitions, not bar[0]. SM_TDI Section 5 step 7 makes this explicit.
- **Lookahead bias in Python rolling windows** — `df['col'].rolling(N).mean()` is left-aligned by default; the value at index `i` is `mean(df.iloc[i-N+1:i+1])`. This is correct for our use case (the value at bar `i` reflects the closed bar `i`). Do NOT use `.shift(-N)` or any forward-looking aggregator. Phase 8 PitClock would catch this in PiT-gated tests but Phase 12 doesn't run those — be careful.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Broker GMT offset detection on Python live side | `datetime - utcnow` math + custom DST table | `zoneinfo.ZoneInfo("Europe/Nicosia").utcoffset(datetime.now())` | DST handled correctly, IANA-database-backed |
| OBJ_RECTANGLE for session boxes | Per-bar OBJ_VLINE rendering or buffer-based | OBJ_RECTANGLE with chart-id 0, send-to-back, prefix cleanup | `BandD_WorktimeRibbon.mq5` Pattern 2 already proven |
| RSI in Python | Manual gain/loss tracking with EMA | `_compute_rsi()` 5-line helper using Wilder's smoothing OR pandas-ta `ta.rsi()` if dep accepted | Standard pattern; the helper goes in `sm_indicators/_common.py` |
| Bollinger Bands on RSI in Python | Manual std-dev windowing | `df['rsi_raw'].rolling(N).std(ddof=0)` (population stddev per SM_TDI Section 5) | `ddof=0` is the Bollinger convention |
| MQ5 indicator buffer registration | Hand-rolled MQL5 buffer arrays | `SetIndexBuffer(idx, arr, INDICATOR_DATA)` + `#property indicator_buffers N` | Standard MQL5 pattern; RegimeClassifier.mq5 lines 47-50 |
| MetaEditor headless compile detection | bash regex on stdout | `/log:` capture + `grep -E "0 errors, 0 warnings"` on the log | The summary line is stable across MT5 builds |
| Trade-time CSV parsing in MQ5 | StringSplit on FileReadString | `FileOpen(path, FILE_READ \| FILE_CSV \| FILE_ANSI, ',')` + `FileReadDatetime` / `FileReadNumber` / `FileReadString` per column | `BandD_TradeReplay.mq5` lines 65-105 — already proven |

**Key insight:** Most of the MQ5 plumbing is already proven in the four existing Helix indicators. Phase 12's MQ5 work is overwhelmingly about translating spec algorithms into the established skeleton — not about novel MQL5 architecture decisions.

## Runtime State Inventory

**Phase 12 is greenfield code generation, not a rename/refactor/migration. Most categories are not applicable.** Exceptions and explicit answers:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 12 produces source files only. No DB writes, no cache mutations. ChromaDB and Supabase untouched. | None |
| Live service config | n8n / Datadog / Tailscale / Cloudflare — not relevant to indicator code. | None |
| OS-registered state | None — indicators are loaded into MT4/MT5 manually by the operator after each tier review. No Task Scheduler / systemd / pm2 registrations. | None |
| Secrets/env vars | None — indicators don't read env vars. | None |
| Build artifacts | **CRITICAL — `.ex4` and `.ex5` compiled outputs.** MetaEditor produces these next to the source `.mq4`/`.mq5`. They are recompilable from source by any operator with MetaEditor. **Verified existing pattern:** `/home/user/.mt5/drive_c/Program Files/MetaTrader 5/MQL5/Indicators/` already has paired `.ex5` files alongside `.mq5` (e.g., `ADR_Levels.ex5` 13380 bytes alongside `ADR_Levels.mq5` 3427 bytes). The `.gitignore` does not currently exclude `*.ex5` or `*.ex4`. **Decision needed (see "Build Artifact Strategy" below):** add `*.ex5` and `*.ex4` to `.gitignore` — they are derived artifacts, recompilable. The Phase 8.4 P04 pattern of committing `.mq5` source only and leaving `.ex5` recompilable is the precedent. |

## Pytest Fixture Pattern for Spec Test Cases

**Existing pattern (verified — `V2/tests/v3_intelligence/conftest.py` + `conftest_infra.py`):**

The bridge file pattern is established and proven (Phase 8.4 P02 SUMMARY documents the Rule 3 deviation that established it):
- `conftest.py` — pytest's only auto-discovered file. Contains Phase 8 fixtures (`synthetic_three_regime_returns`, `v1_baseline`).
- `conftest_infra.py` — Phase 8.4 fixtures kept in a logically-separate file. Re-exported from `conftest.py` via `from .conftest_infra import (sample_trade, in_memory_logger, mock_chroma_collection, mock_psycopg_conn)`.

**Recommended Phase 12 layout:**

```
V2/tests/v3_intelligence/sm_indicators/
├── __init__.py
├── conftest.py                       # OHLCV fixtures + bridge re-export
└── test_<name>.py                    # one per indicator
```

**`conftest.py` (Phase 12):**

```python
"""Phase 12 SM Indicators test fixtures.

Provides synthetic and real OHLCV fixtures for the 14 SM indicator test
modules. Fixtures match Title-case OHLC convention (Phase 8.4 D-20).
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import pytest

DATA_DIR = Path(__file__).resolve().parents[3] / "V2" / "data"


@pytest.fixture(scope="session")
def ohlcv_eurusd_h1() -> pd.DataFrame:
    """Real EURUSD H1 4yr corpus (from Phase 8.4 INFRA-02). Title-case OHLC."""
    df = pd.read_csv(DATA_DIR / "EURUSD_H1_4yr.csv", parse_dates=["timestamp"])
    return df.set_index("timestamp")


@pytest.fixture(scope="session")
def ohlcv_usdjpy_h1() -> pd.DataFrame:
    """Real USDJPY H1 4yr corpus (3-digit JPY pair — exercises pip-format edge cases)."""
    df = pd.read_csv(DATA_DIR / "USDJPY_H1_4yr.csv", parse_dates=["timestamp"])
    return df.set_index("timestamp")


@pytest.fixture
def synthetic_ohlc_uptrend() -> pd.DataFrame:
    """Deterministic uptrending OHLC for SM_Crossover_Arrows / SM_TDI bullish-cross tests."""
    idx = pd.date_range("2024-01-01", periods=100, freq="h")
    closes = pd.Series([1.0850 + i * 0.0001 for i in range(100)], index=idx)
    return pd.DataFrame({
        "Open":  closes.shift(1).fillna(1.0850),
        "High":  closes + 0.0005,
        "Low":   closes - 0.0005,
        "Close": closes,
        "Volume": [1000] * 100,
    }, index=idx)


# Bridge re-export for any future *_infra.py file (precedent: Phase 8.4)
# Currently empty — uncomment when needed.
# from .conftest_infra import (…)
```

**Recommendation:**

| Question | Answer | Rationale |
|----------|--------|-----------|
| One conftest per indicator vs shared? | **Shared `conftest.py` at `tests/v3_intelligence/sm_indicators/`** | Most indicators consume the same OHLCV fixtures; per-indicator fixtures = duplication. Indicator-specific fixtures (e.g., a synthetic Doji series for SM_BPCT) live INSIDE the test file, not the conftest. |
| Inline OHLCV CSV strings vs fixture files? | **Real CSV via existing `V2/data/*_H1_4yr.csv`** for happy-path tests; **inline synthetic DataFrames** for edge-case tests (uptrend / Doji / VB-squeeze / DST-window / oversold-hook) | Real data verifies the indicator computes against realistic price; synthetic data isolates a specific algorithmic property. SM_TDI Section 10 has 5 test cases — at least 3 (Shark Fin, Blood in the Water, VB Squeeze) need synthetic constructs because real-data extracts are nondeterministic. |
| Per-indicator `parametrize` vs explicit functions? | **Explicit functions** for the 2-4 cases each spec lists. Explicit is more readable and matches existing `test_adr.py`/`test_pit.py` pattern. | The 4 tests in `test_adr.py` are 4 functions, not parametrize. Existing convention. |

**Example:**

```python
# V2/tests/v3_intelligence/sm_indicators/test_tdi.py
"""SM_TDI tests. Section 10 of SM_TDI.md provides the 5 expected behaviors.
   NOTE: RSI_Period uses Verified-Updates value 21 (not the prior 13)."""
from __future__ import annotations

import pandas as pd
import pytest

from v3_intelligence.sm_indicators.tdi import compute_tdi, TDIParams


def test_tdi_returns_required_columns(ohlcv_eurusd_h1: pd.DataFrame) -> None:
    """compute_tdi returns DataFrame with the 5 buffer columns + alert signal."""
    out = compute_tdi(ohlcv_eurusd_h1.tail(500))
    for col in ("rsi_raw", "rsi_pl", "tsl", "mbl", "vb_upper", "vb_lower", "alert_signal"):
        assert col in out.columns


def test_tdi_uses_verified_rsi_period_21(ohlcv_eurusd_h1: pd.DataFrame) -> None:
    """Verified-Updates: RSI_Period default is 21, not 13."""
    assert TDIParams().rsi_period == 21


def test_tdi_blood_in_water_bullish(synthetic_ohlc_uptrend: pd.DataFrame) -> None:
    """SM_TDI Section 10 case 2: Green crosses Yellow with Green > Red and rising high."""
    out = compute_tdi(synthetic_ohlc_uptrend)
    # MBL Cross BULLISH alert fires somewhere in the synthetic uptrend
    assert (out["alert_signal"] == "MBL_CROSS_BULLISH").any()


def test_tdi_warmup_bars_are_nan(ohlcv_eurusd_h1: pd.DataFrame) -> None:
    """SM_TDI Section 9 edge case 1: first 80 bars (RSI+MBL+VB warmup) are NaN."""
    out = compute_tdi(ohlcv_eurusd_h1.head(100))
    assert out["mbl"].iloc[0:80].isna().all()
```

## Tier Review Checkpoint Format

There is **no pre-existing tier-review checkpoint precedent** for an implementation phase like Phase 12 — Phase 11 was a doc-only phase with markdown audits. The closest precedent is Phase 8.4 P04's INFRA-04 "operator visual verification deferred" pattern. The recommended Phase 12 checkpoint format adapts that:

**Per-tier review payload (returned by orchestrator to user):**

```markdown
## Tier {N} Review — Phase 12 Plan {NN}

**Tier:** {0|1|2}
**Indicators built:** {3|5|6}
**Targets:** MQ4 + MQ5 + Python (per indicator)
**Date:** {YYYY-MM-DD}

### Per-indicator status

| Indicator | MQ4 | MQ5 | Python | Notes |
|-----------|-----|-----|--------|-------|
| sm_gmtoffset | ✅ | ✅ | ✅ | TimeGMT()-TimeCurrent() detection. Python uses zoneinfo. |
| sm_WorkTime | ✅ | ✅ | ✅ | Reads sm_GMTOffset GlobalVariable; Python is plot helper only. |
| sm_WorkTime_no_autogmt | ✅ | ✅ | ✅ | BrokerGMT manual input variant. |

✅ = Built clean; ⚠ = Built with [INFER] caveats; ❌ = Skipped (not used per D-18)

### Compile evidence

- MQ5 compile log: `evidence/tier{N}_compile_smoke/mq5_compile.log` — "Result: 0 errors, 0 warnings"
- MQ4 compile log: `evidence/tier{N}_compile_smoke/mq4_compile.log` — "Result: 0 errors, 0 warnings"
- Screenshot: `evidence/tier{N}_compile_smoke/mt5_chart_load.png`
- pytest output: `evidence/tier{N}_compile_smoke/pytest_green.txt` — "{N} passed, 0 failed"

### Spec footer updates

All {3|5|6} specs at `resource_pack/MMM/SM Indicators/docs/{helpers,indicators}/` have a new "Implementation status" table (D-13). INDEX.md's Implementation matrix updated.

### Advisory parity (D-15)

{Per-indicator parity-check status if applicable. Stays advisory, not blocking.}

### Approval gate

Reply "approved" to proceed to Tier {N+1}, or describe issues.
```

**Evidence files captured (recommended):**
- `evidence/tier{N}_compile_smoke/mq5_compile.log` — MetaEditor `/log:` output, full content
- `evidence/tier{N}_compile_smoke/mq4_compile.log` — same
- `evidence/tier{N}_compile_smoke/mt5_chart_load.png` — screenshot of any chart with the indicators loaded (operator captures via Wine xdotool or screenshotting tool — same constraint as Phase 8.4 P04 INFRA-04 deferred)
- `evidence/tier{N}_compile_smoke/pytest_green.txt` — `pytest -v V2/tests/v3_intelligence/sm_indicators/ > pytest_green.txt`
- `evidence/tier{N}_compile_smoke/parity_<name>.csv` — per-indicator advisory parity CSV (D-15) — only for high-confidence deterministic indicators

**Note on screenshot constraint:** Phase 8.4 P04 SUMMARY documents that "the spawned executor cannot capture MT5 GUI screenshots" — the executor agent cannot drive Wine GUI. Phase 12 inherits this. Solution: the executor produces compile logs + pytest output autonomously; chart-load screenshots are an operator deliverable captured during the user-review checkpoint, not blocked at agent runtime. The plan should make this explicit so that screenshot deferral does NOT block tier approval.

## Spec Footer "Implementation Status" Table Format (D-13)

**Recommended schema (placed AFTER Section 12 Uncertainty log AND any existing "Verified Updates" footer, as a NEW Section 13):**

```markdown
---

## Implementation status (Phase 12)

| Target | Status | File | Commit | Date |
|--------|--------|------|--------|------|
| MQ4 | Built ✅ | `resource_pack/MMM/SM Indicators/MT4/_helix_built/indicators/SM_TDI.mq4` | `<sha>` | 2026-04-XX |
| MQ5 | Built ✅ | `resource_pack/MMM/SM Indicators/MT5/indicators/SM_TDI.mq5` | `<sha>` | 2026-04-XX |
| Python | Built ✅ | `V2/v3_intelligence/sm_indicators/tdi.py` | `<sha>` | 2026-04-XX |

Tests: `V2/tests/v3_intelligence/sm_indicators/test_tdi.py` (`<n>` tests GREEN)
Confidence: High (same as Phase 11 spec; verified against MMM TDI Tradestation PDF + 2026-04-27 operator screenshot of MT4 Inputs dialog).
```

**Status legend (matches D-13):**
- `Built ✅` — implementation matches spec; spec confidence High or Medium
- `Built ⚠` — implementation matches spec but spec confidence is Low (e.g., SM_BPCT, SM_NewHUD per D-17)
- `Skipped ❌` — NOT used by Phase 12 (per D-18, every indicator gets a real implementation; only relevant if a downstream phase decides not to build something)

**Placement decision: NEW Section 13, NOT appended to an existing section.**

Rationale: Phase 11 specs use a 12-section locked template. The "Verified Updates" footer added in 4 specs (BPCT, ADR_Marker, TDI, NewHUD) is rendered as `## Verified Updates (...)` — same H2 level as the 12 sections — which establishes the precedent that **post-Phase-11 augmentations are appended at the bottom as new H2 sections**. Phase 12's "Implementation status" follows that pattern. INDEX.md's "Implementation matrix" (D-14) is the cross-spec roll-up.

## Advisory Parity Check Tooling (D-15)

**Question:** How does an operator manually export an MQ5 indicator buffer to CSV for diff vs Python `compute()`?

**Three options ranked:**

| Option | Mechanism | Effort | Accuracy | Recommendation |
|--------|-----------|--------|----------|----------------|
| 1. **In-indicator FileWrite() to CSV** | Add a `#define DEBUG_DUMP_CSV` block in the MQ5 source that writes (timestamp, buffer_value) rows to `~/.mt5/.../MQL5/Files/<name>_buffer.csv` on the last bar of OnCalculate | Low — one helper function, gated by define so it can be removed before final build | High — exact buffer values | **RECOMMENDED**. Operator toggles the define, recompiles, attaches indicator to chart, observes CSV appear in MQL5/Files. |
| 2. MT5 strategy tester export | Run a synthetic "EA" that calls iCustom on the indicator across a date range and writes to CSV | Medium — needs a wrapper EA per indicator | High but slow | Decline — defer to a tooling phase per CONTEXT deferred-ideas |
| 3. Print() to terminal log + parse | Add `Print(time[i], ",", buffer[i]);` and copy from terminal log | Low | Lossy — terminal log truncates / interleaves with other indicators | Decline |

**Recommended pattern for the 7 High-confidence indicators (per D-15):**

Each indicator's `.mq5` includes:
```mq5
#define DUMP_PARITY_CSV   // Comment out for production builds

#ifdef DUMP_PARITY_CSV
void DumpParityCSV() {
    int handle = FileOpen("parity_" + _Symbol + "_" + EnumToString(_Period) + ".csv",
                           FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    FileWrite(handle, "ts", "rsi_pl", "tsl", "mbl", "vb_upper", "vb_lower");
    int n = ArraySize(rsi_pl);
    for(int i = 0; i < n; i++) {
        FileWrite(handle, TimeToString(iTime(_Symbol, _Period, n - 1 - i)),
                  rsi_pl[i], tsl[i], mbl[i], vb_upper[i], vb_lower[i]);
    }
    FileClose(handle);
}
#endif
```

The `scripts/parity_check_<name>.py` script (per D-15) reads this CSV plus the same OHLCV input, runs `compute_<name>()`, and produces a diff report. Captured under `.planning/phases/12-.../evidence/parity_<name>.csv`. **Advisory only — not a blocker for tier review.**

## Common Pitfalls

### Pitfall 1: Trusting MT5 build differences silently break MQL4 backward compatibility
**What goes wrong:** A `.mq4` source written under MQL5's editor may compile but use MQL5-only constructs that fail at runtime in real MT4.
**Why it happens:** MetaEditor 5 compiles both .mq4 and .mq5; the language dialects overlap heavily but not perfectly. `EventSetTimer` works in both, but `IndicatorSetString(INDICATOR_SHORTNAME, …)` is MQL5-only, while MQL4 uses `IndicatorShortName(…)`.
**How to avoid:** When writing the `.mq4` source, ALWAYS reference the spec's "MQ4 → MQ5 deltas" subsection (Section 11). For each MQ5 idiom, find its MQ4 sibling in the spec.
**Warning signs:** A `.mq4` file that compiles with no errors but produces no output at runtime. Re-check against the MQ4 reference docs.

### Pitfall 2: BandD_TradeReplay header-skip bug (Phase 8.4 P04 SUMMARY documents)
**What goes wrong:** An indicator that reads CSV with `FileReadString` to skip headers misses fields if the count is wrong.
**Why it happens:** CSV header has N columns; you must `FileReadString` N times AND consume the line ending (`if(!FileIsLineEnding) FileReadString(handle);`).
**How to avoid:** For any indicator that reads CSV, count header columns explicitly. Loop N times. Reference `BandD_TradeReplay.mq5` lines 73-78.
**Warning signs:** First data row has misaligned types (e.g., date parses as 0).

### Pitfall 3: Mutating input DataFrame in Python compute_*()
**What goes wrong:** `df["rsi_raw"] = …` modifies the caller's DataFrame.
**Why it happens:** Python passes by reference; assigning to df columns mutates in place.
**How to avoid:** Every `compute_*()` starts with `out = df.copy()` and operates on `out`.
**Warning signs:** Tests for indicator A pass; then a downstream test that uses the same fixture fails because indicator B's prior call mutated the fixture.

### Pitfall 4: NaN handling at series start (rolling window warmup)
**What goes wrong:** `df["close"].rolling(34).mean()` returns NaN for the first 33 rows. Subsequent computations (e.g., `vb_upper = mbl + 1.6185 * sigma`) propagate NaN. If an alert detector compares `>` against NaN, it returns False without raising — the alert silently never fires for early bars (correct), but a downstream test that asserts on a specific bar may fail spuriously.
**How to avoid:** Drop or skip warmup rows in tests. SM_TDI Section 9 edge case 1 documents the 80-bar warmup explicitly.
**Warning signs:** Test passes on `df.tail(500)` but fails on `df.head(50)`.

### Pitfall 5: Lookahead bias when computing rolling windows
**What goes wrong:** Rolling-window functions can be set to right-aligned or center-aligned. Center-aligned uses future bars.
**Why it happens:** `df.rolling(N, center=True)` is opt-in but easy to typo.
**How to avoid:** Default left-aligned (`df.rolling(N).mean()`). The value at index `i` is `mean(df.iloc[i-N+1:i+1])`. NEVER use `center=True` for indicator computation.
**Warning signs:** Backtest Sharpe higher than expected; Phase 8 PitClock would catch this in PiT-gated tests but Phase 12 doesn't run those.

### Pitfall 6: Wine path translation Z:/ vs ~/
**What goes wrong:** A `FileOpen("/home/user/foo.csv")` call in MQ5 fails because MT5 sandboxes file IO into `~/.mt5/.../MQL5/Files/` (Wine-mapped to `Z:\\home\\user\\.mt5\\drive_c\\users\\...`).
**How to avoid:** Use relative paths inside `MQL5/Files/` for any FileOpen call. Operator places parity CSVs there. `BandD_TradeReplay.mq5` line 21 uses `"trades_latest.csv"` (relative).
**Warning signs:** `FileOpen` returns INVALID_HANDLE; `GetLastError()` reports 5004 (FILE_OPEN_ERROR).

### Pitfall 7: Missing #property indicator_buffers N (MQ5 cannot allocate buffer)
**What goes wrong:** `SetIndexBuffer(0, …)` fails at runtime if `#property indicator_buffers 0` (or absent).
**Why it happens:** MQL5 requires the buffer count declared at compile time.
**How to avoid:** Count the buffers — SM_TDI=5, SM_Crossover_Arrows=2, helpers=0, ADR_Marker=0 (uses ObjectCreate), pivots=0, NewHUD=0. Match `#property indicator_buffers <count>` and `#property indicator_plots <count>` to spec.
**Warning signs:** Compile clean, terminal Experts log shows "cannot allocate indicator buffer 0".

### Pitfall 8: Locale-sensitive number formatting in MQ5 FileWrite
**What goes wrong:** `FileWrite(h, 1.234)` may write `"1,234"` on European Wine locales due to decimal separator.
**How to avoid:** Use `DoubleToString(value, _Digits)` and `FileWrite(h, str)`. Phase 8.4 P04 BandD_TradeReplay didn't hit this because it only writes already-stringified columns.
**Warning signs:** Python parity_check fails to parse "1,234" as float.

### Pitfall 9: Font rendering for chart objects under Wine
**What goes wrong:** `OBJPROP_FONT = "Consolas"` may render as Times New Roman under Wine (Consolas not in Wine's font cache).
**How to avoid:** Default to "Arial" or "Courier New" — both ship with Wine. Reference `BandD_WorktimeRibbon.mq5` line 241: `ObjectSetString(0, pipName, OBJPROP_FONT, "Arial")`.
**Warning signs:** SM_NewHUD HUD text alignment looks wrong, columns don't align.

### Pitfall 10: SM_BPCT spec is Low confidence — implementation builds the spec, NOT the original behavior
**What goes wrong:** Operator expects SM_BPCT to behave like the original `!SM_BPCT.ex4` and is disappointed.
**Why it happens:** SM_BPCT spec is Low confidence per Phase 11 (3 candidate interpretations). The Verified Updates footer reveals it is actually a mini-HUD (price + spread + HOD/LOD), not the spec body's "pressure tracker" hypothesis.
**How to avoid:** Phase 12 implements per the **Verified Updates** footer (mini-HUD), not the spec body. Mark `Built ⚠` in the spec footer. Document explicitly in the implementation file's header comment.
**Warning signs:** Operator runs the indicator and the chart shows a corner HUD instead of histogram bars.

## Code Examples

### Example 1: Tier 0 helper sm_gmtoffset MQ5 skeleton

```mq5
// Source: spec sm_gmtoffset.md Section 6 + Section 11
//+------------------------------------------------------------------+
//|  sm_gmtoffset.mq5 — Phase 12 P01 (D-06/D-19)                      |
//|  Reconstructs !sm_gmtoffset.ex4 from spec at                      |
//|  resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md     |
//|  No buffers, no plots — utility indicator publishes GlobalVariable|
//+------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

input bool   InpAutoDetect    = true;
input int    InpManualGMT     = 0;
input bool   InpDSTAdjust     = true;
input string InpGlobalVarName = "sm_GMTOffset";

int OnInit() {
    int offset_hours = ComputeOffset();
    GlobalVariableSet(InpGlobalVarName, (double)offset_hours);
    Comment("GMT Offset detected: ", offset_hours);
    EventSetTimer(3600);                  // hourly refresh per spec Section 5
    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
    EventKillTimer();
    Comment("");
    // Spec Section 5 step 4: do NOT delete GlobalVariable
}

void OnTimer() {
    int offset_hours = ComputeOffset();
    GlobalVariableSet(InpGlobalVarName, (double)offset_hours);
}

int OnCalculate(const int rates_total, const int prev_calculated, …) {
    return rates_total;   // no per-bar work
}

int ComputeOffset() {
    if(!InpAutoDetect) return InpManualGMT;
    long delta_seconds = (long)TimeCurrent() - (long)TimeGMT();
    int raw_offset = (int)MathRound((double)delta_seconds / 3600.0);
    if(InpDSTAdjust) {
        MqlDateTime mdt;
        TimeToStruct(TimeCurrent(), mdt);
        if(mdt.mon >= 3 && mdt.mon <= 10) raw_offset -= 1;
    }
    return raw_offset;
}
```

### Example 2: Tier 0 helper sm_gmtoffset Python skeleton

```python
# Source: spec sm_gmtoffset.md Section 11 (Python port)
"""sm_gmtoffset — broker GMT offset detection helper.

Phase 12 P01 (D-07). In backtesting mode this is a no-op (UTC always 0);
in live mode it reads from MT5 Python bridge or zoneinfo."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class SMGMTOffsetParams:
    auto_detect: bool = True
    manual_gmt: int = 0
    broker_iana_tz: str = "Europe/Nicosia"  # IC Markets EU default — operator-overridable


def detect_broker_offset(params: SMGMTOffsetParams = SMGMTOffsetParams(),
                         broker_ts: Optional[datetime] = None) -> int:
    """Return broker's effective GMT offset in integer hours.

    In backtesting mode (broker_ts is None), returns 0 (timestamps are
    already UTC per pit.py / Phase 8 contract).

    In live mode, computes from broker_ts vs current UTC, optionally with
    DST adjustment via zoneinfo if broker_iana_tz is provided.
    """
    if not params.auto_detect:
        return params.manual_gmt
    if broker_ts is None:
        return 0  # backtesting — UTC always
    utc_now = datetime.now(timezone.utc)
    delta_seconds = (broker_ts - utc_now.replace(tzinfo=None)).total_seconds()
    return round(delta_seconds / 3600)
```

### Example 3: SM_TDI Python compute() — production-ready

```python
# Source: SM_TDI.md Section 11 Python port + Verified Updates 2026-04-27
"""SM_TDI — Traders Dynamic Index (Dean Malone variant).

Phase 12 P03 (D-07/D-10/D-11). Verified-Updates: RSI_Period=21 (was 13),
Shark_Fin levels = 63/37 (was 68/32). Bollinger StdDev still inferred 1.6185.
"""
from __future__ import annotations
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TDIParams:
    rsi_period: int = 21               # Verified-Updates 2026-04-27
    rsi_price_line: int = 2
    trade_signal_line: int = 7
    market_base_line: int = 34
    volatility_band: int = 34
    stddev_mult: float = 1.6185        # [INFER] — could be 2.0; not in Inputs dialog
    shark_fin_upper: float = 63.0      # Verified-Updates
    shark_fin_lower: float = 37.0      # Verified-Updates


def _wilder_rsi(close: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothed RSI — matches MT4/MT5 iRSI() output."""
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_tdi(df: pd.DataFrame, params: TDIParams = TDIParams()) -> pd.DataFrame:
    """SM_TDI buffer columns + alert signal column.

    Args:
        df: OHLCV DataFrame with Title-case 'Close' column.
        params: Frozen TDIParams.

    Returns:
        Copy of df with new columns: rsi_raw, rsi_pl, tsl, mbl, vb_upper,
        vb_lower, alert_signal.
    """
    out = df.copy()  # NEVER mutate input
    out["rsi_raw"]  = _wilder_rsi(out["Close"], params.rsi_period)
    out["rsi_pl"]   = out["rsi_raw"].rolling(params.rsi_price_line).mean()
    out["tsl"]      = out["rsi_raw"].rolling(params.trade_signal_line).mean()
    out["mbl"]      = out["rsi_raw"].rolling(params.market_base_line).mean()
    sigma           = out["rsi_raw"].rolling(params.volatility_band).std(ddof=0)
    out["vb_upper"] = out["mbl"] + params.stddev_mult * sigma
    out["vb_lower"] = out["mbl"] - params.stddev_mult * sigma
    out["alert_signal"] = _detect_alerts(out, params)
    return out


def _detect_alerts(out: pd.DataFrame, params: TDIParams) -> pd.Series:
    """Per spec Section 5 step 7. Returns 'NONE' or alert label per bar.

    Bar-i alerts use bar[i] vs bar[i-1] transitions only — no lookahead.
    """
    rsi_pl = out["rsi_pl"]
    tsl    = out["tsl"]
    mbl    = out["mbl"]
    vb_upper = out["vb_upper"]
    vb_lower = out["vb_lower"]

    # Signal Cross — Green crosses Red
    bull_signal = (rsi_pl > tsl) & (rsi_pl.shift(1) <= tsl.shift(1))
    bear_signal = (rsi_pl < tsl) & (rsi_pl.shift(1) >= tsl.shift(1))

    # MBL Cross — Green crosses Yellow with Green > Red
    bull_mbl = ((rsi_pl > mbl) & (rsi_pl.shift(1) <= mbl.shift(1)) & (rsi_pl > tsl))
    bear_mbl = ((rsi_pl < mbl) & (rsi_pl.shift(1) >= mbl.shift(1)) & (rsi_pl < tsl))

    # Hook — Green re-enters VB from below (bullish) or above (bearish)
    bull_hook = ((rsi_pl > vb_lower) & (rsi_pl.shift(1) <= vb_lower.shift(1)) &
                 (rsi_pl < params.shark_fin_lower + 5))
    bear_hook = ((rsi_pl < vb_upper) & (rsi_pl.shift(1) >= vb_upper.shift(1)) &
                 (rsi_pl > params.shark_fin_upper - 5))

    out_signal = pd.Series("NONE", index=out.index)
    out_signal.loc[bull_signal] = "SIGNAL_CROSS_BULLISH"
    out_signal.loc[bear_signal] = "SIGNAL_CROSS_BEARISH"
    out_signal.loc[bull_mbl] = "MBL_CROSS_BULLISH"  # overrides signal cross
    out_signal.loc[bear_mbl] = "MBL_CROSS_BEARISH"
    out_signal.loc[bull_hook] = "HOOK_BULLISH"
    out_signal.loc[bear_hook] = "HOOK_BEARISH"
    return out_signal
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MQ4 short OnCalculate signature `(int rates_total, int prev_calculated, ...)` | MQ5 full signature `(rates_total, prev_calculated, time, open, high, low, close, tick_volume, volume, spread)` with const refs | MetaTrader 5 release (2010-2011) | All MQ5 indicators in V2/indicators/ use the full form. Phase 12 MQ5 ports MUST use the full form. |
| MQ4 `iRSI(symbol, period, length, price, shift)` returns double directly | MQ5 `iRSI(symbol, period, length, price)` returns handle; values via `CopyBuffer(handle, 0, shift, count, arr)` | MT5 release | SM_TDI MQ5 port MUST acquire RSI handle in OnInit, copy in OnCalculate. RegimeClassifier.mq5 lines 64-71 is the precedent. |
| MQ4 implicit-current-chart `ObjectCreate(name, type, sub, t1, p1)` | MQ5 explicit-chart-id `ObjectCreate(0, name, type, sub, t1, p1)` | MT5 release | All 12 of 14 indicators that draw chart objects need this delta. |
| MQ4 `Period()` global function | MQ5 `_Period` constant + `PeriodSeconds()` helper | MT5 release | One-line change; `BandD_WorktimeRibbon.mq5` line 230 uses `PeriodSeconds()`. |
| MQ4 `ArraySetAsSeries(arr, true)` default | MQ5 buffers default `false` (chronological); set true with `ArraySetAsSeries(buf, true)` | MT5 release | RegimeClassifier.mq5 line 116 uses chronological — `pos = rates_total - 1 - i`. Either convention works; pick one and be consistent within an indicator. |

**Deprecated/outdated:**
- MQ4 `iVolume()` — still works in MT5 via legacy compatibility, but `iTickVolume` + `CopyTickVolume` is the MQ5 idiom. SM_BPCT (if pressure-candle interpretation were correct, which Verified Updates contradicts) would have hit this.
- MQ4 `Bid` / `Ask` globals — replaced by `SymbolInfoDouble(_Symbol, SYMBOL_BID)` in MQ5. SM_NewHUD live-spread display will need this.

## Open Questions

1. **Wine MetaEditor compile reliability for batch / mass compile**
   - What we know: `/compile:<folder>` documented to work; CLI-mode no-GUI confirmed.
   - What's unclear: Whether the IC Markets KE MT5 build accepts `/compile:<folder>` (some MT5 builds reportedly hang on folder mode under Wine — see [MQL5 forum #491543](https://www.mql5.com/en/forum/491543)).
   - Recommendation: Plan 12-01's Wave 0 includes a `scripts/compile_mq.sh` smoke test that compiles ONE indicator first, validates the `/log:` output, and falls back to per-file compilation if folder mode fails. Don't rely on batch.

2. **MQ4 smoke-load (D-08) without an MT4 install**
   - What we know: `/home/user/.mt5/` only has MT5; no separate MT4 Wine prefix found.
   - What's unclear: Whether the operator has a separate MT4 install accessible (the Desktop shortcut `MetaTrader 4 IC Markets Global.lnk` exists, suggesting yes, but path not verified).
   - Recommendation: Plan 12-01 Task 1 includes a "discover MT4 install path" step. If absent, D-08 smoke load becomes operator-deferred (compile only; load testing in operator's separate MT4 session). Document explicitly.

3. **Will the parity-check CSV approach catch the 1e-4 / 1e-6 tolerance?**
   - What we know: MetaTrader writes doubles with `_Digits` precision; locale issues possible (Pitfall 8).
   - What's unclear: Whether MT5 buffer values match Python compute() within 1e-4 absolute on prices for the High-confidence 7. Untested.
   - Recommendation: Plan 12-02 includes ONE end-to-end parity test (SM_ADR_Marker, the simplest deterministic indicator) to validate the tolerance is achievable BEFORE Plan 12-03 commits to the same approach for SM_TDI / SM_PivotPoints.

4. **SM_NewHUD verified-update Av_N EMA periods (1, 4, 13, 26, 52) — is this a separate sub-indicator inside the HUD?**
   - What we know: Verified Updates lists `Av_N` periods that "imply NewHUD computes/displays multiple EMAs."
   - What's unclear: Whether these are pre-computed and displayed as additional HUD rows or whether they trigger logic.
   - Recommendation: Plan 12-03 SM_NewHUD task computes them per the plain-vanilla EMA formula and displays as 5 additional HUD rows (or column-grouped). Mark `Built ⚠` in the spec footer because internals remain `[INFER]`.

5. **Whether `SM_AlertZone_1` and `SM_AlertZone_2` have a real algorithmic difference**
   - What we know: 148-byte binary delta is the only objective evidence; specs hypothesize "same algorithm, different defaults."
   - What's unclear: Without operator running both side-by-side and reading both Inputs dialogs.
   - Recommendation: Plan 12-03 implements them as ONE shared MQ5/MQ4/Python module with two parameter presets. Each spec footer notes the dependency.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x (already installed in V2 environment) |
| Config file | `V2/pyproject.toml` (existing) — pytest config under `[tool.pytest.ini_options]` |
| Quick run command | `cd V2 && pytest -v tests/v3_intelligence/sm_indicators/test_<name>.py` |
| Full suite command | `cd V2 && pytest -v tests/v3_intelligence/sm_indicators/` |
| Estimated runtime | < 30 seconds for full suite (no slow integration tests; all use synthetic or pre-loaded CSV fixtures) |
| MQ4/MQ5 compile gate | `bash scripts/compile_mq.sh <src>` — returns 0 on "0 errors, 0 warnings" + .ex* mtime check |

### Phase Requirements → Test Map

Phase 12 has no formal REQ-IDs (per CONTEXT.md). The success criteria are derived from D-08/D-09/D-10 and the 14 spec files. The verifiable tests are:

| Indicator (Tier) | Behavior | Test Type | Automated Command | File Exists? |
|------------------|----------|-----------|-------------------|-------------|
| sm_gmtoffset (T0) | Returns broker offset hours from delta | unit | `pytest -v V2/tests/v3_intelligence/sm_indicators/helpers/test_sm_gmtoffset.py` | ❌ Wave 0 |
| sm_gmtoffset (T0) | MQ5 compiles 0/0 | compile | `bash scripts/compile_mq.sh resource_pack/MMM/SM\ Indicators/MT5/helpers/sm_gmtoffset.mq5` | ❌ Wave 0 |
| sm_gmtoffset (T0) | MQ4 compiles 0/0 | compile | `bash scripts/compile_mq.sh resource_pack/MMM/SM\ Indicators/MT4/_helix_built/helpers/sm_gmtoffset.mq4` | ❌ Wave 0 |
| sm_WorkTime (T0) | Reads sm_GMTOffset GlobalVariable correctly + draws session boxes | smoke (manual chart load) | operator | manual |
| sm_WorkTime (T0) | Python session-classifier works | unit | `pytest -v .../test_sm_worktime.py` | ❌ Wave 0 |
| sm_WorkTime_no_autogmt (T0) | BrokerGMT manual-input variant produces same boxes as auto variant | unit | `pytest -v .../test_sm_worktime_no_autogmt.py` | ❌ Wave 0 |
| SM_ADR_Marker (T1) | ATR(14) anchored to today_open ± ADR/2 | unit | `pytest -v .../test_adr_marker.py` | ❌ Wave 0 |
| SM_Daily_HiLo (T1) | PHOD/PLOD lines at iHigh/iLow(D1, 1) | unit | `pytest -v .../test_daily_hilo.py` | ❌ Wave 0 |
| SM_BPCT (T1, ⚠) | Mini-HUD renders price + spread + HOD/LOD distance | unit (shape-only) | `pytest -v .../test_bpct.py` | ❌ Wave 0 |
| SM_IlsleyPsychLevels (T1) | Round-number levels at 50-pip intervals | unit | `pytest -v .../test_ilsley_psych_levels.py` | ❌ Wave 0 |
| SM_Crossover_Arrows (T1) | EMA 5/13 cross detection | unit | `pytest -v .../test_crossover_arrows.py` | ❌ Wave 0 |
| SM_TDI (T2) | RSI=21 + 5 buffers + 3 alert types | unit (5 cases per spec Section 10) | `pytest -v .../test_tdi.py` | ❌ Wave 0 |
| SM_PivotPoints (T2) | Standard pivots + M1-M4 mid-pivots | unit | `pytest -v .../test_pivot_points.py` | ❌ Wave 0 |
| SM_AlertZone_1 (T2) | Lower zone alerter | unit | `pytest -v .../test_alert_zone_1.py` | ❌ Wave 0 |
| SM_AlertZone_2 (T2) | Upper zone alerter | unit | `pytest -v .../test_alert_zone_2.py` | ❌ Wave 0 |
| SM_Alerting+TL (T2) | Trendline-touch alerter (mock OBJ_TREND objects) | unit | `pytest -v .../test_alerting_tl.py` | ❌ Wave 0 |
| SM_NewHUD (T2, ⚠) | 18+ field render with Verified-Updates field set | unit (shape-only) | `pytest -v .../test_new_hud.py` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest -v V2/tests/v3_intelligence/sm_indicators/test_<name>.py && bash scripts/compile_mq.sh <mq5> && bash scripts/compile_mq.sh <mq4>` (≤ 5 seconds per-task)
- **Per wave merge (= per tier):** Full Phase 12 pytest suite + all-tier compile gate: `pytest -v V2/tests/v3_intelligence/sm_indicators/ && bash scripts/compile_mq_all_tier.sh <tier>` (≤ 30 seconds)
- **Phase gate (before `/gsd:verify-work 12`):** Full suite GREEN + tier-3 review approved + advisory parity reports captured

### Wave 0 Gaps

- [ ] `V2/tests/v3_intelligence/sm_indicators/__init__.py` — new test package
- [ ] `V2/tests/v3_intelligence/sm_indicators/conftest.py` — OHLCV fixtures (ohlcv_eurusd_h1, ohlcv_usdjpy_h1, ohlcv_gbpnzd_h1, synthetic_ohlc_uptrend, synthetic_doji)
- [ ] `V2/tests/v3_intelligence/sm_indicators/helpers/__init__.py` + `helpers/test_*.py` (3 RED files for Tier 0)
- [ ] `V2/tests/v3_intelligence/sm_indicators/test_*.py` — 11 RED files for Tier 1 + Tier 2
- [ ] `V2/v3_intelligence/sm_indicators/__init__.py` + `helpers/__init__.py` — empty packages so imports resolve in RED tests
- [ ] `scripts/compile_mq.sh` — Wine MetaEditor wrapper with `/log:` parse and `.ex*` mtime check
- [ ] `scripts/compile_mq_all_tier.sh` — wraps `compile_mq.sh` over an entire tier's MQ4 + MQ5 sources
- [ ] `scripts/parity_check_<name>.py` — one per High-confidence indicator (7 total, but only added in Plans 12-02 / 12-03)
- [ ] `resource_pack/MMM/SM Indicators/MT4/_helix_built/README.md` — explains "these are reconstructions"

**Strategy:** Each plan starts with its OWN Wave 0 test scaffold (RED files for indicators in that tier only), not a single Phase-12-wide Wave 0. This matches Phase 8 / Phase 8.4 / Phase 11 cadence.

### Build Artifact Strategy (recommendation)

**Question:** Should `.ex5` and `.ex4` compiled binaries be committed or gitignored?

**Recommendation: gitignored. Reasons:**

1. **They are derived artifacts.** Any operator with MetaEditor can recompile from the `.mq5`/`.mq4` source.
2. **Phase 8.4 P04 precedent:** committed `BandD_TradeReplay.mq5` + `ADR_Levels.mq5` source ONLY; the `.ex5` files in `~/.mt5/.../MQL5/Indicators/` are recompiled per-machine.
3. **Phase 8.4 P04 SUMMARY documents two `.gitignore` Rule 3 deviations** (V2/reports/* exception, mempalace.yaml override) — they were ad-hoc fixes. Phase 12 should preempt this by adding `.ex5` and `.ex4` to `.gitignore` in Plan 12-01 Wave 0, with a comment explaining "compiled MQL outputs — recompilable from source".

**Recommended `.gitignore` addition:**

```
# Phase 12 — compiled MetaEditor outputs (recompilable from .mq4/.mq5 source)
*.ex5
*.ex4
# But preserve the original non-decompilable Phase 11 source binaries
!resource_pack/MMM/SM Indicators/MT4/!SM.Indicators/*.ex4
```

The `!` exception preserves the 14 ORIGINAL `.ex4` binaries that were the input to Phase 11 specs (per CONTEXT canonical_refs "DO NOT TOUCH"). Phase 12's compiled outputs (in `_helix_built/` and `MT5/`) are gitignored.

## Sources

### Primary (HIGH confidence)

- `resource_pack/MMM/SM Indicators/docs/INDEX.md` — overview, dep graph, confidence summary
- `resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md` — Section 11 Port notes
- `resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md` — Section 11 Port notes
- `resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md` — Section 11 Port notes
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md` — Section 11 + Verified Updates 2026-04-27
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_ADR_Marker.md` — Section 11 + Verified Updates 2026-04-27
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_PivotPoints.md` — Section 11 Port notes
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md` — Section 11 + Verified Updates 2026-04-27
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_NewHUD.md` — Section 11 + Verified Updates 2026-04-27
- `V2/indicators/BandD_TradeReplay.mq5` — Phase 8.4 P04 INFRA-04 precedent (MQ5 header/OnInit/OnDeinit/OnCalculate, ObjectCreate, FileOpen CSV pattern)
- `V2/indicators/ADR_Levels.mq5` — timeframe-agnostic MQ5 indicator pattern (D-16)
- `V2/indicators/BandD_WorktimeRibbon.mq5` — session-ribbon with timer + chart-id 0 + multi-day rectangle pattern
- `V2/indicators/RegimeClassifier.mq5` — MQ5 indicator handle composition pattern (iCustom + CopyBuffer)
- `V2/v3_intelligence/adr.py` — Python compute_*() function-shape canonical example (D-11)
- `V2/v3_intelligence/pit.py` — PitClock context manager
- `V2/v3_intelligence/regime/__init__.py` — nested-package re-export pattern (precedent for sm_indicators/helpers/)
- `V2/tests/v3_intelligence/conftest.py` + `conftest_infra.py` — bridge re-export pattern
- `V2/tests/v3_intelligence/test_adr.py`, `test_pit.py` — pytest test pattern (explicit functions, not parametrize)
- `.planning/phases/08.4-.../08.4-04-SUMMARY.md` — Phase 8.4 P04 deviations (gitignore rule, BandD_TradeReplay header skip, screenshot deferral pattern)
- `.planning/phases/12-sm-indicators-implementation/12-CONTEXT.md` — locked phase context
- `.planning/phases/11-sm-indicators-full-spec-documentation/11-CONTEXT.md` — Phase 11 spec template (12 sections) + Tier cadence

### Secondary (MEDIUM confidence — verified with multiple sources)

- [MQL5 Forum #367908 — metaeditor.exe compile help](https://www.mql5.com/en/forum/367908) — `/compile:` `/log:` `/inc:` flags
- [MQL5 Forum #394405 — How do I run a console command](https://www.mql5.com/en/forum/394405/30324400) — Wine path conventions
- [MetaEditor official Help — Compile](https://www.metatrader5.com/en/metaeditor/help/development/compile) — official syntax + behavior
- [MQL5 Forum #491543 — CLI silent fail on large modular projects](https://www.mql5.com/en/forum/491543) — known Wine MetaEditor edge case
- [Trading Strategies Academy — How to Convert MQL4 to MQL5](https://trading-strategies.academy/archives/920) — porting guide for OnCalculate, iRSI handle, ObjectCreate chart-id
- [riodelphino/mql-compile.nvim](https://github.com/riodelphino/mql-compile.nvim) — community plugin confirming the same `/compile:` `/log:` invocation works headlessly under both Wine and Windows
- [MQL5 CopyBuffer official docs](https://www.mql5.com/en/docs/series/copybuffer) — handle-based buffer access
- [LiteFinance — MQL4 vs MQL5 differences](https://www.litefinance.org/blog/for-beginners/what-is-metatrader/metaquotes-languages-mql4-vs-mql5-difference-programming-tutorial/) — high-level dialect comparison

### Tertiary (LOW confidence — verify before relying)

- (none — all key claims grounded in spec files or verified MQL5 community sources)

## Metadata

**Confidence breakdown:**

- Standard stack (MetaEditor, pandas, pytest): **HIGH** — all already in use; no version surprises.
- Architecture patterns (MQ5 idioms, Python compute_*() shape): **HIGH** — directly supported by 4 existing Helix MQ5 indicators + `V2/v3_intelligence/adr.py`.
- Pytest fixture pattern: **HIGH** — Phase 8.4 P02 SUMMARY documents the bridge pattern; convention established.
- Common pitfalls: **HIGH** — Phase 8.4 P04 SUMMARY documents 3 auto-fixed Rule 3 deviations directly applicable here (gitignore, header-skip count, `_Period` vs `Period()` etc.).
- MetaEditor headless compile workflow: **MEDIUM** — documented by MQL5 docs + community; specific behavior under Wine 11.7 / IC Markets KE MT5 build 5800 not exhaustively tested in this session (Wine MetaEditor `/?` invocation timed out, but that's expected — `/?` doesn't exist; `/compile:` is the correct path).
- Tier review checkpoint format: **MEDIUM** — synthesized from Phase 11 review cadence + Phase 8.4 P04 INFRA-04 deferred-evidence pattern; no exact precedent for an "implementation phase tier review" in the codebase.
- Implementation status table format (D-13): **MEDIUM** — Phase 11 specs establish "augment with new H2 sections" precedent (Verified Updates); Phase 12's Implementation status follows that. No prior format to verify directly.
- Advisory parity check tooling (D-15): **MEDIUM** — three options laid out; the FileWrite-CSV approach is straightforward but untested end-to-end. Plan 12-02's first parity test (SM_ADR_Marker) is the validation point.
- Build artifact strategy (.ex5/.ex4 gitignore): **HIGH** — direct precedent in Phase 8.4 P04 SUMMARY (V2/reports/* exception, mempalace.yaml override).

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (30 days for stable; revisit if MetaEditor build changes or if Wine prefix is rebuilt)

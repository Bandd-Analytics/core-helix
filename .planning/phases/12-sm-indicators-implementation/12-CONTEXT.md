# Phase 12: SM Indicators implementation - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Reconstruct runnable code for **all 14 SM indicators** (3 helpers + 5 atomic + 6 composite) from the Phase 11 specs at `resource_pack/MMM/SM Indicators/docs/`, in **three target languages: MQ4, MQ5, and Python**. Phase 11 specs are the canonical contract — Section 11 ("Port notes") of every spec defines the per-target translation rules and is binding.

**In scope (per indicator × per target):**
- MQ4 source file that compiles in MetaEditor and loads on a chart in MT4 under Wine
- MQ5 source file that compiles in MetaEditor and loads on a chart in IC Markets KE MT5 (Wine) — same conventions as `V2/indicators/BandD_TradeReplay.mq5` / `ADR_Levels.mq5`
- Python `compute_<indicator>(df, params)` function in `V2/v3_intelligence/sm_indicators/` returning a DataFrame, plus pytest tests derived from each spec's Section 10 ("Test cases")
- Spec footer ("Implementation status" table) appended to each spec on completion, listing built file paths per target + commit SHA

**Out of scope:**
- Visual parity vs the non-decompilable original `!SM_*.ex4` binaries (cannot be automated; specs already [INFER]-tagged)
- Wiring SM_TDI / SM_PivotPoints into `backtest_hybrid.py` as alpha sources (deferred to a follow-up phase to keep Phase 12 blast radius small)
- Live MT4/MT5 EA integration (Phase 10 owns)
- Python matplotlib/plotly plot helpers (defer to a later visualization phase or build ad-hoc when needed)
- Headless MQ5 export tooling for required-parity testing (advisory parity only — see decisions below)
- The other ~40 third-party indicators in `MT4/!SM.Indicators/` (not `!SM_*` / `!sm_*` namespace)

</domain>

<decisions>
## Implementation Decisions

### Build order & slicing

- **D-01:** Tier-then-platform per indicator. Three plans mirroring Phase 11's tier cadence:
  - Plan 12-01: Tier 0 — 3 helpers (`sm_gmtoffset`, `sm_WorkTime`, `sm_WorkTime_no_autogmt`) × MQ4+MQ5+Python → user review
  - Plan 12-02: Tier 1 — 5 atomic indicators (`SM_ADR_Marker`, `SM_Daily_HiLo`, `SM_BPCT`, `SM_IlsleyPsychLevels`, `SM_Crossover_Arrows`) × MQ4+MQ5+Python → user review
  - Plan 12-03: Tier 2 — 6 composite indicators (`SM_TDI`, `SM_PivotPoints`, `SM_AlertZone_1`, `SM_AlertZone_2`, `SM_Alerting+TL`, `SM_NewHUD`) × MQ4+MQ5+Python → user review
- **D-02:** Within a tier, spec implementations parallelize. Each spec is an independent task per Phase 11's wave model — Tier 1 spawns 5 parallel implementer tasks, each task building 1 spec × 3 targets.
- **D-03:** Tier review checkpoint requires **compile + smoke** before approval:
  - MQ4: 0 errors / 0 warnings in MetaEditor + loads on ≥1 chart in MT4 (Wine) without runtime error
  - MQ5: 0 errors / 0 warnings in MetaEditor + loads on ≥1 chart in IC Markets KE MT5 (Wine) without runtime error
  - Python: imports cleanly + ≥1 passing pytest per indicator
- **D-04:** Phase 12 **does not** build a 4th plan for INDEX-style finalization — Phase 11's existing `INDEX.md` is updated in-place by each tier plan when specs gain "Implementation status" footers (D-13).

### Output paths

- **D-05:** MQ4 sources → `resource_pack/MMM/SM Indicators/MT4/_helix_built/` (new subfolder; isolates new code from the non-decompiled `!SM.Indicators/` originals)
- **D-06:** MQ5 sources → `resource_pack/MMM/SM Indicators/MT5/` (currently empty; this seeds it)
- **D-07:** Python module → `V2/v3_intelligence/sm_indicators/` (alongside `adr.py`, `pit.py`, `cache.py` — canonical Helix-internal location, importable from `backtest_hybrid` without sys.path tweaks when downstream phases need it)

### "Done" criteria per target (per indicator)

- **D-08 (MQ4):** Compile clean (0 errors / 0 warnings in MetaEditor) + indicator loads on ≥1 chart in MT4 under Wine without runtime error + spec's declared buffers/objects render visibly (e.g., ADR_Marker draws lines, TDI subwindow renders). No visual parity vs original `.ex4` required.
- **D-09 (MQ5):** Compile clean + loads on ≥1 chart in IC Markets KE MT5 (Wine) without runtime error + buffers/objects render. Files copied to `~/.mt5/.../IC Markets KE MT5 Terminal/MQL5/Indicators/` per the Phase 8.4 P04 acceptance pattern.
- **D-10 (Python):** Module exposes `compute_<name>(df: DataFrame, params: <Name>Params) -> DataFrame`. Each spec's Section 10 test cases convert into actual pytest test functions in `tests/v3_intelligence/sm_indicators/test_<name>.py`. ≥1 test GREEN per indicator. Module imports cleanly into `V2/`.

### Python module shape

- **D-11:** Function-first surface, params as frozen dataclasses. Mirrors `V2/v3_intelligence/adr.py:compute_adr()`. No class-based `Indicator` interface — heterogeneous spec patterns (helpers ≠ indicators ≠ HUD) make the abstraction premature.
- **D-12 (Alerts in Python):** Log events only — `compute_*()` returns DataFrame with an `alert_signal` column (bool/categorical) where the spec defines alerts. No email/sound/push from Python. Caller decides routing. Matches Phase 11 Port Notes recommendation.
- **D-12a (Plot helpers):** Skipped — Phase 12 ships compute() + tests only. matplotlib/plotly helpers deferred.
- **D-12b (Backtest wiring):** Skipped — `backtest_hybrid.py` is **not modified** by Phase 12. Wiring SM_TDI / SM_PivotPoints to strategies is a follow-up phase.

### Spec linkback

- **D-13:** Every implementation task ends by appending an "Implementation status" table to its spec at `resource_pack/MMM/SM Indicators/docs/{helpers,indicators}/<name>.md`. Table columns: target (MQ4/MQ5/Python), status (Built ✅ / Stubbed ⚠ / Skipped ❌), file path, commit SHA, date. Preserves Phase 11 "spec is canonical" — implementation status is a footer, not a separate registry.
- **D-14:** `INDEX.md` at `resource_pack/MMM/SM Indicators/docs/INDEX.md` gains an "Implementation matrix" section updated at each tier's end, summarizing the per-spec status table.

### Cross-platform parity

- **D-15:** Advisory parity check for High-confidence deterministic indicators (`sm_gmtoffset`, `sm_WorkTime`, `SM_TDI`, `SM_ADR_Marker`, `SM_Daily_HiLo`, `SM_PivotPoints`, `SM_IlsleyPsychLevels`). Plan 12-02 / 12-03 add a `scripts/parity_check_<name>.py` that exports the MQ5 indicator buffer to CSV (manual op via MT5 strategy tester or buffer-print) and diffs vs Python `compute_*()` within tolerance — `1e-4` for prices, `1e-6` for ratios/normalized series. **Captured as evidence in `evidence/`, NOT a blocker for tier review.** Headless MQ5 export tooling stays out of scope.
- **D-16:** No parity tested for medium/low-confidence indicators (`SM_BPCT`, `SM_AlertZone_1/2`, `SM_Alerting+TL`, `SM_Crossover_Arrows`, `SM_NewHUD`) — too many [INFER] defaults make "parity" undefined. Each target stands alone against the spec.

### Low-confidence indicators

- **D-17:** Low-confidence indicators (those with Header confidence Low, or whose Section 12 Uncertainty log has `[INFER:guess]` entries — `SM_BPCT` is the primary case) are built **best-effort** per the spec's best-guess algorithm. Every guessed branch carries an `// [INFER]` (MQ4/MQ5) or `# [INFER]` (Python) source comment with the spec line reference. Tests assert the algorithm runs and produces shape-correct output — they do **not** assert it matches the original `.ex4` (unobservable). Spec footer marks these `Built ⚠` instead of `Built ✅`.
- **D-18:** Stubs and skips are not used. Every indicator gets a real implementation. This satisfies Phase 12's success criterion of "all 14 implemented across all 3 targets" while staying honest about confidence via D-17's `⚠` marker.

### MQ4 ↔ MQ5 source code style

- **D-19:** MQ5 ports follow **MQ5-idiomatic** patterns — indicator handles, `OnCalculate(rates_total, prev_calculated, time, open, high, low, close, tick_volume, volume, spread)`, `CopyBuffer` / `CopyRates`, MQL5 `ObjectCreate(0, name, type, sub_window, ...)` signatures. Reference precedent: `V2/indicators/BandD_TradeReplay.mq5`, `V2/indicators/ADR_Levels.mq5`, `V2/indicators/RegimeClassifier.mq5`. No `#ifdef __MQL5__` shims.
- **D-20:** MQ4 ports use MQL4 idioms — `int init()/start()/deinit()` legacy or `OnInit/OnCalculate(int rates_total, int prev_calculated, ...)` MQL4-style, `iCustom` for inter-indicator calls, MQL4 `ObjectCreate(name, type, sub_window, time, price)` signatures. Two parallel sources per indicator, each idiomatic to its platform — Phase 11 Section 11 "MQ4 → MQ5 deltas" is the rosetta stone.

### Claude's Discretion

- Exact subfolder structure under `_helix_built/` (flat vs `helpers/` + `indicators/`) — recommend mirroring Phase 11 docs/ layout for traceability
- Pytest fixture organization for spec test cases (one fixture file per indicator vs shared OHLCV fixtures)
- Whether parity-check scripts get unit-tested themselves (recommend: no, advisory tooling)
- MQ4 vs MQ5 alert configuration defaults — pick the MMM-typical (popup + sound on, email/push off) where the spec is silent; tag `[INFER]`
- Whether `resource_pack/MMM/SM Indicators/MT4/_helix_built/` gets its own README — recommend yes, brief one explaining "these are reconstructions of !SM_*.ex4 originals from docs/ specs"

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner, plan-checker, executor) MUST read these before doing their work.**

### Phase 11 specs (the implementation contract — read Section 11 of each)

- `resource_pack/MMM/SM Indicators/docs/INDEX.md` — overview, dependency graph, confidence summary
- `resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md` — Tier 0 helper (GMT offset detection)
- `resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime.md` — Tier 0 helper (session windows, depends on sm_gmtoffset)
- `resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md` — Tier 0 helper (manual GMT variant)
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_ADR_Marker.md` — Tier 1 atomic
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_Daily_HiLo.md` — Tier 1 atomic
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md` — Tier 1 atomic (Low confidence — D-17 applies)
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_IlsleyPsychLevels.md` — Tier 1 atomic
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_Crossover_Arrows.md` — Tier 1 atomic
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md` — Tier 2 composite (load-bearing — High confidence)
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_PivotPoints.md` — Tier 2 composite
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_1.md` — Tier 2 composite
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_AlertZone_2.md` — Tier 2 composite
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_Alerting+TL.md` — Tier 2 composite
- `resource_pack/MMM/SM Indicators/docs/indicators/SM_NewHUD.md` — Tier 2 composite (largest — ~5-7 spec pages)

### MQ5 implementation precedents (style + structure templates)

- `V2/indicators/BandD_TradeReplay.mq5` — Phase 8.4 P04 precedent: header block, parameter naming, file-IO pattern
- `V2/indicators/ADR_Levels.mq5` — timeframe-agnostic indicator pattern
- `V2/indicators/BandD_WorktimeRibbon.mq5` — session-ribbon precedent (relevant for sm_WorkTime ports)
- `V2/indicators/RegimeClassifier.mq5`, `V2/indicators/SessionFilter.mq5` — additional pattern references

### Python module precedents (style + test pattern)

- `V2/v3_intelligence/adr.py` — `compute_adr()` function shape (mirrors D-11)
- `V2/v3_intelligence/pit.py` — PitClock context manager (relevant for any time-bucketed compute)
- `V2/v3_intelligence/cache.py` — OHLCVCache (Title-case OHLC convention used in tests)
- `V2/v3_intelligence/regime/` — module-with-submodule pattern (relevant for `sm_indicators/` package layout)

### MMM source material (Phase 11 already references; carry forward)

- `resource_pack/MMM/docs/_MMM Book.pdf` — primary MMM theory
- `resource_pack/MMM/docs/MMM TDI_Tradestation.pdf` — **critical for SM_TDI.md** implementation
- `resource_pack/MMM/docs/MMM TOP 5 TDI Strategies.pdf` — TDI usage patterns
- `resource_pack/MMM/docs/MMM_Glossary_Enhanced.md` — terminology reference

### Source binaries (filenames only — non-decompilable)

- `resource_pack/MMM/SM Indicators/MT4/!SM.Indicators/!SM_*.ex4` (11 files — DO NOT TOUCH)
- `resource_pack/MMM/SM Indicators/MT4/!SM.Indicators/!sm_*.ex4` (3 helper files — DO NOT TOUCH)

### Helix project context

- `.planning/PROJECT.md` — v2.0 architecture, 8-pair × M15/H1/Daily scope
- `.planning/ROADMAP.md` — Phase 12 entry (depends on Phase 11)
- `V2/v3_intelligence/pair_config.py` — canonical pair × strategy × timeframe matrix (relevant if any indicator's defaults are pair/timeframe-aware)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `V2/indicators/BandD_TradeReplay.mq5`, `ADR_Levels.mq5`, `BandD_WorktimeRibbon.mq5` — MQ5 boilerplate templates for header block, OnInit, OnCalculate, OnDeinit, ObjectCreate patterns
- `V2/v3_intelligence/adr.py:compute_adr()` — Python compute-function shape canonical example (D-11)
- `V2/v3_intelligence/pit.py:PitClock` — PiT context manager available if any indicator's Python compute() needs to be PiT-safe (probably only PivotPoints / Daily_HiLo where prior-day close matters)
- Phase 11 spec template Section 11 ("Port notes") — already includes per-target translation rules per spec; planner uses these verbatim as task `<action>` content

### Established Patterns

- Title-case OHLC columns (`Open`, `High`, `Low`, `Close`) in V2/v3_intelligence per Phase 8.4 D-20 — Python `compute_*()` functions accept Title-case (and tolerate lowercase via the existing `bars_to_log_returns` helper if needed)
- pytest fixtures live in `tests/conftest.py` with `conftest_infra.py` bridge for Phase 8.4 fixtures — Phase 12 follows the same conftest discipline
- Plan execution wave-model: Wave 0 RED scaffold → Wave 1 implementation → Wave 2+ integration. Phase 12 tier plans collapse this since the spec is already the contract — each tier plan starts at "implement against existing tests" rather than RED-scaffold-first
- MQ5 indicator distribution: copy `.mq5` source to BOTH `~/.mt5/.../MetaTrader 5/MQL5/Indicators/` AND `~/.mt5/.../IC Markets KE MT5 Terminal/MQL5/Indicators/` per Phase 8.4 P04 Task 3a precedent

### Integration Points

- `V2/v3_intelligence/sm_indicators/__init__.py` — new package; re-exports the 14 `compute_*()` functions for clean `from v3_intelligence.sm_indicators import compute_tdi` imports
- `tests/v3_intelligence/sm_indicators/` — new test directory mirroring the package structure
- `resource_pack/MMM/SM Indicators/MT4/_helix_built/` — new MQ4 home; `MT4/!SM.Indicators/` stays untouched
- `resource_pack/MMM/SM Indicators/MT5/` — currently empty; Phase 12 fills it
- INDEX.md "Implementation matrix" — new section appended; existing INDEX.md content (per Plan 11-04) preserved
- `.gitignore` — likely needs entries for compiled `*.ex5` artifacts (MetaEditor build outputs); confirm in Plan 12-01

</code_context>

<specifics>
## Specific Ideas

- **Compile + smoke evidence capture:** each tier review should leave 1-2 PNG screenshots in `evidence/tierN_compile_smoke/` showing "MetaEditor compile succeeded — N indicators, 0 errors" + 1 chart with the indicators loaded. Mirrors the Phase 8.4 INFRA-04 evidence pattern (which is a non-blocking follow-up but the format is right).
- **TDI is the highest-stakes spec.** SM_TDI feeds strategy generation logic per its Port Notes. Even though wiring to backtest_hybrid is deferred (D-12b), the Python compute_tdi() output shape MUST be backtester-ready: DataFrame with `rsi`, `volatility_band_upper`, `volatility_band_lower`, `price_line`, `signal_line`, `trade_signal` columns at minimum (per the spec). Future wiring phase will be a thin adapter, not a re-design.
- **NewHUD's complexity (~5-7 spec pages, 100KB original `.ex4`)** likely makes it the longest single implementation task. Plan 12-03 may want NewHUD as its own task with extra time budget vs the other 5 composite tasks.
- **Helpers are the most-used.** sm_gmtoffset and sm_WorkTime are referenced by every indicator that needs broker-time normalization. A bug in helpers cascades to Tier 1 + Tier 2 — hence Plan 12-01's tier review is the most important gate.
- **Operator already has IC Markets KE MT5 + Wine MT4 running** (per Phase 8.4 P04 acceptance) — D-08 / D-09 chart-load smoke tests are operationally feasible without additional setup.
- **Memory says `MQ4+MQ5+Python` — confirmed via this discussion as the locked target set.** No silent reduction to "MQ5 only" or similar.

</specifics>

<deferred>
## Deferred Ideas

- **Backtest_hybrid wiring of SM_TDI / SM_PivotPoints as alpha sources** — separate phase. Phase 12 builds the library; whether SM signals add alpha is a strategy-research question.
- **Visual parity vs original `!SM_*.ex4` binaries** — cannot be automated; many specs are [INFER]. If/when an operator wants to spot-check, they can load original + reconstruction side-by-side; capture in a backlog ticket, not Phase 12.
- **Headless MQ5 export tooling for required-parity gate** — would let advisory parity (D-15) become a CI-able required gate. Defer to a tooling phase.
- **matplotlib/plotly plot helpers for Python compute() results** — visualization phase or ad-hoc.
- **Cross-language unit tests across MQ4/MQ5/Python** — once all three exist, a parity test corpus could enforce equivalence. Future v3.0+ phase.
- **Re-spec / re-implement the ~40 third-party non-`!SM_*` indicators** in `MT4/!SM.Indicators/` — out of scope per Phase 11 boundary; carry forward.
- **MMM glossary expansion** for any new terms surfaced during implementation — backlog item, not Phase 12.
- **Live MT4/MT5 EA integration of SM indicators** — Phase 10 (LiveSignalEngine) owns live; SM indicators may feed router signals in a downstream phase, not here.

</deferred>

---

*Phase: 12-sm-indicators-implementation*
*Context gathered: 2026-04-27*

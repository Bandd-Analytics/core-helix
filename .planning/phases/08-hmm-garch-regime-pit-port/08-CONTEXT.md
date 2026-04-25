# Phase 8: HMM-GARCH Regime + PiT Port - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Port the V1 HMM-GARCH regime classifier and runtime PiT manager into V2/v3_intelligence/, harden state-label pinning by variance rank, and enforce that OnlineRegimeFilter is the sole regime source consumed by Phase 9 router and Phase 10 live paths — Viterbi is banned from both backtest and live code paths and the ban is verified by an automated CI gate. Pure Python library port: no UI, no CLI surface besides the offline-fit script. Strategy router, recalibration scheduler, and live execution wiring are out of scope (Phases 9, v3.0 EXPN-03, and Phase 10 respectively).

</domain>

<decisions>
## Implementation Decisions

### Module Structure & Dependencies
- **D-01:** Code lives in subpackage `V2/v3_intelligence/regime/` (not single regime.py). Mirrors V1 layout cleanly. Files inside: `__init__.py`, `hmm_garch.py`, `online_filter.py`, `emissions.py`, `types.py`. No `viterbi.py` (see D-04).
- **D-02:** REGM-01 wording ("regime.py") is interpreted as "the regime module"; subpackage satisfies the spirit. Phase 9 imports as `from v3_intelligence.regime import OnlineRegimeFilter, RegimeState`.
- **D-03:** `hmmlearn>=0.3` and `arch>=6.0` added to `V2/pyproject.toml` `[project.dependencies]`. Standard install path. Plan task verifies they import in V2 environment.
- **D-12:** V1 source at `V1/helix/src/alpha/regime/` is left untouched as historical reference. V2 is greenfield; nothing in V2 imports from V1. Mirrors Phase 6 D-01 pattern.

### Viterbi Banishment (REGM-04)
- **D-04:** Drop Viterbi entirely. No `viterbi.py` ported. `predict_viterbi()` method removed from V2 detector. Cleanest enforcement — REGM-04 grep gate trivially passes.
- **D-05:** Enforcement gate: `tests/v3_intelligence/test_viterbi_ban.py` runs grep against `V2/backtest/`, `V2/v3_intelligence/`, and `V2/live/` (when it exists) — fails if any match for `viterbi`, `Viterbi`, `predict_viterbi`. Permanent CI guard.

### PiT Runtime Manager (REGM-03)
- **D-06:** `V2/v3_intelligence/pit.py` is a **replay-clock context manager**: `with PitClock(t) as clock: clock.read(df, sym)` returns df rows with timestamp ≤ t; raises `FutureBarReadError` on any access where the read timestamp exceeds t. Lightweight, pandas-native. No ArcticDB dependency.
- **D-07:** Integration is **opt-in via decorator on backtest method**. Existing backtest_hybrid.py + backtest_evaluate_all.py loops continue to work unchanged. Phase 9 router 4yr simulation (ROUT-04) opts in by wrapping its replay loop in PitClock. Lowest disruption to Phase 7 work.
- **D-08:** Future-bar check is **timestamp-based**: compare `bar.ts > as_of_ts` and raise. Robust across irregular bars, gaps, and resampled data. Index-based check (i+k) is intentionally not used to avoid coupling to integer-indexed loop semantics.
- **D-09:** Mandatory test: a deliberate out-of-order read (e.g. `clock.read(df, ts=t+1h)` while clock is at t) raises `FutureBarReadError` rather than silently succeeding. This is the success criterion 3 contract.

### Per-Pair Detector + Persistence
- **D-10:** **One detector per pair — 5 detectors total** (USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP). Each pair has independent volatility regimes. Phase 9 router accesses via `detector_registry[pair].update(returns[t])`.
- **D-11:** Fitted state persisted as **JSON + numpy arrays** at `V2/data/regime/{PAIR}_detector.json`. Human-readable, version-controllable, ~1KB per pair. Schema: GARCHParams list (mu, omega, alpha, beta) + transmat (3×3) + startprob (3,) + variance_ordering metadata + fit_timestamp + fit_data_window.
- **D-13:** Offline fit is a **standalone CLI**: `V2/scripts/fit_regime_detectors.py`. Invocation: `python -m scripts.fit_regime_detectors --pair USDJPY --data 4yr` or `--pair all`. Backtest and live both load from disk. Mirrors Phase 7 `download_history.py` CLI pattern.

### Recalibration Scope
- **D-14:** V1 `calibration.py` (RecalibrationService) is **deferred to v3.0 EXPN-03** (walk-forward retraining on rolling 2yr window). Phase 8 ships static-fit detectors only. Keeps Phase 8 critical-path scope contained around REGM-01/02/03/04.
- **D-15:** v2.0 paper-trade drift handling: **manual refit via `fit_regime_detectors.py` CLI**. If 7-day paper trade (LIVE-04) shows obvious regime drift, operator re-runs fit CLI with newer data. Pragmatic for a small operator team; v3.0 automates.

### Validation / Parity Strategy
- **D-16:** Port faithfulness proven by **statistical match within tolerance**, not bit-exact parity. Fixed seed + same returns array → V2 GARCHParams match V1 within 1e-6; OnlineRegimeFilter outputs same state on ≥95% of test bars. Practical and testable; tolerates numpy/scipy version differences between V1 (Python 3.10) and V2 (Python 3.12).
- **D-17:** Parity tests live in **`tests/v3_intelligence/test_regime_parity.py`**, marked `@pytest.mark.slow` so they're deselected from default fast runs. CI runs them on demand or nightly.
- **D-18:** Parity failure during port **blocks phase completion**. Investigation required to identify math drift or version bug. Matches Phase 7 BKTS-01 "demonstrably corrected" bar.

### Returns Input Contract
- **D-19:** V2 detector `fit()` and OnlineRegimeFilter `update()` accept **np.ndarray of log-returns** (V1 contract preserved). Detector stays pure numerical; caller supplies returns. Easier to test with synthetic returns; adapter handles bar→returns at integration layer.
- **D-20:** Bar→log-return conversion lives in **helper `bars_to_log_returns(df: pd.DataFrame) -> np.ndarray`** in `V2/v3_intelligence/regime/__init__.py`. Implementation: `np.log(df['close'] / df['close'].shift(1)).dropna().values`. Reused by offline fit CLI and live integration. Tested independently.
- **D-21:** OnlineRegimeFilter.update() return signature **preserves V1 contract**: `(state: RegimeState, confidence: float)`. Phase 9 router gets enum + confidence. Full state probability vector exposed via `.state_probs` property for any future need.

### RegimeState Enum + Signal Types
- **D-22:** `RegimeState` enum lives at **`V2/v3_intelligence/regime/types.py`**. Re-exported via `regime/__init__.py` for consumer ergonomics: `from v3_intelligence.regime import RegimeState`. Values: `TRENDING=0`, `MEAN_REVERTING=1`, `CRISIS=2` — matches V1.
- **D-23:** **Only RegimeState** is ported from V1 `signal_types.py` for Phase 8. Other types (Signal, etc.) ported when subsequent phases require them. Avoids dead code and pre-emptive shape decisions.

### Fit Data Window
- **D-24:** Offline fit uses **full 4yr H1 data per pair** (~35k bars). Maximizes statistical strength of GARCH parameter estimation. Phase 7 already corrected entry bias on this data — trustworthy. v3.0 walk-forward (EXPN-03) handles drift; Phase 8 needs a stable fit.
- **D-25:** **Offline fit explicitly bypasses PitClock**. Offline fit has the full dataset by definition — PiT is a backtest/live concern. `fit_regime_detectors.py` loads CSV directly, no clock. PitClock is enforced only on Phase 9 router replay loop and Phase 10 live update path.

### Failed-Fit Behavior
- **D-26:** If `detector.fit()` returns False (stationarity fail or HMM non-convergence) for a pair, **CLI exits non-zero and blocks pair_config update**. `fit_regime_detectors.py` prints which pair failed + reason. No persisted JSON for that pair. Mirrors Phase 7 PiT validator gate pattern.
- **D-27:** Phase 9 router treats **missing detector as 'regime data unavailable' and rejects entries on that pair**. `StrategyRouter.route(pair, ...)` returns None. Conservative default: no regime signal = no trade. Aligns with Phase 9 ROUT-01 "or None" contract.

### RAG / vol_regime Alignment
- **D-28:** HMM-GARCH states and RAG `vol_regime` (HIGH_VOL/LOW_VOL/MED_VOL percentile bucketing) **stay independent for v2.0**. HMM is the hard gate (pass/fail on regime), RAG is the soft confidence score (continuous). Two complementary layers compose naturally without coupling. The +0.41 Sharpe RAG lift was validated without HMM in the loop — no evidence coupling helps; risk of double-counting in router confidence math.
- **D-29:** **`rag_signal_filter.py` is untouched in Phase 8**. Phase 8 owns regime + PiT only. If a future phase shows router-level benefit from regime-aware RAG, port it then as a dedicated phase that owns ChromaDB re-indexing.

### Claude's Discretion
- Exact JSON schema layout for persisted detector files (field names, key ordering)
- Internal class/function naming inside the regime subpackage
- Whether `bars_to_log_returns` lives in `__init__.py` directly or in a private `_utils.py` re-exported from __init__
- Exact pytest fixture structure for parity tests (synthetic returns generator, V1 baseline data path)
- Logging verbosity defaults for the offline fit CLI (currently no project-wide logging convention beyond V1's `logging.getLogger("helix.alpha")`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` §Regime + PiT — REGM-01 through REGM-04 definitions (HMM-GARCH port, variance-rank label pinning, PiT manager port, Viterbi ban)
- `.planning/ROADMAP.md` §Phase 8 — Goal, success criteria, dependency on Phase 6 (bar event cadence)

### V1 Port Sources
- `V1/helix/src/alpha/regime/hmm_garch.py` — Two-stage HMM-GARCH detector (253 lines); fit() flow + `_remap_matrix` for variance-rank state pinning; private `_fit_gaussian_hmm` and `_fit_garch` helpers
- `V1/helix/src/alpha/regime/online_filter.py` — OnlineRegimeFilter forward-algorithm filter (151 lines); `update()` return contract, log-space underflow fallback `_log_space_forward`
- `V1/helix/src/alpha/regime/emissions.py` — `GARCHParams` dataclass + `garch_emission_prob` (97 lines); stationarity property; conditional variance recursion
- `V1/helix/src/alpha/regime/viterbi.py` — V1 viterbi_decode (60 lines); **REFERENCE ONLY — NOT PORTED** per D-04
- `V1/helix/src/alpha/regime/calibration.py` — RecalibrationService (194 lines); **REFERENCE ONLY — NOT PORTED** per D-14, deferred to v3.0 EXPN-03
- `V1/helix/src/data/pit_manager.py` — V1 ArcticDB-backed PiT manager (151 lines); **REFERENCE ONLY for semantics** — V2 reimplements as lightweight pandas replay clock per D-06
- `V1/helix/src/alpha/signal_types.py` — Source of `RegimeState` enum (port only this enum per D-23)
- `V1/helix/tests/alpha/test_regime_detector.py` — V1 detector test suite; reference for V2 unit-test scope
- `V1/helix/tests/alpha/test_online_filter.py` — V1 online filter tests; reference for V2 unit-test scope
- `V1/helix/tests/data/test_pit_integrity.py` — V1 PiT integrity tests; informs V2 PitClock test scope (semantics only — V2 contract differs)

### V2 Targets (files to create or modify)
- `V2/v3_intelligence/regime/__init__.py` — NEW; package exports + `bars_to_log_returns` helper
- `V2/v3_intelligence/regime/hmm_garch.py` — NEW; ported HMM-GARCH detector
- `V2/v3_intelligence/regime/online_filter.py` — NEW; ported OnlineRegimeFilter
- `V2/v3_intelligence/regime/emissions.py` — NEW; ported GARCHParams + garch_emission_prob
- `V2/v3_intelligence/regime/types.py` — NEW; RegimeState enum
- `V2/v3_intelligence/pit.py` — NEW; PitClock context manager + FutureBarReadError
- `V2/scripts/fit_regime_detectors.py` — NEW; offline-fit CLI per D-13
- `V2/data/regime/` — NEW directory; persisted detector JSON files (D-11)
- `V2/pyproject.toml` — MODIFY; add hmmlearn + arch to [project.dependencies] per D-03

### V2 Existing Context (do not modify in Phase 8)
- `V2/v3_intelligence/pair_config.py` — Reference for pair list (USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP); not modified by Phase 8
- `V2/v3_intelligence/rag_signal_filter.py` — Untouched per D-29
- `V2/v3_intelligence/__init__.py` — May need import update to expose regime subpackage
- `V2/backtest/pit_validator.py` — Existing static AST validator from Phase 7; complementary to new runtime PitClock, not duplicate
- `V2/backtest/backtest_hybrid.py`, `V2/backtest/backtest_evaluate_all.py` — Not modified in Phase 8 (PitClock is opt-in per D-07; Phase 9 wires the opt-in)

### Phase Predecessor Context
- `.planning/phases/06-zmq-bridge-port/06-CONTEXT.md` §D-13, D-15 — Bar event cadence + OHLCV payload schema; informs how live regime updates are triggered (Phase 10 wiring)
- `.planning/phases/07-backtest-entry-fix-h1-momentum-4yr-validation/07-CONTEXT.md` — Phase 7 PiT validator approach + 4yr CSV layout used by Phase 8 offline fit

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **V1 regime/ subpackage** (922 lines, 5 files): structurally clean, well-typed, has docstrings — port is a faithful translation, not a redesign
- **V1 GARCHParams dataclass** (`emissions.py`): `is_stationary` and `unconditional_variance` properties carry over directly; frozen dataclass shape preserved
- **V1 `_remap_matrix` helper** (`hmm_garch.py`): variance-rank state pinning logic ports verbatim — REGM-02 satisfied by-construction once this is in V2
- **V1 `_log_space_forward` underflow fallback** (`online_filter.py`): numerical robustness; ported as-is
- **V2 pyproject.toml**: already configured for pytest with `pit_check`, `slow`, `spike` markers — Phase 8 reuses `slow` marker for parity tests (D-17)
- **V2/scripts/download_history.py** (Phase 7): CLI structure pattern reused for `fit_regime_detectors.py` (argparse, --pair flag, idempotent skip-if-exists)

### Established Patterns
- **V2/v3_intelligence flat layout** today: 3 modules at root (`pair_config.py`, `rag_signal_filter.py`, `trade_logger.py`). Phase 8 introduces the first subpackage — sets the precedent for future intelligence modules with internal structure
- **Phase 7 test scaffolding pattern**: Wave 0 plan = RED tests collected before implementation; subsequent waves turn them GREEN. Phase 8 should follow the same pattern (Wave 0: regime + PitClock test scaffolding RED; Wave 1: HMM-GARCH + emissions GREEN; Wave 2: OnlineRegimeFilter + PitClock GREEN; Wave 3: offline fit CLI + parity validation)
- **Phase 7 PiT gate pattern**: `pit_validator.py` is a CLI gate that exits non-zero on violation. Phase 8 mirrors with `fit_regime_detectors.py` exiting non-zero on fit failure (D-26)
- **Pair list**: USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP — from `pair_config.py` PAIR_CONFIGS — drives the 5 detectors per D-10

### Integration Points
- **Phase 9 router consumes Phase 8 contract**: `detector_registry: dict[str, OnlineRegimeFilter]` loaded from `V2/data/regime/*.json`; `state, conf = detector_registry[pair].update(log_return)` per bar. Phase 8 contract must support this lookup and incremental update without recreating filter objects.
- **Phase 10 live consumes Phase 8 contract**: ZMQ bar-close events from bridge (Phase 6 D-15) → bars_to_log_returns adapter → OnlineRegimeFilter.update() → router gate. PitClock not used live (live is by definition causal).
- **Phase 7 4yr CSVs**: `V2/data/{PAIR}_H1_4yr.csv` is the input to offline fit. Loaded as pandas DataFrame, converted via `bars_to_log_returns`, passed to `HMMGARCHRegimeDetector.fit()`.
- **No bridge changes**: Phase 6 schema unchanged. Phase 8 reads bridge bar events through Phase 10 wiring; no bridge code modified.

</code_context>

<specifics>
## Specific Ideas

- The persisted detector JSON should include a `fit_metadata` block: `{ "fitted_at_utc": ..., "data_window": "4yr", "data_path": "V2/data/USDJPY_H1_4yr.csv", "n_bars": 35040, "v1_parity_tested": true, "schema_version": 1 }` — for forensic auditing of fit provenance
- The variance-rank ordering metadata should be explicit in JSON: `{ "state_labels": ["TRENDING", "MEAN_REVERTING", "CRISIS"], "unconditional_variances": [1.2e-7, 4.8e-7, 2.3e-6] }` — makes REGM-02 visible on inspection
- Parity test fixture: a deterministic synthetic returns generator (numpy seed=42, T=1000, three-regime mixture) shared between V1 baseline reproduction and V2 port; output captured into `tests/v3_intelligence/parity_baseline.npz`
- "Viterbi banished" log message in regime package init: `WARNING: Viterbi decoding is banned per REGM-04 — use OnlineRegimeFilter for both backtest and live` printed if anyone imports a hypothetical compatibility shim
- PitClock sentinel pattern: `PitClock.UNBOUNDED` clock for offline-fit context that wants no enforcement (D-25) — explicit rather than `None` to make intent visible

</specifics>

<deferred>
## Deferred Ideas

- **RecalibrationService port** — Weekly Baum-Welch refit + two-gate stationarity/agreement validation (V1 calibration.py). Deferred to v3.0 EXPN-03 walk-forward retraining (D-14)
- **Walk-forward regime fitting on rolling window** — Deferred to v3.0 EXPN-03; Phase 8 uses single 4yr fit (D-24)
- **HMM state coupling into RAG context embeddings** — Investigated and deferred. Independent layers preferred for v2.0 (D-28). Future phase would own ChromaDB re-indexing if benefit demonstrated
- **Pair tier–based detector pooling** — Considered (one detector per Sharpe tier). Rejected for v2.0; one-per-pair chosen (D-10). Could be revisited if detector count becomes a maintenance burden in v3.0
- **Mandatory PitClock on existing backtest loops** — Considered. Rejected as too invasive in Phase 8; kept opt-in (D-07). Phase 9 router opts in for ROUT-04 simulation
- **Pre-commit hook for Viterbi import blocking** — Considered. Rejected; pytest grep gate (D-05) is sufficient and lighter infra
- **ArcticDB-backed PiT manager (V1 parity)** — Rejected; too heavy for V2 (D-06). Lightweight pandas wrapper covers REGM-03

</deferred>

---

*Phase: 08-hmm-garch-regime-pit-port*
*Context gathered: 2026-04-25*

# Phase 8: HMM-GARCH Regime + PiT Port - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 08-hmm-garch-regime-pit-port
**Areas discussed:** Module structure & deps, Viterbi banishment, PiT runtime manager, Per-pair detector + persistence, Recalibration scope, Validation/parity, Returns input contract, RegimeState enum + signal_types, Fit data window, Failed-fit fallback, RAG vol_regime alignment

---

## Module Structure & Dependencies

### Q1: Where does HMM-GARCH code live in V2?

| Option | Description | Selected |
|--------|-------------|----------|
| Subpackage: V2/v3_intelligence/regime/ (Recommended) | Mirrors V1 with hmm_garch.py, online_filter.py, emissions.py inside regime/. Cleanest separation. Phase 9 imports as `from v3_intelligence.regime import OnlineRegimeFilter`. | YES |
| Single flat file: V2/v3_intelligence/regime.py | Literal interpretation of REGM-01. Flattens all V1 modules into ~700 lines. Easier import surface but big monolithic file. | |
| Hybrid: regime.py + regime_emissions.py | Top-level regime.py exports public API; emissions/viterbi internals split into sibling files at v3_intelligence/ root. | |

**User's choice:** Subpackage `V2/v3_intelligence/regime/`
**Notes:** REGM-01 wording reinterpreted as "the regime module" rather than literal regime.py file.

### Q2: Where do hmmlearn + arch dependencies get added?

| Option | Description | Selected |
|--------|-------------|----------|
| V2/pyproject.toml [project.dependencies] (Recommended) | Pin hmmlearn>=0.3 and arch>=6.0 in canonical V2 project. | YES |
| Optional extras: [project.optional-dependencies.regime] | Mark as optional install group. Adds complexity for no benefit. | |
| You decide | Claude picks based on what's idiomatic. | |

**User's choice:** V2/pyproject.toml [project.dependencies]

### Q3: Should V1 source be deleted, archived, or left in place?

| Option | Description | Selected |
|--------|-------------|----------|
| Leave V1 untouched — port is greenfield (Recommended) | V1/helix/src/alpha/regime/ stays as historical reference. Matches Phase 6 D-01. | YES |
| Delete V1 regime files after port verified | Cleaner repo but loses reference for future audits. | |
| Archive V1 regime files into V1/.archived/ | Move out of active path but keep accessible. | |

**User's choice:** Leave V1 untouched

---

## Viterbi Banishment (REGM-04)

### Q1: How is Viterbi banished?

| Option | Description | Selected |
|--------|-------------|----------|
| Drop entirely — no viterbi.py, no predict_viterbi() (Recommended) | Cleanest enforcement. V2 has no viterbi.py at all. REGM-04 grep test trivially passes. | YES |
| Keep but raise NotImplementedError on call | Port as a stub that raises with REGM-04 message. Slightly redundant given grep gate. | |
| Move to regime/_research.py, not in __init__ | Keeps for ad-hoc research notebooks. Grep gate must whitelist the _research path. | |

**User's choice:** Drop entirely

### Q2: How is the REGM-04 gate enforced?

| Option | Description | Selected |
|--------|-------------|----------|
| Pytest test that greps codebase + fails on violation (Recommended) | tests/v3_intelligence/test_viterbi_ban.py greps V2/backtest/, V2/v3_intelligence/. Permanent CI guard. | YES |
| Pre-commit hook that blocks viterbi imports | Stronger but adds infra; project doesn't currently use pre-commit hooks. | |
| Documentation only — ADR + comment | Weakest — nothing actually prevents future regression. | |

**User's choice:** Pytest grep gate

---

## PiT Runtime Manager (REGM-03)

### Q1: What shape does V2/v3_intelligence/pit.py take?

| Option | Description | Selected |
|--------|-------------|----------|
| Replay-clock context manager (Recommended) | `with PitClock(t) as clock: clock.read(df, sym)` returns df.loc[:t]; raises FutureBarReadError. Lightweight, pandas-native. | YES |
| Snapshot wrapper class | `PitFrame(df, as_of=t)` instance returns rows up to t. Slightly heavier. | |
| Function-decorator pattern | `@pit_guarded` on data accessors. Less invasive but harder to thread through pandas method calls. | |
| Full ArcticDB port | Match V1 1:1. Heavy dep for in-memory backtest — overkill given V2 reads CSVs. | |

**User's choice:** Replay-clock context manager

### Q2: How does the PiT manager integrate with backtest loops?

| Option | Description | Selected |
|--------|-------------|----------|
| Optional opt-in via decorator on backtest method (Recommended) | Existing backtest loops wrap with PitClock; if not wrapped, behavior unchanged. Phase 9 router opts in. | YES |
| Mandatory — all backtest data access through PitClock | Refactor every iloc[i+1] in backtest_evaluate_all.py. Risk of re-introducing entry bias. | |
| Wrap only the regime detector input | Narrow scope but doesn't catch leakage in non-regime code. | |

**User's choice:** Optional opt-in

### Q3: What does a "future-bar read" mean — timestamp vs index check?

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp check: bar.ts > as_of_ts raises (Recommended) | Robust across irregular bars, gaps, resampled data. | YES |
| Index check: i+k where k>0 raises unless whitelisted | Cheap but couples to integer-indexed loops. | |
| Both — timestamp primary, index check as belt-and-braces | Probably overkill for a single replay loop. | |

**User's choice:** Timestamp check

---

## Per-Pair Detector + Persistence

### Q1: How many fitted detectors does V2 maintain?

| Option | Description | Selected |
|--------|-------------|----------|
| One per pair — 5 detectors (Recommended) | USDJPY behaves nothing like EURGBP. Phase 9 router does `detector_registry[pair].update(returns[t])`. | YES |
| One global detector on concatenated returns | Simpler infra but loses pair-specific volatility regimes. | |
| Tiered — one per Sharpe tier | Some pooling benefit; complex; not aligned with current pair_config tiering. | |

**User's choice:** One per pair (5 detectors)

### Q2: How is fitted detector state persisted?

| Option | Description | Selected |
|--------|-------------|----------|
| JSON + numpy arrays in V2/data/regime/{PAIR}_detector.json (Recommended) | Human-readable, version-controllable. ~1KB per pair. | YES |
| joblib binary serialization in V2/data/regime/{PAIR}_detector.bin | Standard sklearn-style. Bigger file, opaque on inspection. (Note: binary serialization formats can pose security risks if loaded from untrusted sources.) | |
| Refit on every run — no persistence | Cleanest reproducibility; ~30s cost per backtest. | |

**User's choice:** JSON + numpy arrays

### Q3: Where does the offline fit happen?

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone CLI: V2/scripts/fit_regime_detectors.py (Recommended) | Mirrors Phase 7 download_history.py pattern. Backtest + live load from disk. | YES |
| Auto-fit on first backtest run if missing | Lazy. Risks fitting on stale data; mixes concerns. | |
| Both — CLI for explicit fit, fallback to auto-fit | Marginal value over option 1 alone. | |

**User's choice:** Standalone CLI

---

## Recalibration Scope

### Q1: Is V1 calibration.py ported in Phase 8?

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to v3.0 EXPN-03 (Recommended) | Phase 8 ships static-fit detectors only. EXPN-03 (walk-forward retraining) is the natural home. | YES |
| Stub interface in Phase 8, implementation in v3.0 | Adds dead code now. | |
| Port now — full feature parity with V1 | Risks blocking v2.0 critical path. | |

**User's choice:** Defer to v3.0 EXPN-03

### Q2: What handles regime drift during v2.0 paper trade?

| Option | Description | Selected |
|--------|-------------|----------|
| Manual refit via fit_regime_detectors.py CLI (Recommended) | Operator re-runs fit CLI manually with newer data. v3.0 automates. | YES |
| Document drift detection — no auto action | Captures signal without commitment. | |
| No drift handling in v2.0 | 7-day paper trade too short for drift to matter. | |

**User's choice:** Manual refit via CLI

---

## Validation / Parity Strategy

### Q1: What evidence proves the V2 port matches V1?

| Option | Description | Selected |
|--------|-------------|----------|
| Statistical match within tolerance (Recommended) | Fixed seed → V2 GARCHParams match V1 within 1e-6; states match on ≥95% of bars. Tolerates 3.10→3.12 differences. | YES |
| Bit-exact deterministic parity | Strongest but brittle to numpy/scipy version differences. | |
| Contract-only tests | Lightest — but if a math bug slips in, no V1 baseline catches it. | |

**User's choice:** Statistical match within tolerance

### Q2: Where does the parity test live?

| Option | Description | Selected |
|--------|-------------|----------|
| tests/v3_intelligence/test_regime_parity.py (Recommended) | Dedicated parity suite. Marked @pytest.mark.slow. | YES |
| Inline in test_regime_detector.py | Slow tests pollute fast suite. | |
| Standalone validation notebook | Visual but not CI-gated. | |

**User's choice:** test_regime_parity.py with @pytest.mark.slow

### Q3: What happens if parity fails?

| Option | Description | Selected |
|--------|-------------|----------|
| Block phase completion until resolved (Recommended) | Parity is the success gate. | YES |
| Log delta, proceed if behavior reasonable | Lets unidentified bugs ship. | |
| Defer parity to a later validation phase | Defers the truth. | |

**User's choice:** Block phase completion

---

## Returns Input Contract

### Q1: What input does V2 detector accept?

| Option | Description | Selected |
|--------|-------------|----------|
| np.ndarray of log-returns — V1 contract preserved (Recommended) | Pure numerical detector; caller computes returns. Easier to test. | YES |
| pd.DataFrame OHLCV — detector computes returns internally | Couples detector to OHLC schema. | |
| Both — polymorphic accepts ndarray or DataFrame | Branching, harder to test, fuzzy contract. | |

**User's choice:** np.ndarray of log-returns

### Q2: Where does bar → log-return conversion live?

| Option | Description | Selected |
|--------|-------------|----------|
| Helper in regime/__init__.py: bars_to_log_returns(df) (Recommended) | Single function reused by offline fit CLI and online filter. | YES |
| Inline in OnlineRegimeFilter.update_from_bar() method | Couples regime to bridge schema. | |
| Caller's responsibility — no helper | Invites duplication and pct vs log-return bugs. | |

**User's choice:** Helper in regime/__init__.py

### Q3: OnlineRegimeFilter.update() return signature?

| Option | Description | Selected |
|--------|-------------|----------|
| (state: RegimeState, confidence: float) — V1 contract preserved (Recommended) | Phase 9 router gets enum + confidence. Probabilities exposed via .state_probs property. | YES |
| Full state probability vector — (probs: np.ndarray,) | Richer for future RAG-style weighting. | |
| Dict: {state, confidence, probs, sigma2} | Verbose at call site. | |

**User's choice:** (state: RegimeState, confidence: float) — V1 contract preserved

---

## RegimeState Enum + Signal Types

### Q1: Where does the RegimeState enum live in V2?

| Option | Description | Selected |
|--------|-------------|----------|
| regime/types.py (Recommended) | Dedicated types module inside regime subpackage. Re-exported via __init__.py. | YES |
| v3_intelligence/signal_types.py (mirrors V1 path) | Slightly speculative — RAG and pair_config don't reference RegimeState today. | |
| Inline in regime/__init__.py | Couples package init to type definitions. | |

**User's choice:** regime/types.py

### Q2: Does V2 port other types from V1 signal_types.py?

| Option | Description | Selected |
|--------|-------------|----------|
| Only RegimeState — minimum needed for REGM-01–04 (Recommended) | Add others when phases require them. | YES |
| Port the full signal_types.py to V2 | Risk of dead code. | |
| You decide — audit during port | Claude inspects V1 and ports anything genuinely shared. | |

**User's choice:** Only RegimeState

---

## Fit Data Window

### Q1: What data window does the offline fit use?

| Option | Description | Selected |
|--------|-------------|----------|
| Full 4yr H1 — fit on everything (Recommended) | ~35k bars per pair. Maximizes statistical strength. | YES |
| 3yr train + 1yr holdout for parity test | Loses 25% of fit signal. | |
| Last 1260 bars (V1 calibration default) | Loses long-horizon variance structure. | |

**User's choice:** Full 4yr H1

### Q2: How is fit data isolated from PiT validation?

| Option | Description | Selected |
|--------|-------------|----------|
| Offline fit explicitly bypasses PitClock (Recommended) | PiT is a backtest/live concern. fit_regime_detectors.py loads CSV directly. | YES |
| Fit runs through a "training mode" PitClock | Pedantic; offline fit is non-causal by design. | |
| You decide | Planner picks. | |

**User's choice:** Offline fit explicitly bypasses PitClock

---

## Failed-Fit Fallback Behavior

### Q1: If detector.fit() returns False, what happens?

| Option | Description | Selected |
|--------|-------------|----------|
| CLI exits non-zero, blocks pair_config update (Recommended) | Mirrors Phase 7 PiT validator gate pattern. | YES |
| Persist a "failed-fit sentinel" JSON marking pair disabled | Adds bookkeeping vs simply having no file. | |
| Fallback to uniform regime priors and warn | Defeats REGM-01's purpose; risky. | |

**User's choice:** CLI exits non-zero, blocks pair_config update

### Q2: What does the router do when no detector exists for a pair?

| Option | Description | Selected |
|--------|-------------|----------|
| Reject all entries on that pair until detector exists (Recommended) | Conservative: no regime signal = no trade. Aligns with ROUT-01 "or None" contract. | YES |
| Allow swing only, block H1/momentum | Partial trading; complex. | |
| Defer this to Phase 9 design | Reasonable boundary. | |

**User's choice:** Reject all entries on that pair until detector exists

---

## RAG vol_regime Alignment

### Q1: Does Phase 8 reconcile RAG's vol_regime with HMM-GARCH states?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep independent for v2.0 (Recommended) | HMM = hard gate, RAG = soft confidence. Two complementary layers. | YES |
| Replace RAG vol_regime with HMM state label | Invalidates existing ChromaDB embeddings; requires re-indexing. | |
| Add HMM state as additional RAG context field | Couples them; requires ChromaDB re-indexing for full benefit. | |

**User initial reply:** "I am not sure persay. How would adding HMM as additional RAG affect things?"
**Claude's analysis:** Walked through impact — ChromaDB re-indexing requirement, transition asymmetry, regime-fit timing coupling, scope creep, double-counting risk in router confidence. Recommended keeping independent.
**User's final choice:** Keep independent for v2.0

### Q2: Is rag_signal_filter.py modification in scope for Phase 8?

(Skipped — answered implicitly by Q1 final choice: RAG untouched in Phase 8.)

---

## Claude's Discretion

Areas where the user explicitly deferred or where the workflow recommendation was followed without alternative selection:
- Exact JSON schema layout for persisted detector files
- Internal class/function naming inside the regime subpackage
- Whether bars_to_log_returns lives in __init__.py directly or in a private _utils.py
- Exact pytest fixture structure for parity tests
- Logging verbosity defaults for the offline fit CLI

## Deferred Ideas

- RecalibrationService port (V1 calibration.py) → v3.0 EXPN-03
- Walk-forward regime fitting on rolling window → v3.0 EXPN-03
- HMM state coupling into RAG context embeddings → future phase if router benefit demonstrated
- Pair tier–based detector pooling → potential v3.0 revisit
- Mandatory PitClock on existing backtest loops → considered, rejected
- Pre-commit hook for Viterbi import blocking → considered, rejected
- ArcticDB-backed PiT manager → rejected

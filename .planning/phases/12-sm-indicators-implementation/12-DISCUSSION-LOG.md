# Phase 12: SM Indicators implementation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `12-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 12-sm-indicators-implementation
**Areas discussed:** Build order across targets, 'Done' definition per target, Python integration scope, Cross-platform parity & low-confidence handling

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Build order across targets | Tier-by-tier across 3 targets vs platform-by-platform vs full matrix | ✓ |
| 'Done' definition per target | Compile-only / compile+load / compile+visual-parity per platform | ✓ |
| Python integration scope | Standalone library vs library+backtest_hybrid wiring | ✓ |
| Cross-platform parity & low-confidence handling | Required/advisory/skip parity; best-effort/stub/skip for low-conf indicators | ✓ |

**User's choice:** All four areas selected (notes: "all").

---

## Area 1: Build order across targets

### Q1.1 — Plan slicing approach

| Option | Description | Selected |
|--------|-------------|----------|
| Tier-then-platform per indicator (Recommended) | 3 plans mirroring Phase 11; each plan builds 1 tier × all 3 targets in parallel | ✓ |
| Platform-first sweep | All 14 in MQ4 → all 14 in MQ5 → all 14 in Python | |
| Tier + platform matrix (9 plans) | Each tier × platform a separate plan; max review granularity | |

**User's choice:** Tier-then-platform per indicator
**Notes:** Mirrors Phase 11 cadence; surfaces dep issues early; one indicator's 3 ports stay together for parity context.

### Q1.2 — Parallelism within a tier

| Option | Description | Selected |
|--------|-------------|----------|
| Parallel within tier (Recommended) | Each spec is an independent task per Phase 11 wave model | ✓ |
| Serial within tier | One spec × 3 targets at a time, in order | |

**User's choice:** Parallel within tier

### Q1.3 — Output paths

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror Phase 11 + V2 conventions (Recommended) | MQ4 → SM Indicators/MT4/_helix_built/, MQ5 → SM Indicators/MT5/, Python → V2/v3_intelligence/sm_indicators/ | ✓ |
| All under SM Indicators tree | Python at SM Indicators/python/ instead of V2/ | |
| Co-located with V2/indicators/ | All MQ + Python under V2/indicators/ | |

**User's choice:** Mirror Phase 11 + V2 conventions
**Notes:** Keeps originals untouched, MT5/ cleanly seeded, Python in canonical Helix location for downstream import without sys.path tweaks.

### Q1.4 — Tier review gate

| Option | Description | Selected |
|--------|-------------|----------|
| Compile + smoke per tier (Recommended) | MQ4/MQ5 compile + chart-load + Python pytest GREEN before tier approval | ✓ |
| Compile-only per tier | No runtime tests required | |
| Compile + chart-load + pytest per tier (full smoke) | Plus side-by-side chart load on MT4 + MT5 terminals | |

**User's choice:** Compile + smoke per tier
**Notes:** Catches build breakage before composite tier depends on broken helpers.

---

## Area 2: 'Done' definition per target

### Q2.1 — MQ4 done criterion

| Option | Description | Selected |
|--------|-------------|----------|
| Compile + load on chart (Recommended) | 0 errors/warnings + loads on chart in MT4 (Wine) without runtime error | ✓ |
| Compile-only | Just compile clean | |
| Compile + load + visual parity vs original .ex4 | Side-by-side compare against non-decompilable binaries | |

**User's choice:** Compile + load on chart

### Q2.2 — MQ5 done criterion

| Option | Description | Selected |
|--------|-------------|----------|
| Compile + load on chart (Recommended) | 0 errors + loads on IC Markets KE MT5 chart | ✓ |
| Compile-only | Compile clean only | |
| Compile + load + V2/indicators/ convention integration | Plus header block, parameter naming, terminal copy per Phase 8.4 patterns | |

**User's choice:** Compile + load on chart

### Q2.3 — Python done criterion

| Option | Description | Selected |
|--------|-------------|----------|
| Pytest GREEN with spec test cases (Recommended) | Each spec's Section 10 cases convert to pytest functions; ≥1 GREEN per indicator | ✓ |
| Imports + smoke (no spec-test conversion) | Module imports + DataFrame shape on fixture | |
| Pytest GREEN + parity vs MQ5 | Plus numeric output match within tolerance vs MQ5 | |

**User's choice:** Pytest GREEN with spec test cases
**Notes:** Mirrors V2/v3_intelligence/{adr,regime,pit,cache}.py test discipline.

### Q2.4 — Spec linkback

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — amend spec on completion (Recommended) | Append "Implementation status" footer to each spec with paths + commit SHAs | ✓ |
| No — track only in PLAN/STATE | Specs frozen at Phase 11 state | |

**User's choice:** Yes — amend spec on completion

---

## Area 3: Python integration scope

### Q3.1 — Integration depth

| Option | Description | Selected |
|--------|-------------|----------|
| Library now, backtest wiring later (Recommended) | Build sm_indicators/ package; do NOT touch backtest_hybrid.py in Phase 12 | ✓ |
| Library + wire signal-feeding indicators | Plus actively wire SM_TDI / SM_PivotPoints into backtest_hybrid as new sources | |
| Library only — never wire to backtest | Future phase decides whether SM signals enter backtest | |

**User's choice:** Library now, backtest wiring later
**Notes:** Smaller blast radius for Phase 12; wiring becomes its own follow-up phase.

### Q3.2 — Module surface shape

| Option | Description | Selected |
|--------|-------------|----------|
| Function-first, dataclass for params (Recommended) | compute_<name>(df, params) → DataFrame, mirrors compute_adr() | ✓ |
| Class-based Indicator interface | class SM_TDI(Indicator).compute(df) | |
| Both — functions + thin class wrapper | Hybrid | |

**User's choice:** Function-first, dataclass for params

### Q3.3 — Plot helpers

| Option | Description | Selected |
|--------|-------------|----------|
| Skip plot helpers (Recommended) | compute() + tests only | ✓ |
| Build minimal matplotlib plot helpers | One per indicator | |
| Build plotly interactive HTML helpers | More polish; adds plotly dep | |

**User's choice:** Skip plot helpers

### Q3.4 — Python alerts handling

| Option | Description | Selected |
|--------|-------------|----------|
| Log events only (Recommended) | DataFrame `alert_signal` column; no email/sound/push from Python | ✓ |
| Log events + Python logging warning | DataFrame column + log.warning() emit during compute | |
| Skip alert logic entirely | Python ports of alerter indicators ship without alert detection | |

**User's choice:** Log events only

---

## Area 4: Cross-platform parity & low-confidence handling

### Q4.1 — Parity for High-confidence deterministic indicators

| Option | Description | Selected |
|--------|-------------|----------|
| Advisory parity check (Recommended) | scripts/parity_check_<name>.py diffs MQ5 buffer CSV vs Python within tolerance; evidence not blocker | ✓ |
| Required parity gate | Each High-conf indicator MUST pass diff before tier review | |
| Skip parity entirely | Each target stands alone against spec | |

**User's choice:** Advisory parity check

### Q4.2 — Low-confidence indicator handling

| Option | Description | Selected |
|--------|-------------|----------|
| Best-effort impl with [INFER] flagged in code (Recommended) | Build best-guess; comment every guessed line; spec footer = Built ⚠ | ✓ |
| Stub only — raise NotImplementedError | Function signatures only; spec footer = Stubbed ⚠ | |
| Skip Low-confidence indicators | Don't build SM_BPCT etc.; spec footer = Skipped ❌ | |

**User's choice:** Best-effort impl with [INFER] flagged in code

### Q4.3 — MQ4 ↔ MQ5 source code style

| Option | Description | Selected |
|--------|-------------|----------|
| MQ5-idiomatic (Recommended) | Indicator handles, OnCalculate(rates_total, prev_calculated, time, ...), CopyBuffer; no #ifdef shims | ✓ |
| Mirror MQ4 with #ifdef shims | Single source per indicator with __MQL5__ branches | |

**User's choice:** MQ5-idiomatic

### Q4.4 — Out-of-scope confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, all deferred (Recommended) | Visual parity vs .ex4, backtest wiring, live EA, plot helpers, headless MQ5 export — all out of Phase 12 scope | ✓ |
| Some should be in scope | I'd add a note about what to pull in | |

**User's choice:** Yes, all deferred

---

## Claude's Discretion

Areas where the user accepted the recommended default without restriction (Claude has flexibility during planning/implementation):

- Exact subfolder structure under `_helix_built/` (flat vs `helpers/` + `indicators/`)
- Pytest fixture organization for spec test cases
- Whether parity-check scripts get their own unit tests
- MQ4/MQ5 alert configuration defaults (popup + sound on, email/push off — MMM-typical, tagged [INFER])
- Whether `_helix_built/` gets a brief README

## Deferred Ideas

Carried into CONTEXT.md `<deferred>` section:

- backtest_hybrid wiring of SM_TDI / SM_PivotPoints
- Visual parity vs original .ex4 binaries
- Headless MQ5 export tooling
- Python plot helpers (matplotlib/plotly)
- Cross-language parity test corpus
- Re-spec / re-implement non-`!SM_*` third-party indicators
- MMM glossary expansion for new terms
- Live MT4/MT5 EA integration of SM indicators

# CLAUDE CODE TASK MANIFEST
## MT5 Algorithmic Trading POC — Implementation Guide

**Read first:** `mt5-poc-whitepaper.md` (full strategy specifications)
**Read second:** `algorithmic-alpha-research.md` (source code references and architectural patterns)

---

## PROJECT STRUCTURE

```
MarketMind-MT5-POC/
├── docs/
│   ├── mt5-poc-whitepaper.md          # Strategy whitepaper (this session)
│   └── algorithmic-alpha-research.md  # Deep research report (20 source analysis)
├── indicators/
│   ├── AdaptiveATR.mq5
│   ├── VolatilityRegime.mq5
│   ├── SessionFilter.mq5
│   ├── DonchianADX.mq5
│   ├── MeanRevOscillator.mq5
│   ├── HurstExponent.mq5
│   └── RegimeClassifier.mq5
├── ea/
│   ├── include/
│   │   ├── CSignalManager.mqh
│   │   ├── CMeanRevSignal.mqh
│   │   ├── CTrendSignal.mqh
│   │   ├── CHybridSignal.mqh
│   │   ├── CRiskManager.mqh
│   │   ├── CPositionSizer.mqh
│   │   ├── CCorrelationMonitor.mqh
│   │   ├── CCircuitBreaker.mqh
│   │   ├── CPositionManager.mqh
│   │   ├── CEntryManager.mqh
│   │   ├── CExitManager.mqh
│   │   ├── CScalingManager.mqh
│   │   ├── CLogger.mqh
│   │   └── SymbolConfig.mqh
│   └── MultiPairEA.mq5
├── tests/
│   ├── validation_spreadsheets/       # Excel files for indicator validation
│   └── unit_tests/                    # MQL5 script-based tests
├── backtest/
│   ├── wfo_config.set                 # Walk-forward optimization settings
│   ├── results/                       # Backtest output CSVs
│   └── analysis/                      # Statistical test scripts (Python)
└── README.md
```

---

## TASK SEQUENCE (BUILD ORDER)

### TASK 1: Project Setup
- Initialize git repo
- Create directory structure above
- Copy whitepaper and research docs into docs/

### TASK 2: AdaptiveATR.mq5
**Spec:** Whitepaper Section 4.1
- Dynamic period 7-28 based on ATR percentile rank
- 100-bar reference window
- 3 buffers: ATR value, percentile rank (0-100), current period
- **Validation:** Compare output against manual ATR calculation on 100 bars of EURUSD H4 data

### TASK 3: VolatilityRegime.mq5
**Spec:** Whitepaper Section 4.7
- ATR(14) percentile rank over 252-bar lookback
- 3 states: 0 (skip), 1 (normal), 2 (reduce 50%)
- 1 buffer: state code
- **Validation:** Verify state transitions on known volatile periods (2022 rate hiking cycle)

### TASK 4: SessionFilter.mq5
**Spec:** Whitepaper Section 4.6
- Configurable session hours per market
- News event blackout array (Unix timestamps)
- 2 buffers: session active (1/0), overlap active (1/0)
- **Validation:** Confirm correct GMT/UTC handling across DST transitions

### TASK 5: DonchianADX.mq5
**Spec:** Whitepaper Section 4.5
- 20-period entry channel, 10-period exit channel
- Signal only on CLOSE beyond channel (not intrabar)
- ADX threshold gate (default 25)
- 5 buffers: upper, lower, signal, exit upper, exit lower
- **Validation:** Visual overlay on USDJPY H4 chart, compare with manual Donchian calculation

### TASK 6: MeanRevOscillator.mq5
**Spec:** Whitepaper Section 4.4
- Z-score = (Close - SMA(Period)) / StdDev(Period)
- Configurable period (48 for AUDNZD, 30 for EURGBP)
- Half-life computation via OLS regression
- 4 buffers: z-score, upper threshold, lower threshold, half-life
- **Validation:** Compare z-score against Python pandas calculation on same data

### TASK 7: HurstExponent.mq5
**Spec:** Whitepaper Section 4.2
- R/S analysis, 100-bar window, 5 subdivision levels
- Log-log regression for H
- 2 buffers: raw H, discretized signal (-1/0/1)
- **Validation:** Known synthetic data (random walk should give H≈0.50)

### TASK 8: RegimeClassifier.mq5
**Spec:** Whitepaper Section 4.3
- Reads AdaptiveATR and HurstExponent via iCustom()
- 5 regime states encoded as integers
- 1 buffer: regime code
- **Validation:** Walk through state transitions on EURUSD H4 across 2023-2024

### TASK 9: EA Class Architecture
**Spec:** Whitepaper Section 5
Build in this order:
1. SymbolConfig.mqh (pair configuration structures)
2. CLogger.mqh (CSV trade journal)
3. CRiskManager.mqh → CPositionSizer → CCorrelationMonitor → CCircuitBreaker
4. CSignalManager.mqh → CMeanRevSignal → CTrendSignal → CHybridSignal
5. CPositionManager.mqh → CEntryManager → CExitManager → CScalingManager
6. MultiPairEA.mq5 (orchestrator with OnInit/OnTimer)

### TASK 10: Backtesting Pipeline
- Download tick data via Tickstory (Dukascopy feed, 2021-2026)
- Configure MT5 Strategy Tester for "Every tick based on real ticks"
- Run individual pair backtests first
- Then portfolio-level combined backtest
- Export results to CSV for statistical analysis

### TASK 11: Statistical Validation (Python)
- Bootstrap analysis (10,000 iterations)
- Permutation tests (10,000 iterations)
- Deflated Sharpe Ratio computation
- CPCV with N=6, k=2 (15 train-test splits)
- Generate validation report

---

## KEY PARAMETERS REFERENCE

| Parameter | Value | Source |
|-----------|-------|--------|
| Account equity | $1,000 | User specified |
| Risk per trade | 1% ($10) | Whitepaper Layer 1 |
| Max daily loss | 3% ($30) | Whitepaper Layer 2 |
| Max weekly loss | 6% ($60) | Whitepaper Layer 2 |
| Max drawdown | 15% ($150) | Whitepaper Layer 2 |
| Max aggregate portfolio risk | 3% | Whitepaper Layer 3 |
| Kelly fraction | 0.25x | Whitepaper Section 2 |
| Kelly window | 50 trades | Whitepaper Section 5 |
| Correlation threshold | 0.75 | Whitepaper Section 5 |
| Max concurrent positions | 5 | Whitepaper Section 5 |
| Signal threshold | 70/100 | Whitepaper Section 5 |
| Timer interval | 1 second | Whitepaper Section 5 |
| Broker commission | $3.50/lot/side | IC Markets Raw Spread |
| Max leverage (self-imposed) | 1:100 | Whitepaper Layer 4 |

---

## MQL5 CODING STANDARDS

- Use `#property strict` equivalent (MQL5 is strict by default)
- All indicators must use `SetIndexBuffer()` with `INDICATOR_DATA` or `INDICATOR_CALCULATIONS`
- EA uses `CTrade` class from `<Trade/Trade.mqh>` for order management
- All magic numbers assigned dynamically per pair: `MAGIC_BASE + pair_index * 100`
- CSV logging with columns: datetime, pair, direction, lots, entry, SL, TP, signal_score, regime, comment
- Error handling: every `OrderSend()` must check `GetLastError()` and retry with backoff
- No DLL imports — pure MQL5 only

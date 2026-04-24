# MT5 Algorithmic Trading POC: Strategy Whitepaper
## $1,000 IC Markets Raw Spread Account | 5-Pair Portfolio

**Version:** 1.0 | **Date:** April 15, 2026 | **Status:** Pre-Implementation

---

## System Overview

EUR/GBP and GBP/JPY complete the optimal five-pair portfolio, pairing two mean-reversion instruments (AUD/NZD, EUR/GBP) with two trend-followers (USD/JPY, GBP/JPY) and one regime-adaptive hybrid (EUR/USD) on IC Markets Raw Spread. This architecture targets a Sharpe Ratio > 1.5 and maximum drawdown < 15% through ATR-based position sizing at 1% risk per trade, fractional Kelly (0.25x) position capping, and correlation-aware portfolio risk management capped at 3% aggregate exposure.

The system generates ~50 trades per month across all pairs (~1,800 over a 3-year backtest window). Every component is implementable in pure MQL5 with seven custom indicators feeding a class-based multi-pair Expert Advisor.

---

## 1. Pair Universe and Selection Rationale

### Final Portfolio

| # | Pair    | Role             | Est. H4 ATR | Strategy           | Hurst Est.  | Unique Exposure   |
|---|---------|------------------|-------------|--------------------|-------------|-------------------|
| 1 | EURUSD  | Hybrid           | ~35 pips    | Trend + MR         | 0.52–0.55   | EUR, USD          |
| 2 | USDJPY  | Trend following  | ~50 pips    | Donchian breakout  | 0.55–0.60   | JPY carry         |
| 3 | AUDNZD  | Mean reversion   | ~20 pips    | Z-score oscillator | 0.35–0.45   | AUD, NZD          |
| 4 | EURGBP  | Mean reversion   | ~22 pips    | Z-score oscillator | 0.35–0.45   | EUR-GBP spread    |
| 5 | GBPJPY  | Trend following  | ~100 pips   | Donchian breakout  | 0.55–0.65   | GBP-JPY cross     |

### EUR/GBP Selection (Score: 8.85/10)
- Hurst exponent ~0.38 confirms strong mean-reverting character
- IC Markets raw spread: 0.27 pips average
- Correlation: -0.90 with EUR/USD (natural hedge), near-zero with USD/JPY and AUD/NZD
- At 0.01 lots with pip value ~$0.127, $10 risk budget accommodates stops up to 74 pips
- Commission cost: 12.6% of typical trade profit

### GBP/JPY Selection (Score: 6.70/10)
- Hurst exponent ~0.60 indicates persistent trending
- 300-basis-point carry differential (BoE 3.75% vs BoJ 0.75%)
- ~200-pip daily ATR for large directional moves
- Correlation with EUR/USD only ~0.30
- Moderate USD/JPY overlap (~0.75) managed through independent signals and max aggregate risk rules

### GBP/USD Rejection
- +0.85-0.90 correlation with EUR/USD creates redundant USD-weakness exposure
- Despite 0.04-pip spread advantage

### Portfolio Characteristics
- 6 unique currencies (EUR, USD, JPY, GBP, AUD, NZD)
- Average absolute inter-pair correlation: ~0.33
- Volatility spectrum: 20 pips (AUD/NZD) to 100 pips (GBP/JPY) H4 ATR

---

## 2. Theoretical Foundation

### Source Literature
1. Ernest Chan - "Algorithmic Trading" and "Quantitative Trading"
2. Marcos Lopez de Prado - "Advances in Financial Machine Learning"
3. Perry Kaufman - "Trading Systems and Methods"
4. Jason Strimpel - "Python for Algorithmic Trading Cookbook"

### Mean Reversion Framework (Chan)
- ADF test confirms stationarity
- Hurst exponent confirms H < 0.5
- Half-life of Ornstein-Uhlenbeck process determines lookback period
- Bollinger Band entries using lookback = half-life
- Z-score thresholds: +/-2.0 entry, +/-0.5 exit
- Kalman filter for adaptive hedge ratios (no lookback parameter needed)

### Trend Following Framework (Kaufman)
- 20-period Donchian for entry, 10-period for exit
- 25-period EMA above 350-period EMA as trend filter
- 2x ATR stops
- Win rate 30-40% offset by 2:1+ reward-to-risk
- ADX > 25 as trending confirmation threshold

### Regime Detection (Lopez de Prado)
- ADX-based regime classification: trending (>25), ranging (<20), dead zone (20-25)
- Triple barrier method for labeling
- Meta-labeling: primary model for direction, secondary for sizing
- Deflated Sharpe Ratio for overfitting detection

### Position Sizing Consensus
- Fractional Kelly: 0.25x (quarter-Kelly)
- Formula: f* = (p * b - q) / b
- Practical rule: min(ATR-based 1% risk, quarter-Kelly)
- If Kelly goes negative, stop trading entirely

---

## 3. Strategy Specifications

### 3.1 EUR/USD Hybrid Strategy
- **Timeframe:** H1 primary, H4/D1 regime filter
- **Trending Mode** (H4 ADX > 25 and rising):
  - Wait for pullback to 20 EMA on H1
  - Enter on first candle closing in trend direction
  - RSI(14) bouncing from 40-50 zone (longs) or 50-60 zone (shorts)
  - D1 200 SMA confirms macro direction
  - Stop loss: 1.5x ATR(14)
  - Chandelier trailing exit activating at 1R profit
  - Partial close: 50% at 1.5R
- **Ranging Mode** (H4 ADX < 20 for 5+ bars):
  - Z-score entries at +/-1.8 with RSI confirmation and Bollinger Band touch
  - Stop loss: 2.5x ATR(14)
  - Exit at z-score = 0
- **Time exit:** 48 bars (trending), 24 bars (ranging)
- **Regime change triggers immediate position closure**
- **Expected frequency:** ~14 trades/month

### 3.2 USD/JPY Trend Following
- **Timeframe:** H4 primary, D1 filter
- **Entry:** Donchian breakout (20-period) on close
  - ADX(14) > 25 rising, +DI/-DI alignment
  - Price above/below 50 EMA and 100 SMA on H4
  - Preferred: pullback to 20 EMA within established trend, RSI(14) 40-60
- **Stop loss:** 2.0x ATR(14)
- **Exit:** 10-period Donchian opposite channel OR Chandelier at HH(22) - 3.0x ATR(14)
- **Scaling:** Close 33% at 2R, 33% at 3R, trail remaining 34%
- **Session filter:** Tokyo and London hours
- **Expected frequency:** ~6 trades/month

### 3.3 AUD/NZD Mean Reversion
- **Timeframe:** H1 primary, H4 regime
- **Half-life:** ~48 H1 bars (~2 trading days) = z-score lookback period
- **Entry:** Z-score > +/-2.0 AND RSI(14) confirms AND Bollinger Band(48, 2.0) touch
- **Range boundary filter:** 1.0800-1.2200 (reject signals near breakout zones)
- **H4 ADX must be < 25 (ranging confirmation)**
- **Stop loss:** 2.0x ATR(14) or z-score exceeding +/-3.0
- **Exit:** Z-score +/-0.5
- **Time exit:** 72 H1 bars (~1.5x half-life)
- **Session filter:** Asian hours (22:00-08:00 GMT) and early London
- **Expected frequency:** ~16 trades/month

### 3.4 EUR/GBP Mean Reversion
- **Timeframe:** H4 primary, D1 regime
- **Half-life:** ~30 H4 bars (~5 trading days)
- **Entry:** Z-score > +/-2.0, RSI confirmation, Bollinger Band touch, D1 ADX < 25
- **Range-break emergency exit:** Price closes outside 0.8250-0.8850 on D1
- **Stop loss:** 2.5x ATR(14)
- **Exit:** Z-score +/-0.3
- **Session:** London only (07:00-16:00 GMT)
- **Expected frequency:** ~8 trades/month

### 3.5 GBP/JPY Trend Following
- **Timeframe:** H4 primary, D1 filter
- **Entry:** Donchian breakout (20-period) with ADX > 25, MA alignment (50 EMA H4, 200 SMA D1)
- **Stop loss:** 2.5x ATR(14)
- **Exit:** Chandelier at HH(22) - 3.0x ATR(14)
- **Emergency exit:** Any H4 bar > 4x ATR against position
- **Scaling:** 25% at 2R, 25% at 3R, trail 50% with Chandelier
- **Session:** Tokyo and London hours
- **Expected frequency:** ~6 trades/month

---

## 4. Custom Indicator Specifications

### 4.1 AdaptiveATR.mq5
- **Purpose:** Dynamically adjusts ATR period (7-28) based on percentile rank
- **Logic:** ATR > 80th percentile → period = 7 (fast). ATR < 20th percentile → period = 28 (stable)
- **Lookback:** 100-bar reference window
- **Buffers (3):**
  - Buffer 0: ATR value
  - Buffer 1: Percentile rank (0-100)
  - Buffer 2: Current period in use
- **Dependencies:** None (standalone)
- **Feeds into:** VolatilityRegime, CPositionSizer

### 4.2 HurstExponent.mq5
- **Purpose:** Compute Hurst exponent via R/S analysis
- **Logic:** 100-bar rolling window, 5 subdivision levels, log-log regression
- **Buffers (2):**
  - Buffer 0: Raw H value
  - Buffer 1: Discretized signal (1=trending H>0.55, 0=random 0.45-0.55, -1=mean-reverting H<0.45)
- **Dependencies:** None (standalone)
- **Feeds into:** RegimeClassifier

### 4.3 RegimeClassifier.mq5
- **Purpose:** Combine ADX, ATR percentile, and Hurst into single regime code
- **States (5):**
  - TRENDING_STRONG (ADX > 35 AND H > 0.55) = 2
  - TRENDING_MILD (ADX 25-35) = 1
  - RANGING_TIGHT (ADX < 20 AND ATR pct < 30) = -1
  - RANGING_WIDE (ADX < 20 AND ATR pct 30-70) = -2
  - VOLATILE (ATR pct > 85 regardless of ADX) = 3
- **Buffers (1):** Regime code
- **Dependencies:** AdaptiveATR, HurstExponent (via iCustom)
- **Feeds into:** EA signal routing

### 4.4 MeanRevOscillator.mq5
- **Purpose:** Z-score calculation with configurable period
- **Parameters:** Period (48 for AUDNZD, 30 for EURGBP)
- **Formula:** Z = (Close - SMA(Period)) / StdDev(Period)
- **Half-life:** -log(2) / lambda from OLS regression of dP on P(t-1)
- **Buffers (4):**
  - Buffer 0: Z-score value
  - Buffer 1: Upper threshold line
  - Buffer 2: Lower threshold line
  - Buffer 3: Computed half-life
- **Alert:** If half-life > 100 bars, strategy should pause
- **Dependencies:** None (standalone)
- **Feeds into:** CMeanRevSignal

### 4.5 DonchianADX.mq5
- **Purpose:** Donchian channel with ADX-gated breakout signals
- **Parameters:** Entry period (20), Exit period (10), ADX threshold (25)
- **Signal:** Fires ONLY on close beyond channel (not intrabar touch)
- **Buffers (5):**
  - Buffer 0: Upper channel (20-period high)
  - Buffer 1: Lower channel (20-period low)
  - Buffer 2: Signal (1=long, -1=short, 0=none)
  - Buffer 3: Exit upper (10-period high)
  - Buffer 4: Exit lower (10-period low)
- **Dependencies:** None (standalone)
- **Feeds into:** CTrendSignal

### 4.6 SessionFilter.mq5
- **Purpose:** Mark tradeable windows with news event blackout
- **Parameters:** Session hours (configurable per session), news timestamps array, blackout minutes
- **Sessions:** London (07:00-16:00), New York (13:00-22:00), Tokyo (00:00-09:00), Sydney (22:00-07:00)
- **Buffers (2):**
  - Buffer 0: Session active (1/0)
  - Buffer 1: Overlap active (1/0)
- **Dependencies:** None (standalone)
- **Feeds into:** EA entry gating

### 4.7 VolatilityRegime.mq5
- **Purpose:** ATR percentile rank over long lookback
- **Parameters:** ATR period (14), Lookback (252 H4 bars ≈ 1 year)
- **Output states:**
  - 0 = Below 20th percentile (skip trading)
  - 1 = Normal (full position sizing)
  - 2 = Above 80th percentile (reduce size by 50%)
- **Buffers (1):** State code
- **Dependencies:** None (standalone)
- **Feeds into:** CPositionSizer

---

## 5. EA Architecture

### Class Hierarchy

```
CMultiPairEA (main controller)
├── CSignalManager
│   ├── CMeanRevSignal      → AUD/NZD, EUR/GBP
│   ├── CTrendSignal        → USD/JPY, GBP/JPY
│   └── CHybridSignal       → EUR/USD
├── CRiskManager
│   ├── CPositionSizer      → ATR + Kelly sizing
│   ├── CCorrelationMonitor → 90-day rolling correlation matrix
│   └── CCircuitBreaker     → Daily/weekly/drawdown limits
├── CPositionManager
│   ├── CEntryManager       → Order execution
│   ├── CExitManager        → Trailing stops, targets, time exits
│   └── CScalingManager     → Partial close logic
└── CLogger                 → CSV trade journal
```

### OnInit() Sequence
1. Load all 7 indicators for all 5 pairs using iCustom()
2. Initialize 5x5 correlation matrix from last 90 days of daily returns
3. Set high-water mark to account equity
4. Load persisted state (open positions, trade journal) from file
5. Initialize SymbolConfig structures per pair

### OnTimer() Execution Loop (1-second interval)
1. Check circuit breaker: daily loss > 3%? weekly > 6%? drawdown > 15%? → skip
2. For each pair: call IsNewBar() on primary timeframe
3. On new bar: read all indicator buffers via CopyBuffer()
4. Generate composite signal score (0-100)
5. If score > 70 AND no existing position: calculate size, submit entry
6. For existing positions: check exit conditions

### Signal Scoring

**Mean Reversion Pairs:**
- Z-score magnitude: 40 points (scaled 0 at z=1.5 to 40 at z=2.5+)
- RSI confirmation: 30 points
- Bollinger Band touch: 15 points
- Half-life validity: 15 points

**Trend Following Pairs:**
- Donchian breakout: 40 points
- ADX strength: 20 points (scaled 0 at ADX=20 to 20 at ADX=40+)
- DI alignment: 20 points
- MA alignment: 20 points

**Threshold: 70 points required for entry**

### Position Sizing Formula
```
lots = (Equity * 0.01) / (SL_pips * pip_value_per_lot)
```
Round down to nearest 0.01, then apply three caps:
1. Quarter-Kelly maximum from rolling 50-trade window
2. Correlation-adjusted portfolio risk limit (3%)
3. Drawdown-graduated multiplier:
   - 0-5% DD: full risk (1.0x)
   - 5-10% DD: 0.75x
   - 10-15% DD: 0.5x
   - >15% DD: 0x (halt)

### Maximum Concurrent Positions
- 5 total across portfolio
- No more than 2 highly correlated pairs (rho > 0.75) simultaneously

---

## 6. Risk Framework (5 Layers)

### Layer 1: Per-Trade Risk
- Never exceeds 1% ($10) of current equity
- Formula: Position_Size = (Equity * 0.01) / (ATR * SL_Multiplier * Pip_Value)
- Known constraint: GBP/JPY at 0.01 lots with 2.5x ATR may slightly exceed 1%

### Layer 2: Circuit Breakers
- Daily loss limit: 3% ($30)
- Weekly loss limit: 6% ($60)
- Maximum drawdown: 15% ($150)
- After 15% DD: halt 48 hours minimum, resume at 0.5% risk for first 10 trades

### Layer 3: Correlation-Aware Portfolio Risk
- Aggregate exposure cap: 3%
- 5x5 correlation matrix updated daily (90-day rolling)
- Pairs with rho > 0.75: each position risk reduced by 1/(1+rho)
- Maximum single-currency exposure: 2% of equity

### Layer 4: Black Swan Mitigation
- Close all positions Friday 23:00 server time (unless >2x ATR profit with BE stop)
- Server-side hard stop losses on every position
- Emergency exit: any H4 bar > 4x ATR against position
- Self-imposed max leverage: 1:100 (despite broker offering 1:1000)

### Layer 5: IC Markets Cost Management
- Commission: $3.50/lot/side = $0.07 round-trip per micro lot
- Break-even pips: EURUSD 0.8, USDJPY 1.3, AUDNZD 2.2, EURGBP 1.0, GBPJPY 2.3
- Maximum 5-day hold time to limit swap erosion
- Average execution: 35ms, 73.87% zero slippage

---

## 7. Backtesting & Validation Protocol

### Data Requirements
- 5 years tick data (Jan 2021 – present) via Tickstory/Dukascopy
- MT5 Strategy Tester: "Every tick based on real ticks" mode
- Conservative spread: 1.5-2x published averages
- Slippage: 0.3-0.5 pips majors, 0.5-1.0 pips minors

### Walk-Forward Optimization
- 6-month optimization windows, 2-month forward steps
- ~25 WFO iterations across 5-year dataset
- Walk-Forward Efficiency (WFE) must exceed 0.50
- Parameter stability: optimal params must cluster across windows

### Data Splits
- 60% in-sample: Jan 2021 – Dec 2023
- 20% validation: Jan 2024 – Dec 2024
- 20% out-of-sample: Jan 2025 – present
- OOS test is single-shot, no modification

### Statistical Significance Tests
1. **Bootstrap** (10,000 iterations): Sharpe CI lower bound > 1.0, 95th pct MDD < 20%, P(ruin) < 1%
2. **Permutation** (10,000 iterations): p-value < 0.05 (ideally < 0.01)
3. **Deflated Sharpe Ratio:** DSR > 0.95
4. **CPCV:** PBO < 0.40

### 4-Week Demo Validation
- Week 1: System integrity (signal match > 95%, zero critical errors)
- Weeks 2-3: Metric tracking vs backtest distributions
- Week 4: Statistical comparison (Sharpe within bootstrap CI)
- Decision matrix: GO (all pass) → ITERATE (below CI but positive) → ABANDON (Sharpe negative)

---

## 8. Identified Risks and Mitigations

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | Regime breakdown (MR pairs break range) | Critical | Range boundary filters, ADX regime gate, emergency bounds |
| 2 | BoJ intervention (USD/JPY, GBP/JPY) | High | Hard SL, 4x ATR emergency exit, verbal warning monitoring |
| 3 | Minimum lot size floor ($1K constraint) | Medium | Accept 1.65% on GBP/JPY, correlation limits |
| 4 | Weekend gap risk (GBP pairs) | Medium | Friday 23:00 close rule |
| 5 | Overfitting | Critical | ≤5 params per strategy, DSR > 0.95, PBO < 0.40 |
| 6 | Swap cost erosion | Low | 5-day max hold, intraday exit preference |
| 7 | Geopolitical volatility (current) | Medium | Volatility regime filter, circuit breakers |
| 8 | Broker disconnection | Medium | Server-side hard SLs on all positions |
| 9 | Correlation spike in crisis | High | Real-time correlation check before entry |
| 10 | Commission erosion on small trades | Medium | H1/H4 timeframes only (no scalping) |
| 11 | Flash crash (GBP/JPY) | High | 4x ATR emergency exit, 1:100 max leverage |
| 12 | MT5 Strategy Tester bias | Medium | Tick data + variable spread + slippage simulation |
| 13 | Parameter instability across WFO windows | Medium | Cluster analysis, ±10% robustness test |

---

## 9. Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| A: Validation & Setup | Days 1-3 | IC Markets demo, tick data download, sparring session |
| B: Indicator Development | Days 4-10 | 7 custom .mq5 indicators with validation |
| C: EA Development | Days 11-20 | Class-based multi-pair EA |
| D: Backtesting | Days 21-35 | WFO results, statistical tests |
| E: Demo Trading | Days 36-63 | 4-week live demo validation |
| F: Go/No-Go Decision | Day 64 | Live deployment at 25% size or iterate |

### Indicator Build Order
1. AdaptiveATR.mq5 (foundation)
2. VolatilityRegime.mq5 (depends on AdaptiveATR)
3. SessionFilter.mq5 (standalone)
4. DonchianADX.mq5 (trend signal)
5. MeanRevOscillator.mq5 (MR signal)
6. HurstExponent.mq5 (regime)
7. RegimeClassifier.mq5 (aggregator)

### EA Build Order
1. CRiskManager (safety first)
2. CPositionSizer
3. CCorrelationMonitor
4. CCircuitBreaker
5. CSignalManager
6. CPositionManager
7. CLogger
8. CMultiPairEA (orchestrator)

---

## 10. IC Markets Execution Economics

| Pair | Avg Raw Spread | Commission RT | Break-Even | Pip Value (0.01 lot) | Max SL ($10 risk) |
|------|---------------|---------------|------------|---------------------|-------------------|
| EURUSD | 0.02 pips | $0.07 | 0.8 pips | $0.10 | 100 pips |
| USDJPY | 0.13 pips | $0.07 | 1.3 pips | $0.065 | 153 pips |
| AUDNZD | 0.72 pips | $0.07 | 2.2 pips | $0.058 | 172 pips |
| EURGBP | 0.27 pips | $0.07 | 1.0 pips | $0.127 | 79 pips |
| GBPJPY | 0.82 pips | $0.07 | 2.3 pips | $0.065 | 153 pips |

# MarketMind V2 - Hybrid Multi-Timeframe Trading Strategy

**Version:** 2.0 (Hybrid Multi-Timeframe)  
**Status:** Ready for EA Implementation  
**Last Updated:** 2026-04-20

---

## 📁 Project Structure

```
BA PRJ - Helix/V2/
├── V2_STRATEGY_DOCUMENTATION.md          [MAIN: 15-section strategy bible]
├── HYBRID_STRATEGY_DESIGN.md             [Design spec with decision trees]
├── ADJUSTED_PARAMETERS_V2.md             [Parameter tuning guide]
│
├── Backtesting/
│   ├── backtest_hybrid.py                [Primary: hybrid multi-timeframe backtest]
│   ├── backtest_all_timeframes.py        [Comparison: daily vs H1 analysis]
│   ├── backtest_strategy.py              [Legacy: single-timeframe version]
│   └── results/                          [Generated backtest outputs]
│
├── data/
│   ├── EURUSD_DAILY_2015-2026.csv        [11 years daily data]
│   ├── EURUSD_H1_730d.csv                [2 years hourly data]
│   └── [... 4 more currency pairs ...]
│
├── scripts/
│   ├── get_forex_daily.py                [Download daily data via yfinance]
│   └── download_intraday_data.py         [Download H1 data via yfinance]
│
├── ea/
│   ├── MultiPairEA.mq5                   [Main expert advisor implementation]
│   ├── CZScoreIndicator.mq5              [Z-score calculation module]
│   └── [... additional MQL5 modules ...]
│
├── indicators/
│   ├── AdaptiveATR.mq5                   [ATR with volatility adjustment]
│   ├── ZScoreMeanReversion.mq5           [Z-score signal generation]
│   └── SessionFilter.mq5                 [Session-aware entry filter]
│
└── docs/
    ├── IMPLEMENTATION_CHECKLIST.md       [EA development progress]
    ├── TESTING_PLAN.md                   [Paper trading validation plan]
    └── LIVE_TRADING_GUIDE.md             [Go-live procedures]
```

---

## 🎯 Quick Start

### 1. **Understand the Strategy** (30 min)
Start with **V2_STRATEGY_DOCUMENTATION.md** (Sections 1-4):
- Executive summary of hybrid approach
- Entry rules by position type (Daily Swings, Session Scalps, Momentum)
- Exit rules and position sizing

### 2. **Review Design & Methodology** (30 min)
Read **HYBRID_STRATEGY_DESIGN.md** for:
- Detailed decision tree logic
- Real-world scenario examples
- Session timing and market regimes

### 3. **Check Backtest Results** (15 min)
Review **ADJUSTED_PARAMETERS_V2.md**:
- Final optimized parameters
- Backtest metrics (488 trades, 35.9% win, +23.35% P&L, Sharpe 1.22)
- Performance by pair and position type

### 4. **Run Current Backtest** (2 min)
```bash
cd /home/user/Desktop/Bandd\ Analytics/BA\ PRJ\ -\ Helix/V2
python3 backtest_hybrid.py
```

---

## 📊 Strategy at a Glance

### Position Types & Sizing

| Type | Trigger | Size | Hold | P&L Target | Risk Stop |
|------|---------|------|------|-----------|-----------|
| **DAILY SWING** | Daily Z > \|2.0\| | 1.0x | 5 days | 4x ATR | 1.5x ATR |
| **SCALP** | H1 Z > \|1.2\| + liquid hour | 0.5x | 4 hours | 2x ATR | 0.75x ATR |
| **MOMENTUM** | H1 Z > \|1.0\| + Daily Z > \|1.0\| aligned | 0.3x | 2 hours | 1x ATR | 0.5x ATR |

### Session Windows (UTC)

- **London:** 07:00-18:00 (expanded from 08:00-17:00)
- **New York:** 12:00-23:00 (expanded from 13:00-22:00)
- **Optimal:** 13:00-17:00 (NY-London overlap)

### Decision Priority

1. **Daily Swing** (if Z > 2.0) → Take 1.0x
2. **Session Scalp** (if H1 Z > 1.2 during liquid hour) → Take 0.5x
3. **Momentum** (if both aligned) → Take 0.3x only

---

## 📈 Backtest Performance (Updated 2026-04-20)

### Summary Metrics
```
Total Trades:          488 (✓ good diversification)
Win Rate:              35.9% (✓ acceptable for mean reversion)
Avg P&L/Trade:         0.048% (✓ consistent, small avg)
Total Portfolio P&L:   +23.35% (✓ strong returns)
Sharpe Ratio:          1.22 (✓ excellent risk-adjusted)
Avg Bars Held:         33 hours (✓ swing-focused)
```

### By Position Type
- **DAILY_SWING_LONG:** 207 trades, 39.6% win, Sharpe **1.72** (best)
- **DAILY_SWING_SHORT:** 276 trades, 33.3% win, Sharpe 0.84
- **SCALP_LONG/SHORT:** 5 trades combined (rare, as expected)
- **MOMENTUM:** Supplementary, included in swings

### Best Performing Pairs
1. **GBPJPY:** +11.37% (107 trades, 37.4% win)
2. **USDJPY:** +11.08% (90 trades, 42.2% win)
3. **EURUSD:** +2.15% (123 trades, 35.8% win)
4. **EURGBP:** +1.44% (87 trades, 34.5% win)
5. **AUDNZD:** -2.69% (81 trades, 28.4% win) [underperformer]

---

## 🔧 Key Parameters

### Z-Score Thresholds
- Daily swing: **2.0** (high conviction, 95th percentile)
- Session scalp: **1.2** (medium conviction, relaxed from 2.0)
- Momentum alignment: **1.0** (low conviction, for supplement)

### ATR Multipliers
```
Daily Swing:    Target 4x ATR,  Stop 1.5x ATR
Session Scalp:  Target 2x ATR,  Stop 0.75x ATR
Momentum:       Target 1x ATR,  Stop 0.5x ATR
```

### Risk Management
- Max concurrent positions: **2** (same currency pair: max 1)
- Daily swing account risk: **2%**
- Session scalp account risk: **1%**
- Momentum account risk: **0.5%**

---

## 🚀 Implementation Status

### ✅ Complete
- [x] Strategy design & methodology documented
- [x] 11 years daily data downloaded (2015-2026)
- [x] 2 years hourly data downloaded (730-day limit)
- [x] Hybrid backtesting engine built
- [x] Performance metrics calculated
- [x] Parameters optimized and documented
- [x] Decision tree logic validated

### 🔄 In Progress
- [ ] MQL5 Expert Advisor development (MultiPairEA.mq5)
- [ ] Indicator implementation (AdaptiveATR, ZScore, SessionFilter)
- [ ] Risk management module (position sizing, stop calculation)

### ⏳ Pending
- [ ] Paper trading on IC Markets demo (1-2 weeks)
- [ ] Signal validation vs. backtest
- [ ] Position sizing adjustment for live account
- [ ] Live deployment (starting with 1 pair at 50% risk)

---

## 📚 Documentation Map

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **V2_STRATEGY_DOCUMENTATION.md** | Complete strategy specification | 20 min |
| **HYBRID_STRATEGY_DESIGN.md** | Design decision tree & examples | 15 min |
| **ADJUSTED_PARAMETERS_V2.md** | Parameter tuning & live guide | 10 min |
| **V2_README.md** | This file - project overview | 10 min |

---

## 🔍 How to Use This Project

### For Understanding Strategy
```
1. Read: V2_STRATEGY_DOCUMENTATION.md (Sections 1-7)
2. Review: HYBRID_STRATEGY_DESIGN.md (examples)
3. Check: ADJUSTED_PARAMETERS_V2.md (live parameters)
```

### For Backtesting
```
1. Ensure data files exist in data/
2. Run: python3 backtest_hybrid.py
3. Review results in terminal output
4. Compare vs. ADJUSTED_PARAMETERS_V2.md metrics
```

### For EA Implementation
```
1. Read: V2_STRATEGY_DOCUMENTATION.md (Sections 8, 9, 12)
2. Implement: indicators/ modules (AdaptiveATR, ZScore, SessionFilter)
3. Build: ea/MultiPairEA.mq5 using decision tree from docs
4. Test: Paper trade before live deployment
```

### For Live Trading
```
1. Read: ADJUSTED_PARAMETERS_V2.md (Parameter Tuning Guide)
2. Note: USDJPY & GBPJPY are best performers
3. Start: 1 pair, daily swings only, 50% position sizing
4. Monitor: Entry/exit signals for 1-2 weeks
5. Scale: Add pairs and scalps based on confidence
```

---

## ⚙️ Data & Environment

### Data Files
- **Source:** yfinance (Yahoo Finance)
- **Daily:** 2015-2026 (11 years, ~2,800 bars per pair)
- **Hourly:** Last 730 days (~17,000 bars per pair)
- **Pairs:** EURUSD, USDJPY, AUDNZD, EURGBP, GBPJPY

### Python Environment
```bash
# Required packages
pip install pandas numpy scipy

# To download new data:
pip install yfinance
python3 scripts/get_forex_daily.py
python3 scripts/download_intraday_data.py
```

### MQL5 Environment
- **Platform:** MetaTrader 5
- **Broker:** IC Markets (demo account established)
- **Symbols:** EURUSD, USDJPY, AUDNZD, EURGBP, GBPJPY
- **Account:** Demo (for paper trading validation)

---

## 🎓 Key Learnings

### Why Hybrid Approach?
- **Pure Daily:** Good P&L (+67%) but stop hunts on small accounts
- **Pure H1:** Lots of trades (+17%) but tiny winners, lots of noise
- **Hybrid:** Best of both—reliable swings + quick scalps when rare

### Why Z-Score?
- Measures statistical deviation from equilibrium
- Self-normalizing across volatility regimes
- |Z| > 2.0 = 95th percentile (statistically significant)

### Why Adaptive ATR?
- Avoids over-sizing stops in low-vol periods
- Avoids under-sizing targets in high-vol periods
- Scales dynamically: ATR_adjusted = ATR_base × (current_vol / 20d_vol_MA)

### Why Multi-Timeframe?
- Daily = trend direction + conviction
- H1 = precise entry timing + session awareness
- Together = high-conviction entries with tight risk management

---

## 📞 Quick Reference

### Troubleshooting

**Q: Backtest shows 0 trades**
→ Check: data/ directory has CSV files, file paths match symbol names

**Q: Backtest shows different results than docs**
→ Check: Parameters in backtest_hybrid.py match ADJUSTED_PARAMETERS_V2.md

**Q: Too many losing trades in paper trading**
→ Adjust: Increase Z-score thresholds (2.0 → 2.2, 1.2 → 1.5)

**Q: Too few trades in paper trading**
→ Adjust: Decrease Z-score thresholds (2.0 → 1.8, 1.2 → 1.0)

### File Locations
```
Strategy Docs: BA PRJ - Helix/V2/V2_STRATEGY_DOCUMENTATION.md
Backtest Code: BA PRJ - Helix/V2/backtest_hybrid.py
Data Files:    BA PRJ - Helix/V2/data/
EA Code:       BA PRJ - Helix/V2/ea/MultiPairEA.mq5
```

---

**Status:** ✅ Ready for EA Implementation  
**Next Step:** Begin MQL5 expert advisor development  
**Target:** Paper trading by 2026-05-04

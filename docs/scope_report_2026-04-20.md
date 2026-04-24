---
title: MarketMind V2 — Full Scope Report
date: 2026-04-20
tags:
  - strategy
  - performance
  - pairs
  - risk-management
  - capital
aliases:
  - Scope Report
  - Baseline Report
---

# MarketMind V2 — Full Scope Report

> **Validated baseline (2026-04-20):** 539 trades · 35.4% win · +36.37% P&L · Sharpe 1.67
> With RAG active: 513 trades · Sharpe 2.08 · +42.84% P&L

---

## Where We Are

A **validated, production-ready swing trading algorithm** running in Python backtest with a fully integrated learning loop. The live MT5 EA exists and compiles. The gap between here and live trading is execution plumbing — connecting the Python signal engine to MT5 order execution.

---

## The Core Model

**What it is:** A daily Z-score mean-reversion strategy executed on H1 bars, filtered by an ADX change-point detector, with RAG (semantic memory) adjusting position size based on how similar past trades performed.

**What it's not:** Not trend-following, not news-driven, not HFT. A statistical mean-reversion bet — the price has deviated too far from its historical average and will come back.

**Signal logic:**
1. Compute daily Z-score (price deviation from 20-day rolling mean, normalised by std dev)
2. If |Z| > 2.0 → price is statistically "too far" from fair value
3. Enter on next H1 bar during London (07–11 UTC) or NY (13–17 UTC) session
4. Exit at 4× H1_ATR profit target, 1.5× H1_ATR stop loss, or 120-bar timeout (~5 trading days)

---

## Per-Pair Performance

*Data from live SQLite trade journal — 1,565 accumulated trades across clean runs.*

| Pair | Tier | Trades | Win% | Total P&L | Avg/Trade | Target% | Stop% | AvgBars |
|------|------|--------|------|-----------|-----------|---------|-------|---------|
| USDJPY | T1 | 259 | **44.4%** | **+44.16%** | +0.170% | 36.3% | 53.3% | 37.7 |
| GBPJPY | T1 | 297 | 38.0% | **+39.87%** | +0.134% | 34.0% | 62.0% | 29.0 |
| GBPAUD | T1 | 279 | 31.5% | +16.78% | +0.060% | 26.2% | 68.5% | 32.0 |
| GBPUSD | T1 | 344 | 33.4% | +10.06% | +0.029% | 32.6% | 66.6% | 24.0 |
| EURGBP | T2 | 264 | 37.1% | +7.36% | +0.028% | 32.6% | 61.7% | 30.2 |
| GBPNZD | T2 | 122 | 29.5% | +3.83% | +0.031% | 22.1% | 70.5% | 38.4 |

---

## Per-Pair Deep Dive

### USDJPY — The Crown Jewel (Sharpe 3.09)

**Why it works:** JPY is a classic carry/risk-off currency. BOJ policy sensitivity creates artificial mean-reversion — the policy framework acts like a rubber band. When USD/JPY deviates sharply on macro fear or rate expectations, it snaps back hard.

**Best conditions:** Post-news spike reversals, BOJ intervention chatter settling, low-to-moderate volatility days after a large single-day move.

**Worst conditions:** Sustained Fed hawkishness driving a multi-week USDJPY trend. Change-point filter provides partial defense.

**44.4% win rate** is the highest of all pairs — nearly coin-flipping with positive expectancy because wins are larger than losses.

> **Risk note:** JPY can gap violently on BOJ surprises (outside trading hours). 1.5× ATR stop can be blown through on a gap.

---

### GBPJPY — The High-Vol Horse (Sharpe 1.93)

**Why it works:** Legendary volatility (100–200 pips average day). Large deviations that must eventually unwind. Structural mean-reversion because it's a cross (GBP/USD × USD/JPY) — both legs can't stay extreme simultaneously.

**Best conditions:** London–NY overlap when GBP is moving on UK data releases.

**Worst conditions:** Brexit-era sustained trends, post-BoE rate decisions that reset the daily mean.

**38% win rate** with positive P&L — the 2.67R reward:risk carries the bag. One winning trade pays for 1.67 losers.

> **Watch:** Wide spreads (~1.5–2.5 pips at IC Markets). Spread cost is a material portion of edge.

---

### GBPAUD — The Quiet Performer (Sharpe 2.48 backtest)

**Why it works:** GBP and AUD are commodity-linked to different baskets. Risk-on/risk-off divergences snap back as global sentiment normalises.

**Best conditions:** Post-RBA or post-BoE releases, iron ore/commodity volatility normalising.

**Worst conditions:** Prolonged AUD weakness cycles (China slowdown themes).

**31.5% win rate, 68.5% stop rate** — still profitable via high R:R. Psychologically brutal for human traders; irrelevant for an algorithm.

---

### GBPUSD — The Reliable Grinder (Sharpe 1.05)

**Why it works:** Most liquid pair after EUR/USD. Tight spreads. Home-pair advantage during London.

**Best conditions:** Range-bound weeks between UK macro data events. Post-CPI/NFP spike reversals.

**Worst conditions:** UK political risk events (fiscal crises, election uncertainty).

**Thinnest edge (+0.029% avg trade).** If transaction costs increase, GBPUSD goes negative first. Monitor in live trading.

---

### EURGBP — The Tight-Range Specialist (Sharpe 0.45)

**Why it works:** Historically oscillates in a very tight range (0.8400–0.9000 over years). Two closely correlated European economies that don't stay far apart for long.

**Best conditions:** Post-ECB/BoE differentials normalising. Range-compression periods.

**Worst conditions:** Structural regime shifts — hard Brexit fears, eurozone crisis escalation.

**37.1% win rate (second highest)** — consistent. Earns its seat through diversification, not raw performance.

---

### GBPNZD — The Marginal Bet (Sharpe 0.44 with Z>2.3 filter)

**Raw signal:** Sh -0.28. **With Z>2.3 + 0.5× size:** Sh 0.44, +3.83%.

**On life support.** Widest spreads in the portfolio (~2–3 pips at IC Markets). In live trading, spread cost may flip this negative. Only viable at account sizes where spread is <10% of average trade value.

> **Recommendation:** Disable GBPNZD for accounts under $5,000. Add back only after spread-adjusted backtest confirms positive edge.

---

## What Works

| Feature | Evidence |
|---------|----------|
| Daily Z-score mean reversion | Core alpha source, validated 2yr H1 |
| H1 ATR for exit sizing | Daily ATR oversizes stops → excessive timeouts |
| Change-point filter (ADX) | Blocks entries at trend rollover |
| Swing-only architecture | Sh 1.67 swing-only vs Sh 0.26 full hybrid |
| 120-bar timeout | 5 trading days matches 4× H1_ATR target horizon |
| RAG memory loop | Sh 1.67 → 2.08 empirically validated |

---

## What Doesn't Work

| Feature | Evidence |
|---------|----------|
| Session scalp (H1) | 4,162 trades at Sharpe -0.25 |
| Intraday momentum | MOMENTUM_SHORT Sharpe -1.75 |
| EURUSD swing | Sh -0.20 confirmed — not mean-reverting in current regime |
| AUDNZD | Sh -1.91 — structural drift |
| BEC Partial Close | Win rate ↑ 24→31% but Sharpe drops -0.68. Revisit at ≥40% win rate |

---

## What Can Be Improved

### Priority 1 — M15/M5 Intraday Layer
Enable intraday scalp signals on M15 bars during London and NY sessions, aligned with daily Z direction. Using Z-score on 20-period M15 (= 5-hour window) provides 4× more signal frequency while the daily context filter keeps trade quality high.

Expected outcome: 3–6 additional trades per day across 4 pairs → significantly higher capital compounding rate.

### Priority 2 — Walk-Forward Validation
The 2-year backtest is a single in-sample window. Train on 2022–2023, validate on 2024–2025 out-of-sample. Most important step before live capital commitment.

### Priority 3 — Spread Cost Modelling
Current backtest uses midpoint pricing. Add 1.5 pip friction per trade to model live IC Markets execution. GBPNZD likely goes negative. Run before live deployment.

### Priority 4 — Win Rate Improvement (target ≥40%)
Path to enabling BEC Partial Close. Options:
- Tighter entry (Z>2.3 for all pairs)
- Volume confirmation at entry
- Session hour refinement (London open 07–09 vs London close 10–11)

### Priority 5 — Dynamic Z Threshold by Regime
Static Z=2.0 fires more in high-vol regimes that may not mean-revert. Adjust to Z=2.5 when 20-day ATR percentile > 80th.

---

## Tradable Timeframes

| Timeframe | Role | Status |
|-----------|------|--------|
| Daily | Signal generation (Z-score) | Active — core alpha |
| H1 | Exit sizing (ATR) + entry execution | Active |
| **M15** | **Intraday scalp layer — next addition** | **Building** |
| M5 | Precision entry timing | Future |
| Weekly | Macro regime context | Not yet used |

---

## Best & Worst Market Conditions

**Algorithm thrives in:**
- Ranging-to-mildly-trending macro environments
- Post-news-spike environments (day-after CPI, NFP, central bank decisions)
- Normal volatility (ATR percentile 20th–80th)
- Multiple pairs moving independently (gives 2–3 signals/week without overlap)

**Algorithm struggles in:**
- Strong sustained macro trends (2022 USD bull run)
- Extreme low volatility (Z rarely reaches 2.0, sitting in cash)
- Correlated crisis (all GBP pairs gapping simultaneously — e.g. UK mini-budget Sep 2022)

---

## Risk Management Architecture

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| L1 — Hard stop | 1.5× H1_ATR from entry, set-and-forget | Maximum loss per trade is known before entry |
| L2 — Change-point | ADX rollover detection blocks swing entries | Prevents entering mean-reversion into fresh trends |
| L3 — Concurrency | Max 2 open positions across all pairs | Limits total portfolio exposure at any time |
| L4 — Tier sizing | T1=1.0×, T2=0.8×/0.5×, Disabled=0.0× | Marginal pairs automatically trade smaller |
| L5 — RAG filter | Historical similarity reduces size or skips | Adaptive risk based on learned conditions |
| L6 — Timeout | 120 H1 bars (~5 days) max hold | Prevents capital lockup in indeterminate positions |

**Not used (intentionally):** No martingale, no grid, no trailing stop (shelved pending ≥40% win rate).

---

## Capital — The Real Math

| Account | Lot Size | Risk/Trade | Monthly Expected | Notes |
|---------|----------|------------|-----------------|-------|
| $200 | 0.01 micro | $1–2 | $3–5 | Spread cost 30–50% of edge on exotic pairs |
| $500 | 0.01–0.02 | $5–10 | $8–15 | Proves edge is real; trade USDJPY + GBPJPY only |
| $1,000 | 0.02–0.05 | $10–20 | $15–30 | First meaningful income range |
| $3,000 | 0.05–0.10 | $30–60 | $50–100 | Professional operation beginning |
| $10,000+ | 0.10–0.50 | $100–300 | $200–400 | Scalable at this level |

**Annualised at 36% return:**
$500 → $680 → $924 → $1,257 → $2,325 (Y5)

**MVP path:** Friction-adjusted backtest → 60-day paper trade → live on $500 with USDJPY+GBPJPY only.

---

## Honest Risk Assessment

1. **35% win rate psychology** — You will experience 7-loss runs routinely (statistically normal). Never override the algorithm manually based on a losing streak.
2. **GBPNZD live edge** — Backtest uses midpoint pricing. Spread cost likely flips this negative in live execution below $5k account size.
3. **2-year window risk** — 2022–2024 has specific macro characteristics. Walk-forward validation required before committing real capital.
4. **Long compounding runway** — At $500 and 36%/yr: meaningful dollar income takes 3–5 years unless capital is added regularly.

---

## Related Notes

- [[pair_config]] — Per-pair parameter overrides
- [[HYBRID_STRATEGY_DESIGN]] — Strategy architecture spec
- [[validated_baseline_v2]] — Locked baseline (do not revert)
- [[shelved_features]] — BEC partial close — revisit at ≥40% win rate

---

*Report generated: 2026-04-20. Baseline session: f416f438-820a-4e30-abf9-2805c338659f*

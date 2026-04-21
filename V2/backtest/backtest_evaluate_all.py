"""
Comprehensive Strategy Evaluation — All Pairs × All Strategies

Tests every pair against every strategy independently and produces a
ranked comparison matrix. Does NOT modify pair_config.py — overrides
are applied in-memory only.

Strategies tested:
  SWING    — Daily Z-score mean reversion, H1 execution (730-day window)
  M15      — M15 Z-score scalp, 5hr mean reversion window (60-day window)
  SCALP    — H1 session scalp during London/NY (730-day window)
  MOMENTUM — H1 momentum with daily Z alignment (730-day window)

Usage:
  python backtest_evaluate_all.py            # full matrix, all pairs all strategies
  python backtest_evaluate_all.py --swing    # swing only
  python backtest_evaluate_all.py --m15      # M15 only
  python backtest_evaluate_all.py --intraday # scalp + momentum only
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))
from v3_intelligence.pair_config import PairConfig, PAIR_CONFIGS, get_pair_config
from backtest_hybrid import HybridMultiTimeframeBacktest, _session

DATA_DIR = Path(__file__).parent / "data"

ALL_PAIRS    = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP", "GBPNZD", "EURUSD", "AUDNZD"]
ACTIVE_PAIRS = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD", "EURGBP", "GBPNZD"]

# ── Strategy parameter overrides for evaluation ───────────────────────────────

def _eval_cfg_swing(sym):
    """Force swing enabled, use default ATR/Z thresholds."""
    base = PAIR_CONFIGS.get(sym, PairConfig(symbol=sym, tier=2))
    return PairConfig(
        symbol=sym, tier=base.tier,
        swing_size_mult=1.0,
        swing_z_threshold=2.0,
        swing_target_atr=4.0, swing_stop_atr=1.5,
        swing_max_bars=120,
        allow_swing=True, allow_scalp=False, allow_momentum=False, allow_m15_scalp=False,
    )

def _eval_cfg_m15(sym):
    """Force M15 scalp enabled."""
    base = PAIR_CONFIGS.get(sym, PairConfig(symbol=sym, tier=2))
    return PairConfig(
        symbol=sym, tier=base.tier,
        m15_size_mult=0.7,
        m15_z_threshold=2.0,
        m15_target_atr=2.5, m15_stop_atr=1.5,
        m15_max_bars=12,
        allow_swing=False, allow_scalp=False, allow_momentum=False, allow_m15_scalp=True,
    )

def _eval_cfg_scalp(sym):
    """Force H1 session scalp enabled."""
    base = PAIR_CONFIGS.get(sym, PairConfig(symbol=sym, tier=2))
    return PairConfig(
        symbol=sym, tier=base.tier,
        scalp_size_mult=0.5,
        scalp_z_threshold=2.0,
        scalp_target_atr=2.0, scalp_stop_atr=0.75,
        scalp_max_bars=4,
        allow_swing=False, allow_scalp=True, allow_momentum=False, allow_m15_scalp=False,
    )

def _eval_cfg_momentum(sym):
    """Force momentum enabled."""
    base = PAIR_CONFIGS.get(sym, PairConfig(symbol=sym, tier=2))
    return PairConfig(
        symbol=sym, tier=base.tier,
        momentum_size_mult=0.3,
        momentum_z_threshold=1.5, momentum_daily_z_threshold=1.5,
        momentum_target_atr=1.0, momentum_stop_atr=0.5,
        momentum_max_bars=2,
        allow_swing=False, allow_scalp=False, allow_momentum=True, allow_m15_scalp=False,
    )


# ── Standalone backtest runners (inject override cfg) ────────────────────────

class Evaluator(HybridMultiTimeframeBacktest):
    """Extends the main backtest to accept injected configs for evaluation."""

    def run_swing_with_cfg(self, symbol, daily, h1, cfg):
        """Run swing backtest with injected config instead of pair_config.py."""
        if daily is None or h1 is None:
            return pd.DataFrame()
        daily = daily.copy(); h1 = h1.copy()

        daily['atr']     = self.adaptive_atr(daily['High'], daily['Low'], daily['Close'])
        daily['z_score'] = self.z_score_signal(daily['Close'])
        if self.enable_changepoint:
            daily['changepoint'] = self.regime_changepoint(
                self.compute_adx(daily['High'], daily['Low'], daily['Close']))
        else:
            daily['changepoint'] = 0

        h1['atr']     = self.adaptive_atr(h1['High'], h1['Low'], h1['Close'])
        h1['z_score'] = self.z_score_signal(h1['Close'])
        h1['vol_pct'] = self.vol_percentile(h1['atr'])

        daily_d = np.array([str(d)[:10] for d in daily.index])
        h1_d    = np.array([str(d)[:10] for d in h1.index])
        idx     = np.clip(np.searchsorted(daily_d, h1_d, side='right') - 1, 0, len(daily) - 1)
        h1['daily_z']     = daily['z_score'].values[idx]
        h1['changepoint'] = daily['changepoint'].values[idx]

        position = None; trades = []
        for i in range(100, len(h1)):
            row  = h1.iloc[i]; ts = h1.index[i]
            dz   = row['daily_z']; atr = row['atr']; px = row['Close']
            cp   = int(row['changepoint']) if not pd.isna(row['changepoint']) else 0
            sess = _session(ts.hour)

            if position is not None:
                ep = position['entry_price']; lng = 'LONG' in position['type']
                pnl = (px - ep) / ep if lng else (ep - px) / ep
                av  = position['atr_entry']; bars = i - position['entry_bar']
                tgt = av * cfg.swing_target_atr / ep
                sl  = av * cfg.swing_stop_atr   / ep
                why = None
                if   pnl >= tgt:                  why = 'target'
                elif pnl <= -sl:                  why = 'stop'
                elif bars > cfg.swing_max_bars:   why = 'timeout'
                if why:
                    trades.append({'symbol': symbol, 'type': position['type'],
                                   'direction': 'LONG' if lng else 'SHORT',
                                   'strategy': 'SWING', 'entry_date': position['entry_date'],
                                   'exit_date': ts, 'entry_price': ep, 'exit_price': px,
                                   'pnl_pct': pnl, 'bars_held': bars, 'size': position['size'],
                                   'exit_reason': why, 'daily_z': position['daily_z'],
                                   'session': sess})
                    position = None
            else:
                if (not pd.isna(dz) and abs(dz) > cfg.swing_z_threshold
                        and not pd.isna(atr) and atr > 0
                        and not (self.enable_changepoint and cp == 1)):
                    pt = 'DAILY_SWING_LONG' if dz < 0 else 'DAILY_SWING_SHORT'
                    position = {'type': pt, 'entry_price': px, 'entry_date': ts,
                                'entry_bar': i, 'entry_hour': ts.hour, 'atr_entry': atr,
                                'size': cfg.swing_size_mult, 'daily_z': dz}
        return pd.DataFrame(trades)

    def run_scalp_with_cfg(self, symbol, daily, h1, cfg):
        """Run H1 session scalp with injected config."""
        if daily is None or h1 is None:
            return pd.DataFrame()
        daily = daily.copy(); h1 = h1.copy()

        daily['z_score'] = self.z_score_signal(daily['Close'])
        if self.enable_changepoint:
            daily['changepoint'] = self.regime_changepoint(
                self.compute_adx(daily['High'], daily['Low'], daily['Close']))
        else:
            daily['changepoint'] = 0

        h1['atr']     = self.adaptive_atr(h1['High'], h1['Low'], h1['Close'])
        h1['z_score'] = self.z_score_signal(h1['Close'])

        daily_d = np.array([str(d)[:10] for d in daily.index])
        h1_d    = np.array([str(d)[:10] for d in h1.index])
        idx     = np.clip(np.searchsorted(daily_d, h1_d, side='right') - 1, 0, len(daily) - 1)
        h1['daily_z']     = daily['z_score'].values[idx]
        h1['changepoint'] = daily['changepoint'].values[idx]

        position = None; trades = []
        for i in range(100, len(h1)):
            row  = h1.iloc[i]; ts = h1.index[i]
            h1z  = row['z_score']; dz = row['daily_z']; atr = row['atr']
            px   = row['Close']; cp = int(row['changepoint']) if not pd.isna(row['changepoint']) else 0
            sess = _session(ts.hour)

            if position is not None:
                ep = position['entry_price']; lng = 'LONG' in position['type']
                pnl = (px - ep) / ep if lng else (ep - px) / ep
                av  = position['atr_entry']; bars = i - position['entry_bar']
                tgt = av * cfg.scalp_target_atr / ep
                sl  = av * cfg.scalp_stop_atr   / ep
                why = None
                if   pnl >= tgt:                 why = 'target'
                elif pnl <= -sl:                 why = 'stop'
                elif bars > cfg.scalp_max_bars:  why = 'timeout'
                if why:
                    trades.append({'symbol': symbol, 'type': position['type'],
                                   'direction': 'LONG' if lng else 'SHORT',
                                   'strategy': 'H1_SCALP', 'entry_date': position['entry_date'],
                                   'exit_date': ts, 'entry_price': ep, 'exit_price': px,
                                   'pnl_pct': pnl, 'bars_held': bars, 'size': position['size'],
                                   'exit_reason': why, 'daily_z': position.get('daily_z'),
                                   'session': sess})
                    position = None
            else:
                if (sess in ('LONDON', 'NY')
                        and not pd.isna(h1z) and abs(h1z) > cfg.scalp_z_threshold
                        and not pd.isna(atr) and atr > 0
                        and not (self.enable_changepoint and cp == -1)
                        and (pd.isna(dz) or abs(dz) < 1.5
                             or (dz < 0 and h1z < 0) or (dz > 0 and h1z > 0))):
                    pt = 'H1_SCALP_LONG' if h1z < 0 else 'H1_SCALP_SHORT'
                    position = {'type': pt, 'entry_price': px, 'entry_date': ts,
                                'entry_bar': i, 'atr_entry': atr, 'size': cfg.scalp_size_mult,
                                'daily_z': dz}
        return pd.DataFrame(trades)

    def run_momentum_with_cfg(self, symbol, daily, h1, cfg):
        """Run intraday momentum with injected config."""
        if daily is None or h1 is None:
            return pd.DataFrame()
        daily = daily.copy(); h1 = h1.copy()

        daily['z_score'] = self.z_score_signal(daily['Close'])
        if self.enable_changepoint:
            daily['changepoint'] = self.regime_changepoint(
                self.compute_adx(daily['High'], daily['Low'], daily['Close']))
        else:
            daily['changepoint'] = 0

        h1['atr']     = self.adaptive_atr(h1['High'], h1['Low'], h1['Close'])
        h1['z_score'] = self.z_score_signal(h1['Close'])

        daily_d = np.array([str(d)[:10] for d in daily.index])
        h1_d    = np.array([str(d)[:10] for d in h1.index])
        idx     = np.clip(np.searchsorted(daily_d, h1_d, side='right') - 1, 0, len(daily) - 1)
        h1['daily_z']     = daily['z_score'].values[idx]
        h1['changepoint'] = daily['changepoint'].values[idx]

        position = None; trades = []
        for i in range(100, len(h1)):
            row  = h1.iloc[i]; ts = h1.index[i]
            h1z  = row['z_score']; dz = row['daily_z']; atr = row['atr']
            px   = row['Close']; cp = int(row['changepoint']) if not pd.isna(row['changepoint']) else 0
            sess = _session(ts.hour)

            if position is not None:
                ep = position['entry_price']; lng = 'LONG' in position['type']
                pnl = (px - ep) / ep if lng else (ep - px) / ep
                av  = position['atr_entry']; bars = i - position['entry_bar']
                tgt = av * cfg.momentum_target_atr / ep
                sl  = av * cfg.momentum_stop_atr   / ep
                why = None
                if   pnl >= tgt:                    why = 'target'
                elif pnl <= -sl:                    why = 'stop'
                elif bars > cfg.momentum_max_bars:  why = 'timeout'
                if why:
                    trades.append({'symbol': symbol, 'type': position['type'],
                                   'direction': 'LONG' if lng else 'SHORT',
                                   'strategy': 'MOMENTUM', 'entry_date': position['entry_date'],
                                   'exit_date': ts, 'entry_price': ep, 'exit_price': px,
                                   'pnl_pct': pnl, 'bars_held': bars, 'size': position['size'],
                                   'exit_reason': why, 'daily_z': position.get('daily_z'),
                                   'session': sess})
                    position = None
            else:
                if (sess in ('LONDON', 'NY')
                        and not pd.isna(h1z) and not pd.isna(dz)
                        and abs(h1z) > cfg.momentum_z_threshold
                        and abs(dz) > cfg.momentum_daily_z_threshold
                        and not pd.isna(atr) and atr > 0
                        and ((dz < 0 and h1z < 0) or (dz > 0 and h1z > 0))):
                    pt = 'MOMENTUM_LONG' if h1z < 0 else 'MOMENTUM_SHORT'
                    position = {'type': pt, 'entry_price': px, 'entry_date': ts,
                                'entry_bar': i, 'atr_entry': atr, 'size': cfg.momentum_size_mult,
                                'daily_z': dz}
        return pd.DataFrame(trades)

    def run_m15_with_cfg(self, symbol, daily, m15, cfg):
        """Run M15 scalp with injected config."""
        if daily is None or m15 is None:
            return pd.DataFrame()
        daily = daily.copy(); m15 = m15.copy()

        daily['z_score'] = self.z_score_signal(daily['Close'])
        if self.enable_changepoint:
            daily['changepoint'] = self.regime_changepoint(
                self.compute_adx(daily['High'], daily['Low'], daily['Close']))
        else:
            daily['changepoint'] = 0

        m15['atr']     = self.adaptive_atr(m15['High'], m15['Low'], m15['Close'])
        m15['z_score'] = self.z_score_signal(m15['Close'], period=20)

        daily_d = np.array([str(d)[:10] for d in daily.index])
        m15_d   = np.array([str(d)[:10] for d in m15.index])
        idx     = np.clip(np.searchsorted(daily_d, m15_d, side='right') - 1, 0, len(daily) - 1)
        m15['daily_z']     = daily['z_score'].values[idx]
        m15['changepoint'] = daily['changepoint'].values[idx]

        position = None; trades = []
        for i in range(50, len(m15)):
            row  = m15.iloc[i]; ts = m15.index[i]
            m15z = row['z_score']; dz = row['daily_z']; atr = row['atr']
            px   = row['Close']; cp = int(row['changepoint']) if not pd.isna(row['changepoint']) else 0
            sess = _session(ts.hour)

            if position is not None:
                ep = position['entry_price']; lng = 'LONG' in position['type']
                pnl = (px - ep) / ep if lng else (ep - px) / ep
                av  = position['atr_entry']; bars = i - position['entry_bar']
                tgt = av * cfg.m15_target_atr / ep
                sl  = av * cfg.m15_stop_atr   / ep
                why = None
                if   pnl >= tgt:                 why = 'target'
                elif pnl <= -sl:                 why = 'stop'
                elif bars > cfg.m15_max_bars:    why = 'timeout'
                if why:
                    trades.append({'symbol': symbol, 'type': position['type'],
                                   'direction': 'LONG' if lng else 'SHORT',
                                   'strategy': 'M15_SCALP', 'entry_date': position['entry_date'],
                                   'exit_date': ts, 'entry_price': ep, 'exit_price': px,
                                   'pnl_pct': pnl, 'bars_held': bars, 'size': position['size'],
                                   'exit_reason': why, 'daily_z': position.get('daily_z'),
                                   'session': sess})
                    position = None
            elif sess in ('LONDON', 'NY'):
                if (not pd.isna(m15z) and not pd.isna(atr) and atr > 0
                        and abs(m15z) > cfg.m15_z_threshold
                        and not (self.enable_changepoint and cp == 1)):
                    dz_safe = dz if not pd.isna(dz) else 0.0
                    aligned = (abs(dz_safe) < 1.5
                               or (dz_safe < -1.5 and m15z < 0)
                               or (dz_safe >  1.5 and m15z > 0))
                    if aligned:
                        pt = 'M15_SCALP_LONG' if m15z < 0 else 'M15_SCALP_SHORT'
                        position = {'type': pt, 'entry_price': px, 'entry_date': ts,
                                    'entry_bar': i, 'atr_entry': atr,
                                    'size': cfg.m15_size_mult, 'daily_z': dz_safe}
        return pd.DataFrame(trades)


# ── Metrics helper ────────────────────────────────────────────────────────────

def metrics(df):
    if df is None or len(df) == 0:
        return None
    pnl    = df['pnl_pct']
    wins   = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    sharpe = pnl.mean() / pnl.std() * np.sqrt(252) if pnl.std() > 0 else 0.0
    wl     = abs(wins.mean() / losses.mean()) if len(wins) > 0 and len(losses) > 0 else 0.0
    exp    = ((len(wins)/len(df)) * wins.mean() + (len(losses)/len(df)) * losses.mean()
              if len(wins) > 0 and len(losses) > 0 else 0.0)
    cum    = pnl.cumsum()
    max_dd = (cum - cum.cummax()).min() * 100
    return {
        'n':       len(df),
        'win_pct': len(wins) / len(df) * 100,
        'pnl':     pnl.sum() * 100,
        'avg':     pnl.mean() * 100,
        'sharpe':  sharpe,
        'wl':      wl,
        'exp':     exp * 100,
        'max_dd':  max_dd,
        'avg_win': wins.mean() * 100  if len(wins)   > 0 else 0.0,
        'avg_los': losses.mean() * 100 if len(losses) > 0 else 0.0,
    }


# ── Main evaluation ───────────────────────────────────────────────────────────

def run_evaluation(run_swing=True, run_m15=True, run_scalp=True, run_momentum=True):
    ev = Evaluator(DATA_DIR, enable_rag=False, enable_logging=False, enable_changepoint=True)

    results = {}   # {(pair, strategy): metrics_dict}
    print("\nRunning evaluation matrix — this may take 2-3 minutes...")

    for sym in ALL_PAIRS:
        daily = ev._load_daily(sym)
        h1    = ev._load_h1(sym)
        m15   = ev._load_m15(sym)
        print(f"  {sym}...", end=" ", flush=True)

        if run_swing:
            t = ev.run_swing_with_cfg(sym, daily, h1, _eval_cfg_swing(sym))
            results[(sym, 'SWING')] = metrics(t)

        if run_scalp:
            t = ev.run_scalp_with_cfg(sym, daily, h1, _eval_cfg_scalp(sym))
            results[(sym, 'H1_SCALP')] = metrics(t)

        if run_momentum:
            t = ev.run_momentum_with_cfg(sym, daily, h1, _eval_cfg_momentum(sym))
            results[(sym, 'MOMENTUM')] = metrics(t)

        if run_m15 and m15 is not None:
            t = ev.run_m15_with_cfg(sym, daily, m15, _eval_cfg_m15(sym))
            results[(sym, 'M15_SCALP')] = metrics(t)
        elif run_m15:
            results[(sym, 'M15_SCALP')] = None

        print("done")

    # ── Print comparison matrix ───────────────────────────────────────────────
    strategies = []
    if run_swing:     strategies.append('SWING')
    if run_scalp:     strategies.append('H1_SCALP')
    if run_momentum:  strategies.append('MOMENTUM')
    if run_m15:       strategies.append('M15_SCALP')

    W = 118

    print("\n" + "█"*W)
    print("█" + "  ALL PAIRS × ALL STRATEGIES — EVALUATION MATRIX".center(W-2) + "█")
    print("█" + "  SWING=730d H1 data | H1_SCALP=730d H1 | MOMENTUM=730d H1 | M15=60d M15 data".center(W-2) + "█")
    print("█"*W)

    # ── Per-strategy section ──────────────────────────────────────────────────
    for strat in strategies:
        col_w = W
        print(f"\n{'─'*col_w}")
        print(f"  STRATEGY: {strat}")
        print(f"{'─'*col_w}")
        print(f"  {'Pair':8} {'Trades':8} {'Win%':7} {'PnL':9} {'Avg/Tr':8} "
              f"{'W/L':6} {'Sharpe':8} {'MaxDD':8} {'AvgWin':8} {'AvgLoss':9} {'Expectancy':11}  Verdict")
        print(f"  {'-'*113}")

        strat_results = [(sym, results.get((sym, strat))) for sym in ALL_PAIRS]
        # Sort by Sharpe descending
        strat_results.sort(key=lambda x: x[1]['sharpe'] if x[1] else -99, reverse=True)

        for sym, m in strat_results:
            if m is None:
                print(f"  {sym:8} {'NO DATA':>8}")
                continue
            verdict = _verdict(m)
            print(f"  {sym:8} {m['n']:8} {m['win_pct']:6.1f}%  {m['pnl']:+8.2f}%  "
                  f"{m['avg']:+7.3f}%  {m['wl']:5.2f}  {m['sharpe']:7.2f}  "
                  f"{m['max_dd']:+7.2f}%  {m['avg_win']:+7.3f}%  {m['avg_los']:+8.3f}%  "
                  f"{m['exp']:+10.4f}%  {verdict}")

    # ── Full cross-strategy matrix (best strategy per pair) ───────────────────
    print(f"\n\n{'█'*W}")
    print("█" + "  BEST STRATEGY PER PAIR — RANKED BY SHARPE".center(W-2) + "█")
    print("█"*W)
    print(f"\n  {'Pair':8} {'Best Strategy':14} {'Trades':8} {'Win%':7} {'PnL':9} "
          f"{'Sharpe':8} {'W/L':6} {'MaxDD':8}  vs 2nd Best")
    print(f"  {'-'*113}")

    for sym in ALL_PAIRS:
        pair_results = [(strat, results.get((sym, strat))) for strat in strategies]
        valid = [(s, m) for s, m in pair_results if m is not None and m['n'] > 5]
        if not valid:
            print(f"  {sym:8}  No valid results")
            continue
        valid.sort(key=lambda x: x[1]['sharpe'], reverse=True)
        best_s, best_m = valid[0]
        second = f"{valid[1][0]} Sh={valid[1][1]['sharpe']:.2f}" if len(valid) > 1 else "N/A"
        print(f"  {sym:8} {best_s:14} {best_m['n']:8} {best_m['win_pct']:6.1f}%  "
              f"{best_m['pnl']:+8.2f}%  {best_m['sharpe']:7.2f}  {best_m['wl']:5.2f}  "
              f"{best_m['max_dd']:+7.2f}%   2nd: {second}")

    # ── Strategy totals (summed across all pairs) ─────────────────────────────
    print(f"\n\n{'█'*W}")
    print("█" + "  STRATEGY TOTALS — ALL PAIRS COMBINED".center(W-2) + "█")
    print("█"*W)
    print(f"\n  {'Strategy':14} {'Total Trades':14} {'Avg Win%':9} {'Total PnL':11} "
          f"{'Portfolio Sharpe':17} {'Avg W/L':8} {'Pairs Positive':15}")
    print(f"  {'-'*100}")

    for strat in strategies:
        all_m = [results.get((sym, strat)) for sym in ALL_PAIRS]
        valid = [m for m in all_m if m is not None and m['n'] > 0]
        if not valid:
            continue
        total_t   = sum(m['n']    for m in valid)
        avg_wr    = np.mean([m['win_pct'] for m in valid])
        total_pnl = sum(m['pnl']  for m in valid)
        avg_sh    = np.mean([m['sharpe']  for m in valid])
        avg_wl    = np.mean([m['wl']      for m in valid if m['wl'] > 0])
        pos_pairs = sum(1 for m in valid if m['pnl'] > 0)
        print(f"  {strat:14} {total_t:14} {avg_wr:8.1f}%  {total_pnl:+10.2f}%  "
              f"{avg_sh:16.2f}  {avg_wl:7.2f}  {pos_pairs}/{len(valid)} positive")

    # ── Recommendation grid ───────────────────────────────────────────────────
    print(f"\n\n{'█'*W}")
    print("█" + "  RECOMMENDED CONFIGURATION — DATA-DRIVEN PAIR × STRATEGY ASSIGNMENTS".center(W-2) + "█")
    print("█"*W)
    print(f"\n  {'Pair':8}", end="")
    for s in strategies:
        print(f"  {s:12}", end="")
    print(f"  {'Recommended'}"); print(f"  {'-'*113}")

    for sym in ALL_PAIRS:
        print(f"  {sym:8}", end="")
        best_sharpe = -99; best_s = None
        for strat in strategies:
            m = results.get((sym, strat))
            if m is None:
                print(f"  {'N/A':12}", end="")
            else:
                flag = "✓ " if m['sharpe'] > 0.3 and m['pnl'] > 0 else "✗ "
                print(f"  {flag}Sh={m['sharpe']:5.2f}   ", end="")
                if m['sharpe'] > best_sharpe and m['n'] > 5:
                    best_sharpe = m['sharpe']; best_s = strat
        rec = f"USE {best_s}" if best_s and best_sharpe > 0.3 else "DISABLE"
        print(f"  → {rec}")

    print(f"\n{'═'*W}\n")


def _verdict(m):
    if m['n'] < 10:
        return "INSUFFICIENT"
    if m['sharpe'] >= 1.5 and m['pnl'] > 0:
        return "STRONG ✓"
    if m['sharpe'] >= 0.5 and m['pnl'] > 0:
        return "POSITIVE ✓"
    if m['sharpe'] >= 0 and m['pnl'] > 0:
        return "MARGINAL ~"
    return "NEGATIVE ✗"


if __name__ == "__main__":
    args = sys.argv[1:]
    run_evaluation(
        run_swing    ="--swing"    in args or not args,
        run_m15      ="--m15"      in args or not args,
        run_scalp    ="--scalp"    in args or ("--intraday" in args) or not args,
        run_momentum ="--momentum" in args or ("--intraday" in args) or not args,
    )

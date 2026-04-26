"""
MarketMind V2 — Dual-Strategy Backtest Engine

Two INDEPENDENT strategies with separate position tracking and reporting:

  Strategy 1: DAILY SWING (H1 execution)
    - Signal: daily Z-score mean reversion (|Z| > 2.0)
    - Exits:  4.0× H1_ATR target, 1.5× H1_ATR stop, 120-bar timeout
    - Pairs:  6 active (USDJPY T1, GBPJPY T1, GBPAUD T1, GBPUSD T1, EURGBP T2, GBPNZD T2)

  Strategy 2: M15 INTRADAY SCALP (independent)
    - Signal: M15 Z-score on 20-period window (5-hour mean reversion)
    - Filter: Must align with or be neutral to daily Z direction
    - Session: London (07-11 UTC) or NY (13-17 UTC) only
    - Exits:  2.5× M15_ATR target, 1.5× M15_ATR stop, 12-bar timeout (3 hrs)
    - Pairs:  5 active (USDJPY, GBPJPY, GBPAUD, GBPUSD, EURGBP)

Capital note: Designed for IC Markets Raw account at 1:100 leverage.
  Raw spreads near 0 (0.1-0.2 pips) + commission $3.50/lot/side.
  Raw account mandatory for M15 scalp — standard spreads destroy M15 edge.

NOTE: BEC Partial Close shelved — revisit when win rate reaches >=40%.
      See docs/shelved_features.md for implementation details.
"""
import sys
import io
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))
from v3_intelligence.trade_logger import TradeLogger
from v3_intelligence.pair_config import get_pair_config, print_pair_summary
from v3_intelligence.rag_signal_filter import RAGSignalFilter, CHROMA_AVAILABLE
from v3_intelligence.learning_loop import on_trade_close
from signal_filters import rolling_hurst

# Session windows (UTC hours)
_LONDON_HOURS = frozenset(range(7, 12))
_NY_HOURS     = frozenset(range(13, 18))


def _session(hour: int) -> str:
    if hour in _LONDON_HOURS: return 'LONDON'
    if hour in _NY_HOURS:     return 'NY'
    return 'OFF'


class HybridMultiTimeframeBacktest:
    def __init__(self, data_dir, enable_rag=True, enable_logging=True,
                 enable_changepoint=True, enable_hurst_filter=False):
        self.data_dir          = Path(data_dir)
        self.reports_dir       = Path(data_dir).parent / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.swing_symbols     = ["USDJPY", "GBPJPY", "GBPAUD", "GBPUSD",
                                  "EURGBP", "GBPNZD", "EURUSD", "AUDNZD"]
        # M15: enabled on all pairs except GBPJPY (structurally negative all thresholds)
        self.m15_symbols       = ["USDJPY", "GBPAUD", "GBPUSD", "EURGBP",
                                  "GBPNZD", "EURUSD", "AUDNZD"]
        self.enable_changepoint = enable_changepoint

        self.enable_hurst_filter = enable_hurst_filter
        self.logger = TradeLogger() if enable_logging else None
        self.rag    = RAGSignalFilter() if (enable_rag and CHROMA_AVAILABLE) else None
        self._rag_enabled = enable_rag and CHROMA_AVAILABLE
        self._rag_cache: dict = {}
        self._report_buffer: list[str] = []   # accumulates lines for file save

    # ─────────────────────────────────────────────────────────────────────────
    # SIGNAL HELPERS  (shared by both strategies)
    # ─────────────────────────────────────────────────────────────────────────

    def adaptive_atr(self, high, low, close, period=14, lookback=50):
        tr     = np.maximum(high - low,
                            np.maximum(np.abs(high - close.shift(1)),
                                       np.abs(low  - close.shift(1))))
        atr    = tr.rolling(period).mean()
        vol    = close.pct_change().rolling(lookback).std()
        vol_ma = vol.rolling(lookback).mean()
        return atr * (vol / vol_ma)

    def z_score_signal(self, close, period=20):
        ma  = close.rolling(period).mean()
        std = close.rolling(period).std()
        return (close - ma) / std

    def vol_percentile(self, atr, window=20):
        def _pct(x):
            return (x[:-1] < x[-1]).sum() / (len(x) - 1) * 100 if len(x) > 1 else 50.0
        return atr.rolling(window + 1).apply(_pct, raw=True)

    def compute_adx(self, high, low, close, period=14):
        prev_close = close.shift(1)
        tr         = pd.concat([high - low,
                                (high - prev_close).abs(),
                                (low  - prev_close).abs()], axis=1).max(axis=1)
        dm_plus    = high.diff()
        dm_minus   = -low.diff()
        dm_plus    = dm_plus.where((dm_plus > dm_minus) & (dm_plus > 0),   0.0)
        dm_minus   = dm_minus.where((dm_minus > dm_plus) & (dm_minus > 0), 0.0)
        alpha      = 1.0 / period
        atr14      = tr.ewm(alpha=alpha, adjust=False).mean()
        di_plus    = 100 * dm_plus.ewm(alpha=alpha, adjust=False).mean() / atr14
        di_minus   = 100 * dm_minus.ewm(alpha=alpha, adjust=False).mean() / atr14
        denom      = (di_plus + di_minus).replace(0, np.nan)
        dx         = (100 * (di_plus - di_minus).abs() / denom).fillna(0)
        return dx.ewm(alpha=alpha, adjust=False).mean()

    def regime_changepoint(self, adx, strong_threshold=25.0, range_threshold=20.0,
                           window=5, rollover_frac=0.15, range_end_rise=0.30):
        adx_peak     = adx.rolling(window).max()
        trend_ending = (
            (adx_peak > strong_threshold) &
            (adx < adx_peak * (1.0 - rollover_frac)) &
            (adx < adx.shift(1))
        )
        range_ending = (
            (adx.shift(window) < range_threshold) &
            ((adx - adx.shift(window)) > strong_threshold * range_end_rise)
        )
        cp = pd.Series(0, index=adx.index, dtype=int)
        cp[trend_ending] = 1
        cp[range_ending] = -1
        return cp

    def _rag_size_modifier(self, symbol, strategy_type, session,
                           daily_z, h1_z, vol_pctl, hour_utc):
        if not self._rag_enabled or self.rag is None or self.rag.count < 30:
            return 1.0
        z_bucket   = round(daily_z * 2) / 2
        h1_bucket  = round(h1_z) if h1_z else 0
        vol_bucket = (int(vol_pctl) // 20) * 20 if vol_pctl and not np.isnan(vol_pctl) else 40
        hr_bucket  = hour_utc // 4 * 4
        key = (symbol, strategy_type, session, z_bucket, h1_bucket, vol_bucket, hr_bucket)
        if key in self._rag_cache:
            return self._rag_cache[key]
        score  = self.rag.score_signal(
            symbol=symbol, strategy_type=strategy_type, session=session,
            daily_z=daily_z, h1_z=h1_z or 0.0,
            vol_percentile=vol_pctl, hour_utc=hour_utc)
        result = score["size_modifier"] if score["action"] != "SKIP" else 0.0
        self._rag_cache[key] = result
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # DATA LOADERS
    # ─────────────────────────────────────────────────────────────────────────

    def _load_daily(self, sym):
        f = self.data_dir / f"{sym}_DAILY_2015-2026.csv"
        if not f.exists():
            return None
        return pd.read_csv(f, index_col=0, parse_dates=True)

    def _load_h1(self, sym):
        f = self.data_dir / f"{sym}_H1_730d.csv"
        if not f.exists():
            return None
        return pd.read_csv(f, index_col=0, parse_dates=True)

    def _load_m15(self, sym):
        # Prefer full-history file (from fetch_data.py) over 60-day yfinance file
        for name in (f"{sym}_M15.csv", f"{sym}_M15_60d.csv"):
            f = self.data_dir / name
            if f.exists():
                return pd.read_csv(f, index_col=0, parse_dates=True)
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # STRATEGY 1: DAILY SWING  (independent H1 execution loop)
    # ─────────────────────────────────────────────────────────────────────────

    def _backtest_swing_symbol(self, symbol, daily_data, h1_data):
        """Daily Z-score mean-reversion swing trades executed on H1 bars."""
        cfg   = get_pair_config(symbol)
        if not cfg.allow_swing:
            return pd.DataFrame()

        daily = daily_data.copy()
        h1    = h1_data.copy()

        daily['atr']     = self.adaptive_atr(daily['High'], daily['Low'], daily['Close'])
        daily['z_score'] = self.z_score_signal(daily['Close'])

        if self.enable_hurst_filter:
            daily['hurst'] = rolling_hurst(daily['Close'], window=80)
        else:
            daily['hurst'] = 0.0  # neutral — never blocks

        h1['atr']     = self.adaptive_atr(h1['High'], h1['Low'], h1['Close'])
        h1['z_score'] = self.z_score_signal(h1['Close'])
        h1['vol_pct'] = self.vol_percentile(h1['atr'])

        if self.enable_changepoint:
            daily['changepoint'] = self.regime_changepoint(
                self.compute_adx(daily['High'], daily['Low'], daily['Close']))
        else:
            daily['changepoint'] = 0

        # Timezone-safe date merge
        daily_d = np.array([str(d)[:10] for d in daily.index])
        h1_d    = np.array([str(d)[:10] for d in h1.index])
        idx     = np.clip(np.searchsorted(daily_d, h1_d, side='right') - 1, 0, len(daily) - 1)
        h1['daily_z']     = daily['z_score'].values[idx]
        h1['hurst']       = daily['hurst'].values[idx]
        h1['changepoint'] = daily['changepoint'].values[idx]

        position = None
        trades   = []

        for i in range(100, len(h1) - 1):
            row      = h1.iloc[i]
            next_row = h1.iloc[i + 1]
            ts   = h1.index[i]
            hour = ts.hour
            dz   = row['daily_z']
            h1z  = row['z_score']
            atr  = row['atr']
            vpct = row['vol_pct']
            px   = row['Close']
            cp   = int(row['changepoint']) if not pd.isna(row['changepoint']) else 0
            hv   = row['hurst'] if not pd.isna(row['hurst']) else 0.0
            sess = _session(hour)

            # ── EXIT ──────────────────────────────────────────────────────────
            if position is not None:
                ep   = position['entry_price']
                lng  = 'LONG' in position['type']
                pnl  = (px - ep) / ep if lng else (ep - px) / ep
                av   = position['atr_entry']
                bars = i - position['entry_bar']
                tgt  = av * cfg.swing_target_atr / ep
                sl   = av * cfg.swing_stop_atr   / ep
                why  = None
                if   pnl >= tgt:             why = 'target'
                elif pnl <= -sl:             why = 'stop'
                elif bars > cfg.swing_max_bars: why = 'timeout'

                if why:
                    rec = {
                        'symbol':        symbol,
                        'type':          position['type'],
                        'direction':     'LONG' if lng else 'SHORT',
                        'strategy':      'SWING',
                        'entry_date':    position['entry_date'],
                        'exit_date':     ts,
                        'entry_price':   ep,
                        'exit_price':    px,
                        'pnl_pct':       pnl,
                        'bars_held':     bars,
                        'size':          position['size'],
                        'exit_reason':   why,
                        'daily_z':       position['daily_z'],
                        'h1_z':          position['h1_z'],
                        'h1_atr':        av,
                        'vol_percentile': position['vol_pct'],
                        'session':       position['session'],
                        'hour_utc':      position['entry_hour'],
                    }
                    # INFRA-03 / D-10..D-13 — close RAG learning loop synchronously.
                    # decision_log diff requires strategy_type column (matches trades
                    # table column name) and a params_json JSON-string snapshot.
                    rec['strategy_type'] = 'SWING'
                    rec['params_json'] = json.dumps({
                        'swing_z_threshold': cfg.swing_z_threshold,
                        'swing_target_atr':  cfg.swing_target_atr,
                        'swing_stop_atr':    cfg.swing_stop_atr,
                        'swing_size_mult':   cfg.swing_size_mult,
                    })
                    trades.append(rec)
                    on_trade_close(rec)
                    position = None

            # ── ENTRY ─────────────────────────────────────────────────────────
            elif position is None:
                if (not pd.isna(dz)
                        and abs(dz) > cfg.swing_z_threshold
                        and not pd.isna(atr) and atr > 0
                        and not (self.enable_changepoint and cp == 1)
                        and not (self.enable_hurst_filter and hv > 0.55)):
                    pt  = 'DAILY_SWING_LONG' if dz < 0 else 'DAILY_SWING_SHORT'
                    sz  = 1.0 * cfg.swing_size_mult
                    rm  = self._rag_size_modifier(symbol, pt, sess, dz, h1z, vpct, hour)
                    if rm > 0:
                        # BKTS-01 (D-01): next-bar open fill — see .planning/phases/07-.../07-CONTEXT.md
                        entry_px = next_row['Open']
                        position = {
                            'type':        pt,
                            'entry_price': entry_px,
                            'entry_date':  ts,
                            'entry_bar':   i,
                            'entry_hour':  hour,
                            'atr_entry':   atr,
                            'size':        sz * rm,
                            'daily_z':     dz,
                            'h1_z':        h1z,
                            'vol_pct':     vpct,
                            'session':     sess,
                        }

        return pd.DataFrame(trades) if trades else pd.DataFrame()

    # ─────────────────────────────────────────────────────────────────────────
    # STRATEGY 2: M15 INTRADAY SCALP  (independent M15 loop)
    # ─────────────────────────────────────────────────────────────────────────

    def _backtest_m15_symbol(self, symbol, daily_data, m15_data):
        """
        M15 Z-score mean-reversion scalp, aligned with daily direction.

        Entry rules:
          - M15 Z-score (20-period = 5hr window) |z| > m15_z_threshold
          - Direction aligned with daily Z: if daily oversold (dz<-1.5) → LONG only;
            if daily overbought (dz>1.5) → SHORT only; neutral → both
          - Session: London (07-11 UTC) or NY (13-17 UTC) only
          - Change-point filter: trend-ending (cp=1) blocks entry
        Exit rules:
          - Target: 2.5× M15_ATR
          - Stop:   1.5× M15_ATR
          - Timeout: 12 M15 bars = 3 hours
        """
        cfg = get_pair_config(symbol)
        if not cfg.allow_m15_scalp:
            return pd.DataFrame()

        daily = daily_data.copy()
        m15   = m15_data.copy()

        daily['z_score'] = self.z_score_signal(daily['Close'])
        if self.enable_changepoint:
            daily['changepoint'] = self.regime_changepoint(
                self.compute_adx(daily['High'], daily['Low'], daily['Close']))
        else:
            daily['changepoint'] = 0

        m15['atr']     = self.adaptive_atr(m15['High'], m15['Low'], m15['Close'])
        m15['z_score'] = self.z_score_signal(m15['Close'], period=20)
        m15['vol_pct'] = self.vol_percentile(m15['atr'])

        if self.enable_hurst_filter:
            m15['hurst'] = rolling_hurst(m15['Close'], window=200)
        else:
            m15['hurst'] = 0.0

        # Merge daily context onto M15 timestamps
        daily_d = np.array([str(d)[:10] for d in daily.index])
        m15_d   = np.array([str(d)[:10] for d in m15.index])
        idx     = np.clip(np.searchsorted(daily_d, m15_d, side='right') - 1, 0, len(daily) - 1)
        m15['daily_z']     = daily['z_score'].values[idx]
        m15['changepoint'] = daily['changepoint'].values[idx]
        # m15['hurst'] already computed on M15 data above (not from daily)

        position = None
        trades   = []

        for i in range(50, len(m15) - 1):
            row      = m15.iloc[i]
            next_row = m15.iloc[i + 1]
            ts   = m15.index[i]
            hour = ts.hour
            m15z = row['z_score']
            dz   = row['daily_z']
            atr  = row['atr']
            vpct = row['vol_pct']
            px   = row['Close']
            cp   = int(row['changepoint']) if not pd.isna(row['changepoint']) else 0
            hv   = row['hurst'] if not pd.isna(row['hurst']) else 0.0
            sess = _session(hour)

            # ── EXIT ──────────────────────────────────────────────────────────
            if position is not None:
                ep   = position['entry_price']
                lng  = 'LONG' in position['type']
                pnl  = (px - ep) / ep if lng else (ep - px) / ep
                av   = position['atr_entry']
                bars = i - position['entry_bar']
                tgt  = av * cfg.m15_target_atr / ep
                sl   = av * cfg.m15_stop_atr   / ep
                why  = None
                if   pnl >= tgt:              why = 'target'
                elif pnl <= -sl:              why = 'stop'
                elif bars > cfg.m15_max_bars: why = 'timeout'

                if why:
                    rec = {
                        'symbol':        symbol,
                        'type':          position['type'],
                        'direction':     'LONG' if lng else 'SHORT',
                        'strategy':      'M15_SCALP',
                        'entry_date':    position['entry_date'],
                        'exit_date':     ts,
                        'entry_price':   ep,
                        'exit_price':    px,
                        'pnl_pct':       pnl,
                        'bars_held':     bars,
                        'size':          position['size'],
                        'exit_reason':   why,
                        'daily_z':       position['daily_z'],
                        'h1_z':          position['m15_z'],
                        'h1_atr':        av,
                        'vol_percentile': position['vol_pct'],
                        'session':       position['session'],
                        'hour_utc':      position['entry_hour'],
                    }
                    # INFRA-03 / D-10..D-13 — same hook as swing site, m15 cfg keys.
                    rec['strategy_type'] = 'M15_SCALP'
                    rec['params_json'] = json.dumps({
                        'm15_z_threshold': cfg.m15_z_threshold,
                        'm15_target_atr':  cfg.m15_target_atr,
                        'm15_stop_atr':    cfg.m15_stop_atr,
                        'm15_size_mult':   cfg.m15_size_mult,
                        'm15_max_bars':    cfg.m15_max_bars,
                    })
                    trades.append(rec)
                    on_trade_close(rec)
                    position = None

            # ── ENTRY ─────────────────────────────────────────────────────────
            elif position is None and sess in ('LONDON', 'NY'):
                if (not pd.isna(m15z) and not pd.isna(atr) and atr > 0
                        and abs(m15z) > cfg.m15_z_threshold
                        and not (self.enable_changepoint and cp == 1)
                        and not (self.enable_hurst_filter and hv > 0.55)):

                    # Direction alignment filter
                    # daily oversold (dz<-1.5) → only M15_SCALP_LONG (m15z<0)
                    # daily overbought (dz>+1.5) → only M15_SCALP_SHORT (m15z>0)
                    # daily neutral → allow both
                    dz_safe = dz if not pd.isna(dz) else 0.0
                    aligned = (
                        abs(dz_safe) < 1.5
                        or (dz_safe < -1.5 and m15z < 0)
                        or (dz_safe >  1.5 and m15z > 0)
                    )
                    if not aligned:
                        continue

                    pt  = 'M15_SCALP_LONG' if m15z < 0 else 'M15_SCALP_SHORT'
                    sz  = cfg.m15_size_mult
                    rm  = self._rag_size_modifier(symbol, pt, sess, dz_safe, m15z, vpct, hour)
                    if rm > 0:
                        # BKTS-01 (D-01): next-bar open fill — see .planning/phases/07-.../07-CONTEXT.md
                        entry_px = next_row['Open']
                        position = {
                            'type':        pt,
                            'entry_price': entry_px,
                            'entry_date':  ts,
                            'entry_bar':   i,
                            'entry_hour':  hour,
                            'atr_entry':   atr,
                            'size':        sz * rm,
                            'daily_z':     dz_safe,
                            'm15_z':       m15z,
                            'vol_pct':     vpct,
                            'session':     sess,
                        }

        return pd.DataFrame(trades) if trades else pd.DataFrame()

    # ─────────────────────────────────────────────────────────────────────────
    # RUN METHODS  (call independently or together)
    # ─────────────────────────────────────────────────────────────────────────

    def run_swing(self):
        """Run daily swing strategy only. Returns trades DataFrame."""
        print("\n" + "█"*90)
        print("█" + "  MARKETMIND V2 — DAILY SWING STRATEGY  [H1 Execution]".center(88) + "█")
        print("█"*90)
        print(f"  Change-Point Filter: {'ON' if self.enable_changepoint else 'OFF'}")
        print(f"  Hurst Regime Filter: {'ON (H>0.55 blocks entry)' if self.enable_hurst_filter else 'OFF'}")
        print(f"  RAG: {'ACTIVE (' + str(self.rag.count) + ' trades)' if self.rag else 'WARMING UP'}\n")

        all_trades = []
        for sym in self.swing_symbols:
            daily = self._load_daily(sym)
            h1    = self._load_h1(sym)
            if daily is None or h1 is None:
                continue
            try:
                t = self._backtest_swing_symbol(sym, daily, h1)
                if len(t) > 0:
                    t['symbol'] = sym
                    all_trades.append(t)
            except Exception as e:
                print(f"  [swing] Error {sym}: {e}")

        df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()

        if len(df) > 0:
            if self.rag:
                self.rag.index_trades(df)
            self._print_report(df, "DAILY SWING STRATEGY")
            if self.logger:
                self.logger.print_summary()
        else:
            print("  No swing trades generated.")

        return df

    def run_m15(self):
        """Run M15 intraday scalp strategy only. Returns trades DataFrame."""
        print("\n" + "█"*90)
        print("█" + "  MARKETMIND V2 — M15 INTRADAY SCALP  [Independent Strategy]".center(88) + "█")
        print("█"*90)
        print(f"  Capital note: Requires IC Markets RAW account (1:100 leverage).")
        print(f"  Spread cost at raw: ~0.1-0.3 pips vs 0.5-0.8 pips standard.")
        print(f"  Change-Point Filter: {'ON' if self.enable_changepoint else 'OFF'}")
        print(f"  Hurst Regime Filter: {'ON (H>0.55 blocks entry)' if self.enable_hurst_filter else 'OFF'}")
        print(f"  RAG: {'ACTIVE (' + str(self.rag.count) + ' trades)' if self.rag else 'WARMING UP'}\n")

        all_trades = []
        for sym in self.m15_symbols:
            daily = self._load_daily(sym)
            m15   = self._load_m15(sym)
            if daily is None or m15 is None:
                print(f"  [m15] Missing data for {sym} — run scripts/download_intraday_data.py")
                continue
            try:
                t = self._backtest_m15_symbol(sym, daily, m15)
                if len(t) > 0:
                    t['symbol'] = sym
                    all_trades.append(t)
            except Exception as e:
                print(f"  [m15] Error {sym}: {e}")

        df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()

        if len(df) > 0:
            self._print_report(df, "M15 INTRADAY SCALP")
        else:
            print("  No M15 trades generated.")

        return df

    def run(self):
        """Run both strategies independently, then show combined capital view."""
        swing_df = self.run_swing()
        m15_df   = self.run_m15()
        self._print_combined_summary(swing_df, m15_df)
        return swing_df, m15_df

    def index_rag_history(self):
        """One-time step: seed ChromaDB from existing swing history."""
        if not self.rag:
            print("RAG not available.")
            return
        all_trades = []
        for sym in self.swing_symbols:
            daily = self._load_daily(sym)
            h1    = self._load_h1(sym)
            if daily is None or h1 is None:
                continue
            t = self._backtest_swing_symbol(sym, daily, h1)
            if len(t) > 0:
                t['symbol'] = sym
                all_trades.append(t)
        df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        if len(df) == 0:
            print("No trades to index.")
            return
        self.rag.index_trades(df)
        print(f"RAG index updated: {self.rag.count} trades.")

    # ─────────────────────────────────────────────────────────────────────────
    # ENHANCED REPORTING
    # ─────────────────────────────────────────────────────────────────────────

    def _emit(self, line: str = ""):
        """Print to stdout and append to the in-memory report buffer."""
        print(line)
        self._report_buffer.append(line)

    def _save_report(self, label: str, trades_df: pd.DataFrame):
        """Write buffered report text + per-trade CSV to reports/ directory."""
        ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        slug = label.lower().replace(' ', '_').replace('/', '-')

        txt_path = self.reports_dir / f"{slug}_{ts}.txt"
        txt_path.write_text('\n'.join(self._report_buffer), encoding='utf-8')
        print(f"  [saved] {txt_path}")

        if trades_df is not None and len(trades_df) > 0:
            csv_path = self.reports_dir / f"{slug}_{ts}_trades.csv"
            trades_df.to_csv(csv_path, index=False)
            print(f"  [saved] {csv_path}")

        self._report_buffer.clear()

    def _metrics(self, df):
        if df is None or len(df) == 0:
            return {}
        pnl    = df['pnl_pct']
        wins   = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        sharpe = pnl.mean() / pnl.std() * np.sqrt(252) if pnl.std() > 0 else 0.0

        # Max drawdown from cumulative P&L curve
        cum = pnl.cumsum()
        roll_max   = cum.cummax()
        drawdown   = cum - roll_max
        max_dd     = drawdown.min()

        # Consecutive win/loss streaks
        won       = (pnl > 0).astype(int).values
        max_wins  = max_losses = cur_wins = cur_losses = 0
        for w in won:
            if w:
                cur_wins   += 1; cur_losses = 0
            else:
                cur_losses += 1; cur_wins   = 0
            max_wins   = max(max_wins,   cur_wins)
            max_losses = max(max_losses, cur_losses)

        return {
            'trades':       len(df),
            'win_pct':      len(wins) / len(df) * 100,
            'total_pnl':    pnl.sum() * 100,
            'avg_pnl':      pnl.mean() * 100,
            'sharpe':       sharpe,
            'avg_bars':     df['bars_held'].mean(),
            'avg_win':      wins.mean() * 100  if len(wins)   > 0 else 0.0,
            'avg_loss':     losses.mean() * 100 if len(losses) > 0 else 0.0,
            'win_loss_ratio': abs(wins.mean() / losses.mean()) if len(wins) > 0 and len(losses) > 0 else 0.0,
            'best_trade':   pnl.max() * 100,
            'worst_trade':  pnl.min() * 100,
            'max_dd':       max_dd * 100,
            'max_con_wins': max_wins,
            'max_con_loss': max_losses,
            'expectancy':   (len(wins) / len(df)) * wins.mean() + (len(losses) / len(df)) * losses.mean()
                            if len(wins) > 0 and len(losses) > 0 else 0.0,
        }

    def _print_report(self, df, title):
        W = 100
        run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._emit(f"\n  Report generated: {run_ts}")
        self._emit("\n" + "="*W)
        self._emit(f"  {title} — RESULTS BY PAIR")
        self._emit("="*W)

        header = (f"  {'Pair':8} {'Tier':5} {'Trades':7} {'Win%':6} {'TotalPnL':10} "
                  f"{'AvgTrade':9} {'W/L Ratio':10} {'Sharpe':7} {'AvgBars':8}")
        self._emit(header)
        self._emit("-"*W)
        for sym in (self.swing_symbols if 'SWING' in title else self.m15_symbols):
            if 'symbol' in df.columns:
                st = df[df['symbol'] == sym]
            else:
                continue
            if len(st) == 0:
                continue
            cfg  = get_pair_config(sym)
            m    = self._metrics(st)
            wl   = f"{m['win_loss_ratio']:.2f}" if m['win_loss_ratio'] > 0 else "N/A"
            self._emit(f"  {sym:8} [T{cfg.tier}]  "
                       f"{m['trades']:7}  {m['win_pct']:5.1f}%  "
                       f"{m['total_pnl']:+9.2f}%  {m['avg_pnl']:+8.3f}%  "
                       f"{wl:>9}  {m['sharpe']:6.2f}  {m['avg_bars']:7.1f}")

        # ── Buy vs Sell distribution per pair ────────────────────────────────
        self._emit("\n" + "="*W)
        self._emit(f"  {title} — BUY / SELL DISTRIBUTION")
        self._emit("="*W)
        self._emit(f"  {'Pair':8} {'Long Trades':12} {'Long PnL':10} {'Short Trades':13} {'Short PnL':10} {'Net Bias':10}")
        self._emit("-"*W)
        for sym in (self.swing_symbols if 'SWING' in title else self.m15_symbols):
            st = df[df['symbol'] == sym] if 'symbol' in df.columns else pd.DataFrame()
            if len(st) == 0:
                continue
            longs  = st[st['direction'] == 'LONG']
            shorts = st[st['direction'] == 'SHORT']
            l_pnl  = longs['pnl_pct'].sum() * 100  if len(longs)  > 0 else 0.0
            s_pnl  = shorts['pnl_pct'].sum() * 100 if len(shorts) > 0 else 0.0
            bias   = "LONG BIAS" if len(longs) > len(shorts) else ("SHORT BIAS" if len(shorts) > len(longs) else "NEUTRAL")
            self._emit(f"  {sym:8} {len(longs):5} ({len(longs)/len(st)*100:4.0f}%)   "
                       f"{l_pnl:+9.2f}%  "
                       f"{len(shorts):6} ({len(shorts)/len(st)*100:4.0f}%)   "
                       f"{s_pnl:+9.2f}%  {bias}")

        # ── Session breakdown ─────────────────────────────────────────────────
        self._emit("\n" + "="*W)
        self._emit(f"  {title} — SESSION BREAKDOWN")
        self._emit("="*W)
        self._emit(f"  {'Session':10} {'Trades':7} {'Win%':7} {'TotalPnL':10} {'AvgTrade':10} {'W/L Ratio':10}")
        self._emit("-"*W)
        for sess in ['LONDON', 'NY', 'OFF']:
            sg = df[df['session'] == sess] if 'session' in df.columns else pd.DataFrame()
            if len(sg) == 0:
                continue
            m = self._metrics(sg)
            wl = f"{m['win_loss_ratio']:.2f}" if m['win_loss_ratio'] > 0 else "N/A"
            self._emit(f"  {sess:10} {m['trades']:7}  {m['win_pct']:5.1f}%  "
                       f"{m['total_pnl']:+9.2f}%  {m['avg_pnl']:+9.3f}%  {wl:>9}")

        # ── Exit reason breakdown ─────────────────────────────────────────────
        self._emit("\n" + "="*W)
        self._emit(f"  {title} — EXIT BREAKDOWN")
        self._emit("="*W)
        self._emit(f"  {'Exit':10} {'Count':7} {'Win%':7} {'AvgPnL':9} {'TotalPnL':10} {'AvgBars':8}")
        self._emit("-"*W)
        if 'exit_reason' in df.columns:
            for reason, grp in df.groupby('exit_reason'):
                m = self._metrics(grp)
                self._emit(f"  {reason:10} {m['trades']:7}  {m['win_pct']:5.1f}%  "
                           f"{m['avg_pnl']:+8.3f}%  {m['total_pnl']:+9.2f}%  {m['avg_bars']:7.1f}")

        # ── Portfolio summary ─────────────────────────────────────────────────
        m = self._metrics(df)
        self._emit("\n" + "="*W)
        self._emit(f"  {title} — PORTFOLIO SUMMARY")
        self._emit("="*W)
        self._emit(f"  Total Trades:          {m['trades']}")
        self._emit(f"  Win Rate:              {m['win_pct']:.1f}%")
        self._emit(f"  Win / Loss Ratio:      {m['win_loss_ratio']:.3f}  "
                   f"(avg win {m['avg_win']:+.3f}% / avg loss {m['avg_loss']:+.3f}%)")
        self._emit(f"  Trade Expectancy:      {m['expectancy']*100:+.4f}% per trade")
        self._emit(f"  Total Portfolio P&L:   {m['total_pnl']:+.2f}%")
        self._emit(f"  Avg P&L per Trade:     {m['avg_pnl']:+.3f}%")
        self._emit(f"  Best Trade:            {m['best_trade']:+.3f}%")
        self._emit(f"  Worst Trade:           {m['worst_trade']:+.3f}%")
        self._emit(f"  Max Drawdown:          {m['max_dd']:+.2f}%")
        self._emit(f"  Sharpe Ratio:          {m['sharpe']:.2f}")
        self._emit(f"  Avg Bars Held:         {m['avg_bars']:.0f}")
        self._emit(f"  Max Consecutive Wins:  {m['max_con_wins']}")
        self._emit(f"  Max Consecutive Losses:{m['max_con_loss']}")
        self._emit("="*W + "\n")

        # ── Capital projection: $200 account at 1:100 leverage, IC Raw ───────
        self._emit(f"  CAPITAL PROJECTION — $200 IC Markets Raw (1:100 leverage):")
        self._emit(f"  Assumption: 0.01 lots, 2% risk per swing / 1.5% risk per M15 scalp")
        ann_rate  = m['total_pnl'] / 100
        m1_est    = 200 * (1 + ann_rate / 12)
        m3_est    = 200 * (1 + ann_rate / 4)
        m12_est   = 200 * (1 + ann_rate)
        self._emit(f"  Projected month 1:  ${m1_est:7.0f}   |  Month 3: ${m3_est:7.0f}   |  Month 12: ${m12_est:7.0f}")

        m15_note = "" if (self.data_dir / "GBPUSD_M15.csv").exists() else \
                   "  NOTE: M15 history = 60 days (yfinance). Run fetch_data.py for full history."
        if m15_note:
            self._emit(m15_note)
        self._emit("")

        self._save_report(title, df)

    def _print_combined_summary(self, swing_df, m15_df):
        W = 100
        self._emit("\n" + "█"*W)
        self._emit("█" + "  COMBINED CAPITAL VIEW — Swing + M15 Running Independently".center(W-2) + "█")
        self._emit("█"*W)
        s = self._metrics(swing_df) if len(swing_df) > 0 else {}
        m = self._metrics(m15_df)  if len(m15_df)  > 0 else {}

        self._emit(f"\n  {'Strategy':20} {'Trades':8} {'Win%':7} {'TotalPnL':11} {'Sharpe':8} {'W/L Ratio':10} {'MaxDD':8}")
        self._emit("-"*W)
        if s:
            wl = f"{s['win_loss_ratio']:.2f}" if s.get('win_loss_ratio', 0) > 0 else "N/A"
            self._emit(f"  {'Daily Swing':20} {s['trades']:8} {s['win_pct']:5.1f}%  "
                       f"{s['total_pnl']:+10.2f}%  {s['sharpe']:7.2f}  {wl:>9}  {s['max_dd']:+7.2f}%")
        if m:
            wl = f"{m['win_loss_ratio']:.2f}" if m.get('win_loss_ratio', 0) > 0 else "N/A"
            self._emit(f"  {'M15 Intraday Scalp':20} {m['trades']:8} {m['win_pct']:5.1f}%  "
                       f"{m['total_pnl']:+10.2f}%  {m['sharpe']:7.2f}  {wl:>9}  {m['max_dd']:+7.2f}%")

        total_trades = s.get('trades', 0) + m.get('trades', 0)
        total_pnl    = s.get('total_pnl', 0) + m.get('total_pnl', 0)
        self._emit("-"*W)
        self._emit(f"  {'COMBINED':20} {total_trades:8}  {'---':5}   {total_pnl:+10.2f}%  {'---':>7}  {'---':>9}  {'---':>7}%")
        self._emit("="*W + "\n")

        combined_df = pd.concat([swing_df, m15_df], ignore_index=True) if (len(swing_df) > 0 and len(m15_df) > 0) else \
                      swing_df if len(swing_df) > 0 else m15_df
        self._save_report("combined", combined_df)


if __name__ == "__main__":
    import sys as _sys
    data_dir = "/home/user/Desktop/Bandd Analytics/BA PRJ - Helix/V2/data"
    args     = _sys.argv[1:]

    bt = HybridMultiTimeframeBacktest(
        data_dir,
        enable_rag=("--no-rag" not in args),
        enable_logging=("--no-log" not in args),
        enable_changepoint=True,
        enable_hurst_filter=("--hurst" in args),
    )

    if "--index-rag" in args:
        bt.index_rag_history()
    elif "--swing" in args:
        bt.run_swing()
    elif "--m15" in args:
        bt.run_m15()
    else:
        # Default: run both strategies independently
        bt.run()

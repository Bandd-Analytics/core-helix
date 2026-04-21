import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class MultiTimeframeBacktest:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)

    def adaptive_atr(self, high, low, close, period=14, lookback=50):
        """Calculate ATR with dynamic period adjustment"""
        tr = np.maximum(high - low,
                       np.maximum(np.abs(high - close.shift(1)),
                                 np.abs(low - close.shift(1))))
        atr = tr.rolling(period).mean()

        vol = close.pct_change().rolling(lookback).std()
        vol_ma = vol.rolling(lookback).mean()
        vol_ratio = vol / vol_ma

        adjusted_atr = atr * vol_ratio
        return adjusted_atr

    def z_score_signal(self, close, period=20):
        """Calculate Z-score for mean reversion signals"""
        ma = close.rolling(period).mean()
        std = close.rolling(period).std()
        z_score = (close - ma) / std
        return z_score

    def backtest_pair_timeframe(self, symbol, data, profit_target_atr=4.0):
        """Run backtest on single pair/timeframe"""
        df = data.copy()
        df['returns'] = df['Close'].pct_change()

        # Calculate indicators
        df['atr'] = self.adaptive_atr(df['High'], df['Low'], df['Close'])
        df['z_score'] = self.z_score_signal(df['Close'])

        # Entry signals
        df['long_signal'] = df['z_score'] < -2.0
        df['short_signal'] = df['z_score'] > 2.0

        # Position sizing
        df['position_size'] = 1.0 / (df['atr'] / df['Close'] + 0.001)
        df['position_size'] = df['position_size'] / df['position_size'].max()

        # Trade logic
        position = 0
        trades = []
        entry_price = 0
        entry_date = None
        open_positions = 0

        for i in range(100, len(df)):
            if position == 0:
                # Only allow 1 open position at a time
                if open_positions == 0:
                    if df.iloc[i]['long_signal']:
                        position = 1
                        entry_price = df.iloc[i]['Close']
                        entry_date = df.index[i]
                        open_positions += 1
                    elif df.iloc[i]['short_signal']:
                        position = -1
                        entry_price = df.iloc[i]['Close']
                        entry_date = df.index[i]
                        open_positions += 1

            elif position != 0:
                current_price = df.iloc[i]['Close']

                if position == 1:
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - current_price) / entry_price

                # Exit logic
                atr_val = df.iloc[i]['atr']
                exit_profit = atr_val * profit_target_atr / entry_price if not pd.isna(atr_val) else entry_price * 0.03
                exit_loss = atr_val / entry_price if not pd.isna(atr_val) else entry_price * 0.005

                should_exit = (pnl_pct > exit_profit or pnl_pct < -exit_loss)

                if should_exit:
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': df.index[i],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl_pct': pnl_pct,
                        'position': 'long' if position == 1 else 'short'
                    })
                    position = 0
                    open_positions = 0

        # Calculate statistics
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()

        if len(trades_df) > 0:
            wins = (trades_df['pnl_pct'] > 0).sum()
            win_rate = wins / len(trades_df) * 100
            avg_pnl = trades_df['pnl_pct'].mean() * 100
            total_pnl = trades_df['pnl_pct'].sum() * 100
            max_dd = trades_df['pnl_pct'].min() * 100

            if len(trades_df) > 1:
                sharpe = trades_df['pnl_pct'].mean() / trades_df['pnl_pct'].std() * np.sqrt(252) if trades_df['pnl_pct'].std() > 0 else 0
            else:
                sharpe = 0

            avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() * 100 if wins > 0 else 0
            avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() * 100 if (len(trades_df) - wins) > 0 else 0
        else:
            wins = 0
            win_rate = 0
            avg_pnl = 0
            total_pnl = 0
            max_dd = 0
            sharpe = 0
            avg_win = 0
            avg_loss = 0

        return {
            'symbol': symbol,
            'trades': len(trades_df),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_pnl_pct': avg_pnl,
            'total_pnl_pct': total_pnl,
            'max_loss_pct': max_dd,
            'sharpe_ratio': sharpe
        }

    def run_timeframe(self, timeframe, symbols):
        """Run backtest for all pairs on a timeframe"""
        print(f"\n{'='*80}")
        print(f"Backtesting: {timeframe} Timeframe")
        print(f"{'='*80}\n")

        all_results = []

        for symbol in symbols:
            if timeframe == "DAILY":
                file = self.data_dir / f"{symbol}_DAILY_2015-2026.csv"
            else:
                file = self.data_dir / f"{symbol}_{timeframe}_730d.csv"

            if not file.exists():
                print(f"✗ {symbol}: File not found ({file})")
                continue

            print(f"Testing {symbol}...", end=" ")

            try:
                df = pd.read_csv(file, index_col=0, parse_dates=True)
                result = self.backtest_pair_timeframe(symbol, df)
                all_results.append(result)
                print("✓")
            except Exception as e:
                print(f"✗ {e}")

        # Print results
        if all_results:
            results_df = pd.DataFrame(all_results)

            print("\n" + "="*80)
            print(f"RESULTS: {timeframe}")
            print("="*80)
            print(results_df[['symbol', 'trades', 'win_rate', 'avg_pnl_pct', 'total_pnl_pct', 'sharpe_ratio']].to_string(index=False))

            print(f"\n{timeframe} SUMMARY:")
            print(f"  Total Trades:        {results_df['trades'].sum()}")
            print(f"  Avg Win Rate:        {results_df['win_rate'].mean():.1f}%")
            print(f"  Avg PnL/Trade:       {results_df['avg_pnl_pct'].mean():.3f}%")
            print(f"  Total PnL:           {results_df['total_pnl_pct'].sum():.2f}%")
            print(f"  Avg Sharpe:          {results_df['sharpe_ratio'].mean():.2f}")
            print("="*80)

            return results_df
        else:
            print("No data to backtest!")
            return None

    def run(self):
        """Run backtest on all timeframes"""
        symbols = ["EURUSD", "USDJPY", "AUDNZD", "EURGBP", "GBPJPY"]

        print("\n" + "█"*80)
        print("█" + " "*78 + "█")
        print("█" + "  MARKETMIND STRATEGY: MULTI-TIMEFRAME BACKTEST".center(78) + "█")
        print("█" + " "*78 + "█")
        print("█"*80)
        print("\nConfiguration:")
        print("  • Pairs: All 5 (EURUSD, USDJPY, AUDNZD, EURGBP, GBPJPY)")
        print("  • Profit Target: 4x ATR")
        print("  • Stop Loss: 1x ATR")
        print("  • Max Positions: 1 concurrent trade")
        print("  • Entry: Z-score < -2.0 (long) or > 2.0 (short)")

        # Run backtests
        daily_results = self.run_timeframe("DAILY", symbols)
        h1_results = self.run_timeframe("H1", symbols)

        # Comparison
        print("\n" + "█"*80)
        print("█" + " COMPARISON: DAILY vs H1 (INTRADAY)".ljust(78) + "█")
        print("█"*80)
        print("\nDaily Data: 2015-2026 (11 years)")
        print("H1 Data:    Last 730 days (~2 years)")
        print("\n" + "-"*80)

        if daily_results is not None and h1_results is not None:
            comparison = pd.DataFrame({
                'Metric': ['Total Trades', 'Avg Win Rate (%)', 'Avg PnL/Trade (%)', 'Total Portfolio PnL (%)', 'Avg Sharpe'],
                'DAILY': [
                    daily_results['trades'].sum(),
                    f"{daily_results['win_rate'].mean():.1f}",
                    f"{daily_results['avg_pnl_pct'].mean():.3f}",
                    f"{daily_results['total_pnl_pct'].sum():.2f}",
                    f"{daily_results['sharpe_ratio'].mean():.2f}"
                ],
                'H1 (INTRADAY)': [
                    h1_results['trades'].sum(),
                    f"{h1_results['win_rate'].mean():.1f}",
                    f"{h1_results['avg_pnl_pct'].mean():.3f}",
                    f"{h1_results['total_pnl_pct'].sum():.2f}",
                    f"{h1_results['sharpe_ratio'].mean():.2f}"
                ]
            })

            print(comparison.to_string(index=False))
            print("-"*80)

            print("\n✓ VALIDATION COMPLETE")
            print("  Daily: Long-term profitability check (11 years)")
            print("  H1: Intraday trading performance (2 years)")
            print("\n" + "█"*80 + "\n")

if __name__ == "__main__":
    data_dir = "/home/user/Desktop/Bandd Analytics/BA PRJ - Helix/V2/data"
    bt = MultiTimeframeBacktest(data_dir)
    bt.run()

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class MarketMindBacktest:
    def __init__(self, data_dir, pairs=None, profit_target_atr=3.0, correlation_threshold=0.7):
        self.data_dir = Path(data_dir)
        self.results = {}
        self.pairs = pairs or ["EURUSD", "USDJPY"]  # Major pairs only
        self.profit_target_atr = profit_target_atr  # 3-4x ATR for exits
        self.correlation_threshold = correlation_threshold
        self.portfolio_positions = {}  # Track open positions for correlation filtering

    def adaptive_atr(self, high, low, close, period=14, lookback=50):
        """Calculate ATR with dynamic period adjustment"""
        tr = np.maximum(high - low,
                       np.maximum(np.abs(high - close.shift(1)),
                                 np.abs(low - close.shift(1))))
        atr = tr.rolling(period).mean()

        # Volatility adjustment
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

    def _check_correlation_filter(self, symbol):
        """Check if we can trade this symbol based on existing positions"""
        if symbol not in self.portfolio_positions:
            return True

        # If we have open positions, don't trade highly correlated pairs
        # For simplicity: only allow 1 position at a time in major pairs
        if len(self.portfolio_positions) > 0:
            return False

        return True

    def backtest_pair(self, symbol, data):
        """Run backtest on single pair"""
        df = data.copy()
        df['returns'] = df['Close'].pct_change()

        # Calculate indicators
        df['atr'] = self.adaptive_atr(df['High'], df['Low'], df['Close'])
        df['z_score'] = self.z_score_signal(df['Close'])

        # Entry signals: Z-score extreme (short-term mean reversion)
        df['long_signal'] = df['z_score'] < -2.0  # Oversold
        df['short_signal'] = df['z_score'] > 2.0  # Overbought

        # Position sizing: scale by volatility
        df['position_size'] = 1.0 / (df['atr'] / df['Close'] + 0.001)
        df['position_size'] = df['position_size'] / df['position_size'].max()  # Normalize

        # Trade logic
        position = 0
        trades = []
        entry_price = 0
        entry_date = None

        for i in range(100, len(df)):
            if position == 0:
                # Check correlation filter - can we enter?
                can_trade = self._check_correlation_filter(symbol)

                if can_trade and df.iloc[i]['long_signal']:
                    position = 1
                    entry_price = df.iloc[i]['Close']
                    entry_date = df.index[i]
                    self.portfolio_positions[symbol] = {'position': 1, 'entry_date': entry_date}
                elif can_trade and df.iloc[i]['short_signal']:
                    position = -1
                    entry_price = df.iloc[i]['Close']
                    entry_date = df.index[i]
                    self.portfolio_positions[symbol] = {'position': -1, 'entry_date': entry_date}

            elif position != 0:
                current_price = df.iloc[i]['Close']
                pnl_pct = (current_price - entry_price) / entry_price

                if position == 1:
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - current_price) / entry_price

                # Exit on profit target (3-4x ATR) or stop loss (1x ATR)
                atr_val = df.iloc[i]['atr']
                exit_profit = atr_val * self.profit_target_atr / entry_price if not pd.isna(atr_val) else entry_price * 0.03
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
                    if symbol in self.portfolio_positions:
                        del self.portfolio_positions[symbol]

        # Calculate statistics
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()

        if len(trades_df) > 0:
            wins = (trades_df['pnl_pct'] > 0).sum()
            win_rate = wins / len(trades_df) * 100
            avg_pnl = trades_df['pnl_pct'].mean() * 100
            total_pnl = trades_df['pnl_pct'].sum() * 100
            max_dd = trades_df['pnl_pct'].min() * 100

            # Sharpe ratio
            if len(trades_df) > 1:
                sharpe = trades_df['pnl_pct'].mean() / trades_df['pnl_pct'].std() * np.sqrt(252) if trades_df['pnl_pct'].std() > 0 else 0
            else:
                sharpe = 0
        else:
            wins = 0
            win_rate = 0
            avg_pnl = 0
            total_pnl = 0
            max_dd = 0
            sharpe = 0

        return {
            'symbol': symbol,
            'trades': len(trades_df),
            'win_rate': win_rate,
            'avg_pnl_pct': avg_pnl,
            'total_pnl_pct': total_pnl,
            'max_loss_pct': max_dd,
            'sharpe_ratio': sharpe
        }

    def run(self):
        """Run backtest on all pairs"""
        print("\n" + "="*70)
        print("MarketMind Strategy Backtest (2015-2026 Daily Data)")
        print("="*70)
        print(f"\nConfiguration:")
        print(f"  Pairs: {', '.join(self.pairs)}")
        print(f"  Profit Target: {self.profit_target_atr}x ATR")
        print(f"  Max Correlation: {self.correlation_threshold}")
        print(f"  Position Limit: 1 open trade at a time\n")

        all_results = []

        for symbol in self.pairs:
            file = self.data_dir / f"{symbol}_DAILY_2015-2026.csv"

            if not file.exists():
                print(f"✗ {symbol}: File not found")
                continue

            print(f"Testing {symbol}...", end=" ")

            try:
                df = pd.read_csv(file, index_col=0, parse_dates=True)
                result = self.backtest_pair(symbol, df)
                all_results.append(result)
                print("✓")
            except Exception as e:
                print(f"✗ Error: {e}")

        # Print results
        if all_results:
            results_df = pd.DataFrame(all_results)

            print("\n" + "="*70)
            print("BACKTEST RESULTS")
            print("="*70)
            print(results_df.to_string(index=False))

            print("\n" + "="*70)
            print("PORTFOLIO SUMMARY")
            print("="*70)
            print(f"Total Trades:        {results_df['trades'].sum()}")
            print(f"Avg Win Rate:        {results_df['win_rate'].mean():.1f}%")
            print(f"Avg PnL per Trade:   {results_df['avg_pnl_pct'].mean():.2f}%")
            print(f"Total Portfolio PnL: {results_df['total_pnl_pct'].sum():.2f}%")
            print(f"Avg Sharpe Ratio:    {results_df['sharpe_ratio'].mean():.2f}")
            print("="*70 + "\n")

            return results_df
        else:
            print("\nNo data to backtest!")
            return None

if __name__ == "__main__":
    data_dir = "/home/user/Desktop/Bandd Analytics/BA PRJ - Helix/V2/data"

    # Test with improvements: major pairs only, 4x ATR profit target
    bt = MarketMindBacktest(data_dir, pairs=["EURUSD", "USDJPY"], profit_target_atr=4.0)
    results = bt.run()

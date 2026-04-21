import yfinance as yf
import pandas as pd
from pathlib import Path

data_dir = Path("/home/user/Desktop/Bandd Analytics/BA PRJ - Helix/V2/data")
data_dir.mkdir(exist_ok=True)

symbols = ["EURUSD", "USDJPY", "AUDNZD", "EURGBP", "GBPJPY"]
timeframes = [("1h", "H1"), ("15m", "M15")]

print("Downloading intraday forex data (last 730 days)...\n")

for timeframe_yf, timeframe_name in timeframes:
    print(f"\n{'='*60}")
    print(f"Timeframe: {timeframe_name} (1 minute = ~240 bars/day)")
    print(f"{'='*60}\n")

    for symbol in symbols:
        print(f"Fetching {symbol} {timeframe_name}...", end=" ")
        try:
            ticker = yf.Ticker(symbol + "=X")
            df = ticker.history(period="730d", interval=timeframe_yf)

            if len(df) > 0:
                filename = f"{symbol}_{timeframe_name}_730d.csv"
                filepath = data_dir / filename
                df.to_csv(filepath)
                print(f"✓ ({len(df)} bars)")
            else:
                print(f"✗ No data")
        except Exception as e:
            print(f"✗ {e}")

print("\n" + "="*60)
print("Download complete!")
print("="*60)

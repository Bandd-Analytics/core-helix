import yfinance as yf
import pandas as pd
from pathlib import Path

data_dir = Path("/home/user/Desktop/Bandd Analytics/BA PRJ - Helix/V2/data")
data_dir.mkdir(exist_ok=True)

# New pairs to download
new_pairs = ["GBPUSD", "GBPAUD", "GBPNZD"]

print("Downloading daily forex data (2015-2026) for new pairs...\n")

for symbol in new_pairs:
    print(f"Fetching {symbol} DAILY...", end=" ")
    try:
        ticker = yf.Ticker(symbol + "=X")
        df = ticker.history(period="max", interval="1d")
        
        if len(df) > 0:
            filename = f"{symbol}_DAILY_2015-2026.csv"
            filepath = data_dir / filename
            df.to_csv(filepath)
            print(f"✓ ({len(df)} bars)")
        else:
            print(f"✗ No data")
    except Exception as e:
        print(f"✗ {e}")

print("\nDownloading H1 forex data (last 730 days) for new pairs...\n")

for symbol in new_pairs:
    print(f"Fetching {symbol} H1...", end=" ")
    try:
        ticker = yf.Ticker(symbol + "=X")
        df = ticker.history(period="730d", interval="1h")
        
        if len(df) > 0:
            filename = f"{symbol}_H1_730d.csv"
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

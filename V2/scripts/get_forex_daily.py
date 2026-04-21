import yfinance as yf
import pandas as pd

symbols = ["EURUSD", "USDJPY", "AUDNZD", "EURGBP", "GBPJPY"]

print("Downloading daily forex data from yfinance (2015-2026)...\n")

for symbol in symbols:
    print(f"Fetching {symbol}...")
    try:
        ticker = yf.Ticker(symbol + "=X")
        df = ticker.history(start="2015-01-01", end="2026-04-20")

        if len(df) > 0:
            filename = f"{symbol}_DAILY_2015-2026.csv"
            df.to_csv(filename)
            print(f"  ✓ {filename} ({len(df)} bars)\n")
        else:
            print(f"  ✗ No data returned\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")

print("Done!")

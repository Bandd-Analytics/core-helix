import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# Initialize MT5
if not mt5.initialize():
    print("MT5 init failed")
    exit()

symbols = ["EURUSD", "USDJPY", "AUDNZD", "EURGBP", "GBPJPY"]
start_date = datetime(2015, 1, 1)
end_date = datetime(2026, 4, 20)

for symbol in symbols:
    print(f"\nDownloading {symbol}...")

    # Download H1 data
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start_date, end_date)

    if rates is None or len(rates) == 0:
        print(f"  Failed: {mt5.last_error()}")
        continue

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')

    filename = f"{symbol}_H1_2015-2026.csv"
    df.to_csv(filename, index=False)
    print(f"  ✓ Saved {len(df)} bars → {filename}")

mt5.shutdown()
print("\nDone!")

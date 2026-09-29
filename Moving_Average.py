import time
import MetaTrader5 as mt5
import pandas as pd

# ---------------------Constants---------------------#
SYMBOL = "EURUSD"
MA_TIMEFRAME = mt5.TIMEFRAME_M5  # Timeframe to check moving average on
MA_PERIOD = 5  # Moving average period
MA_PRICE = "close"  # MT5 columns are lowercase: 'open', 'high', 'low', 'close'
POLL_INTERVAL = 5  # Seconds between tick checks
# --------------------XXXXXXXXX---------------------#


def init() -> bool:
  if not mt5.initialize():
    print("Failed to initialize Metatrader5 connection!!!")
    return False

  if not mt5.symbol_select(SYMBOL, True):
    print(f"Failed to select symbol: {SYMBOL}")
    return False

  print(
      f"MetaTrader5 connection is initialized and symbol {SYMBOL} ({MA_PERIOD} -"
      " SMA on Minutes=5) is selected!!!"
  )
  print("-" * 50)
  return True


def loop() -> bool:
  # Pull MA_PERIOD + 1 to ensure enough historical bars for the calculation
  rates = mt5.copy_rates_from_pos(SYMBOL, MA_TIMEFRAME, 0, MA_PERIOD + 1)

  if rates is None or len(rates) == 0:
    print("Warning: Failed to retrieve rates from broker. Retrying...")
    return True

  df = pd.DataFrame(rates)

  # Calculate Simple Moving Average (SMA)
  df["MA"] = df[MA_PRICE].rolling(MA_PERIOD).mean()

  # Get the most recent calculated MA value
  current_ma = df["MA"].iloc[-1]

  print(f"[{SYMBOL}] Latest {MA_PERIOD}-SMA: {current_ma:.5f}")
  return True


def deinit():
  mt5.shutdown()
  print("MetaTrader5 connection is closed!!!")


def main():
  if not init():
    deinit()
    return

  try:
    while loop():
      time.sleep(POLL_INTERVAL)
  except KeyboardInterrupt:
    print("\nProcess interrupted by user!!!!")
  finally:
    deinit()


if __name__ == "__main__":
  main()

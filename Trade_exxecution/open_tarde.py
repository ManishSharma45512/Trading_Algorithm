import time
import MetaTrader5 as mt5


# --------------------- USER CONFIGURATION PROMPT ---------------------#
def get_user_configuration():
  print("Select Asset:")
  print("1. EURUSD")
  print("2. XAUUSD (Gold)")
  choice = input("Enter choice (1 or 2): ").strip()

  if choice == "1":
    symbol = "EURUSD"
    magic = 1001
    deviation = 20
    sl_prompt = "Enter Stop Loss distance in price (e.g., 0.0050 for 50 pips): "
    tp_prompt = (
        "Enter Take Profit distance in price (e.g., 0.0100 for 100 pips): "
    )
  elif choice == "2":
    symbol = "XAUUSD"
    magic = 1002
    deviation = 50
    sl_prompt = (
        "Enter Stop Loss distance in price (e.g., 15.0 for $15 move): "
    )
    tp_prompt = (
        "Enter Take Profit distance in price (e.g., 30.0 for $30 move): "
    )
  else:
    print("Invalid asset choice. Exiting...")
    exit()

  volume = float(input(f"Enter volume for {symbol} (minimum 0.01): "))

  print("Order Action: [1] BUY | [0] SELL")
  action_input = int(input("Enter order action: "))
  if action_input == 1:
    order_type = mt5.ORDER_TYPE_BUY
  elif action_input == 0:
    order_type = mt5.ORDER_TYPE_SELL
  else:
    print("Invalid action. Please enter 1 or 0.")
    exit()

  stop_loss = float(input(sl_prompt))
  take_profit = float(input(tp_prompt))

  return {
      "symbol": symbol,
      "volume": volume,
      "order_type": order_type,
      "magic": magic,
      "deviation": deviation,
      "stop_loss": stop_loss,
      "take_profit": take_profit,
  }


# --------------------- DETECT BROKER FILLING MODE ---------------------#
def get_filling_mode(symbol: str) -> int:
  """Detects which filling mode is supported by checking bitmask flags."""
  info = mt5.symbol_info(symbol)
  if info is None:
    return mt5.ORDER_FILLING_RETURN

  modes = info.filling_mode
  # modes bitmask: 1 = FOK, 2 = IOC
  if modes & 1:
    return mt5.ORDER_FILLING_FOK
  elif modes & 2:
    return mt5.ORDER_FILLING_IOC
  else:
    return mt5.ORDER_FILLING_RETURN


# Load configuration
config = get_user_configuration()
SYMBOL = config["symbol"]
VOLUME = config["volume"]
ORDER_TYPE = config["order_type"]
MAGIC = config["magic"]
DEVIATION = config["deviation"]
STOP_LOSS = config["stop_loss"]
TAKE_PROFIT = config["take_profit"]


# --------------------- INITIALIZATION ---------------------#
def init() -> bool:
  if not mt5.initialize():
    print("Failed to initialize MetaTrader 5 connection!")
    return False

  if not mt5.symbol_select(SYMBOL, True):
    print(f"Failed to select symbol: {SYMBOL}")
    return False

  print("-" * 55)
  print(f"MT5 Initialized. Target: {SYMBOL} | Lot: {VOLUME}")
  print("-" * 55)
  return True


# --------------------- TICK & ORDER EXECUTION ---------------------#
def loop() -> bool:
  price_info = mt5.symbol_info_tick(SYMBOL)
  if price_info is None:
    print(f"Failed to get tick info for {SYMBOL}. Retrying...")
    return True

  # Determine prices and accurate SL/TP depending on order direction
  if ORDER_TYPE == mt5.ORDER_TYPE_BUY:
    price = price_info.ask
    sl = price_info.bid - STOP_LOSS
    tp = price_info.bid + TAKE_PROFIT
  else:
    price = price_info.bid
    sl = price_info.ask + STOP_LOSS
    tp = price_info.ask - TAKE_PROFIT

  # Query the broker's supported filling policy dynamically
  filling_type = get_filling_mode(SYMBOL)

  request = {
      "action": mt5.TRADE_ACTION_DEAL,
      "symbol": SYMBOL,
      "volume": VOLUME,
      "type": ORDER_TYPE,
      "price": price,
      "sl": sl,
      "tp": tp,
      "deviation": DEVIATION,
      "magic": MAGIC,
      "comment": "Python Trade Dispatcher",
      "type_time": mt5.ORDER_TIME_GTC,
      "type_filling": filling_type,
  }

  print(f"Sending order request (filling: {filling_type}):\n{request}")
  result = mt5.order_send(request)

  if result.retcode != mt5.TRADE_RETCODE_DONE:
    print(f"Order failed! Return code: {result.retcode}")
    print(f"Full broker response: {result}")
    return False

  print(f"SUCCESS! Trade placed successfully: {result}")
  return False


# --------------------- CLEANUP ---------------------#
def deinit():
  mt5.shutdown()
  print("MetaTrader 5 connection closed.")


# --------------------- MAIN CONTROLLER ---------------------#
def main():
  if not init():
    deinit()
    return

  try:
    while loop():
      time.sleep(1)
  except KeyboardInterrupt:
    print("\nProcess interrupted by user.")
  finally:
    deinit()


if __name__ == "__main__":
  main()

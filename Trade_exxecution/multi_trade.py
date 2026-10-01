import time
import MetaTrader5 as mt5

#------------------------configuration list----------------------------#


SYMBOLS_TO_TRADE = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]

tf = mt5.TIMEFRAME_M5
slow_MA_period = 30
fast_MA_period = 10
magic_number = 123456

#---------------------dynamic filling mode helper---------------------#

def set_filling_mode(request) -> bool:

    sym_info = mt5.symbol_info(request["symbol"])
    if sym_info is None:
        return False

    modes = sym_info.filling_mode

    # Check broker allowed filling modes via bitwise flags
    # 1 = FOK, 2 = IOC, default/fallback = RETURN
    if modes & 1:
        request["type_filling"] = mt5.ORDER_FILLING_FOK
        return True
    elif modes & 2:
        request["type_filling"] = mt5.ORDER_FILLING_IOC
        return True
    else:
        request["type_filling"] = mt5.ORDER_FILLING_RETURN
        return True



#--------------------------trade exsecution---------------------------#

def execute_trade(symbol, action_type, lot, sl_points, tp_points) -> bool:

    sym_info = mt5.symbol_info(symbol)
    if sym_info is None:
        print(f"[Error] Failed to get symbol info for {symbol}")
        return False

    if not sym_info.visible:
        mt5.symbol_select(symbol, True)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"[Error] Failed to get price tick for {symbol}")
        return False

    point = sym_info.point
    digits = sym_info.digits

    if action_type == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        sl = round(price - (sl_points * point), digits) if sl_points > 0 else 0.0
        tp = round(price + (tp_points * point), digits) if tp_points > 0 else 0.0

    elif action_type == "SELL":
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
        sl = round(price + (sl_points * point), digits) if sl_points > 0 else 0.0
        tp = round(price - (tp_points * point), digits) if tp_points > 0 else 0.0
    else:
        print(f"[Error] Invalid action type: {action_type}")
        return False

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": magic_number,
        "comment": f"{action_type} order executed",
        "type_time": mt5.ORDER_TIME_GTC, 
    }

    if not set_filling_mode(request):
        print(f"[Rejected] Broker rejected order parameters or filling mode for {symbol}")
        return False

    result = mt5.order_send(request)

    if result is None:
        print(f"[Order Failed] {symbol}: No response from broker. Error: {mt5.last_error()}")
        return False

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[Order Failed] {symbol}: Code {result.retcode} | {result.comment}")
        return False

    print(f"[SUCCESS] {action_type} Order Placed on {symbol} @ {price} | SL: {sl} | TP: {tp}")
    return True

#------------------------moving average automation------------------------#

def get_ma_signal(symbol):
    # Fetch completed candles + buffer to calculate true crossover without repainting
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, slow_MA_period + 3)
    if rates is None or len(rates) < slow_MA_period + 2:
        return None

    # Exclude candle [-1] (currently forming) and evaluate only closed candles
    closes = [r['close'] for r in rates[:-1]]

    # Latest completed bar MAs
    fast_ma_curr = sum(closes[-fast_MA_period:]) / fast_MA_period
    slow_ma_curr = sum(closes[-slow_MA_period:]) / slow_MA_period

    # Previous completed bar MAs
    fast_ma_prev = sum(closes[-fast_MA_period - 1 : -1]) / fast_MA_period
    slow_ma_prev = sum(closes[-slow_MA_period - 1 : -1]) / slow_MA_period

    # Bullish crossover (Golden Cross)
    if fast_ma_prev <= slow_ma_prev and fast_ma_curr > slow_ma_curr:
        return "BUY"

    # Bearish crossover (Death Cross)
    elif fast_ma_prev >= slow_ma_prev and fast_ma_curr < slow_ma_curr:
        return "SELL"

    return None

#--------------------------------MAIN--------------------------------#





def main():
    print("=" * 55)
    print("      MT5 MULTI-SYMBOL ALL-IN-ONE TRADING SCRIPT     ")
    print("=" * 55)

    # Step A: Connect to MetaTrader 5
    if not mt5.initialize():
        print(f"Failed to connect to MetaTrader 5: {mt5.last_error()}")
        return

    print("Connected to MetaTrader 5 successfully.\n")

    # Step B: Get User Inputs
    print("Choose Trading Mode:")
    print(" 1. BUY  (Instantly execute BUY orders across chosen symbols)")
    print(" 2. SELL (Instantly execute SELL orders across chosen symbols)")
    print(" 3. AUTO (Run Moving Average automated loop)")
    choice = input("Enter option (1, 2, or 3): ").strip()

    if choice == "1":
        mode = "BUY"
    elif choice == "2":
        mode = "SELL"
    elif choice == "3":
        mode = "AUTO"
    else:
        print("Invalid choice selected. Exiting.")
        mt5.shutdown()
        return

    try:
        user_lot = float(input("Enter Lot Size (e.g., 0.01): ").strip())
        user_sl = float(input("Enter Stop Loss in Points (e.g., 50, enter 0 to disable): ").strip())
        user_tp = float(input("Enter Take Profit in Points (e.g., 100, enter 0 to disable): ").strip())
    except ValueError:
        print("Invalid number entered. Exiting.")
        mt5.shutdown()
        return

    # Step C: Validate Symbols in MT5 Market Watch
    valid_symbols = []
    print("\n--- Validating Symbols ---")
    for sym in SYMBOLS_TO_TRADE:
        if mt5.symbol_select(sym, True):
            print(f"[OK] Symbol active: {sym}")
            valid_symbols.append(sym)
        else:
            print(f"[Warning] Symbol '{sym}' not found in broker watchlist. Skipped.")

    if not valid_symbols:
        print("No valid symbols available to trade. Exiting.")
        mt5.shutdown()
        return

    print(f"\nConfiguration active: Mode={mode} | Lot={user_lot} | SL={user_sl} | TP={user_tp}\n")

    # Step D: Process Execution based on Mode Selection
    if mode in ["BUY", "SELL"]:
        print(f"--- Executing immediate {mode} orders ---")
        for sym in valid_symbols:
            execute_trade(sym, mode, user_lot, user_sl, user_tp)
        print("\nAll instant orders processed.")

    elif mode == "AUTO":
        print("--- Starting Auto-Trade Monitor (Press Ctrl+C to stop) ---")
        try:
            while True:
                for sym in valid_symbols:
                    # Check if there is already an open position for this symbol
                    positions = mt5.positions_get(symbol=sym)
                    if positions and len(positions) > 0:
                        continue  # Avoid placing multiple duplicate orders

                    signal = get_ma_signal(sym)
                    if signal in ["BUY", "SELL"]:
                        print(f"[Signal Triggered] {signal} for {sym}")
                        execute_trade(sym, signal, user_lot, user_sl, user_tp)

                time.sleep(10)  # Check market every 10 seconds

        except KeyboardInterrupt:
            print("\nStopped auto-trade loop.")

    mt5.shutdown()


if __name__ == "__main__":
    main()

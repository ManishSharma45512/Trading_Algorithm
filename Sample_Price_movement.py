import time
import MetaTrader5 as mt5

# Configuration Constants
SYMBOL = "EURUSD"
DELTA = 0.00005  # 0.5 pips / 5 points
POLL_INTERVAL = 5  # Seconds between tick checks


def main():
    # 1. Initialize MT5 connection
    if not mt5.initialize():
        print("Terminal initialization failed.")
        mt5.shutdown()
        return

    # 2. Select the symbol in the Market Watch window
    if not mt5.symbol_select(SYMBOL, True):
        print(f"Failed to select symbol: {SYMBOL}")
        mt5.shutdown()
        return

    # 3. Retrieve the initial baseline tick
    price_info = mt5.symbol_info_tick(SYMBOL)
    if price_info is None:
        print(f"Failed to get price for {SYMBOL}")
        mt5.shutdown()
        return

    starting_price = price_info.bid
    high_target = starting_price + DELTA
    low_target = starting_price - DELTA

    print(f"Monitoring {SYMBOL}")
    print(f"Starting bid price : {starting_price:.5f}")
    print(f"High target        : {high_target:.5f}")
    print(f"Low target         : {low_target:.5f}")
    print("-" * 40)

    old_price = starting_price

    # 4. Polling loop
    while True:
        price_info = mt5.symbol_info_tick(SYMBOL)

        if price_info is None:
            time.sleep(POLL_INTERVAL)
            continue

        current_price = price_info.bid

        if current_price != old_price:
            print(f"Price updated: {current_price:.5f}")
            old_price = current_price

        if current_price >= high_target:
            print(
                f"\n[ALERT] {SYMBOL} reached Upper Limit: {current_price:.5f} >= {high_target:.5f}"
            )
            break

        if current_price <= low_target:
            print(
                f"\n[ALERT] {SYMBOL} reached Lower Limit: {current_price:.5f} <= {low_target:.5f}"
            )
            break

        time.sleep(POLL_INTERVAL)

    # 5. Clean teardown
    mt5.shutdown()
    print("MT5 connection closed")


if __name__ == "__main__":
    main()

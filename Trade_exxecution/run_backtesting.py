import MetaTrader5 as mt5
import pandas as pd
from backtesting import Backtest, Strategy


# ----------------- INDICATOR WRAPPER ------------------- #
def compute_sma(series_data, period):
    return pd.Series(series_data).rolling(window=period).mean().to_numpy()


# ----------------- BACKTESTING STRATEGY ---------------- #
class SimpleCrossStrategy(Strategy):
    fast_ma_period = 10
    slow_ma_period = 20
    lot_size = 1
    stop_loss_amount = 0.0015
    take_profit_amount = 0.0030

    long_trades = 0
    short_trades = 0

    def init(self):
        self.fast_ma = self.I(compute_sma, self.data.Close, self.fast_ma_period)
        self.slow_ma = self.I(compute_sma, self.data.Close, self.slow_ma_period)

    def next(self):
        fast_curr, fast_prev = self.fast_ma[-1], self.fast_ma[-2]
        slow_curr, slow_prev = self.slow_ma[-1], self.slow_ma[-2]

        close_price = self.data.Close[-1]


        open_longs = sum(1 for trade in self.trades if trade.is_long)
        open_shorts = sum(1 for trade in self.trades if not trade.is_long)

        # Bullish Crossover
        if fast_prev <= slow_prev and fast_curr > slow_curr:
            if open_longs == 0:
                self.buy(
                    size=self.lot_size,
                    sl=close_price - self.stop_loss_amount,
                    tp=close_price + self.take_profit_amount
                )
                self.long_trades += 1
            return

        # Bearish Crossover
        if fast_prev >= slow_prev and fast_curr < slow_curr:
            if open_shorts == 0:
                self.sell(
                    size=self.lot_size,
                    sl=close_price + self.stop_loss_amount,
                    tp=close_price - self.take_profit_amount
                )
                self.short_trades += 1
            return


# ----------------- DATA FETCHING & RUNNER ---------------- #
def run_backtest():
    if not mt5.initialize():
        print(f"MetaTrader5 has not been initialized: {mt5.last_error()}")
        return

    symbol = "EURUSD"
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1000)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        print("Failed to pull rates from MT5. Verify symbol name and broker connection.")
        return

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)

    df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "tick_volume": "Volume"
    }, inplace=True)

    bt = Backtest(
        df,
        SimpleCrossStrategy,
        cash=100000,
        hedging=True,
        finalize_trades=True
    )

    stats = bt.run()
    print(stats)
    print(f"\nTotal Longs Executed: {stats._strategy.long_trades}")
    print(f"Total Shorts Executed: {stats._strategy.short_trades}")


if __name__ == "__main__":
    run_backtest()

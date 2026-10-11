import time
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from backtesting import Backtest, Strategy
from backtesting._util import _Data


# ======================================================================== #
#                Technical Indicators
# ======================================================================== #

def compute_sma(series_data, period: int):
    return pd.Series(series_data).rolling(window=period).mean().to_numpy()


# ======================================================================== #
#       Custom Engine Classes (Dual live / backtest dispatch)
# ======================================================================== #

class CustomStrategy(Strategy):
    is_testing = True
    symbol = "EURUSD"
    timeframe = mt5.TIMEFRAME_M15
    magic = 10001
    deviation = 20

    def set_live_params(self, symbol: str, timeframe: int, magic: int = 10001):
        self.is_testing = False
        self.symbol = symbol
        self.timeframe = timeframe
        self.magic = magic

    def _get_filling_mode(self, request: dict) -> bool:
        for mode in [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN]:
            request["type_filling"] = mode
            chk = mt5.order_check(request)
            if chk is not None and chk.retcode == mt5.TRADE_RETCODE_DONE:
                return True
        return False

    def _execute_mt5_deal(self, order_type: int, size: float, sl: float, tp: float):
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"[ERROR] Failed to get tick data for {self.symbol}")
            return

        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(size),
            "type": order_type,
            "price": price,
            "sl": float(sl) if sl > 0 else 0.0,
            "tp": float(tp) if tp > 0 else 0.0,
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": "DualEngineBot",
            "type_time": mt5.ORDER_TIME_GTC
        }

        if not self._get_filling_mode(request):
            print(f"[ERROR] Broker rejected order fill check for {self.symbol}: {mt5.last_error()}")
            return

        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_comment = result.comment if result else mt5.last_error()
            ret_code = result.retcode if result else "None"
            print(f"[FAILED] MT5 Order Error: {ret_code} | {error_comment}")
        else:
            print(f"[LIVE TRADE] Order #{result.order} opened: {self.symbol} @ {price}")

    def buy(self, size=1.0, sl=None, tp=None, **kwargs):
        if self.is_testing:
            return super().buy(size=size, sl=sl, tp=tp, **kwargs)
        self._execute_mt5_deal(mt5.ORDER_TYPE_BUY, size, sl or 0.0, tp or 0.0)

    def sell(self, size=1.0, sl=None, tp=None, **kwargs):
        if self.is_testing:
            return super().sell(size=size, sl=sl, tp=tp, **kwargs)
        self._execute_mt5_deal(mt5.ORDER_TYPE_SELL, size, sl or 0.0, tp or 0.0)

    def count_open_positions(self, is_long: bool) -> int:
        if self.is_testing:
            return sum(1 for trade in self.trades if trade.is_long == is_long)

        positions = mt5.positions_get(symbol=self.symbol)
        if not positions:
            return 0

        target_type = mt5.POSITION_TYPE_BUY if is_long else mt5.POSITION_TYPE_SELL
        return sum(1 for p in positions if p.type == target_type and p.magic == self.magic)


class CustomBacktest(Backtest):
    def __init__(self, data, strategy, **kwargs):
        self.is_testing = True
        self.symbol = "EURUSD"
        self.timeframe = mt5.TIMEFRAME_M15
        self.cycle_seconds = 5

        if data is None:
            self.is_testing = False
            dummy = pd.DataFrame(
                {"Open": [0.0], "High": [0.0], "Low": [0.0], "Close": [0.0], "Volume": [0]},
                index=pd.to_datetime(["2026-01-01"])
            )
            super().__init__(dummy, strategy, **kwargs)
        else:
            super().__init__(data, strategy, **kwargs)

    def set_live_params(self, symbol: str, timeframe: int, cycle_seconds: int = 5, magic: int = 10001):
        self.is_testing = False
        self.symbol = symbol
        self.timeframe = timeframe
        self.cycle_seconds = cycle_seconds
        self.magic = magic

    def run(self, **kwargs):
        if self.is_testing:
            return super().run(**kwargs)

        if not mt5.symbol_select(self.symbol, True):
            print(f"[ERROR] Failed to select symbol {self.symbol}: {mt5.last_error()}")
            return

        strat = self._strategy(None, self._data, **kwargs)
        strat.set_live_params(self.symbol, self.timeframe, self.magic)

        print(f"[LIVE MODE] Monitoring {self.symbol} every {self.cycle_seconds}s. Press Ctrl+C to stop.")

        try:
            while True:
                strat.next()
                time.sleep(self.cycle_seconds)
        except KeyboardInterrupt:
            print("\n[Stopped] Live bot terminated by user.")
            return None


# ======================================================================== #
#       Strategy Definition
# ======================================================================== #

class MACrossStrategy(CustomStrategy):
    fast_period = 10
    slow_period = 20
    lot_size = 0.01
    sl_points = 0.0015
    tp_points = 0.0030

    def init(self):
        if self.is_testing:
            self.fast_ma = self.I(compute_sma, self.data.Close, self.fast_period)
            self.slow_ma = self.I(compute_sma, self.data.Close, self.slow_period)

    def next(self):
        if not self.is_testing:
            required_bars = self.slow_period + 5
            rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, required_bars)
            if rates is None or len(rates) < required_bars:
                return

            closes = pd.Series([r["close"] for r in rates])
            fast_ma = compute_sma(closes, self.fast_period)
            slow_ma = compute_sma(closes, self.slow_period)

            fast_curr, fast_prev = fast_ma[-1], fast_ma[-2]
            slow_curr, slow_prev = slow_ma[-1], slow_ma[-2]
            current_close = closes.iloc[-1]
        else:
            fast_curr, fast_prev = self.fast_ma[-1], self.fast_ma[-2]
            slow_curr, slow_prev = self.slow_ma[-1], self.slow_ma[-2]
            current_close = self.data.Close[-1]

        long_open = self.count_open_positions(is_long=True)
        short_open = self.count_open_positions(is_long=False)

        # Bullish Crossover
        if fast_prev <= slow_prev and fast_curr > slow_curr:
            if long_open == 0:
                self.buy(
                    size=self.lot_size,
                    sl=current_close - self.sl_points,
                    tp=current_close + self.tp_points
                )
            return

        # Bearish Crossover
        if fast_prev >= slow_prev and fast_curr < slow_curr:
            if short_open == 0:
                self.sell(
                    size=self.lot_size,
                    sl=current_close + self.sl_points,
                    tp=current_close - self.tp_points
                )
            return


# ======================================================================== #
#       Entry Point : Toggle Mode Via Boolean
# ======================================================================== #

if __name__ == "__main__":
    TESTING_MODE = True

    if not mt5.initialize():
        print(f"Failed to initialize MT5: {mt5.last_error()}")
        exit()

    TARGET_SYMBOL = "EURUSD"

    if TESTING_MODE:
        rates = mt5.copy_rates_from_pos(TARGET_SYMBOL, mt5.TIMEFRAME_H1, 0, 1000)
        mt5.shutdown()

        if rates is None or len(rates) == 0:
            print(f"Failed to fetch rates for {TARGET_SYMBOL}")
            exit()

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
        df.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "tick_volume": "Volume"
        }, inplace=True)

        engine = CustomBacktest(df, MACrossStrategy, cash=10000, hedging=True)
        stats = engine.run()
        print(stats)

    else:
        engine = CustomBacktest(None, MACrossStrategy)
        engine.set_live_params(
            symbol=TARGET_SYMBOL,
            timeframe=mt5.TIMEFRAME_M15,
            cycle_seconds=5,
            magic=10001
        )
        engine.run()
        mt5.shutdown()

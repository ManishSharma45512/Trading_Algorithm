import os
import json
import time
from datetime import datetime
from types import SimpleNamespace
import MetaTrader5 as mt5

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_CYCLE_TIME = 30  # Fallback duration when config has syntax/symbol errors
config = None


# --- 1. DEFAULT CONFIGURATION GENERATOR ---
def ensure_default_config():
    """Creates default config folder and file if they do not exist."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    if not os.path.exists(CONFIG_FILE):
        default_data = {
            "cycle_time": 10,
            "groups": [
                {
                    "name": "Forex Majors",
                    "symbols": ["EURUSD", "GBPUSD"],
                    "magic": 10001,
                    "lot": 0.01,
                    "stop_loss_points": 50,
                    "take_profit_points": 100,
                    "fast_ma_period": 10,
                    "slow_ma_period": 30,
                    "timeframe": 5
                },
                {
                    "name": "Yen Crosses",
                    "symbols": ["USDJPY"],
                    "magic": 10002,
                    "lot": 0.01,
                    "stop_loss_points": 40,
                    "take_profit_points": 80,
                    "fast_ma_period": 8,
                    "slow_ma_period": 24,
                    "timeframe": 5
                },
                {
                    "name": "Commodities",
                    "symbols": ["XAUUSD"],
                    "magic": 10003,
                    "lot": 0.01,
                    "stop_loss_points": 150,
                    "take_profit_points": 300,
                    "fast_ma_period": 5,
                    "slow_ma_period": 15,
                    "timeframe": 1
                }
            ]
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_data, f, indent=4)
        print(f"[Setup] Generated default configuration file at '{CONFIG_FILE}'.")


# --- 2. LOGGING WITH TIMESTAMPS ---
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


# --- 3. RECURSIVE DICT TO OBJECT CONVERTER ---
def dict_to_obj(data):
    if isinstance(data, dict):
        return SimpleNamespace(**{k: dict_to_obj(v) for k, v in data.items()})
    elif isinstance(data, list):
        return [dict_to_obj(item) for item in data]
    return data


# --- 4. DYNAMIC CONFIG LOADER WITH LIVE-RELOAD ---
def load_config(file_path, current_config_obj=None):
    if not os.path.exists(file_path):
        log(f"[Error] Config file not found: {file_path}")
        return None

    # Check file modification timestamp
    mod_time = os.path.getmtime(file_path)
    if current_config_obj and hasattr(current_config_obj, "last_mod_time"):
        if current_config_obj.last_mod_time == mod_time:
            return current_config_obj  # No changes detected, reuse existing object

    log(f"Reloading configuration from '{file_path}'...")

    try:
        with open(file_path, "r") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as err:
        log(f"[JSON Error] Invalid syntax in config: {err}")
        return None
    except Exception as err:
        log(f"[Error] Failed to read config: {err}")
        return None

    new_config = dict_to_obj(raw_data)
    available_groups = []

    if hasattr(new_config, "groups"):
        for group in new_config.groups:
            valid_symbols = []
            for sym in group.symbols:
                if mt5.symbol_select(sym, True):
                    valid_symbols.append(sym)
                else:
                    log(f"[Symbol Warning] Could not select '{sym}' (check broker suffix).")

            if valid_symbols:
                group.symbols = valid_symbols
                available_groups.append(group)
            else:
                log(f"[Group Skipped] No valid symbols found in group '{group.name}'.")

    if not available_groups:
        log("[CRITICAL] All groups failed validation.")
        return None

    new_config.groups = available_groups
    new_config.last_mod_time = mod_time
    log("[SUCCESS] Configuration reloaded and verified.")
    return new_config


# --- 5. BROKER FILLING MODE DETECTOR ---
def set_filling_mode(request):
    for filling_mode in [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN]:
        request['type_filling'] = filling_mode
        result = mt5.order_check(request)
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True
    return False


# --- 6. ORDER EXECUTION ---
def execute_trade(symbol, action_type, lot, sl_points, tp_points, magic_number):
    tick = mt5.symbol_info_tick(symbol)
    sym_info = mt5.symbol_info(symbol)

    if tick is None or sym_info is None:
        log(f"[Tick Error] No tick available for {symbol}")
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
        return False

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "magic": int(magic_number),
        "comment": "DynamicBot",
        "type_time": mt5.ORDER_TIME_GTC,
    }

    if not set_filling_mode(request):
        log(f"[Execution Rejected] Invalid filling mode or parameters for {symbol}")
        return False

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log(f"[Order Failed] {symbol}: Error code {result.retcode}")
        return False

    log(f"[TRADE EXECUTED] {action_type} {lot} on {symbol} @ {price} | SL: {sl} | TP: {tp}")
    return True


# --- 7. TIMEFRAME MAPPER & SIGNAL ANALYSIS ---
def get_mt5_timeframe(minutes):
    mapping = {
        1: mt5.TIMEFRAME_M1,
        5: mt5.TIMEFRAME_M5,
        15: mt5.TIMEFRAME_M15,
        30: mt5.TIMEFRAME_M30,
        60: mt5.TIMEFRAME_H1,
        240: mt5.TIMEFRAME_H4,
        1440: mt5.TIMEFRAME_D1
    }
    return mapping.get(minutes, mt5.TIMEFRAME_M5)


def check_trade_signal(symbol, group):
    tf = get_mt5_timeframe(getattr(group, "timeframe", 5))
    required_bars = max(group.fast_ma_period, group.slow_ma_period) + 2

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, required_bars)
    if rates is None or len(rates) < required_bars:
        return None

    closes = [r['close'] for r in rates]
    fast_ma = sum(closes[-group.fast_ma_period:]) / group.fast_ma_period
    slow_ma = sum(closes[-group.slow_ma_period:]) / group.slow_ma_period

    if fast_ma > slow_ma:
        return "BUY"
    elif fast_ma < slow_ma:
        return "SELL"
    return None


# --- 8. SYMBOL PROCESSOR ---
def process_symbol(symbol, group):
    # Check if a position is already open for this magic number + symbol
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        for pos in positions:
            if pos.magic == group.magic:
                return  # Skip duplicate orders

    signal = check_trade_signal(symbol, group)
    if signal:
        log(f"[{group.name}] Signal detected for {symbol}: {signal}")
        execute_trade(
            symbol=symbol,
            action_type=signal,
            lot=group.lot,
            sl_points=group.stop_loss_points,
            tp_points=group.take_profit_points,
            magic_number=group.magic
        )


# --- 9. MAIN EVENT LOOP ---
def main():
    global config

    log("Initializing MetaTrader 5...")
    if not mt5.initialize():
        log(f"MT5 Init failed: {mt5.last_error()}")
        return

    log("MT5 connected successfully.")
    ensure_default_config()

    try:
        while True:
            # Dynamically check/reload config
            config = load_config(CONFIG_FILE, config)

            if config:
                for group in config.groups:
                    for symbol in group.symbols:
                        process_symbol(symbol, group)

                sleep_duration = getattr(config, "cycle_time", DEFAULT_CYCLE_TIME)
            else:
                log(f"Config is invalid. Re-checking in {DEFAULT_CYCLE_TIME} seconds...")
                sleep_duration = DEFAULT_CYCLE_TIME

            time.sleep(sleep_duration)

    except KeyboardInterrupt:
        log("Bot execution stopped by user.")
    finally:
        mt5.shutdown()
        log("Disconnected from MetaTrader 5.")


if __name__ == "__main__":
    main()

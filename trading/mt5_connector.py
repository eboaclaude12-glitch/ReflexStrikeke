"""
ReflexStrike MT5 Connector
───────────────────────────
Thin wrapper around the MetaTrader5 Python package.

Responsibilities:
  • Connect / disconnect
  • Fetch OHLCV bars
  • Query account info and symbol info
  • Place market orders (BUY / SELL) with SL and TP
  • Query and close open positions
"""

import logging
import time
from typing import Optional

import MetaTrader5 as mt5
import pandas as pd

logger = logging.getLogger(__name__)

# MetaTrader5 timeframe map
TIMEFRAME_MAP = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
    "W1":  mt5.TIMEFRAME_W1,
}


# ── Connection ────────────────────────────────────────────────────────────────

def connect() -> None:
    """
    Initialise the MT5 terminal connection.
    The MT5 desktop app must already be running and logged into your FTMO account.
    Raises RuntimeError on failure.
    """
    if not mt5.initialize():
        code, message = mt5.last_error()
        raise RuntimeError(f"MT5 initialisation failed [{code}]: {message}")
    info = mt5.terminal_info()
    logger.info(
        f"MT5 connected | build={info.build} "
        f"server={mt5.account_info().server} "
        f"login={mt5.account_info().login}"
    )


def disconnect() -> None:
    mt5.shutdown()
    logger.info("MT5 disconnected.")


# ── Market Data ───────────────────────────────────────────────────────────────

def get_ohlcv(symbol: str, timeframe: str, n_bars: int = 300) -> pd.DataFrame:
    """
    Fetch the last n_bars OHLCV bars for symbol on the given timeframe.
    Bar at index -1 is the currently forming (live) bar.
    Bar at index -2 is the last completed bar.

    Returns a DataFrame with columns:
        time, open, high, low, close, tick_volume, spread, real_volume
    """
    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        raise ValueError(f"Unknown timeframe: {timeframe}. Use one of {list(TIMEFRAME_MAP)}")

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
    if rates is None or len(rates) == 0:
        code, msg = mt5.last_error()
        raise RuntimeError(f"Failed to fetch rates for {symbol}/{timeframe} [{code}]: {msg}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


# ── Account ───────────────────────────────────────────────────────────────────

def get_account_info() -> dict:
    info = mt5.account_info()
    if info is None:
        code, msg = mt5.last_error()
        raise RuntimeError(f"Failed to get account info [{code}]: {msg}")
    return info._asdict()


def get_symbol_info(symbol: str) -> mt5.SymbolInfo:
    info = mt5.symbol_info(symbol)
    if info is None:
        code, msg = mt5.last_error()
        raise RuntimeError(f"Symbol '{symbol}' not found [{code}]: {msg}")
    if not info.visible:
        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)
    return info


# ── Orders ────────────────────────────────────────────────────────────────────

def place_market_order(
    symbol: str,
    order_type: int,              # mt5.ORDER_TYPE_BUY or mt5.ORDER_TYPE_SELL
    volume: float,
    sl: float,
    tp: float,
    magic: int,
    comment: str,
    digits: int,
) -> mt5.OrderSendResult:
    """
    Send a market order with stop loss and take profit.
    Returns the OrderSendResult namedtuple.
    Logs a warning if the order fails.
    """
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        code, msg = mt5.last_error()
        raise RuntimeError(f"Cannot get tick for {symbol} [{code}]: {msg}")

    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    request = {
        "action":      mt5.TRADE_ACTION_DEAL,
        "symbol":      symbol,
        "volume":      volume,
        "type":        order_type,
        "price":       price,
        "sl":          round(sl, digits),
        "tp":          round(tp, digits),
        "magic":       magic,
        "comment":     comment,
        "type_time":   mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None:
        code, msg = mt5.last_error()
        raise RuntimeError(f"order_send returned None [{code}]: {msg}")

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.warning(
            f"Order failed | retcode={result.retcode} comment='{result.comment}' "
            f"request={request}"
        )
    else:
        direction = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
        logger.info(
            f"Order filled | {direction} {volume} {symbol} @ {result.price:.5f} "
            f"SL={sl:.5f} TP={tp:.5f} ticket=#{result.order}"
        )

    return result


# ── Positions ─────────────────────────────────────────────────────────────────

def get_open_positions(symbol: str, magic: int) -> list:
    """Return all open positions for symbol belonging to this bot (by magic number)."""
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return []
    return [p for p in positions if p.magic == magic]


def close_position(position) -> Optional[mt5.OrderSendResult]:
    """
    Close a single open position at market price.
    Returns the OrderSendResult or None on error.
    """
    symbol = position.symbol
    is_buy = position.type == mt5.ORDER_TYPE_BUY

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"Cannot get tick to close position #{position.ticket}")
        return None

    close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
    close_price = tick.bid if is_buy else tick.ask

    request = {
        "action":      mt5.TRADE_ACTION_DEAL,
        "symbol":      symbol,
        "volume":      position.volume,
        "type":        close_type,
        "position":    position.ticket,
        "price":       close_price,
        "magic":       position.magic,
        "comment":     "ReflexStrike_Close",
        "type_time":   mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code, msg = mt5.last_error()
        logger.error(
            f"Failed to close position #{position.ticket} "
            f"retcode={getattr(result, 'retcode', None)} [{code}]: {msg}"
        )
    else:
        logger.info(
            f"Position closed | #{position.ticket} {symbol} "
            f"{'BUY' if is_buy else 'SELL'} @ {result.price:.5f}"
        )
    return result

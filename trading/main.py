"""
ReflexStrike Trading Bot — Main Entry Point
────────────────────────────────────────────
Strategy : EMA 20/50 Crossover + RSI 14 Filter
Instrument: XAUUSD (Gold) on H1
Broker    : FTMO via MetaTrader 5

Usage:
    python trading/main.py

Requirements:
    • MetaTrader 5 desktop app running and logged into your FTMO account
    • Python packages installed: pip install -r requirements.txt
    • Windows OS (MT5 Python library is Windows-only)
"""

import logging
import time
from datetime import datetime, timezone

import MetaTrader5 as mt5

import config
from mt5_connector import (
    connect, disconnect,
    get_account_info, get_symbol_info,
    get_ohlcv,
    place_market_order,
    get_open_positions, close_position,
)
from strategy import generate_signal
from risk_manager import calculate_lot_size, FTMOGuard


# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("reflex_strike.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _direction_label(order_type: int) -> str:
    return "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"


def _has_position_in_direction(positions: list, order_type: int) -> bool:
    return any(p.type == order_type for p in positions)


def _close_opposite_positions(positions: list, signal: int) -> None:
    """Close any positions that are in the opposite direction of the new signal."""
    opposite_type = mt5.ORDER_TYPE_SELL if signal == 1 else mt5.ORDER_TYPE_BUY
    for pos in positions:
        if pos.type == opposite_type:
            logger.info(
                f"Closing opposite position #{pos.ticket} "
                f"({'SELL' if opposite_type == mt5.ORDER_TYPE_SELL else 'BUY'})"
            )
            close_position(pos)


# ── Core loop ─────────────────────────────────────────────────────────────────

def run() -> None:
    logger.info("=" * 60)
    logger.info("  ReflexStrike Bot — Starting up")
    logger.info(f"  Symbol    : {config.SYMBOL}")
    logger.info(f"  Timeframe : {config.TIMEFRAME}")
    logger.info(f"  Strategy  : EMA {config.FAST_EMA}/{config.SLOW_EMA} + RSI {config.RSI_PERIOD}")
    logger.info(f"  Risk      : {config.RISK_PERCENT}% per trade")
    logger.info("=" * 60)

    # --- Connect ---
    connect()

    account = get_account_info()
    symbol_info = get_symbol_info(config.SYMBOL)
    initial_balance = account["balance"]

    logger.info(
        f"Account | login={account['login']} balance={initial_balance:.2f} "
        f"{account['currency']} server={account['server']}"
    )
    logger.info(
        f"Symbol  | {config.SYMBOL} digits={symbol_info.digits} "
        f"tick_size={symbol_info.trade_tick_size} "
        f"tick_value={symbol_info.trade_tick_value} "
        f"lot_min={symbol_info.volume_min} lot_step={symbol_info.volume_step}"
    )

    ftmo_guard = FTMOGuard(
        initial_balance=initial_balance,
        daily_loss_limit_pct=config.FTMO_DAILY_LOSS_LIMIT,
        max_drawdown_pct=config.FTMO_MAX_DRAWDOWN,
    )

    last_bar_time = None
    last_day = None

    try:
        while True:
            # --- Fetch latest bars ---
            try:
                df = get_ohlcv(config.SYMBOL, config.TIMEFRAME, n_bars=config.BARS_HISTORY)
            except RuntimeError as e:
                logger.error(f"Failed to fetch bars: {e}. Retrying in {config.SLEEP_SECONDS}s.")
                time.sleep(config.SLEEP_SECONDS)
                continue

            current_bar_time = df["time"].iloc[-1]

            # --- Wait for a new bar ---
            if current_bar_time == last_bar_time:
                time.sleep(config.SLEEP_SECONDS)
                continue

            last_bar_time = current_bar_time
            logger.info(f"── New bar: {current_bar_time} ─────────────────────────")

            # --- Refresh account state ---
            account = get_account_info()
            current_balance = account["balance"]
            ftmo_guard.update(current_balance)

            # --- Daily reset ---
            today = datetime.now(timezone.utc).date()
            if today != last_day:
                ftmo_guard.reset_daily(current_balance)
                last_day = today

            # --- FTMO safety check ---
            allowed, reason = ftmo_guard.is_trading_allowed(current_balance)
            if not allowed:
                logger.warning(f"Trading halted — {reason}")
                time.sleep(config.SLEEP_SECONDS)
                continue

            # --- Generate signal ---
            try:
                signal, atr_value, indicators = generate_signal(
                    df,
                    fast=config.FAST_EMA,
                    slow=config.SLOW_EMA,
                    rsi_period=config.RSI_PERIOD,
                    atr_period=config.ATR_PERIOD,
                    rsi_overbought=config.RSI_OVERBOUGHT,
                    rsi_oversold=config.RSI_OVERSOLD,
                )
            except ValueError as e:
                logger.warning(f"Signal generation skipped: {e}")
                time.sleep(config.SLEEP_SECONDS)
                continue

            logger.info(
                f"Indicators | EMA{config.FAST_EMA}={indicators['ema_fast']:.2f}  "
                f"EMA{config.SLOW_EMA}={indicators['ema_slow']:.2f}  "
                f"RSI={indicators['rsi']:.1f}  ATR={indicators['atr']:.2f}  "
                f"Signal={'BUY' if signal==1 else 'SELL' if signal==-1 else 'NONE'}"
            )

            if signal == 0:
                time.sleep(config.SLEEP_SECONDS)
                continue

            # --- Manage open positions ---
            open_positions = get_open_positions(config.SYMBOL, config.MAGIC_NUMBER)
            _close_opposite_positions(open_positions, signal)

            # Refresh after potential closes
            open_positions = get_open_positions(config.SYMBOL, config.MAGIC_NUMBER)

            # --- Enforce max open trades ---
            desired_type = mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL
            if len(open_positions) >= config.MAX_OPEN_TRADES:
                logger.info(
                    f"Max open trades ({config.MAX_OPEN_TRADES}) reached — skipping new entry."
                )
                time.sleep(config.SLEEP_SECONDS)
                continue

            if _has_position_in_direction(open_positions, desired_type):
                logger.info("Already in a position in this direction — skipping.")
                time.sleep(config.SLEEP_SECONDS)
                continue

            # --- Calculate SL / TP ---
            tick = mt5.symbol_info_tick(config.SYMBOL)
            entry = tick.ask if signal == 1 else tick.bid
            sl_distance = atr_value * config.ATR_SL_MULTIPLIER
            tp_distance = atr_value * config.ATR_TP_MULTIPLIER

            if signal == 1:   # BUY
                sl = entry - sl_distance
                tp = entry + tp_distance
            else:             # SELL
                sl = entry + sl_distance
                tp = entry - tp_distance

            # --- Calculate lot size ---
            lot = calculate_lot_size(
                account_balance=current_balance,
                risk_percent=config.RISK_PERCENT,
                sl_distance=sl_distance,
                tick_value=symbol_info.trade_tick_value,
                tick_size=symbol_info.trade_tick_size,
                volume_min=symbol_info.volume_min,
                volume_max=symbol_info.volume_max,
                volume_step=symbol_info.volume_step,
            )

            logger.info(
                f"Trade plan | {_direction_label(desired_type)} {lot} {config.SYMBOL} "
                f"entry≈{entry:.2f}  SL={sl:.2f}  TP={tp:.2f}  "
                f"ATR={atr_value:.2f}  Risk={config.RISK_PERCENT}%"
            )

            # --- Place order ---
            result = place_market_order(
                symbol=config.SYMBOL,
                order_type=desired_type,
                volume=lot,
                sl=sl,
                tp=tp,
                magic=config.MAGIC_NUMBER,
                comment=config.TRADE_COMMENT,
                digits=symbol_info.digits,
            )

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Order accepted | ticket=#{result.order} deal=#{result.deal}")
            else:
                logger.error(
                    f"Order rejected | retcode={result.retcode} '{result.comment}'"
                )

            time.sleep(config.SLEEP_SECONDS)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        disconnect()
        logger.info("ReflexStrike Bot shut down.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run()

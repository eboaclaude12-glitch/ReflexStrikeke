"""
ReflexStrike Trading Bot — Main Entry Point
────────────────────────────────────────────
Strategy  : EMA 20/50 Crossover + RSI 14 Filter
            + Supply & Demand Zones + FVG + Price Action
Instrument: XAUUSD (Gold) on H1
Broker    : FTMO via MetaAPI (works on macOS, Linux, Windows)

Usage:
    python trading/main.py

Setup (one-time):
    1. pip install -r requirements.txt
    2. Sign up free at https://app.metaapi.cloud
    3. Add your FTMO MT5 account under "MetaTrader Accounts"
    4. Copy your API Token and Account ID into trading/config.py
    5. Run the bot — first launch syncs data (2-5 min), then it trades live
"""

import asyncio
import logging
from datetime import datetime, timezone

import config
from mt5_connector import (
    connect, disconnect,
    get_account_info, get_symbol_info,
    get_ohlcv, get_current_price,
    place_market_order,
    get_open_positions, close_position,
)
from strategy import generate_signal
from risk_manager import calculate_lot_size, FTMOGuard


# ── Logging ───────────────────────────────────────────────────────────────────

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

def _has_position_in_direction(positions: list, order_type: str) -> bool:
    """order_type: 'BUY' or 'SELL'"""
    key = f"POSITION_TYPE_{order_type}"
    return any(p["type"] == key for p in positions)


async def _close_opposite_positions(connection, positions: list, signal: int) -> None:
    """Close any positions in the direction opposite to the new signal."""
    opposite = "POSITION_TYPE_SELL" if signal == 1 else "POSITION_TYPE_BUY"
    for pos in positions:
        if pos["type"] == opposite:
            logger.info(f"Closing opposite {opposite.replace('POSITION_TYPE_', '')} #{pos['id']}")
            await close_position(connection, pos)


# ── Core loop ─────────────────────────────────────────────────────────────────

async def run() -> None:
    logger.info("=" * 60)
    logger.info("  ReflexStrike Bot — Starting up")
    logger.info(f"  Symbol    : {config.SYMBOL}")
    logger.info(f"  Timeframe : {config.TIMEFRAME}")
    logger.info(f"  Strategy  : EMA {config.FAST_EMA}/{config.SLOW_EMA} + RSI {config.RSI_PERIOD} + S/D + FVG + PA")
    logger.info(f"  Risk      : {config.RISK_PERCENT}%  |  Min confluence: {config.MIN_CONFLUENCE_SCORE}/3")
    logger.info("=" * 60)

    # --- Connect to MetaAPI ---
    api, connection = await connect(config.METAAPI_TOKEN, config.METAAPI_ACCOUNT_ID)

    account     = await get_account_info(connection)
    symbol_info = await get_symbol_info(connection, config.SYMBOL)
    initial_balance = account["balance"]

    logger.info(
        f"Account | login={account['login']}  balance={initial_balance:.2f} "
        f"{account['currency']}  server={account['server']}"
    )
    logger.info(
        f"Symbol  | {config.SYMBOL}  digits={symbol_info['digits']}  "
        f"tick_size={symbol_info['tick_size']}  tick_value={symbol_info['tick_value']}  "
        f"lot_min={symbol_info['volume_min']}  lot_step={symbol_info['volume_step']}"
    )

    ftmo_guard = FTMOGuard(
        initial_balance=initial_balance,
        daily_loss_limit_pct=config.FTMO_DAILY_LOSS_LIMIT,
        max_drawdown_pct=config.FTMO_MAX_DRAWDOWN,
    )

    last_bar_time = None
    last_day      = None

    try:
        while True:
            # --- Fetch latest bars ---
            try:
                df = await get_ohlcv(
                    connection, config.SYMBOL, config.TIMEFRAME,
                    n_bars=config.BARS_HISTORY
                )
            except Exception as e:
                logger.error(f"Failed to fetch bars: {e}. Retrying in {config.SLEEP_SECONDS}s.")
                await asyncio.sleep(config.SLEEP_SECONDS)
                continue

            # --- Wait for a new bar (track live bar opening time) ---
            current_bar_time = df["time"].iloc[-1]
            if current_bar_time == last_bar_time:
                await asyncio.sleep(config.SLEEP_SECONDS)
                continue

            last_bar_time = current_bar_time
            logger.info(f"── New bar: {current_bar_time} ─────────────────────────")

            # --- Refresh account balance ---
            try:
                account = await get_account_info(connection)
            except Exception as e:
                logger.warning(f"Could not refresh account info: {e}")
                await asyncio.sleep(config.SLEEP_SECONDS)
                continue

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
                await asyncio.sleep(config.SLEEP_SECONDS)
                continue

            # --- Generate signal ---
            try:
                signal, atr_value, details = generate_signal(
                    df,
                    fast=config.FAST_EMA,
                    slow=config.SLOW_EMA,
                    rsi_period=config.RSI_PERIOD,
                    atr_period=config.ATR_PERIOD,
                    rsi_overbought=config.RSI_OVERBOUGHT,
                    rsi_oversold=config.RSI_OVERSOLD,
                    swing_window=config.ZONE_SWING_WINDOW,
                    zone_atr_width=config.ZONE_ATR_WIDTH,
                    min_impulse_atr=config.ZONE_MIN_IMPULSE,
                    max_zones=config.ZONE_MAX_ZONES,
                    fvg_lookback=config.FVG_LOOKBACK,
                    fvg_min_gap_atr=config.FVG_MIN_GAP_ATR,
                    fvg_proximity_atr=config.FVG_PROXIMITY_ATR,
                    min_confluence=config.MIN_CONFLUENCE_SCORE,
                )
            except ValueError as e:
                logger.warning(f"Signal skipped: {e}")
                await asyncio.sleep(config.SLEEP_SECONDS)
                continue

            # --- Log indicators ---
            logger.info(
                f"Indicators | EMA{config.FAST_EMA}={details['ema_fast']:.2f}  "
                f"EMA{config.SLOW_EMA}={details['ema_slow']:.2f}  "
                f"RSI={details['rsi']:.1f}  ATR={details['atr']:.2f}  "
                f"Cross={details['crossover'].upper()}"
            )

            zone_label = (f"{details['zone']['type']}  str={details['zone']['strength']}"
                          if details["zone"] else "—")
            fvg_label  = (f"{details['fvg']['type']}  mid={details['fvg']['gap_mid']:.2f}"
                          if details["fvg"] else "—")
            logger.info(
                f"Confluence | score={details['score']}/{config.MIN_CONFLUENCE_SCORE} needed  "
                f"| RSI={'✓' if details['rsi_ok'] else '✗'}  "
                f"| Zone={'✓ ' + zone_label if details['at_zone'] else '✗'}  "
                f"| FVG={'✓ ' + fvg_label if details['near_fvg'] else '✗'}  "
                f"| PA={'✓ ' + details['candle_pattern'] if details['pa_confirmed'] else '✗'}  "
                f"→ {'BUY' if signal==1 else 'SELL' if signal==-1 else 'NO TRADE'}"
            )

            if signal == 0:
                await asyncio.sleep(config.SLEEP_SECONDS)
                continue

            # --- Manage existing positions ---
            try:
                open_positions = await get_open_positions(
                    connection, config.SYMBOL, config.MAGIC_NUMBER
                )
            except Exception as e:
                logger.error(f"Could not fetch positions: {e}")
                await asyncio.sleep(config.SLEEP_SECONDS)
                continue

            await _close_opposite_positions(connection, open_positions, signal)

            # Refresh after any closes
            open_positions = await get_open_positions(
                connection, config.SYMBOL, config.MAGIC_NUMBER
            )

            # --- Enforce max open trades ---
            desired_type = "BUY" if signal == 1 else "SELL"

            if len(open_positions) >= config.MAX_OPEN_TRADES:
                logger.info(f"Max open trades ({config.MAX_OPEN_TRADES}) reached — skipping.")
                await asyncio.sleep(config.SLEEP_SECONDS)
                continue

            if _has_position_in_direction(open_positions, desired_type):
                logger.info(f"Already have a {desired_type} position — skipping.")
                await asyncio.sleep(config.SLEEP_SECONDS)
                continue

            # --- Get live price for entry ---
            try:
                price = await get_current_price(connection, config.SYMBOL)
            except Exception as e:
                logger.error(f"Could not get price: {e}")
                await asyncio.sleep(config.SLEEP_SECONDS)
                continue

            entry       = price["ask"] if signal == 1 else price["bid"]
            sl_distance = atr_value * config.ATR_SL_MULTIPLIER
            tp_distance = atr_value * config.ATR_TP_MULTIPLIER

            if signal == 1:   # BUY
                sl = entry - sl_distance
                tp = entry + tp_distance
            else:             # SELL
                sl = entry + sl_distance
                tp = entry - tp_distance

            # --- Size the position ---
            lot = calculate_lot_size(
                account_balance=current_balance,
                risk_percent=config.RISK_PERCENT,
                sl_distance=sl_distance,
                tick_value=symbol_info["tick_value"],
                tick_size=symbol_info["tick_size"],
                volume_min=symbol_info["volume_min"],
                volume_max=symbol_info["volume_max"],
                volume_step=symbol_info["volume_step"],
            )

            logger.info(
                f"Trade plan | {desired_type} {lot} {config.SYMBOL}  "
                f"entry≈{entry:.2f}  SL={sl:.2f}  TP={tp:.2f}  "
                f"ATR={atr_value:.2f}  Risk={config.RISK_PERCENT}%"
            )

            # --- Place order ---
            try:
                await place_market_order(
                    connection,
                    symbol=config.SYMBOL,
                    order_type=desired_type,
                    volume=lot,
                    sl=sl,
                    tp=tp,
                    magic=config.MAGIC_NUMBER,
                    comment=config.TRADE_COMMENT,
                    digits=symbol_info["digits"],
                )
            except Exception as e:
                logger.error(f"Order failed: {e}")

            await asyncio.sleep(config.SLEEP_SECONDS)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C).")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        await disconnect(api)
        logger.info("ReflexStrike Bot shut down.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(run())

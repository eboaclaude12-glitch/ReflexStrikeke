"""
ReflexStrike — MetaAPI Connector
──────────────────────────────────
Replaces the Windows-only MetaTrader5 Python library with MetaAPI,
a cloud bridge that works on macOS, Linux, and Windows.

MetaAPI connects to your FTMO MT5 account through their cloud servers,
so the MT5 desktop app does NOT need to be running on your machine.

Docs: https://metaapi.cloud/docs/client/python/
"""

import logging
import os
import ssl
from datetime import datetime, timezone

import certifi
import pandas as pd
from metaapi_cloud_sdk import MetaApi

# Fix macOS SSL certificate verification issue (Python from python.org ships
# without system certificates; certifi provides a bundled CA bundle).
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
ssl._create_default_https_context = lambda: ssl.create_default_context(
    cafile=certifi.where()
)

logger = logging.getLogger(__name__)

# MetaAPI timeframe strings
TIMEFRAME_MAP = {
    "M1":  "1m",
    "M5":  "5m",
    "M15": "15m",
    "M30": "30m",
    "H1":  "1h",
    "H4":  "4h",
    "D1":  "1d",
    "W1":  "1w",
}


# ── Connection ────────────────────────────────────────────────────────────────

async def connect(token: str, account_id: str):
    """
    Connect to your MT5 account through MetaAPI.

    First run: MetaAPI deploys your account and syncs historical data —
    this can take 2–5 minutes. Subsequent runs are instant.

    Returns (api, connection) — pass these to every other function.
    """
    api = MetaApi(token)

    logger.info("Fetching MT5 account from MetaAPI...")
    account = await api.metatrader_account_api.get_account(account_id)

    if account.state not in ("DEPLOYED", "DEPLOYING"):
        logger.info("Deploying account (first-time setup, may take a few minutes)...")
        await account.deploy()

    logger.info("Waiting for broker connection...")
    await account.wait_connected()

    connection = account.get_rpc_connection()
    await connection.connect()

    logger.info("Waiting for data sync...")
    await connection.wait_synchronized()

    info = await connection.get_account_information()
    logger.info(
        f"Connected | login={info['login']}  server={info.get('server', '?')}  "
        f"balance={info['balance']:.2f} {info['currency']}"
    )
    return api, connection


async def disconnect(api) -> None:
    await api.close()
    logger.info("MetaAPI connection closed.")


# ── Market Data ───────────────────────────────────────────────────────────────

async def get_ohlcv(connection, symbol: str, timeframe: str,
                    n_bars: int = 300) -> pd.DataFrame:
    """
    Fetch the last n_bars OHLCV candles.

    Bar at index -1 is the currently forming (live) bar.
    Bar at index -2 is the last completed bar — use this for signals.

    Returns DataFrame with columns: time, open, high, low, close, tick_volume
    """
    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        raise ValueError(f"Unknown timeframe '{timeframe}'. Use: {list(TIMEFRAME_MAP)}")

    end_time = datetime.now(timezone.utc)
    candles = await connection.get_historical_candles(symbol, tf, end_time, n_bars)

    if not candles:
        raise RuntimeError(f"No candles returned for {symbol}/{timeframe}")

    df = pd.DataFrame([{
        "time":        c["time"],
        "open":        c["open"],
        "high":        c["high"],
        "low":         c["low"],
        "close":       c["close"],
        "tick_volume": c.get("tickVolume", 0),
    } for c in candles])

    df = df.sort_values("time").reset_index(drop=True)
    return df


async def get_current_price(connection, symbol: str) -> dict:
    """Return current ask and bid prices."""
    price = await connection.get_symbol_price(symbol)
    return {"ask": price["ask"], "bid": price["bid"]}


# ── Account & Symbol ──────────────────────────────────────────────────────────

async def get_account_info(connection) -> dict:
    info = await connection.get_account_information()
    return {
        "login":    info["login"],
        "balance":  info["balance"],
        "equity":   info["equity"],
        "currency": info["currency"],
        "server":   info.get("server", "unknown"),
        "leverage": info.get("leverage", 0),
    }


async def get_symbol_info(connection, symbol: str) -> dict:
    """
    Return trading specs for symbol.
    Keys: digits, volume_min, volume_max, volume_step, tick_size, tick_value
    """
    spec = await connection.get_symbol_specification(symbol)
    logger.debug(f"Symbol spec keys: {list(spec.keys())}")

    # Field names vary across brokers/MetaAPI versions — try both forms.
    volume_min  = spec.get("minVolume")  or spec.get("volumeMin",  0.01)
    volume_max  = spec.get("maxVolume")  or spec.get("volumeMax",  500.0)
    volume_step = spec.get("volumeStep", 0.01)
    tick_size   = spec.get("tickSize",   0.01)
    digits      = spec.get("digits",     2)

    # tickValue is not always provided by the broker.
    # Fall back to contractSize × tickSize (correct for XAUUSD/USD accounts).
    tick_value = spec.get("tickValue")
    if not tick_value:
        contract_size = spec.get("contractSize", 100)
        tick_value = tick_size * contract_size
        logger.info(
            f"tickValue absent in spec — computed: "
            f"{tick_size} × {contract_size} = {tick_value}"
        )

    return {
        "digits":      digits,
        "volume_min":  volume_min,
        "volume_max":  volume_max,
        "volume_step": volume_step,
        "tick_size":   tick_size,
        "tick_value":  tick_value,
    }


# ── Orders ────────────────────────────────────────────────────────────────────

async def place_market_order(
    connection,
    symbol: str,
    order_type: str,        # "BUY" or "SELL"
    volume: float,
    sl: float,
    tp: float,
    magic: int,
    comment: str,
    digits: int,
) -> dict:
    """
    Place a market order with stop loss and take profit.
    Raises an exception if the order is rejected.
    Returns the result dict from MetaAPI.
    """
    sl = round(sl, digits)
    tp = round(tp, digits)
    opts = {"comment": comment, "magic": magic}

    if order_type == "BUY":
        result = await connection.create_market_buy_order(symbol, volume, sl, tp, opts)
    else:
        result = await connection.create_market_sell_order(symbol, volume, sl, tp, opts)

    logger.info(
        f"Order placed | {order_type} {volume} {symbol}  "
        f"SL={sl}  TP={tp}  orderId={result.get('orderId', '?')}"
    )
    return result


# ── Positions ─────────────────────────────────────────────────────────────────

async def get_open_positions(connection, symbol: str, magic: int) -> list:
    """Return open positions for symbol belonging to this bot (matched by magic number)."""
    all_positions = await connection.get_positions()
    return [
        p for p in all_positions
        if p["symbol"] == symbol and p.get("magic") == magic
    ]


async def close_position(connection, position: dict) -> None:
    """Close a single open position at market price."""
    pos_id = position["id"]
    logger.info(
        f"Closing position #{pos_id}  "
        f"{position['type'].replace('POSITION_TYPE_', '')}  "
        f"{position['volume']} {position['symbol']}"
    )
    await connection.close_position(pos_id)

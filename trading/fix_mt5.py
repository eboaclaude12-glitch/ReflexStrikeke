"""
Run this once to restore mt5_connector.py
Usage: python3 fix_mt5.py
"""
import os

content = '''"""
ReflexStrike -- MetaAPI Connector
"""
import logging
import os
import ssl
from datetime import datetime, timezone

import certifi
import pandas as pd
from metaapi_cloud_sdk import MetaApi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

logger = logging.getLogger(__name__)

TIMEFRAME_MAP = {
    "M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m",
    "H1": "1h", "H4": "4h", "D1": "1d", "W1": "1w",
}


async def connect(token, account_id):
    api = MetaApi(token)
    logger.info("Fetching MT5 account from MetaAPI...")
    account = await api.metatrader_account_api.get_account(account_id)
    if account.state not in ("DEPLOYED", "DEPLOYING"):
        logger.info("Deploying account...")
        await account.deploy()
    logger.info("Waiting for broker connection...")
    await account.wait_connected()
    connection = account.get_rpc_connection()
    await connection.connect()
    logger.info("Waiting for data sync...")
    await connection.wait_synchronized()
    info = await connection.get_account_information()
    login = str(info["login"])
    bal = str(info["balance"])
    cur = str(info["currency"])
    logger.info("Connected | login=" + login + " balance=" + bal + " " + cur)
    return api, connection


async def disconnect(api):
    await api.close()
    logger.info("MetaAPI connection closed.")


async def get_ohlcv(connection, symbol, timeframe, n_bars=300):
    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        raise ValueError("Unknown timeframe " + timeframe)
    end_time = datetime.now(timezone.utc)
    candles = await connection.get_historical_candles(symbol, tf, end_time, n_bars)
    if not candles:
        raise RuntimeError("No candles returned for " + symbol)
    df = pd.DataFrame([{
        "time": c["time"],
        "open": c["open"],
        "high": c["high"],
        "low": c["low"],
        "close": c["close"],
        "tick_volume": c.get("tickVolume", 0),
    } for c in candles])
    df = df.sort_values("time").reset_index(drop=True)
    return df


async def get_current_price(connection, symbol):
    price = await connection.get_symbol_price(symbol)
    return {"ask": price["ask"], "bid": price["bid"]}


async def get_account_info(connection):
    info = await connection.get_account_information()
    return {
        "login": info["login"],
        "balance": info["balance"],
        "equity": info["equity"],
        "currency": info["currency"],
        "server": info.get("server", "unknown"),
        "leverage": info.get("leverage", 0),
    }


async def get_symbol_info(connection, symbol):
    spec = await connection.get_symbol_specification(symbol)
    volume_min = spec.get("minVolume") or spec.get("volumeMin", 0.01)
    volume_max = spec.get("maxVolume") or spec.get("volumeMax", 500.0)
    volume_step = spec.get("volumeStep", 0.01)
    tick_size = spec.get("tickSize", 0.01)
    digits = spec.get("digits", 2)
    tick_value = spec.get("tickValue")
    if not tick_value:
        contract_size = spec.get("contractSize", 100)
        tick_value = tick_size * contract_size
        logger.info("tickValue computed: " + str(tick_value))
    return {
        "digits": digits,
        "volume_min": volume_min,
        "volume_max": volume_max,
        "volume_step": volume_step,
        "tick_size": tick_size,
        "tick_value": tick_value,
    }


async def place_market_order(connection, symbol, order_type, volume, sl, tp, magic, comment, digits):
    sl = round(sl, digits)
    tp = round(tp, digits)
    opts = {"comment": comment, "magic": magic}
    if order_type == "BUY":
        result = await connection.create_market_buy_order(symbol, volume, sl, tp, opts)
    else:
        result = await connection.create_market_sell_order(symbol, volume, sl, tp, opts)
    logger.info("Order placed | " + order_type + " " + str(volume) + " " + symbol)
    return result


async def get_open_positions(connection, symbol, magic):
    all_positions = await connection.get_positions()
    return [p for p in all_positions if p["symbol"] == symbol and p.get("magic") == magic]


async def close_position(connection, position):
    pos_id = position["id"]
    logger.info("Closing position #" + str(pos_id))
    await connection.close_position(pos_id)
'''

script_dir = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(script_dir, "mt5_connector.py")

with open(out_path, "w") as f:
    f.write(content)

print("mt5_connector.py restored successfully!")

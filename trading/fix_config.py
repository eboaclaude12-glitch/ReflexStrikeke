"""
Run this once to restore your config.py with all credentials.
Usage: python3 fix_config.py
"""

config = """\
# ─────────────────────────────────────────────
# ReflexStrike Trading Bot — Configuration
# Strategy: EMA 20/50 Crossover + RSI 14 Filter
#           + Supply & Demand Zones
#           + Fair Value Gaps (FVG)
#           + Candlestick Price Action
# Market:   XAUUSD (Gold Futures) | H1
# Broker:   FTMO on MetaTrader 5
# ─────────────────────────────────────────────

# --- MetaAPI Credentials ---
METAAPI_TOKEN      = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI3YTMxMWMzZTIwZWYzOGE4ZmNmZmRkYzExOWUwZDliNiIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVzdC1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcnBjLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6d3M6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJtZXRhc3RhdHMtYXBpIiwibWV0aG9kcyI6WyJtZXRhc3RhdHMtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6InJpc2stbWFuYWdlbWVudC1hcGkiLCJtZXRob2RzIjpbInJpc2stbWFuYWdlbWVudC1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoiY29weWZhY3RvcnktYXBpIiwibWV0aG9kcyI6WyJjb3B5ZmFjdG9yeS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibXQtbWFuYWdlci1hcGkiLCJtZXRob2RzIjpbIm10LW1hbmFnZXItYXBpOnJlc3Q6ZGVhbGluZzoqOioiLCJtdC1tYW5hZ2VyLWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJiaWxsaW5nLWFwaSIsIm1ldGhvZHMiOlsiYmlsbGluZy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiN2EzMTFjM2UyMGVmMzhhOGZjZmZkZGMxMTllMGQ5YjYiLCJpYXQiOjE3NzYxODgxMzB9.EEtmxnID9OMbFsUdtRR-fnHQ7jYTpEjH2KPn_c5j9pEq48_BczUM7rSBoZlAZluN4fGUPVshgTSUpxTo0DjWkr4l9HuH42mX3VAj7qioyEz1akfuqDb2y4Ki-cqd0C1u5PVJpfcQwjwWxuzn3R9KqkSyjDMR5s85UX8QFx2Z27Wr9MLnNwAeTOnuDeOyKCdaosq3UMgMdhDb6ysWC7AR5MjjUwiz6MTcjN5oiri6L0eN3O4uGRhH8d3eQpWULbFszEGpxIDFrMAdP9msrTNmXopRrvNrPaqiLk3LwTgQ-XOP6Jw9T5eXAjkUhKLSA_3DhECKu1j1HDnhPICJLbnny1W_g4ud0MhCHWqJ136gK3_uVrBmFj_bQlQNxeKNsvu2RgwS1vmOVoUGs2Ef00r600Gnk4NoG3GhARHg8EDOFn6qKdQBFTaID0Och_3P0DbkGOZAO_B2MsCbFje0hAuIuyBIDkxUAcM9IYf3MuaCXOXxsu8jUsJyH3RxJs9ir-ko44cPurFyx9LYORuZ1zcotZynrLrQVyW5Q5wAOLDECddxpPEy2ihbJsSet-RPa75xXQN56qBV49OEadGnF86SUhZvbGkTVKhYTMDIODvqX0bhlUMQa4y-arQZwnkAvxE6iF-mq626oFQlBVCMb6o5ncwm2J2sx7UBwWXfTUr9rLQ"
METAAPI_ACCOUNT_ID = "1a99bdc3-d742-4770-bed6-df140370c319"

# --- Instrument ---
SYMBOL = "XAUUSD"
TIMEFRAME = "H1"
BARS_HISTORY = 300

# --- EMA Settings ---
FAST_EMA = 20
SLOW_EMA = 50

# --- RSI Settings ---
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# --- ATR Settings (Stop Loss / Take Profit) ---
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.5
ATR_TP_MULTIPLIER = 3.0

# --- Risk Management ---
RISK_PERCENT = 2.0

# --- FTMO Safety Limits ---
FTMO_DAILY_LOSS_LIMIT = 5.0
FTMO_MAX_DRAWDOWN = 10.0

# --- Order Settings ---
MAGIC_NUMBER = 20050001
TRADE_COMMENT = "ReflexStrike_v2"
MAX_OPEN_TRADES = 1

# --- Supply & Demand Zones ---
ZONE_SWING_WINDOW   = 5
ZONE_ATR_WIDTH      = 0.5
ZONE_MIN_IMPULSE    = 1.5
ZONE_MAX_ZONES      = 5

# --- Fair Value Gaps (FVG) ---
FVG_LOOKBACK        = 30
FVG_MIN_GAP_ATR     = 0.1
FVG_PROXIMITY_ATR   = 0.5

# --- Confluence Scoring ---
MIN_CONFLUENCE_SCORE = 1

# --- Telegram Notifications ---
TELEGRAM_ENABLED = True
TELEGRAM_TOKEN   = "8680399394:AAFYVTHxIGa30vo-3TIznXk8_Dkh5LGFwnI"
TELEGRAM_CHAT_ID = "1039051272"

# --- Loop Settings ---
SLEEP_SECONDS = 10
"""

import os
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "config.py")

with open(config_path, "w") as f:
    f.write(config)

print("config.py restored successfully!")

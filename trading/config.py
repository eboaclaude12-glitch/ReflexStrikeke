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
# 1. Sign up free at https://app.metaapi.cloud
# 2. Add your FTMO MT5 account under "MetaTrader Accounts"
# 3. Copy your API token and Account ID here
METAAPI_TOKEN      = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI3YTMxMWMzZTIwZWYzOGE4ZmNmZmRkYzExOWUwZDliNiIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVzdC1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcnBjLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6d3M6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJtZXRhc3RhdHMtYXBpIiwibWV0aG9kcyI6WyJtZXRhc3RhdHMtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6InJpc2stbWFuYWdlbWVudC1hcGkiLCJtZXRob2RzIjpbInJpc2stbWFuYWdlbWVudC1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoiY29weWZhY3RvcnktYXBpIiwibWV0aG9kcyI6WyJjb3B5ZmFjdG9yeS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibXQtbWFuYWdlci1hcGkiLCJtZXRob2RzIjpbIm10LW1hbmFnZXItYXBpOnJlc3Q6ZGVhbGluZzoqOioiLCJtdC1tYW5hZ2VyLWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJiaWxsaW5nLWFwaSIsIm1ldGhvZHMiOlsiYmlsbGluZy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiN2EzMTFjM2UyMGVmMzhhOGZjZmZkZGMxMTllMGQ5YjYiLCJpYXQiOjE3NzYxODgxMzB9.EEtmxnID9OMbFsUdtRR-fnHQ7jYTpEjH2KPn_c5j9pEq48_BczUM7rSBoZlAZluN4fGUPVshgTSUpxTo0DjWkr4l9HuH42mX3VAj7qioyEz1akfuqDb2y4Ki-cqd0C1u5PVJpfcQwjwWxuzn3R9KqkSyjDMR5s85UX8QFx2Z27Wr9MLnNwAeTOnuDeOyKCdaosq3UMgMdhDb6ysWC7AR5MjjUwiz6MTcjN5oiri6L0eN3O4uGRhH8d3eQpWULbFszEGpxIDFrMAdP9msrTNmXopRrvNrPaqiLk3LwTgQ-XOP6Jw9T5eXAjkUhKLSA_3DhECKu1j1HDnhPICJLbnny1W_g4ud0MhCHWqJ136gK3_uVrBmFj_bQlQNxeKNsvu2RgwS1vmOVoUGs2Ef00r600Gnk4NoG3GhARHg8EDOFn6qKdQBFTaID0Och_3P0DbkGOZAO_B2MsCbFje0hAuIuyBIDkxUAcM9IYf3MuaCXOXxsu8jUsJyH3RxJs9ir-ko44cPurFyx9LYORuZ1zcotZynrLrQVyW5Q5wAOLDECddxpPEy2ihbJsSet-RPa75xXQN56qBV49OEadGnF86SUhZvbGkTVKhYTMDIODvqX0bhlUMQa4y-arQZwnkAvxE6iF-mq626oFQlBVCMb6o5ncwm2J2sx7UBwWXfTUr9rLQ"
METAAPI_ACCOUNT_ID = "1a99bdc3-d742-4770-bed6-df140370c319"

# --- Instrument ---
SYMBOL = "XAUUSD"
TIMEFRAME = "H1"          # M1, M5, M15, M30, H1, H4, D1
BARS_HISTORY = 300        # Number of historical bars to load

# --- EMA Settings ---
FAST_EMA = 20
SLOW_EMA = 50

# --- RSI Settings ---
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70       # Do NOT buy above this level
RSI_OVERSOLD = 30         # Do NOT sell below this level

# --- ATR Settings (Stop Loss / Take Profit) ---
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.5  # Stop loss  = ATR * 1.5
ATR_TP_MULTIPLIER = 3.0  # Take profit = ATR * 3.0  → 2:1 RR

# --- Risk Management ---
RISK_PERCENT = 2.0        # Risk 2% of account balance per trade

# --- FTMO Safety Limits ---
FTMO_DAILY_LOSS_LIMIT = 5.0     # Max daily loss as % of initial balance (FTMO rule)
FTMO_MAX_DRAWDOWN = 10.0        # Max total drawdown as % of initial balance (FTMO rule)

# --- Order Settings ---
MAGIC_NUMBER = 20050001          # Unique identifier for this bot's orders
TRADE_COMMENT = "ReflexStrike_v2"
MAX_OPEN_TRADES = 1              # Maximum simultaneous positions per symbol

# --- Supply & Demand Zones ---
ZONE_SWING_WINDOW   = 5     # bars on each side to define a swing point
ZONE_ATR_WIDTH      = 0.5   # zone height in ATR units
ZONE_MIN_IMPULSE    = 1.5   # minimum impulse from zone (× ATR) to validate it
ZONE_MAX_ZONES      = 5     # max active zones to track

# --- Fair Value Gaps (FVG) ---
FVG_LOOKBACK        = 30    # bars to look back for FVGs
FVG_MIN_GAP_ATR     = 0.1   # minimum gap size (× ATR) to qualify as FVG
FVG_PROXIMITY_ATR   = 0.5   # price within this many ATRs of FVG counts as "near"

# --- Confluence Scoring ---
# Signal requires: EMA crossover (mandatory) + RSI filter (mandatory)
# +1 point each for: price at S/D zone, price near FVG, matching PA pattern
# MIN_CONFLUENCE_SCORE = 0  → trade any crossover that passes RSI
# MIN_CONFLUENCE_SCORE = 1  → at least one extra confluence factor (recommended)
# MIN_CONFLUENCE_SCORE = 2  → two extra factors (very selective)
MIN_CONFLUENCE_SCORE = 1

# --- Telegram Notifications ---
# Follow the 5-step setup in trading/notifier.py to get these values
TELEGRAM_ENABLED = True
TELEGRAM_TOKEN   = "8680399394:AAFYVTHxIGa30vo-3TIznXk8_Dkh5LGFwnI"
TELEGRAM_CHAT_ID = "1039051272"

# --- Loop Settings ---
SLEEP_SECONDS = 10               # Polling interval in seconds

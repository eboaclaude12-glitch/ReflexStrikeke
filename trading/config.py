# ─────────────────────────────────────────────
# ReflexStrike Trading Bot — Configuration
# Strategy: EMA 20/50 Crossover + RSI 14 Filter
#           + Supply & Demand Zones
#           + Fair Value Gaps (FVG)
#           + Candlestick Price Action
# Market:   XAUUSD (Gold Futures) | H1
# Broker:   FTMO on MetaTrader 5
# ─────────────────────────────────────────────

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

# --- Loop Settings ---
SLEEP_SECONDS = 10               # Polling interval in seconds

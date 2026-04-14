"""
ReflexStrike Strategy Module
─────────────────────────────
EMA 20/50 Crossover + RSI 14 Filter on XAUUSD H1

Entry rules:
  BUY  → EMA20 crosses ABOVE EMA50 AND RSI < 70 (not overbought)
  SELL → EMA20 crosses BELOW EMA50 AND RSI > 30 (not oversold)

Signals are computed on the LAST COMPLETED BAR (index -2) to avoid
lookahead / repainting on the live (still-forming) bar.

Exit:
  Stop Loss  = entry ± ATR(14) × 1.5
  Take Profit = entry ± ATR(14) × 3.0  (2:1 reward/risk)
  Opposite crossover also closes the current trade.
"""

import pandas as pd


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, prev_close = df["high"], df["low"], df["close"].shift()
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(com=period - 1, adjust=False).mean()


def compute_indicators(df: pd.DataFrame, fast: int, slow: int,
                       rsi_period: int, atr_period: int) -> pd.DataFrame:
    """
    Attach all indicator columns to a copy of df and return it.
    Expects df columns: open, high, low, close, tick_volume, time
    """
    df = df.copy()
    df["ema_fast"] = _ema(df["close"], fast)
    df["ema_slow"] = _ema(df["close"], slow)
    df["rsi"] = _rsi(df["close"], rsi_period)
    df["atr"] = _atr(df, atr_period)
    return df


def generate_signal(df: pd.DataFrame,
                    fast: int, slow: int,
                    rsi_period: int, atr_period: int,
                    rsi_overbought: float, rsi_oversold: float):
    """
    Returns:
        signal (int)  : 1=BUY, -1=SELL, 0=no signal
        atr    (float): ATR value of the last completed bar (for SL/TP sizing)
        indicators (dict): snapshot of key values (for logging)

    Raises ValueError if df has fewer than slow+2 rows.
    """
    min_bars = slow + rsi_period + 2
    if len(df) < min_bars:
        raise ValueError(
            f"Not enough bars: need at least {min_bars}, got {len(df)}"
        )

    df = compute_indicators(df, fast, slow, rsi_period, atr_period)

    # Index -1 is the live (unfinished) bar — never trade on it
    # Index -2 is the last completed bar — use this for signals
    # Index -3 is the bar before that — used to confirm crossover direction
    cur = df.iloc[-2]
    prev = df.iloc[-3]

    indicators = {
        "ema_fast": round(cur.ema_fast, 5),
        "ema_slow": round(cur.ema_slow, 5),
        "rsi":      round(cur.rsi, 2),
        "atr":      round(cur.atr, 5),
        "close":    round(cur.close, 5),
        "bar_time": cur.time,
    }

    # Bullish crossover: EMA20 crossed above EMA50 on the completed bar
    if prev.ema_fast <= prev.ema_slow and cur.ema_fast > cur.ema_slow:
        if cur.rsi < rsi_overbought:
            return 1, cur.atr, indicators

    # Bearish crossover: EMA20 crossed below EMA50 on the completed bar
    if prev.ema_fast >= prev.ema_slow and cur.ema_fast < cur.ema_slow:
        if cur.rsi > rsi_oversold:
            return -1, cur.atr, indicators

    return 0, cur.atr, indicators

"""
ReflexStrike Strategy Module — v2
──────────────────────────────────
Baseline signal: EMA 20/50 crossover + RSI 14 filter
Confluence filters (scored):
  [A] Price at Supply / Demand zone   → +1
  [B] Unmitigated Fair Value Gap      → +1
  [C] Matching price action pattern   → +1

Entry logic:
  1. EMA crossover must be present              (hard requirement)
  2. RSI must pass the overbought/oversold check (hard requirement)
  3. Confluence score (A + B + C) ≥ MIN_CONFLUENCE_SCORE

Signals fire only on the LAST COMPLETED BAR (index -2) to avoid
lookahead / repainting on the still-forming live bar.

Exit (handled in main.py):
  Stop Loss  = entry ± ATR(14) × ATR_SL_MULTIPLIER
  Take Profit = entry ± ATR(14) × ATR_TP_MULTIPLIER  (2:1 RR default)
  Opposite crossover also closes the current trade.
"""

import pandas as pd

from price_action import (
    detect_supply_demand_zones,
    price_at_zone,
    detect_fvg,
    price_near_fvg,
    detect_candle_pattern,
)


# ── Private indicator helpers ─────────────────────────────────────────────────

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta    = series.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs       = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    h, l, pc = df["high"], df["low"], df["close"].shift()
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, adjust=False).mean()


# ── Public: attach indicators to df ──────────────────────────────────────────

def compute_indicators(df: pd.DataFrame, fast: int, slow: int,
                       rsi_period: int, atr_period: int) -> pd.DataFrame:
    """Return a copy of df with ema_fast, ema_slow, rsi, atr columns attached."""
    df = df.copy()
    df["ema_fast"] = _ema(df["close"], fast)
    df["ema_slow"] = _ema(df["close"], slow)
    df["rsi"]      = _rsi(df["close"], rsi_period)
    df["atr"]      = _atr(df, atr_period)
    return df


# ── Public: main signal generator ────────────────────────────────────────────

def generate_signal(
    df: pd.DataFrame,
    # EMA / RSI / ATR
    fast: int,
    slow: int,
    rsi_period: int,
    atr_period: int,
    rsi_overbought: float,
    rsi_oversold: float,
    # Supply & Demand
    swing_window: int   = 5,
    zone_atr_width: float = 0.5,
    min_impulse_atr: float = 1.5,
    max_zones: int      = 5,
    # FVG
    fvg_lookback: int   = 30,
    fvg_min_gap_atr: float = 0.1,
    fvg_proximity_atr: float = 0.5,
    # Confluence gate
    min_confluence: int = 1,
) -> tuple[int, float, dict]:
    """
    Evaluate the full strategy on df and return the trading decision.

    Returns:
        signal    (int)  : 1=BUY, -1=SELL, 0=no signal
        atr_value (float): ATR of the last completed bar (used for SL/TP sizing)
        details   (dict) : full snapshot of indicators + confluence breakdown

    Raises ValueError if df is too short to compute indicators.
    """
    min_bars = slow + rsi_period + 4   # +4 for crossover context and PA check
    if len(df) < min_bars:
        raise ValueError(f"Need ≥{min_bars} bars, got {len(df)}")

    df = compute_indicators(df, fast, slow, rsi_period, atr_period)

    cur  = df.iloc[-2]   # last COMPLETED bar  — signals fire here
    prev = df.iloc[-3]   # bar before it       — crossover context

    atr_value     = float(cur.atr)
    current_close = float(cur.close)

    # ── LAYER 1: EMA crossover (hard requirement) ─────────────────────────────
    bullish_cross = (prev.ema_fast <= prev.ema_slow) and (cur.ema_fast > cur.ema_slow)
    bearish_cross = (prev.ema_fast >= prev.ema_slow) and (cur.ema_fast < cur.ema_slow)

    if not bullish_cross and not bearish_cross:
        return 0, atr_value, _details(cur, atr_value, raw=0, rsi_ok=False,
                                      at_zone=False, zone=None,
                                      near_fvg=False, fvg=None,
                                      candle="none", pa_ok=False, score=0)

    raw_signal = 1 if bullish_cross else -1

    # ── LAYER 2: RSI filter (hard requirement) ────────────────────────────────
    rsi_ok = (
        (raw_signal ==  1 and float(cur.rsi) < rsi_overbought) or
        (raw_signal == -1 and float(cur.rsi) > rsi_oversold)
    )

    if not rsi_ok:
        return 0, atr_value, _details(cur, atr_value, raw=raw_signal, rsi_ok=False,
                                      at_zone=False, zone=None,
                                      near_fvg=False, fvg=None,
                                      candle="none", pa_ok=False, score=0)

    # ── LAYER 3A: Supply / Demand zone ───────────────────────────────────────
    zones = detect_supply_demand_zones(
        df,
        swing_window=swing_window,
        atr_period=atr_period,
        zone_atr_width=zone_atr_width,
        min_impulse_atr=min_impulse_atr,
        max_zones=max_zones,
    )
    zone_type          = "demand" if raw_signal == 1 else "supply"
    at_zone, hit_zone  = price_at_zone(
        current_close, zones, zone_type,
        buffer=atr_value * 0.3,   # price approaching zone also counts
    )

    # ── LAYER 3B: Fair Value Gap ──────────────────────────────────────────────
    fvgs = detect_fvg(
        df,
        lookback=fvg_lookback,
        atr_period=atr_period,
        min_gap_atr=fvg_min_gap_atr,
    )
    fvg_dir           = "bullish" if raw_signal == 1 else "bearish"
    near_fvg, hit_fvg = price_near_fvg(
        current_close, fvgs, fvg_dir,
        current_atr=atr_value,
        proximity_atr=fvg_proximity_atr,
    )

    # ── LAYER 3C: Candlestick price action ────────────────────────────────────
    candle   = detect_candle_pattern(df)
    pa_ok    = candle["direction"] == raw_signal

    # ── Confluence gate ───────────────────────────────────────────────────────
    score = int(at_zone) + int(near_fvg) + int(pa_ok)   # max = 3

    det = _details(cur, atr_value, raw=raw_signal, rsi_ok=True,
                   at_zone=at_zone, zone=hit_zone,
                   near_fvg=near_fvg, fvg=hit_fvg,
                   candle=candle["pattern"], pa_ok=pa_ok, score=score)

    if score < min_confluence:
        return 0, atr_value, det

    return raw_signal, atr_value, det


# ── Private: build details dict ───────────────────────────────────────────────

def _details(cur, atr_value, raw, rsi_ok,
             at_zone, zone, near_fvg, fvg, candle, pa_ok, score) -> dict:
    return {
        # Core indicators
        "bar_time":       cur.time,
        "close":          round(float(cur.close),    5),
        "ema_fast":       round(float(cur.ema_fast), 5),
        "ema_slow":       round(float(cur.ema_slow), 5),
        "rsi":            round(float(cur.rsi),      2),
        "atr":            round(atr_value,           5),
        # Signal direction before confluence gate
        "crossover":      "bullish" if raw == 1 else "bearish" if raw == -1 else "none",
        # Confluence breakdown
        "rsi_ok":         rsi_ok,
        "at_zone":        at_zone,
        "zone":           zone,
        "near_fvg":       near_fvg,
        "fvg":            fvg,
        "candle_pattern": candle,
        "pa_confirmed":   pa_ok,
        "score":          score,
    }

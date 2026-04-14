"""
ReflexStrike — Price Action Module
────────────────────────────────────
Three analysis layers used as confluence filters on top of EMA/RSI:

  1. Supply & Demand Zones
     Swing-based zones where institutional activity caused strong impulse moves.
     Demand zones → support (look to BUY).
     Supply zones  → resistance (look to SELL).

  2. Fair Value Gaps (FVG / Imbalance)
     Three-candle patterns where the middle candle leaves a price gap.
     Bullish FVG → gap is support (price expected to bounce up from it).
     Bearish FVG → gap is resistance (price expected to reject down from it).

  3. Candlestick Price Action Patterns
     Reversal patterns on the last completed bar:
       Bullish: bullish_engulfing, hammer, bullish_pin_bar
       Bearish: bearish_engulfing, shooting_star, bearish_pin_bar
"""

import pandas as pd


# ── Shared helper ─────────────────────────────────────────────────────────────

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, pc = df["high"], df["low"], df["close"].shift()
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, adjust=False).mean()


# ══════════════════════════════════════════════════════════════════════════════
# 1. SUPPLY & DEMAND ZONES
# ══════════════════════════════════════════════════════════════════════════════

def detect_supply_demand_zones(
    df: pd.DataFrame,
    swing_window: int = 5,
    atr_period: int = 14,
    zone_atr_width: float = 0.5,
    min_impulse_atr: float = 1.5,
    max_zones: int = 5,
) -> list[dict]:
    """
    Detect active supply and demand zones from OHLCV history.

    Algorithm:
      • Find swing highs (local maxima within ±swing_window bars).
      • Find swing lows  (local minima within ±swing_window bars).
      • Validate each swing by requiring a strong impulse move away from it:
          swing high → price dropped ≥ min_impulse_atr × ATR  → SUPPLY zone
          swing low  → price rallied ≥ min_impulse_atr × ATR  → DEMAND zone
      • Zone boundaries:
          Demand: [swing_low,  swing_low  + zone_atr_width × ATR]
          Supply: [swing_high − zone_atr_width × ATR, swing_high]
      • Invalidate zone if a subsequent close breaks through it.

    Returns up to max_zones active zones, most recent first.
    Each dict: {type, high, low, strength}
    """
    atr = _atr(df, atr_period)
    roll_window = 2 * swing_window + 1

    # Rolling max/min with center=True to detect swings (NaN at edges is fine)
    swing_high_mask = df["high"] == df["high"].rolling(roll_window, center=True).max()
    swing_low_mask  = df["low"]  == df["low"].rolling(roll_window, center=True).min()

    zones: list[dict] = []
    search_end   = len(df) - swing_window - 1   # exclude bars too close to live edge
    search_start = swing_window

    for i in reversed(range(search_start, search_end)):
        if len(zones) >= max_zones:
            break

        bar_atr = float(atr.iloc[i])
        if bar_atr == 0:
            continue

        # ── Supply zone (swing high) ──────────────────────────────────────────
        if swing_high_mask.iloc[i]:
            pivot = float(df["high"].iloc[i])
            future = df.iloc[i + 1: i + 11]
            if future.empty:
                continue
            max_drop = pivot - float(future["low"].min())
            if max_drop >= min_impulse_atr * bar_atr:
                z_low  = pivot - zone_atr_width * bar_atr
                z_high = pivot
                # Invalidated if any close pierced above the zone top after formation
                if not (df["close"].iloc[i + 1:] > z_high).any():
                    zones.append({
                        "type":     "supply",
                        "high":     z_high,
                        "low":      z_low,
                        "strength": round(max_drop / bar_atr, 2),
                    })

        # ── Demand zone (swing low) ───────────────────────────────────────────
        if swing_low_mask.iloc[i]:
            pivot = float(df["low"].iloc[i])
            future = df.iloc[i + 1: i + 11]
            if future.empty:
                continue
            max_rally = float(future["high"].max()) - pivot
            if max_rally >= min_impulse_atr * bar_atr:
                z_low  = pivot
                z_high = pivot + zone_atr_width * bar_atr
                # Invalidated if any close pierced below the zone bottom
                if not (df["close"].iloc[i + 1:] < z_low).any():
                    zones.append({
                        "type":     "demand",
                        "high":     z_high,
                        "low":      z_low,
                        "strength": round(max_rally / bar_atr, 2),
                    })

    return zones[:max_zones]


def price_at_zone(
    current_price: float,
    zones: list[dict],
    zone_type: str,
    buffer: float = 0.0,
) -> tuple[bool, dict | None]:
    """
    Returns (True, zone) if current_price is inside or within buffer of a zone.
    buffer: extra price distance beyond zone edges (e.g. 0.3 × ATR for approach).
    """
    for zone in zones:
        if zone["type"] != zone_type:
            continue
        if (zone["low"] - buffer) <= current_price <= (zone["high"] + buffer):
            return True, zone
    return False, None


# ══════════════════════════════════════════════════════════════════════════════
# 2. FAIR VALUE GAPS
# ══════════════════════════════════════════════════════════════════════════════

def detect_fvg(
    df: pd.DataFrame,
    lookback: int = 30,
    atr_period: int = 14,
    min_gap_atr: float = 0.1,
) -> list[dict]:
    """
    Detect Fair Value Gaps (imbalances) in the last `lookback` bars.

    Bullish FVG (acts as support):
      candle[i].high  <  candle[i+2].low
      Gap = (candle[i].high, candle[i+2].low)
      Filled (invalidated) when price closes BELOW gap_low.

    Bearish FVG (acts as resistance):
      candle[i].low   >  candle[i+2].high
      Gap = (candle[i+2].high, candle[i].low)
      Filled (invalidated) when price closes ABOVE gap_high.

    Only gaps larger than min_gap_atr × ATR are returned.

    Returns list of dicts: {type, gap_high, gap_low, gap_mid, filled}
    """
    atr = _atr(df, atr_period)
    fvgs: list[dict] = []

    start = max(0, len(df) - lookback - 2)

    for i in range(start, len(df) - 2):
        bar_atr = float(atr.iloc[i])
        if bar_atr == 0:
            continue

        h0 = float(df["high"].iloc[i])
        l0 = float(df["low"].iloc[i])
        h2 = float(df["high"].iloc[i + 2])
        l2 = float(df["low"].iloc[i + 2])

        # ── Bullish FVG ───────────────────────────────────────────────────────
        if l2 > h0:
            gap_low  = h0
            gap_high = l2
            gap_size = gap_high - gap_low
            if gap_size >= min_gap_atr * bar_atr:
                subsequent_closes = df["close"].iloc[i + 3:]
                filled = bool((subsequent_closes < gap_low).any())
                fvgs.append({
                    "type":     "bullish",
                    "gap_high": gap_high,
                    "gap_low":  gap_low,
                    "gap_mid":  (gap_high + gap_low) / 2,
                    "filled":   filled,
                })

        # ── Bearish FVG ───────────────────────────────────────────────────────
        elif h2 < l0:
            gap_high = l0
            gap_low  = h2
            gap_size = gap_high - gap_low
            if gap_size >= min_gap_atr * bar_atr:
                subsequent_closes = df["close"].iloc[i + 3:]
                filled = bool((subsequent_closes > gap_high).any())
                fvgs.append({
                    "type":     "bearish",
                    "gap_high": gap_high,
                    "gap_low":  gap_low,
                    "gap_mid":  (gap_high + gap_low) / 2,
                    "filled":   filled,
                })

    return fvgs


def price_near_fvg(
    current_price: float,
    fvgs: list[dict],
    direction: str,
    current_atr: float,
    proximity_atr: float = 0.5,
) -> tuple[bool, dict | None]:
    """
    Returns (True, fvg) if current_price is within or approaching an unmitigated FVG.
    proximity_atr: extend check by this many ATRs beyond the gap edges.
    Scans from most recent FVG first.
    """
    buffer = proximity_atr * current_atr
    for fvg in reversed(fvgs):
        if fvg["type"] != direction or fvg["filled"]:
            continue
        if (fvg["gap_low"] - buffer) <= current_price <= (fvg["gap_high"] + buffer):
            return True, fvg
    return False, None


# ══════════════════════════════════════════════════════════════════════════════
# 3. CANDLESTICK PRICE ACTION PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

def detect_candle_pattern(df: pd.DataFrame) -> dict:
    """
    Detect bullish/bearish reversal patterns on the last completed bar (index -2).
    Uses the previous bar (index -3) for engulfing context.

    Bullish patterns  → direction = +1
      bullish_engulfing : current body fully engulfs previous bearish body
      hammer            : small body at top, lower wick ≥ 2× body, tiny upper wick
      bullish_pin_bar   : lower wick ≥ 60% of total range, close in upper 40%

    Bearish patterns  → direction = -1
      bearish_engulfing : current body fully engulfs previous bullish body
      shooting_star     : small body at bottom, upper wick ≥ 2× body, tiny lower wick
      bearish_pin_bar   : upper wick ≥ 60% of total range, close in lower 40%

    Returns dict: {pattern: str, direction: int}
    """
    if len(df) < 4:
        return {"pattern": "none", "direction": 0}

    # Last completed bar
    o  = float(df["open"].iloc[-2])
    h  = float(df["high"].iloc[-2])
    l  = float(df["low"].iloc[-2])
    c  = float(df["close"].iloc[-2])

    # Previous bar
    po = float(df["open"].iloc[-3])
    pc = float(df["close"].iloc[-3])

    candle_range = h - l
    if candle_range < 1e-10:
        return {"pattern": "none", "direction": 0}

    body       = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    body_ratio = body / candle_range
    prev_body  = abs(pc - po)

    # ── Bullish Engulfing ─────────────────────────────────────────────────────
    # Previous bar bearish; current bar bullish and fully engulfs previous body
    if (pc < po and c > o and prev_body > 0
            and o <= pc and c >= po):
        return {"pattern": "bullish_engulfing", "direction": 1}

    # ── Bearish Engulfing ─────────────────────────────────────────────────────
    if (pc > po and c < o and prev_body > 0
            and o >= pc and c <= po):
        return {"pattern": "bearish_engulfing", "direction": -1}

    # ── Hammer (bullish reversal) ─────────────────────────────────────────────
    # Small body, long lower wick (≥ 2× body), tiny upper wick (≤ 0.5× body)
    if (body > 0 and body_ratio <= 0.35
            and lower_wick >= 2.0 * body
            and upper_wick <= 0.5 * body):
        return {"pattern": "hammer", "direction": 1}

    # ── Shooting Star (bearish reversal) ─────────────────────────────────────
    if (body > 0 and body_ratio <= 0.35
            and upper_wick >= 2.0 * body
            and lower_wick <= 0.5 * body):
        return {"pattern": "shooting_star", "direction": -1}

    # ── Bullish Pin Bar ───────────────────────────────────────────────────────
    # Lower wick dominates (≥ 60% of range), close in upper portion
    if (lower_wick >= 0.6 * candle_range
            and (c - l) >= 0.6 * candle_range):
        return {"pattern": "bullish_pin_bar", "direction": 1}

    # ── Bearish Pin Bar ───────────────────────────────────────────────────────
    # Upper wick dominates (≥ 60% of range), close in lower portion
    if (upper_wick >= 0.6 * candle_range
            and (h - c) >= 0.6 * candle_range):
        return {"pattern": "bearish_pin_bar", "direction": -1}

    return {"pattern": "none", "direction": 0}

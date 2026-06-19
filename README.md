# Smart-Money Toolkit for MetaTrader 5

Liquidity sweeps & inverse fair-value-gap detection for XAUUSD and NAS100,
with EA-readable signal buffers and an automated execution layer.

## Files

| File | Purpose |
|------|---------|
| `Indicators/LiquiditySweeps_iFVG.mq5` | Indicator: draws FVG zones, iFVG inversions, sweep markers, exposes signal buffers |
| `Experts/SmartMoneyEA.mq5` | EA: reads indicator buffers via `iCustom()`, trades on HTF bias + LTF confluence |

---

## Installation

1. Open MetaEditor (F4 from MetaTrader).
2. Copy `Indicators/LiquiditySweeps_iFVG.mq5` → `MQL5/Indicators/`.
3. Copy `Experts/SmartMoneyEA.mq5` → `MQL5/Experts/`.
4. Compile both files (F7). Target: **0 errors, 0 warnings**.
5. Attach the indicator to a chart manually if you want visuals.
6. Attach the EA to the same symbol/timeframe as `InpLTFPeriod`.

> The EA creates its own internal indicator instances — you do not need to attach the indicator to the same chart as the EA.

---

## Indicator inputs

### Detection
| Input | Default | Notes |
|-------|---------|-------|
| `BarsToScan` | 600 | History depth for FVG and sweep scan |
| `SwingLength` | 5 | Fractal length — bars on each side required to confirm a swing high/low |
| `MinFVGPoints` | 0 | Filter out tiny gaps smaller than N points (0 = disabled) |
| `SweepLookahead` | 60 | Max bars after a swing high/low to look for its sweep |

### Display
| Input | Default | Notes |
|-------|---------|-------|
| `ShowFVG` | true | Draw un-inverted FVG rectangles |
| `ShowIFVG` | true | Draw inverted FVG rectangles (polarity-flipped color) |
| `ShowSweeps` | true | Draw sweep dotted lines and arrows |
| `ExtendRight` | true | Stretch zone rectangles to the current bar |
| `MaxZones` | 40 | Cap on drawn rectangles (does not limit buffer signals) |

### Alerts
Alerts fire on bar close, once per event, never on first attach.

| Input | Default | Notes |
|-------|---------|-------|
| `AlertPopup` | true | Terminal popup + sound |
| `AlertPush` | false | Push notification (requires MetaQuotes ID) |
| `AlertOnSweep` | true | Fire on liquidity sweep |
| `AlertOnIFVG` | true | Fire on FVG inversion |

---

## Signal buffers (for `iCustom()`)

Read with `CopyBuffer(handle, bufferIndex, startBar, count, array)`.
Always start at bar **1** (skip the forming bar 0).

| Index | Array | Values | Set on |
|-------|-------|--------|--------|
| 0 | `SweepSignal` | `+1` buy-side sweep, `-1` sell-side sweep, `0` none | Bar that swept and closed back |
| 1 | `IFVGSignal` | `+1` bearish FVG→bullish iFVG, `-1` bullish FVG→bearish iFVG, `0` none | First bar to close through the far side |
| 2 | `SweepLevel` | Price of the swept swing high or low | Same bar as `SweepSignal` |

### Minimal test EA (verify signals)
```mql5
int h = iCustom(_Symbol, PERIOD_M15, "LiquiditySweeps_iFVG");
double sweep[], ifvg[];
ArraySetAsSeries(sweep, true);
ArraySetAsSeries(ifvg,  true);
CopyBuffer(h, 0, 1, 50, sweep);
CopyBuffer(h, 1, 1, 50, ifvg);
for(int i = 0; i < 50; i++)
   if(sweep[i] != 0 || ifvg[i] != 0)
      PrintFormat("bar %d  sweep=%.0f  ifvg=%.0f", i, sweep[i], ifvg[i]);
```

---

## EA inputs

### Timeframes
| Input | Default | Notes |
|-------|---------|-------|
| `HTFPeriod` | H1 | Timeframe for directional bias |
| `LTFPeriod` | M15 | Timeframe for entry signals |

### Signal Settings
| Input | Default | Notes |
|-------|---------|-------|
| `HTFLookback` | 20 | Bars to scan on HTF for the most recent bias signal |
| `ConfluenceBars` | 10 | LTF window: both a sweep and an iFVG must appear within this many bars |
| `BarsToScan` … `SweepLookahead` | — | Must match indicator settings |

### Trade
| Input | Default | Notes |
|-------|---------|-------|
| `RiskPct` | 1.0 | % of balance risked per trade |
| `RR` | 2.0 | TP = SL distance × RR (default 1:2) |
| `SLBuffer` | 10 | Extra points beyond the swept level for the stop-loss |
| `Magic` | 202406 | Magic number; one position per magic per symbol |

### Prop-Firm Risk Limits
| Input | Default | Notes |
|-------|---------|-------|
| `DailyLossLimit` | 2.0 | Halt new trades if equity has dropped this % from UTC midnight balance |
| `MaxDrawdown` | 10.0 | Halt permanently if equity drops this % from session peak |

### Session Filter (UTC)
| Input | Default | Notes |
|-------|---------|-------|
| `SessionStartHour` | 7 | London open |
| `SessionEndHour` | 20 | NY close |

---

## Entry logic

1. **HTF bias**: scan the last `HTFLookback` bars on the HTF. The most recent non-zero `SweepSignal` or `IFVGSignal` sets the directional bias (+1 bull / -1 bear).
2. **LTF confluence**: within the last `ConfluenceBars` bars on the LTF, require *both* a sweep and an iFVG pointing in the same direction as the HTF bias.
3. **Trade**: market order at ask/bid; SL beyond the `SweepLevel` by `SLBuffer` points; TP at `RR × SL distance`.

Detection logic is never duplicated — the EA reads only the indicator's buffers.

---

## Backtesting

1. Strategy Tester → **Every tick based on real ticks** for accurate spread/execution.
2. Set date range to include at least 3 months of XAUUSD M15 data.
3. Attach `SmartMoneyEA` to the tester; set `LTFPeriod = M15`, `HTFPeriod = H1`.
4. Check the journal tab for any risk-limit or lot-size warnings.
5. Verify the daily loss cap fires correctly by inspecting equity curves around large losing days.

> This toolkit is a decision-support tool. Backtest performance does not predict live results.

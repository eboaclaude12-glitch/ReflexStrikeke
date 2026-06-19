# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repo has two separate concerns:

1. **ReflexStrike** — a static French-language e-commerce site for boxing equipment (`index.html`, `valentine.html`). No build step; open in browser or serve with `python3 -m http.server 8000`.

2. **Smart-Money Toolkit for MT5** — an MQL5 indicator + EA for XAUUSD/NAS100 prop trading. The compile target is MetaEditor (F7). "0 errors, 0 warnings in MetaEditor" is the definition of done for any `.mq5` file.

---

## MT5 Project Layout

```
Indicators/LiquiditySweeps_iFVG.mq5   # indicator with signal buffers
Experts/SmartMoneyEA.mq5              # EA that reads the indicator via iCustom()
Include/SmartMoney/                    # shared helpers if needed later
README.md                              # input reference + install + backtest guide
CHANGELOG.md
```

Install: copy each file into the matching `MQL5/Indicators/` or `MQL5/Experts/` folder inside the MetaTrader data directory, then compile with F7.

---

## MQL5 Non-Negotiables

- **No repainting.** All signal logic runs on closed bars only (series index ≥ 1). Index 0 (forming bar) is never used to confirm a signal or write a buffer value.
- **`ArraySetAsSeries` must be explicit.** Call it on all price arrays *and* on buffer arrays at the top of `OnCalculate`.
- **New-bar gate.** Redraw and buffer writes happen only when `time[0] != g_lastBarTime`. Per-tick work is limited to reading prices and checking guards.
- **Bounded objects.** All chart objects use the `PREFIX` ("LSIF_") and are deleted in `OnDeinit` and before each redraw.
- **Alert dedup.** Alerts are skipped when `g_lastBarTime == 0` (first attach) to avoid history spam.

---

## Indicator Signal Buffers

Buffer arrays are `INDICATOR_CALCULATIONS` (invisible on chart, readable by EA via `iCustom()`).

| Index | Name | Values |
|-------|------|--------|
| 0 | `SweepSignal` | +1 buy-side sweep, −1 sell-side sweep, 0 none |
| 1 | `IFVGSignal` | +1 bearish FVG→bull iFVG, −1 bullish FVG→bear iFVG, 0 none |
| 2 | `SweepLevel` | Price of the swept swing level (0 if no sweep on that bar) |

When reading in the EA: `CopyBuffer(handle, index, 1, N, array)` — start at bar 1, not 0.

---

## EA Architecture

- **Two `iCustom()` handles** per symbol: one for HTF (bias), one for LTF (entry).
- **Detection lives only in the indicator.** The EA reads buffers; it never re-implements swing/FVG/sweep logic.
- **Entry model:** HTF sweep or iFVG sets directional bias → LTF sweep + LTF iFVG in same direction within `InpConfluenceBars` bars triggers a market order.
- **Lot sizing:** `riskAmt / (slDist / tickSize * tickVal)`, floored to `lotStep`.
- **Prop-firm guards (checked every tick):**
  - Daily loss: equity vs. UTC-midnight balance snapshot, halt at `InpDailyLossLimit`%.
  - Max drawdown: equity vs. session equity peak, halt at `InpMaxDrawdown`%.
- **Session filter:** `TimeGMT()` hour checked against `InpSessionStartHour/EndHour`.

---

## SMC Concept Definitions (use these literally)

**FVG pattern** — 3-bar sequence C1, C2, C3 (oldest→newest):
- Bullish FVG: `C1.high < C3.low` — zone = `[C1.high, C3.low]`
- Bearish FVG: `C1.low > C3.high` — zone = `[C3.high, C1.low]`

**iFVG** — a later bar *closes* beyond the far side of an FVG (wick alone does not invert):
- Bullish FVG inverted (close < bottom) → bearish iFVG
- Bearish FVG inverted (close > top) → bullish iFVG

**Swing high/low** — fractal with `InpSwingLength` bars on each side (strict inequality).

**Liquidity sweep** — a bar whose wick exceeds a prior swing level and whose *close* is back inside:
- Sell-side sweep: `high > swingHigh && close < swingHigh`
- Buy-side sweep: `low < swingLow && close > swingLow`

---

## Static Site (index.html)

- Products are a hard-coded `products[]` array rendered by `renderProducts()`.
- Cart state: plain `cart` object `{ [productId]: quantity }`.
- All CSS and JS inline in `index.html`. Design tokens: primary `#ff6b35`, accent `#ffd93d`. Fonts: Oswald + Outfit via Google Fonts. Breakpoints: 1024 px and 768 px.
- `valentine.html` is fully self-contained; no shared code with `index.html`.

# Changelog

## Indicator — v2.00 (2026-06-19)

**New**
- Added 3 EA-readable signal buffers (`INDICATOR_CALCULATIONS`, invisible on chart):
  - Buffer 0 `SweepSignal`: +1 buy-side sweep, -1 sell-side sweep
  - Buffer 1 `IFVGSignal`: +1 bull iFVG, -1 bear iFVG
  - Buffer 2 `SweepLevel`: price of the swept swing level (for SL placement)
- Buffers populated on the confirming closed bar; forming bar (index 0) is never written
- Buffer signals fire for all detected events, independent of `MaxZones` draw cap

**Changed**
- `indicator_buffers` 0 → 3
- `DrawSweeps()` now always runs (was gated by `InpShowSweeps`); visual markers still respect the toggle
- Buffer arrays set as series in `OnCalculate` to match price array indexing
- Scan range zeroed before each redraw so stale values never persist

**Unchanged**
- All v1.10 inputs kept verbatim
- Visual output (rectangles, dotted lines, arrows) identical to v1.10
- Alert logic unchanged

---

## Indicator — v1.10 (original)

- FVG detection (bullish and bearish)
- iFVG inversion detection (polarity flip on close-through)
- Liquidity sweep detection (fractal swing + rejection close)
- Graphical objects: rectangles for zones, dotted trend lines + arrows for sweeps
- Bar-close popup and push alerts with dedup on attach

---

## EA — v1.00 (2026-06-19)

Initial release.

- Reads `LiquiditySweeps_iFVG` buffers via `iCustom()` — no duplicated detection logic
- Two indicator handles per symbol: HTF (bias) and LTF (entry)
- Entry: HTF sweep/iFVG bias confirmed by LTF sweep + iFVG confluence within N bars
- Lot sizing: fixed % of balance risk with SL beyond the swept swing level
- Prop-firm guards: daily loss cap (2%) and max drawdown cap (10%), both configurable
- Session filter: UTC hour range (default 07:00–20:00)
- One position per magic number per symbol; full journal logging

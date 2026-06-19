//+------------------------------------------------------------------+
//|                                     LiquiditySweeps_iFVG.mq5    |
//|        Liquidity Sweeps & Inverse Fair Value Gaps (ICT / SMC)   |
//|        Works on XAUUSD (gold) or any symbol & timeframe         |
//|        + EA-readable signal buffers + popup/push alerts         |
//|                                                                  |
//|  SIGNAL BUFFERS – read via iCustom("LiquiditySweeps_iFVG", …): |
//|    Buffer 0 – SweepSignal : +1 buy-side sweep (bull rejection)  |
//|                              -1 sell-side sweep (bear rejection) |
//|                               0 no signal                        |
//|    Buffer 1 – IFVGSignal  : +1 bearish FVG inverted→bull iFVG  |
//|                              -1 bullish FVG inverted→bear iFVG  |
//|                               0 no signal                        |
//|    Buffer 2 – SweepLevel  : price of the swept swing level      |
//|                              (0 if no sweep on that bar)         |
//|                                                                  |
//|  Value is set on the CLOSED bar that confirmed the event.       |
//|  The forming bar (index 0) is never used for signals.           |
//+------------------------------------------------------------------+
#property copyright "Built with Claude"
#property version   "2.00"
#property description "FVGs, iFVG inversions, liquidity sweeps + signal buffers + alerts."
#property indicator_chart_window
#property indicator_buffers 3
#property indicator_plots   0

//============================ INPUTS =================================
input group "=== Detection ==="
input int    InpBarsToScan      = 600;  // Bars to scan back
input int    InpSwingLength     = 5;    // Swing strength (bars each side)
input double InpMinFVGPoints    = 0;    // Min FVG size in points (0 = no filter)
input int    InpSweepLookahead  = 60;   // Max bars ahead of swing to find a sweep

input group "=== Display ==="
input bool   InpShowFVG      = true;    // Show un-inverted Fair Value Gaps
input bool   InpShowIFVG     = true;    // Show Inverse FVGs (flipped gaps)
input bool   InpShowSweeps   = true;    // Show liquidity sweep markers
input bool   InpExtendRight  = true;    // Extend zones to the latest bar
input int    InpMaxZones     = 40;      // Max FVG/iFVG rectangles drawn

input group "=== Alerts ==="
input bool   InpAlertPopup   = true;    // Terminal popup + sound
input bool   InpAlertPush    = false;   // Push to phone (needs MetaQuotes ID set)
input bool   InpAlertOnSweep = true;    // Alert on liquidity sweeps
input bool   InpAlertOnIFVG  = true;    // Alert on FVG inversions (iFVG)

input group "=== Colors ==="
input color  InpBullFVG  = C'20,90,60';    // Bullish FVG (support gap)
input color  InpBearFVG  = C'120,30,30';   // Bearish FVG (resistance gap)
input color  InpBullIFVG = clrLime;        // Inverted → now bullish
input color  InpBearIFVG = clrOrangeRed;   // Inverted → now bearish
input color  InpSweepCol = clrGold;        // Liquidity sweep marker

//============================ GLOBALS ================================
#define PREFIX "LSIF_"
datetime g_lastBarTime = 0;

double SweepSignal[];   // buffer 0 — +1 buy-side, -1 sell-side
double IFVGSignal[];    // buffer 1 — +1 bull iFVG, -1 bear iFVG
double SweepLevel[];    // buffer 2 — price of swept swing level (0 if none)

//+------------------------------------------------------------------+
int OnInit()
{
   IndicatorSetString(INDICATOR_SHORTNAME, "Liquidity Sweeps & iFVG 2.0");

   SetIndexBuffer(0, SweepSignal, INDICATOR_CALCULATIONS);
   SetIndexBuffer(1, IFVGSignal,  INDICATOR_CALCULATIONS);
   SetIndexBuffer(2, SweepLevel,  INDICATOR_CALCULATIONS);

   ObjectsDeleteAll(0, PREFIX);
   g_lastBarTime = 0;
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   ObjectsDeleteAll(0, PREFIX);
   ChartRedraw();
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   if(rates_total < InpSwingLength * 2 + 3)
      return(rates_total);

   // All arrays and buffers use series indexing: index 0 = most recent bar.
   ArraySetAsSeries(time,        true);
   ArraySetAsSeries(open,        true);
   ArraySetAsSeries(high,        true);
   ArraySetAsSeries(low,         true);
   ArraySetAsSeries(close,       true);
   ArraySetAsSeries(SweepSignal, true);
   ArraySetAsSeries(IFVGSignal,  true);
   ArraySetAsSeries(SweepLevel,  true);

   bool isNewBar = (time[0] != g_lastBarTime);

   if(prev_calculated == 0 || isNewBar)
   {
      // Zero signal buffers for the full scan range before repopulating.
      int clearLimit = (int)MathMin(InpBarsToScan, rates_total - 1);
      for(int i = 0; i <= clearLimit; i++)
      {
         SweepSignal[i] = 0.0;
         IFVGSignal[i]  = 0.0;
         SweepLevel[i]  = 0.0;
      }

      ObjectsDeleteAll(0, PREFIX);
      DrawFVGs(rates_total, time, high, low, close);
      DrawSweeps(rates_total, time, high, low, close); // always runs (buffers need it)
      ChartRedraw();
   }

   // Alerts: only on a genuine new bar, never on first load (g_lastBarTime == 0).
   if(isNewBar)
   {
      if(g_lastBarTime != 0)
         CheckAlerts(rates_total, time, high, low, close);
      g_lastBarTime = time[0];
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Detect FVGs, flag inversions, populate IFVGSignal, draw visuals  |
//+------------------------------------------------------------------+
void DrawFVGs(const int rates_total,
              const datetime &time[],
              const double &high[],
              const double &low[],
              const double &close[])
{
   double minSize  = InpMinFVGPoints * _Point;
   int    limit    = (int)MathMin(InpBarsToScan - 1, rates_total - 3);
   datetime rightEdge = time[0];
   int drawn = 0;

   // i is the NEWEST candle of the 3-bar FVG pattern (series order: i+2 is oldest).
   for(int i = 0; i <= limit; i++)
   {
      bool   isBull = false, isBear = false;
      double top = 0, bot = 0;

      // Bullish FVG: gap between C1.high and C3.low
      if(high[i + 2] < low[i])        { isBull = true; bot = high[i + 2]; top = low[i]; }
      // Bearish FVG: gap between C3.high and C1.low
      else if(low[i + 2] > high[i])   { isBear = true; top = low[i + 2]; bot = high[i]; }
      else continue;

      if(minSize > 0 && (top - bot) < minSize) continue;

      // Check if any newer bar closed through the far side (inversion).
      // Buffer write happens regardless of display settings — EA reads all events.
      bool inverted = false;
      for(int j = i - 1; j >= 0; j--)
      {
         if(isBull && close[j] < bot)
         {
            inverted = true;
            IFVGSignal[j] = -1.0; // bullish FVG flipped → bearish iFVG
            break;
         }
         if(isBear && close[j] > top)
         {
            inverted = true;
            IFVGSignal[j] = 1.0; // bearish FVG flipped → bullish iFVG
            break;
         }
      }

      // Visual drawing is capped and respects show/hide toggles.
      if(drawn >= InpMaxZones)                continue;
      if(inverted  && !InpShowIFVG)           continue;
      if(!inverted && !InpShowFVG)            continue;

      color col = inverted ? (isBull ? InpBearIFVG : InpBullIFVG)
                           : (isBull ? InpBullFVG  : InpBearFVG);

      datetime t1 = time[i + 1];
      datetime t2 = InpExtendRight ? rightEdge : time[i];

      string nm = PREFIX + "Z" + IntegerToString(drawn);
      if(ObjectCreate(0, nm, OBJ_RECTANGLE, 0, t1, top, t2, bot))
      {
         ObjectSetInteger(0, nm, OBJPROP_COLOR,     col);
         ObjectSetInteger(0, nm, OBJPROP_FILL,      true);
         ObjectSetInteger(0, nm, OBJPROP_BACK,      true);
         ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, nm, OBJPROP_HIDDEN,    true);
         string lbl = inverted ? "iFVG" : "FVG";
         ObjectSetString(0, nm, OBJPROP_TOOLTIP, lbl + (isBull ? " (bull origin)" : " (bear origin)"));
         drawn++;
      }
   }
}

//+------------------------------------------------------------------+
//| Detect swing highs/lows, find sweep bars, populate SweepSignal  |
//+------------------------------------------------------------------+
void DrawSweeps(const int rates_total,
                const datetime &time[],
                const double &high[],
                const double &low[],
                const double &close[])
{
   int L     = InpSwingLength;
   int limit = (int)MathMin(InpBarsToScan - 1, rates_total - 1);
   int marker = 0;

   for(int k = L; k <= limit - L; k++)
   {
      // --- Swing HIGH: high[k] strictly greater than all bars in [k-L, k+L] ---
      bool isSwingHigh = true;
      for(int n = k - L; n <= k + L; n++)
      {
         if(n == k) continue;
         if(high[n] >= high[k]) { isSwingHigh = false; break; }
      }
      if(isSwingHigh)
      {
         int stop = (int)MathMax(0, k - InpSweepLookahead);
         for(int m = k - 1; m >= stop; m--)
         {
            if(high[m] > high[k] && close[m] < high[k])
            {
               // Bar m spiked above the swing high but closed back below → sell-side sweep
               SweepSignal[m] = -1.0;
               SweepLevel[m]  = high[k];
               if(InpShowSweeps)
                  MarkSweep(marker++, time, high[k], time[m], high[m], true);
               break;
            }
         }
      }

      // --- Swing LOW: low[k] strictly less than all bars in [k-L, k+L] ---
      bool isSwingLow = true;
      for(int n = k - L; n <= k + L; n++)
      {
         if(n == k) continue;
         if(low[n] <= low[k]) { isSwingLow = false; break; }
      }
      if(isSwingLow)
      {
         int stop = (int)MathMax(0, k - InpSweepLookahead);
         for(int m = k - 1; m >= stop; m--)
         {
            if(low[m] < low[k] && close[m] > low[k])
            {
               // Bar m spiked below the swing low but closed back above → buy-side sweep
               SweepSignal[m] = 1.0;
               SweepLevel[m]  = low[k];
               if(InpShowSweeps)
                  MarkSweep(marker++, time, low[k], time[m], low[m], false);
               break;
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Draw one sweep: dotted line at swept level + arrow               |
//+------------------------------------------------------------------+
void MarkSweep(int id, const datetime &time[], double level,
               datetime sweepTime, double sweepExtreme, bool sellSide)
{
   string ln = PREFIX + "SL" + IntegerToString(id);
   if(ObjectCreate(0, ln, OBJ_TREND, 0, sweepTime, level, time[0], level))
   {
      ObjectSetInteger(0, ln, OBJPROP_COLOR,      InpSweepCol);
      ObjectSetInteger(0, ln, OBJPROP_STYLE,      STYLE_DOT);
      ObjectSetInteger(0, ln, OBJPROP_WIDTH,      1);
      ObjectSetInteger(0, ln, OBJPROP_RAY_RIGHT,  false);
      ObjectSetInteger(0, ln, OBJPROP_BACK,       true);
      ObjectSetInteger(0, ln, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, ln, OBJPROP_HIDDEN,     true);
   }

   string ar = PREFIX + "SA" + IntegerToString(id);
   if(ObjectCreate(0, ar, OBJ_ARROW, 0, sweepTime, sweepExtreme))
   {
      ObjectSetInteger(0, ar, OBJPROP_ARROWCODE,  sellSide ? 234 : 233); // down / up arrow
      ObjectSetInteger(0, ar, OBJPROP_COLOR,      InpSweepCol);
      ObjectSetInteger(0, ar, OBJPROP_ANCHOR,     sellSide ? ANCHOR_BOTTOM : ANCHOR_TOP);
      ObjectSetInteger(0, ar, OBJPROP_WIDTH,      1);
      ObjectSetInteger(0, ar, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, ar, OBJPROP_HIDDEN,     true);
   }
}

//+------------------------------------------------------------------+
//| Helpers for alerts                                               |
//+------------------------------------------------------------------+
string TfStr()
{
   return StringSubstr(EnumToString((ENUM_TIMEFRAMES)Period()), 7); // "PERIOD_M5" → "M5"
}

void FireAlert(string msg)
{
   string full = _Symbol + " " + TfStr() + ": " + msg;
   if(InpAlertPopup) Alert(full);
   if(InpAlertPush)  SendNotification(full);
   Print(full);
}

//+------------------------------------------------------------------+
//| Check the just-closed bar (index 1) for fresh signals to alert  |
//+------------------------------------------------------------------+
void CheckAlerts(const int rates_total,
                 const datetime &time[],
                 const double &high[],
                 const double &low[],
                 const double &close[])
{
   int L = InpSwingLength;
   int b = 1; // just-closed bar (index 0 is the new forming bar)

   //--- liquidity sweeps ---
   if(InpAlertOnSweep)
   {
      int kmax = (int)MathMin(InpSweepLookahead + b, rates_total - 1 - L);

      // Sell-side: swing HIGH above wicked then rejected by bar b
      for(int k = b + 1; k <= kmax; k++)
      {
         bool sh = true;
         for(int n = k - L; n <= k + L; n++)
         {
            if(n == k) continue;
            if(n < 0 || n >= rates_total) { sh = false; break; }
            if(high[n] >= high[k])        { sh = false; break; }
         }
         if(sh && high[b] > high[k] && close[b] < high[k])
         {
            FireAlert(StringFormat("Sell-side liquidity SWEEP (high %.*f taken & rejected)", _Digits, high[k]));
            break;
         }
      }

      // Buy-side: swing LOW below wicked then rejected by bar b
      for(int k = b + 1; k <= kmax; k++)
      {
         bool sl = true;
         for(int n = k - L; n <= k + L; n++)
         {
            if(n == k) continue;
            if(n < 0 || n >= rates_total) { sl = false; break; }
            if(low[n] <= low[k])          { sl = false; break; }
         }
         if(sl && low[b] < low[k] && close[b] > low[k])
         {
            FireAlert(StringFormat("Buy-side liquidity SWEEP (low %.*f taken & rejected)", _Digits, low[k]));
            break;
         }
      }
   }

   //--- fresh iFVG inversions caused by bar b ---
   if(InpAlertOnIFVG)
   {
      bool firedBull = false, firedBear = false;
      int  imax = (int)MathMin(InpBarsToScan, rates_total - 3);

      for(int i = b + 1; i <= imax; i++)
      {
         double top = 0, bot = 0; bool isBull = false, isBear = false;
         if(high[i + 2] < low[i])      { isBull = true; bot = high[i + 2]; top = low[i]; }
         else if(low[i + 2] > high[i]) { isBear = true; top = low[i + 2]; bot = high[i]; }
         else continue;

         if(InpMinFVGPoints > 0 && (top - bot) < InpMinFVGPoints * _Point) continue;

         // Bar b must be the FIRST bar to close through the far side.
         bool earlier = false;
         for(int j = i - 1; j >= b + 1; j--)
         {
            if(isBull && close[j] < bot) { earlier = true; break; }
            if(isBear && close[j] > top) { earlier = true; break; }
         }
         if(earlier) continue;

         if(isBull && close[b] < bot && !firedBull)
         {
            FireAlert(StringFormat("Bullish FVG INVERTED → bearish iFVG (closed below %.*f)", _Digits, bot));
            firedBull = true;
         }
         if(isBear && close[b] > top && !firedBear)
         {
            FireAlert(StringFormat("Bearish FVG INVERTED → bullish iFVG (closed above %.*f)", _Digits, top));
            firedBear = true;
         }

         if(firedBull && firedBear) break;
      }
   }
}
//+------------------------------------------------------------------+

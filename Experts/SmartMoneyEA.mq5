//+------------------------------------------------------------------+
//|                                           SmartMoneyEA.mq5      |
//|        Smart-Money Confluence EA                                 |
//|        Reads LiquiditySweeps_iFVG buffers via iCustom()         |
//|                                                                  |
//|  Entry logic:                                                    |
//|    1. HTF sweep or iFVG signal sets the directional bias        |
//|    2. LTF sweep + LTF iFVG in same direction within N bars      |
//|    3. Trade opened; SL beyond the swept swing level             |
//|                                                                  |
//|  Detection logic lives ONLY in the indicator (single source).   |
//+------------------------------------------------------------------+
#property copyright "Built with Claude"
#property version   "1.00"
#property description "Automated SMC confluence EA using LiquiditySweeps_iFVG signals."

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

//============================ INPUTS =================================
input group "=== Timeframes ==="
input ENUM_TIMEFRAMES InpHTFPeriod       = PERIOD_H1;   // Higher timeframe (bias)
input ENUM_TIMEFRAMES InpLTFPeriod       = PERIOD_M15;  // Lower timeframe (entry)

input group "=== Signal Settings ==="
input int    InpHTFLookback              = 20;   // HTF bars to scan for directional bias
input int    InpConfluenceBars           = 10;   // LTF window: bars to find sweep + iFVG together

// These must match the indicator settings on your chart.
input int    InpBarsToScan               = 600;
input int    InpSwingLength              = 5;
input double InpMinFVGPoints             = 0;
input int    InpSweepLookahead           = 60;

input group "=== Trade ==="
input double InpRiskPct                  = 1.0;   // Risk per trade (% of balance)
input double InpRR                       = 2.0;   // Reward : Risk ratio (2.0 = 1:2)
input int    InpSLBuffer                 = 10;    // Extra points beyond swept level for SL
input ulong  InpMagic                    = 202406;

input group "=== Prop-Firm Risk Limits ==="
input double InpDailyLossLimit           = 2.0;  // Halt if daily loss exceeds this % of day-start balance
input double InpMaxDrawdown              = 10.0; // Halt if equity drops this % from peak

input group "=== Session Filter (UTC) ==="
input int    InpSessionStartHour         = 7;    // Open trades from this UTC hour
input int    InpSessionEndHour           = 20;   // Stop opening trades at this UTC hour

//============================ GLOBALS ================================
CTrade        g_trade;
CPositionInfo g_pos;
CAccountInfo  g_account;

int      g_ltfHandle      = INVALID_HANDLE;
int      g_htfHandle      = INVALID_HANDLE;
datetime g_lastLTFBar     = 0;
double   g_dayStartBal    = 0.0;
double   g_peakEquity     = 0.0;
datetime g_lastDayReset   = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(10);

   // Both handles point to the same indicator on different timeframes.
   // Alerts disabled in indicator when the EA is driving the decisions.
   g_ltfHandle = iCustom(_Symbol, InpLTFPeriod, "LiquiditySweeps_iFVG",
      InpBarsToScan, InpSwingLength, InpMinFVGPoints, InpSweepLookahead,
      true, true, true, true, 40,       // display params (don't affect buffers)
      false, false, false, false,        // alerts off
      C'20,90,60', C'120,30,30', clrLime, clrOrangeRed, clrGold);

   g_htfHandle = iCustom(_Symbol, InpHTFPeriod, "LiquiditySweeps_iFVG",
      InpBarsToScan, InpSwingLength, InpMinFVGPoints, InpSweepLookahead,
      true, true, true, true, 40,
      false, false, false, false,
      C'20,90,60', C'120,30,30', clrLime, clrOrangeRed, clrGold);

   if(g_ltfHandle == INVALID_HANDLE || g_htfHandle == INVALID_HANDLE)
   {
      Print("ERROR: Could not create indicator handles. Compile LiquiditySweeps_iFVG.mq5 first.");
      return(INIT_FAILED);
   }

   g_dayStartBal  = g_account.Balance();
   g_peakEquity   = g_account.Equity();
   g_lastDayReset = TimeCurrent();

   Print("SmartMoneyEA started | ", _Symbol,
         " | LTF:", EnumToString(InpLTFPeriod),
         " | HTF:", EnumToString(InpHTFPeriod),
         " | Risk:", InpRiskPct, "% | R:R 1:", InpRR);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_ltfHandle != INVALID_HANDLE) { IndicatorRelease(g_ltfHandle); g_ltfHandle = INVALID_HANDLE; }
   if(g_htfHandle != INVALID_HANDLE) { IndicatorRelease(g_htfHandle); g_htfHandle = INVALID_HANDLE; }
}

//+------------------------------------------------------------------+
void OnTick()
{
   ResetDailyBalance();

   double equity = g_account.Equity();
   if(equity > g_peakEquity) g_peakEquity = equity;

   if(!RiskOK())    return;
   if(!InSession()) return;

   // Only process logic once per closed LTF bar.
   datetime ltfTime[1];
   if(CopyTime(_Symbol, InpLTFPeriod, 0, 1, ltfTime) < 1) return;
   if(ltfTime[0] == g_lastLTFBar) return;
   g_lastLTFBar = ltfTime[0];

   if(HasPosition()) return;

   int bias = GetHTFBias();
   if(bias == 0) return;

   double sweepLevel = 0.0;
   int    dir        = GetLTFConfluence(bias, sweepLevel);
   if(dir == 0 || sweepLevel == 0.0) return;

   OpenTrade(dir, sweepLevel);
}

//+------------------------------------------------------------------+
//| Returns +1 (bullish bias), -1 (bearish bias), or 0 (none)       |
//+------------------------------------------------------------------+
int GetHTFBias()
{
   double htfSweep[], htfIFVG[];
   ArraySetAsSeries(htfSweep, true);
   ArraySetAsSeries(htfIFVG,  true);

   // Start at bar 1 to skip the forming bar.
   if(CopyBuffer(g_htfHandle, 0, 1, InpHTFLookback, htfSweep) < InpHTFLookback) return 0;
   if(CopyBuffer(g_htfHandle, 1, 1, InpHTFLookback, htfIFVG)  < InpHTFLookback) return 0;

   // Most recent non-zero signal wins.
   for(int i = 0; i < InpHTFLookback; i++)
   {
      if(htfSweep[i] != 0.0) return (int)htfSweep[i];
      if(htfIFVG[i]  != 0.0) return (int)htfIFVG[i];
   }
   return 0;
}

//+------------------------------------------------------------------+
//| Returns bias direction when LTF sweep + iFVG both agree with it |
//| sweepLevel is set to the swept swing price for SL placement.    |
//+------------------------------------------------------------------+
int GetLTFConfluence(int bias, double &sweepLevel)
{
   double ltfSweep[], ltfIFVG[], ltfLevel[];
   ArraySetAsSeries(ltfSweep, true);
   ArraySetAsSeries(ltfIFVG,  true);
   ArraySetAsSeries(ltfLevel, true);

   if(CopyBuffer(g_ltfHandle, 0, 1, InpConfluenceBars, ltfSweep) < InpConfluenceBars) return 0;
   if(CopyBuffer(g_ltfHandle, 1, 1, InpConfluenceBars, ltfIFVG)  < InpConfluenceBars) return 0;
   if(CopyBuffer(g_ltfHandle, 2, 1, InpConfluenceBars, ltfLevel) < InpConfluenceBars) return 0;

   bool   hasSweep    = false, hasIFVG = false;
   double foundLevel  = 0.0;

   for(int i = 0; i < InpConfluenceBars; i++)
   {
      if(ltfSweep[i] == (double)bias && foundLevel == 0.0)
      {
         hasSweep   = true;
         foundLevel = ltfLevel[i];
      }
      if(ltfIFVG[i] == (double)bias)
         hasIFVG = true;
   }

   if(hasSweep && hasIFVG)
   {
      sweepLevel = foundLevel;
      return bias;
   }
   return 0;
}

//+------------------------------------------------------------------+
//| Place a market order with computed lots, SL, and TP             |
//+------------------------------------------------------------------+
void OpenTrade(int direction, double sweepLevel)
{
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   double entry, sl, tp, slDist;

   if(direction == 1) // Buy: SL below swept low
   {
      entry  = ask;
      sl     = NormalizeDouble(sweepLevel - InpSLBuffer * point, digits);
      slDist = entry - sl;
      tp     = NormalizeDouble(entry + slDist * InpRR, digits);
   }
   else               // Sell: SL above swept high
   {
      entry  = bid;
      sl     = NormalizeDouble(sweepLevel + InpSLBuffer * point, digits);
      slDist = sl - entry;
      tp     = NormalizeDouble(entry - slDist * InpRR, digits);
   }

   if(slDist <= 0)
   {
      Print("WARN: SL distance <= 0, skipping trade. sweepLevel=", sweepLevel, " entry=", entry);
      return;
   }

   double lots = CalcLots(slDist);
   if(lots <= 0) return;

   string comment = StringFormat("SMC %s sweep+iFVG", direction == 1 ? "bull" : "bear");

   if(direction == 1)
      g_trade.Buy(lots, _Symbol, entry, sl, tp, comment);
   else
      g_trade.Sell(lots, _Symbol, entry, sl, tp, comment);

   if(g_trade.ResultRetcode() == TRADE_RETCODE_DONE)
      Print("Trade opened | dir=", direction, " lots=", lots,
            " entry=", entry, " sl=", sl, " tp=", tp);
   else
      Print("Trade FAILED | retcode=", g_trade.ResultRetcode(),
            " | ", g_trade.ResultRetcodeDescription());
}

//+------------------------------------------------------------------+
//| Lot size for 1% balance risk given the SL distance in price     |
//+------------------------------------------------------------------+
double CalcLots(double slDist)
{
   double balance  = g_account.Balance();
   double riskAmt  = balance * InpRiskPct / 100.0;
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double lotStep  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   if(tickVal == 0.0 || tickSize == 0.0)
   {
      Print("WARN: tick value/size unavailable, skipping trade.");
      return 0.0;
   }

   double lots = riskAmt / (slDist / tickSize * tickVal);
   lots = MathFloor(lots / lotStep) * lotStep;
   lots = MathMax(minLot, MathMin(maxLot, lots));

   if(lots < minLot)
   {
      Print("WARN: Computed lots (", lots, ") below minimum (", minLot, "), skipping.");
      return 0.0;
   }
   return lots;
}

//+------------------------------------------------------------------+
//| Prop-firm guard: returns false if a risk limit is breached       |
//+------------------------------------------------------------------+
bool RiskOK()
{
   double equity  = g_account.Equity();

   // Daily loss: compare current equity to balance at start of UTC day.
   if(g_dayStartBal > 0.0)
   {
      double dailyLossPct = (g_dayStartBal - equity) / g_dayStartBal * 100.0;
      if(dailyLossPct >= InpDailyLossLimit)
      {
         Print("Daily loss limit hit (", DoubleToString(dailyLossPct, 2), "%). No new trades today.");
         return false;
      }
   }

   // Max drawdown: compare current equity to highest recorded equity.
   if(g_peakEquity > 0.0)
   {
      double ddPct = (g_peakEquity - equity) / g_peakEquity * 100.0;
      if(ddPct >= InpMaxDrawdown)
      {
         Print("Max drawdown limit hit (", DoubleToString(ddPct, 2), "%). EA halted.");
         return false;
      }
   }

   return true;
}

//+------------------------------------------------------------------+
//| Reset day-start balance snapshot at UTC midnight                 |
//+------------------------------------------------------------------+
void ResetDailyBalance()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   datetime todayMidnight = StringToTime(
      StringFormat("%04d.%02d.%02d 00:00", dt.year, dt.mon, dt.day));

   if(todayMidnight > g_lastDayReset)
   {
      g_dayStartBal  = g_account.Balance();
      g_lastDayReset = todayMidnight;
      Print("New trading day. Balance snapshot: ", g_dayStartBal);
   }
}

//+------------------------------------------------------------------+
//| True when current UTC hour is within the configured session      |
//+------------------------------------------------------------------+
bool InSession()
{
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   return (dt.hour >= InpSessionStartHour && dt.hour < InpSessionEndHour);
}

//+------------------------------------------------------------------+
//| True if there is already an open position for this symbol+magic  |
//+------------------------------------------------------------------+
bool HasPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i) &&
         g_pos.Symbol() == _Symbol &&
         g_pos.Magic()  == InpMagic)
         return true;
   }
   return false;
}
//+------------------------------------------------------------------+

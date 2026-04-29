//+------------------------------------------------------------------+
//|  SM_BPCT.mq4                                                      |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (MQ4 idiomatic / D-20)|
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md |
//|                                                                   |
//|  D-17 Built ⚠ Low confidence — implementation per Verified Updates|
//|  2026-04-27 mini-HUD interpretation (NOT pressure-tracker; see    |
//|  Pitfall 10). // [INFER] on every guessed branch.                 |
//|                                                                   |
//|  v2.00 (operator-tuned 2026-04-28) — adds open-trade tracking:    |
//|     - Weekly first-4hr H/L (psych S/R per IlsleyPsychLevels v2.00)|
//|     - PHOD / PLOD (yesterday's D1 high/low)                        |
//|     - Per open position on current symbol: distance from each of  |
//|       the four key levels in pips, signed                          |
//|                                                                   |
//|  v2.01 (operator-tuned 2026-04-28 round 2):                        |
//|     - Bar countdown row (TF-adaptive: <15min=Ns, 15m-1h=M:SS,     |
//|       >1h=H:MM)                                                    |
//|     - Removed InpTradeBuyColor / InpTradeSellColor                |
//|     - Added InpTradeColor (unified trade row colour)              |
//|     - Added InpYOffset to avoid overlap with SM_ADR_Marker HUD    |
//|     - Base Y bumped from 20 -> 60                                 |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_BPCT.ex4 (mini-HUD)"
#property version   "2.01"
#property indicator_chart_window
#property strict

// [INFER] (D-17) — Verified Updates 2026-04-27 mini-HUD; not pressure-tracker.

//--- Spec Section 3 — Verified Updates 2026-04-27 (16 inputs verbatim)
extern int    InpCornerOfChart        = 1;     // 0=LL 1=UR 2=LR 3=UL — VERIFIED RIGHT_TOP=1
extern bool   InpShowPrice            = true;
extern bool   InpShowXtraDetails      = true;
extern bool   InpShowSmallerSize      = true;
extern bool   InpShowTradePips        = true;
extern int    InpShiftUpDn            = 0;
extern int    InpAdjustSideToSide     = 0;
extern color  InpLabelColor           = clrWhite;
extern color  InpSpreadColor          = clrGold;
extern color  InpPriceUpColor         = clrLime;
extern color  InpPriceDnColor         = clrCrimson;
extern color  InpPriceAtExtremeColor  = clrDarkGreen;
extern double InpDistanceFromExtreme  = 12.0;  // VERIFIED
extern bool   InpHODLODAlert          = false;
extern double InpPipsToHODLODForAlert = 5.0;   // VERIFIED

//--- v2.00 inputs (operator-tuned 2026-04-28)
extern bool   InpShowWeekLevels       = true;   // Weekly first-4hr H/L
extern bool   InpShowPHODPLOD         = true;   // Yesterday's D1 H/L
extern bool   InpShowOpenTrades       = true;   // Per-position rows
extern bool   InpShowBarTimer         = true;   // v2.01 bar countdown
extern int    InpWeekStartDOW         = 1;      // 0=Sun 1=Mon
extern int    InpWeekFirstHours       = 4;
extern int    InpMaxTradesShown       = 6;
extern color  InpWeekHiColor          = clrDeepSkyBlue;
extern color  InpWeekLoColor          = clrOrange;
extern color  InpPHODColor            = clrRed;
extern color  InpPLODColor            = clrLimeGreen;
extern color  InpBarTimerColor        = clrGold;
//--- v2.01 inputs
extern color  InpTradeColor           = clrWhite; // unified trade-row colour (replaces buy/sell)
extern int    InpYOffset              = 0;         // vertical offset to avoid HUD overlap

string ObjectPrefix = "smBPCT_";
double g_pip = 0.0;
datetime g_last_alert_ts = 0;

//+------------------------------------------------------------------+
int init()
  {
   // [INFER] JPY/3-digit detection — pip math (Pitfall: pip math).
   int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
   g_pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;
   IndicatorShortName("SM_BPCT (mini-HUD)");
   CreateLabels();
   Recompute();
   EventSetTimer(1);  // [INFER] 1-second refresh for live HUD
   return(0);
  }

//+------------------------------------------------------------------+
int deinit()
  {
   CleanupObjects();
   EventKillTimer();
   return(0);
  }

//+------------------------------------------------------------------+
int start()
  {
   return(0);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
  }

//+------------------------------------------------------------------+
//  EnsureLabel — idempotently create and position a row label at
//  the given vertical slot. MQ4 uses 5-arg ObjectCreate then separate
//  ObjectSet/ObjectSetText calls.
//+------------------------------------------------------------------+
void EnsureLabel(string suffix, int row_index)
  {
   string name = ObjectPrefix + suffix;
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_LABEL, 0, 0, 0);  // [INFER] MQ4 5-arg form

   ObjectSet(name, OBJPROP_CORNER,    InpCornerOfChart);
   ObjectSet(name, OBJPROP_XDISTANCE, 8 + InpAdjustSideToSide);
   //--- v2.01: base Y = 60 + InpYOffset so HUD sits below SM_ADR_Marker (Y=40)
   ObjectSet(name, OBJPROP_YDISTANCE,
             60 + InpYOffset + InpShiftUpDn + row_index * 16);
   ObjectSetText(name, "", InpShowSmallerSize ? 9 : 11, "Arial", InpLabelColor);
  }

//+------------------------------------------------------------------+
void CreateLabels()
  {
   // Pre-create the fixed-row labels. Trade rows are created lazily in Recompute().
   // v2.01: bar_timer inserted after spread.
   string rows[10];
   rows[0] = "price";
   rows[1] = "spread";
   rows[2] = "bar_timer";
   rows[3] = "hod";
   rows[4] = "lod";
   rows[5] = "wkhi";
   rows[6] = "wklo";
   rows[7] = "phod";
   rows[8] = "plod";
   rows[9] = "alert";
   for(int i = 0; i < 10; i++)
      EnsureLabel(rows[i], i);
  }

//+------------------------------------------------------------------+
//  v2.01 — bar-close countdown. Format adapts to current timeframe:
//    period <  M15 : "Bar: 47s"
//    M15 <= p <= H1 : "Bar: 12:34"
//    period >  H1  : "Bar: 3:42" (hours:minutes)
//  Uses PeriodSeconds() - (TimeCurrent() % PeriodSeconds()) equivalent.
//+------------------------------------------------------------------+
string FormatBarCountdown()
  {
   int period_s = Period() * 60;  // [INFER] Period() returns minutes in MQ4
   if(period_s <= 0) return("Bar: --");

   // Seconds remaining in the current bar
   long remain = (long)(period_s - ((long)TimeCurrent() % (long)period_s));
   if(remain <= 0) remain = 0;

   if(period_s < 900)              // < M15
      return("Bar: " + IntegerToString((int)remain) + "s");
   if(period_s <= 3600)            // M15..H1
     {
      int mm = (int)(remain / 60);
      int ss = (int)(remain % 60);
      return("Bar: " + IntegerToString(mm) + ":" + (ss < 10 ? "0" : "") + IntegerToString(ss));
     }
   // > H1
   int hh = (int)(remain / 3600);
   int mm = (int)((remain % 3600) / 60);
   return("Bar: " + IntegerToString(hh) + ":" + (mm < 10 ? "0" : "") + IntegerToString(mm));
  }

//+------------------------------------------------------------------+
//  v2.00 — current week's first-4hr H/L.
//  [INFER] Walk back to find the most recent InpWeekStartDOW day,
//  then collect H4 highs/lows within InpWeekFirstHours from that anchor.
//+------------------------------------------------------------------+
bool ComputeWeekFirst4hr(double &hi, double &lo)
  {
   // [INFER] Find the start-of-week anchor (midnight of InpWeekStartDOW)
   datetime now    = TimeCurrent();
   long     s      = (long)now;
   long     anchor = (s / 86400) * 86400;
   datetime day    = (datetime)anchor;
   for(int i = 0; i < 7; i++)
     {
      MqlDateTime mdt;
      TimeToStruct(day, mdt);
      if(mdt.day_of_week == InpWeekStartDOW) break;
      day -= 86400;
     }
   datetime t1 = day;
   datetime t2 = t1 + InpWeekFirstHours * 3600;

   // [INFER] Scan current-chart-period bars between t1 and t2
   hi = -DBL_MAX;
   lo =  DBL_MAX;
   bool found = false;
   int total_bars = iBars(_Symbol, _Period);
   for(int b = total_bars - 1; b >= 0; b--)
     {
      datetime bar_t = (datetime)iTime(_Symbol, _Period, b);
      if(bar_t < t1) continue;
      if(bar_t >= t2) continue;
      double bhi = iHigh(_Symbol, _Period, b);
      double blo = iLow (_Symbol, _Period, b);
      if(bhi > hi) hi = bhi;
      if(blo < lo) lo = blo;
      found = true;
     }
   return(found && hi > -DBL_MAX && lo < DBL_MAX);
  }

//+------------------------------------------------------------------+
void Recompute()
  {
   double bid = MarketInfo(_Symbol, MODE_BID);
   double ask = MarketInfo(_Symbol, MODE_ASK);
   if(bid <= 0.0 || ask <= 0.0 || g_pip <= 0.0)
      return;

   double hod = iHigh(_Symbol, PERIOD_D1, 0);
   double lod = iLow (_Symbol, PERIOD_D1, 0);
   double spread_pips = (ask - bid) / g_pip;
   double hod_dist    = (hod - bid) / g_pip;
   double lod_dist    = (bid - lod) / g_pip;

   //--- v2.00 — yesterday's D1 H/L (PHOD/PLOD — bar[1] is yesterday; Pitfall 5 guard)
   double phod = iHigh(_Symbol, PERIOD_D1, 1);
   double plod = iLow (_Symbol, PERIOD_D1, 1);

   //--- v2.00 — current week's first-4hr H/L
   double wk_hi = 0.0, wk_lo = 0.0;
   bool   wk_ok = ComputeWeekFirst4hr(wk_hi, wk_lo);

   color price_color = InpLabelColor;
   if(InpShowPrice)
     {
      // [INFER] At-extreme color
      if(hod_dist < InpDistanceFromExtreme || lod_dist < InpDistanceFromExtreme)
         price_color = InpPriceAtExtremeColor;
      else
         price_color = (bid >= (hod + lod) / 2.0) ? InpPriceUpColor : InpPriceDnColor;
     }

   if(InpShowPrice)
      SetLabel("price",
               _Symbol + "  " + DoubleToStr(bid, (int)MarketInfo(_Symbol, MODE_DIGITS)),
               price_color);

   if(InpShowXtraDetails)
      SetLabel("spread",
               "Spread: " + DoubleToStr(spread_pips, 1) + " pips",
               InpSpreadColor);

   //--- v2.01 bar countdown
   if(InpShowBarTimer)
      SetLabel("bar_timer", FormatBarCountdown(), InpBarTimerColor);
   else
      SetLabel("bar_timer", "", InpLabelColor);

   if(InpShowTradePips)
     {
      SetLabel("hod",
               "HOD: " + DoubleToStr(hod, (int)MarketInfo(_Symbol, MODE_DIGITS))
                       + " (-" + DoubleToStr(hod_dist, 1) + " pips)",
               InpLabelColor);
      SetLabel("lod",
               "LOD: " + DoubleToStr(lod, (int)MarketInfo(_Symbol, MODE_DIGITS))
                       + " (+" + DoubleToStr(lod_dist, 1) + " pips)",
               InpLabelColor);
     }
   else
     {
      SetLabel("hod", "", InpLabelColor);
      SetLabel("lod", "", InpLabelColor);
     }

   //--- v2.00 weekly + PHOD/PLOD rows
   if(InpShowWeekLevels && wk_ok)
     {
      double wk_hi_dist = (bid - wk_hi) / g_pip;
      double wk_lo_dist = (bid - wk_lo) / g_pip;
      SetLabel("wkhi",
               "WkHi: " + DoubleToStr(wk_hi, (int)MarketInfo(_Symbol, MODE_DIGITS))
                        + " (" + (wk_hi_dist >= 0 ? "+" : "") + DoubleToStr(wk_hi_dist, 1) + " p)",
               InpWeekHiColor);
      SetLabel("wklo",
               "WkLo: " + DoubleToStr(wk_lo, (int)MarketInfo(_Symbol, MODE_DIGITS))
                        + " (" + (wk_lo_dist >= 0 ? "+" : "") + DoubleToStr(wk_lo_dist, 1) + " p)",
               InpWeekLoColor);
     }
   else
     {
      SetLabel("wkhi", "", InpLabelColor);
      SetLabel("wklo", "", InpLabelColor);
     }

   if(InpShowPHODPLOD)
     {
      double phod_dist = (bid - phod) / g_pip;
      double plod_dist = (bid - plod) / g_pip;
      SetLabel("phod",
               "PHOD: " + DoubleToStr(phod, (int)MarketInfo(_Symbol, MODE_DIGITS))
                        + " (" + (phod_dist >= 0 ? "+" : "") + DoubleToStr(phod_dist, 1) + " p)",
               InpPHODColor);
      SetLabel("plod",
               "PLOD: " + DoubleToStr(plod, (int)MarketInfo(_Symbol, MODE_DIGITS))
                        + " (" + (plod_dist >= 0 ? "+" : "") + DoubleToStr(plod_dist, 1) + " p)",
               InpPLODColor);
     }
   else
     {
      SetLabel("phod", "", InpLabelColor);
      SetLabel("plod", "", InpLabelColor);
     }

   //--- v2.00 per-trade rows (MQ4 order model)
   //--- v2.01: 10 fixed rows (bar_timer added between spread and hod).
   int next_row     = 9;  // start trades at row index 9 (which was "alert")
   int trades_drawn = 0;
   if(InpShowOpenTrades)
     {
      for(int i = OrdersTotal() - 1; i >= 0 && trades_drawn < InpMaxTradesShown; i--)
        {
         if(!OrderSelect(i, SELECT_BY_POS)) continue;         // [INFER] MQ4 order model
         if(OrderSymbol() != _Symbol)       continue;

         double entry   = OrderOpenPrice();
         int    otype   = OrderType();
         bool   is_buy  = (otype == OP_BUY);  // [INFER] OP_BUY / OP_SELL MQ4 constants

         //--- distances signed from ENTRY price (positive = level above entry)
         double d_wkhi = wk_ok ? (wk_hi - entry) / g_pip : 0.0;
         double d_wklo = wk_ok ? (wk_lo - entry) / g_pip : 0.0;
         double d_phod = (phod - entry) / g_pip;
         double d_plod = (plod - entry) / g_pip;

         string row_suffix = "trade_" + IntegerToString(trades_drawn);
         EnsureLabel(row_suffix, next_row);
         //--- v2.01: unified trade colour (InpTradeBuyColor / InpTradeSellColor removed)
         SetLabel(row_suffix,
                  (is_buy ? "L " : "S ") + DoubleToStr(entry, (int)MarketInfo(_Symbol, MODE_DIGITS))
                  + ": WkH" + (d_wkhi >= 0 ? "+" : "") + DoubleToStr(d_wkhi, 0)
                  + " WkL" + (d_wklo >= 0 ? "+" : "") + DoubleToStr(d_wklo, 0)
                  + " PHOD" + (d_phod >= 0 ? "+" : "") + DoubleToStr(d_phod, 0)
                  + " PLOD" + (d_plod >= 0 ? "+" : "") + DoubleToStr(d_plod, 0),
                  InpTradeColor);
         trades_drawn++;
         next_row++;
        }

      //--- Hide unused trade slots from prior frames
      for(int t = trades_drawn; t < InpMaxTradesShown; t++)
        {
         string nm = ObjectPrefix + "trade_" + IntegerToString(t);
         if(ObjectFind(nm) >= 0)
            ObjectSetText(nm, "", InpShowSmallerSize ? 9 : 11, "Arial", InpLabelColor);
        }
     }

   //--- Alert row pinned below all dynamic rows
   EnsureLabel("alert", next_row);

   string alert_text  = "";
   color  alert_color = InpLabelColor;
   if(InpHODLODAlert)
     {
      if(hod_dist < InpPipsToHODLODForAlert)
        {
         alert_text  = "NEAR HOD";
         alert_color = InpPriceAtExtremeColor;
         FireAlertOnce("SM_BPCT: " + _Symbol + " near HOD");
        }
      else if(lod_dist < InpPipsToHODLODForAlert)
        {
         alert_text  = "NEAR LOD";
         alert_color = InpPriceAtExtremeColor;
         FireAlertOnce("SM_BPCT: " + _Symbol + " near LOD");
        }
     }
   SetLabel("alert", alert_text, alert_color);
  }

//+------------------------------------------------------------------+
void SetLabel(string suffix, string text, color c)
  {
   string name = ObjectPrefix + suffix;
   ObjectSetText(name, text, InpShowSmallerSize ? 9 : 11, "Arial", c);
  }

//+------------------------------------------------------------------+
void FireAlertOnce(string msg)
  {
   // [INFER] Suppress duplicate alerts within the same minute.
   datetime now = TimeCurrent();
   if(now - g_last_alert_ts < 60)
      return;
   g_last_alert_ts = now;
   Alert(msg);
  }

//+------------------------------------------------------------------+
void CleanupObjects()
  {
   for(int i = ObjectsTotal() - 1; i >= 0; i--)
     {
      string n = ObjectName(i);
      if(StringFind(n, ObjectPrefix) == 0)
         ObjectDelete(n);
     }
  }

//+------------------------------------------------------------------+
//|  SM_BPCT.mq5                                                      |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (v2.00)               |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md |
//|                                                                   |
//|  D-17 Built ⚠ Low confidence — implementation per Verified Updates|
//|  2026-04-27 mini-HUD interpretation, NOT spec body's pressure-    |
//|  tracker hypothesis (Pitfall 10). Every guessed branch carries    |
//|  // [INFER] (D-17).                                                |
//|                                                                   |
//|  v2.00 (operator-tuned 2026-04-28) — adds open-trade tracking:    |
//|     - Weekly first-4hr H/L (psych S/R per IlsleyPsychLevels v2.00)|
//|     - PHOD / PLOD (yesterday's D1 high/low)                        |
//|     - Per open position on current symbol: distance from each of  |
//|       the four key levels in pips, signed                          |
//|                                                                   |
//|  v2.01 (operator-tuned 2026-04-28 round 2):                        |
//|     - Bar countdown row (TF-adaptive: <15min=Ns, 15m–1h=M:SS,     |
//|       >1h=H:MM)                                                    |
//|     - Removed InpTradeBuyColor / InpTradeSellColor                |
//|     - Base Y offset 20→60 to coexist with SM_ADR_Marker corner    |
//|       label (Y=40)                                                 |
//|                                                                   |
//|  Mini-HUD: corner-positioned OBJ_LABEL stack displaying real-time |
//|  price + spread + bar timer + HOD/LOD + weekly + PHOD/PLOD +      |
//|  per-trade rows.                                                  |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_BPCT.ex4 (mini-HUD per Verified Updates)"
#property version   "2.01"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

// [INFER] (D-17 Low confidence) — implementation per Verified Updates
// 2026-04-27 mini-HUD interpretation, NOT spec body's pressure-tracker
// hypothesis (see SM_BPCT.md Pitfall 10).

//--- Spec Section 3 — Verified Updates 2026-04-27 (16 inputs verbatim)
input ENUM_BASE_CORNER InpCornerOfChart        = CORNER_RIGHT_UPPER; // VERIFIED RIGHT_TOP
input bool             InpShowPrice            = true;
input bool             InpShowXtraDetails      = true;
input bool             InpShowSmallerSize      = true;
input bool             InpShowTradePips        = true;
input int              InpShiftUpDn            = 0;        // pixel offset
input int              InpAdjustSideToSide     = 0;
input color            InpLabelColor           = clrWhite;
input color            InpSpreadColor          = clrGold;
input color            InpPriceUpColor         = clrLime;
input color            InpPriceDnColor         = clrCrimson;
input color            InpPriceAtExtremeColor  = clrDarkGreen; // C'0,100,0' equivalent
input double           InpDistanceFromExtreme  = 12.0;     // VERIFIED pip threshold
input bool             InpHODLODAlert          = false;
input double           InpPipsToHODLODForAlert = 5.0;      // VERIFIED

//--- v2.00 inputs (operator-tuned 2026-04-28)
input bool             InpShowWeekLevels       = true;       // Weekly first-4hr H/L
input bool             InpShowPHODPLOD         = true;       // Yesterday's D1 H/L
input bool             InpShowOpenTrades       = true;       // Per-position rows
input bool             InpShowBarTimer         = true;       // v2.01 bar countdown
input int              InpWeekStartDOW         = 1;          // 0=Sun 1=Mon
input int              InpWeekFirstHours       = 4;
input int              InpMaxTradesShown       = 6;
input color            InpWeekHiColor          = clrDeepSkyBlue;
input color            InpWeekLoColor          = clrOrange;
input color            InpPHODColor            = clrRed;
input color            InpPLODColor            = clrLimeGreen;
input color            InpBarTimerColor        = clrGold;

const string InpObjectPrefix = "smBPCT_";

//--- Module state
double g_pip = 0.0;
datetime g_last_alert_ts = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   // [INFER] JPY/3-digit detection — pip math (Pitfall: pip math).
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   g_pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;

   IndicatorSetString(INDICATOR_SHORTNAME, "SM_BPCT (mini-HUD)");

   CreateLabels();
   Recompute();
   EventSetTimer(1);  // [INFER] 1-second refresh for live HUD
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   CleanupObjects();
   EventKillTimer();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tv[],
                const long &v[], const int &sp[])
  {
   // [INFER] No per-bar buffer work — HUD updates on timer.
   return(rates_total);
  }

//+------------------------------------------------------------------+
//  v2.00 — labels now created lazily as needed, since the row count
//  depends on the number of open positions. EnsureLabel idempotently
//  creates and positions a row at the given vertical slot.
//+------------------------------------------------------------------+
void EnsureLabel(string suffix, int row_index)
  {
   string name = InpObjectPrefix + suffix;
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);

   ObjectSetInteger(0, name, OBJPROP_CORNER,    InpCornerOfChart);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 8 + InpAdjustSideToSide);
   //--- v2.01 base Y bumped from 20 → 60 so HUD sits below the SM_ADR_Marker
   //--- corner label (which lives at Y=40) when both run on the same chart.
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE,
                    60 + InpShiftUpDn + row_index * 16);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE,
                    InpShowSmallerSize ? 9 : 11);
   ObjectSetString (0, name, OBJPROP_FONT, "Arial");
   ObjectSetInteger(0, name, OBJPROP_ANCHOR,
                    (InpCornerOfChart == CORNER_RIGHT_UPPER ||
                     InpCornerOfChart == CORNER_RIGHT_LOWER)
                       ? ANCHOR_RIGHT_UPPER : ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN,    true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE,false);
  }

//+------------------------------------------------------------------+
void CreateLabels()
  {
   // Pre-create the fixed-row labels. Trade rows are created in Recompute().
   // v2.01: bar_timer inserted after spread.
   string fixed_rows[] = {"price", "spread", "bar_timer",
                          "hod", "lod", "wkhi", "wklo", "phod", "plod", "alert"};
   for(int i = 0; i < ArraySize(fixed_rows); i++)
      EnsureLabel(fixed_rows[i], i);
  }

//+------------------------------------------------------------------+
//  v2.01 — bar-close countdown text. Format adapts to the current
//  timeframe per operator request:
//    period <  15min : "Bar: 47s"
//    15min ≤ p ≤ 1h  : "Bar: 12:34"
//    period >  1h    : "Bar: 3:42" (hours:minutes)
//+------------------------------------------------------------------+
string FormatBarCountdown()
  {
   datetime cur_bar  = iTime(_Symbol, _Period, 0);
   int      period_s = PeriodSeconds(_Period);
   if(cur_bar == 0 || period_s <= 0) return("Bar: --");

   datetime next_bar = cur_bar + period_s;
   long     remain   = (long)(next_bar - TimeCurrent());
   if(remain < 0) remain = 0;

   if(period_s < 900)               // < M15
      return(StringFormat("Bar: %ds", (int)remain));
   if(period_s <= 3600)             // M15..H1
     {
      int mm = (int)(remain / 60);
      int ss = (int)(remain % 60);
      return(StringFormat("Bar: %d:%02d", mm, ss));
     }
   // > H1
   int hh = (int)(remain / 3600);
   int mm = (int)((remain % 3600) / 60);
   return(StringFormat("Bar: %d:%02d", hh, mm));
  }

//+------------------------------------------------------------------+
void Recompute()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(bid <= 0.0 || ask <= 0.0 || g_pip <= 0.0)
      return;

   double hod = iHigh(_Symbol, PERIOD_D1, 0);
   double lod = iLow (_Symbol, PERIOD_D1, 0);
   double spread_pips = (ask - bid) / g_pip;
   double hod_dist    = (hod - bid) / g_pip;
   double lod_dist    = (bid - lod) / g_pip;

   //--- v2.00 — yesterday's D1 H/L (PHOD/PLOD)
   double phod = iHigh(_Symbol, PERIOD_D1, 1);
   double plod = iLow (_Symbol, PERIOD_D1, 1);

   //--- v2.00 — current week's first-4hr H/L
   double wk_hi = 0.0, wk_lo = 0.0;
   bool   wk_ok = ComputeWeekFirst4hr(wk_hi, wk_lo);

   color price_color = InpLabelColor;
   if(InpShowPrice)
     {
      if(hod_dist < InpDistanceFromExtreme || lod_dist < InpDistanceFromExtreme)
         price_color = InpPriceAtExtremeColor;
      else
         price_color = (bid >= (hod + lod) / 2.0) ? InpPriceUpColor : InpPriceDnColor;
     }

   if(InpShowPrice)
      SetLabel("price",
               StringFormat("%s  %.5f", _Symbol, bid),
               price_color);

   if(InpShowXtraDetails)
      SetLabel("spread",
               StringFormat("Spread: %.1f pips", spread_pips),
               InpSpreadColor);

   if(InpShowBarTimer)
      SetLabel("bar_timer", FormatBarCountdown(), InpBarTimerColor);
   else
      SetLabel("bar_timer", "", InpLabelColor);

   if(InpShowTradePips)
     {
      SetLabel("hod",
               StringFormat("HOD: %.5f (-%.1f pips)", hod, hod_dist),
               InpLabelColor);
      SetLabel("lod",
               StringFormat("LOD: %.5f (+%.1f pips)", lod, lod_dist),
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
      SetLabel("wkhi",
               StringFormat("WkHi: %.5f (%+.1f p)", wk_hi, (bid - wk_hi) / g_pip),
               InpWeekHiColor);
      SetLabel("wklo",
               StringFormat("WkLo: %.5f (%+.1f p)", wk_lo, (bid - wk_lo) / g_pip),
               InpWeekLoColor);
     }
   else
     {
      SetLabel("wkhi", "", InpLabelColor);
      SetLabel("wklo", "", InpLabelColor);
     }

   if(InpShowPHODPLOD)
     {
      SetLabel("phod",
               StringFormat("PHOD: %.5f (%+.1f p)", phod, (bid - phod) / g_pip),
               InpPHODColor);
      SetLabel("plod",
               StringFormat("PLOD: %.5f (%+.1f p)", plod, (bid - plod) / g_pip),
               InpPLODColor);
     }
   else
     {
      SetLabel("phod", "", InpLabelColor);
      SetLabel("plod", "", InpLabelColor);
     }

   //--- v2.00 per-trade rows (after the 10 fixed rows)
   //--- v2.01: 10 fixed rows now (bar_timer added between spread and hod).
   int next_row = 10;
   int trades_drawn = 0;
   if(InpShowOpenTrades)
     {
      next_row = 9;  // start trades at row index 9 (which was "alert")
      int total = PositionsTotal();
      for(int idx = 0; idx < total && trades_drawn < InpMaxTradesShown; idx++)
        {
         ulong ticket = PositionGetTicket(idx);
         if(ticket == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

         double entry = PositionGetDouble(POSITION_PRICE_OPEN);
         long   ptype = PositionGetInteger(POSITION_TYPE);
         bool   is_buy = (ptype == POSITION_TYPE_BUY);

         //--- distances signed from ENTRY price (positive = level above entry)
         double d_wkhi = wk_ok ? (wk_hi - entry) / g_pip : 0.0;
         double d_wklo = wk_ok ? (wk_lo - entry) / g_pip : 0.0;
         double d_phod = (phod - entry) / g_pip;
         double d_plod = (plod - entry) / g_pip;

         string row_suffix = StringFormat("trade_%d", trades_drawn);
         EnsureLabel(row_suffix, next_row);
         //--- v2.01: trade color inputs removed; use InpLabelColor uniformly
         SetLabel(row_suffix,
                  StringFormat("%s %.5f: WkH%+.0f WkL%+.0f PHOD%+.0f PLOD%+.0f",
                               is_buy ? "L" : "S", entry,
                               d_wkhi, d_wklo, d_phod, d_plod),
                  InpLabelColor);
         trades_drawn++;
         next_row++;
        }

      //--- Hide unused trade slots from prior frames
      for(int t = trades_drawn; t < InpMaxTradesShown; t++)
        {
         string row_suffix = StringFormat("trade_%d", t);
         string nm = InpObjectPrefix + row_suffix;
         if(ObjectFind(0, nm) >= 0)
            ObjectSetString(0, nm, OBJPROP_TEXT, "");
        }
     }

   //--- Alert row pinned below all dynamic rows
   EnsureLabel("alert", next_row);

   string alert_text = "";
   color  alert_color = InpLabelColor;
   if(InpHODLODAlert)
     {
      if(hod_dist < InpPipsToHODLODForAlert)
        {
         alert_text = "NEAR HOD";
         alert_color = InpPriceAtExtremeColor;
         FireAlertOnce("SM_BPCT: " + _Symbol + " near HOD");
        }
      else if(lod_dist < InpPipsToHODLODForAlert)
        {
         alert_text = "NEAR LOD";
         alert_color = InpPriceAtExtremeColor;
         FireAlertOnce("SM_BPCT: " + _Symbol + " near LOD");
        }
     }
   SetLabel("alert", alert_text, alert_color);
   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
//  v2.00 — current week's first-4hr H/L (matches IlsleyPsychLevels v2)
//+------------------------------------------------------------------+
bool ComputeWeekFirst4hr(double &hi, double &lo)
  {
   datetime now = TimeCurrent();
   long s = (long)now;
   long anchor = (s / 86400) * 86400;
   datetime day = (datetime)anchor;
   for(int i = 0; i < 7; i++)
     {
      MqlDateTime mdt; TimeToStruct(day, mdt);
      if(mdt.day_of_week == InpWeekStartDOW) break;
      day -= 86400;
     }
   datetime t1 = day;
   datetime t2 = t1 + InpWeekFirstHours * 3600;

   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int n = CopyRates(_Symbol, _Period, t1, t2, rates);
   if(n <= 0) return(false);
   hi = -DBL_MAX; lo = DBL_MAX;
   for(int i = 0; i < n; i++)
     {
      if(rates[i].high > hi) hi = rates[i].high;
      if(rates[i].low  < lo) lo = rates[i].low;
     }
   return(hi > -DBL_MAX && lo < DBL_MAX);
  }

//+------------------------------------------------------------------+
void SetLabel(string suffix, string text, color c)
  {
   string name = InpObjectPrefix + suffix;
   ObjectSetString (0, name, OBJPROP_TEXT,  text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
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
   for(int i = ObjectsTotal(0, 0, -1) - 1; i >= 0; i--)
     {
      string n = ObjectName(0, i, 0, -1);
      if(StringFind(n, InpObjectPrefix) == 0)
         ObjectDelete(0, n);
     }
  }

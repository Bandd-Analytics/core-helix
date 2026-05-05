//+------------------------------------------------------------------+
//|  SM_ADR_Marker.mq5                                                |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (v2.00)               |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_ADR_Marker.md                                            |
//|  Verified Updates 2026-04-27: ATRPeriod=14 (was claimed 20)       |
//|  Precedent: V2/indicators/ADR_Levels.mq5 (Phase 8.4 INFRA-04)     |
//|                                                                   |
//|  v2.00 (operator-tuned 2026-04-28):                                |
//|    - Fixed disappear/reappear bug on TF/symbol switch:            |
//|      adds OnChartEvent CHART_CHANGE handler + retry on            |
//|      CopyBuffer-not-ready (was a one-shot fail-silent path).      |
//|    - Adds OBJ_TEXT price labels ABOVE each line ("ADR Hi 1.2540") |
//|    - Confirmed daily-anchored: ADR re-anchors to today_open every |
//|      D1 bar; the lines do NOT change between intra-day TF switches.|
//|                                                                   |
//|  Computes ATR(14) on PERIOD_D1 and draws three OBJ_HLINE markers: |
//|     adr-high  =  today_open + ADR / 2                              |
//|     adr-mid   =  today_open                                        |
//|     adr-low   =  today_open - ADR / 2                              |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_ADR_Marker.ex4"
#property version   "2.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0   // We draw via ObjectCreate, not buffers.

// Optional advisory parity dump — operator defines DUMP_PARITY_CSV at top
// to emit per-bar CSV to MQL5/Files/parity_SM_ADR_Marker_<symbol>_<tf>.csv
// for use with scripts/parity_check_adr_marker.py (CONTEXT D-15 advisory).
// #define DUMP_PARITY_CSV

//--- Spec Section 3 inputs (Verified Updates 2026-04-27)
input int             InpTimeZoneOfData     = 0;            // Broker server-time offset hours
input int             InpTimeZoneOfSession  = 0;            // Trading-session reference TZ hours
input int             InpATRPeriod          = 14;           // VERIFIED 2026-04-27 (was 20)
input bool            InpUseManualADR       = false;        // Bypass auto-ATR
input int             InpManualADRValuePips = 0;            // Used when UseManualADR=true
input ENUM_LINE_STYLE InpLineStyle          = STYLE_DOT;    // VERIFIED LineStyle=2
input int             InpLineThickness1     = 1;            // First-line pixel width
input color           InpLineColor1         = clrOrange;    // VERIFIED LineColor1
input int             InpLineThickness2     = 2;            // Second-line pixel width
input color           InpLineColor2         = clrRed;       // VERIFIED LineColor2
input int             InpBarForLabels       = -10;          // Label X-anchor (bars from last)
input bool            InpDebugLogger        = false;        // Verbose logs
input bool            InpShowtext           = true;         // v2.00: price labels above lines (was false)
input int             InpLabelFontSize      = 9;
input ENUM_BASE_CORNER InpCornerLabelCorner = CORNER_LEFT_UPPER; // Corner for "ADR(N): X pips" summary label
input int             InpCornerLabelX       = 8;            // X offset for corner label
input int             InpCornerLabelY       = 18;           // Y offset for corner label

const string InpObjectPrefix = "smADR_";

//--- Module state
int      g_atr_handle  = INVALID_HANDLE;
datetime g_last_d1_bar = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   //--- ATR(14) on D1 — Pattern 2 indicator-handle composition (RESEARCH).
   g_atr_handle = iATR(_Symbol, PERIOD_D1, InpATRPeriod);
   if(g_atr_handle == INVALID_HANDLE)
     {
      Print("SM_ADR_Marker: iATR handle creation failed");
      return(INIT_FAILED);
     }

   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("SM_ADR_Marker(%d)", InpATRPeriod));

   Recompute();
   EventSetTimer(60);  // Refresh once per minute (cheap; only redraws on D1 change)
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   CleanupObjects();
   if(g_atr_handle != INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   EventKillTimer();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
//  v2.00: redraw on chart timeframe / symbol change. Without this,
//  the iATR handle was reissued by OnInit but CopyBuffer returned 0
//  (data not yet ready) and the indicator silently returned blank.
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lp,
                  const double &dp, const string &sp)
  {
   if(id == CHARTEVENT_CHART_CHANGE)
     {
      Recompute();
      ChartRedraw(0);
     }
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tv[],
                const long &v[], const int &sp[])
  {
   datetime cur_d1 = iTime(_Symbol, PERIOD_D1, 0);
   //--- v2.00: also recompute when our objects are missing (recovery
   //--- path for ATR-not-ready-on-load case).
   bool need_redraw = (cur_d1 != g_last_d1_bar) ||
                      (ObjectFind(0, InpObjectPrefix + "high") < 0);
   if(need_redraw)
     {
      Recompute();
      g_last_d1_bar = cur_d1;
     }
   return(rates_total);
  }

//+------------------------------------------------------------------+
void Recompute()
  {
   double adr = 0.0;

   if(InpUseManualADR)
     {
      // Pip → price conversion. JPY/3-digit detection per Pitfall edge case.
      int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      double pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;
      adr = InpManualADRValuePips * pip;
     }
   else
     {
      // Bar 1 = last completed D1 bar (Pitfall 5 lookahead-bias guard).
      double atr_buf[];
      ArraySetAsSeries(atr_buf, true);
      if(CopyBuffer(g_atr_handle, 0, 1, 1, atr_buf) <= 0)
        {
         if(InpDebugLogger)
            Print("SM_ADR_Marker: CopyBuffer failed — ATR not yet ready");
         return;
        }
      adr = atr_buf[0];
     }

   double today_open = iOpen(_Symbol, PERIOD_D1, 0);
   if(today_open <= 0.0)
      return;

   double adr_high = today_open + adr / 2.0;
   double adr_low  = today_open - adr / 2.0;
   double adr_mid  = today_open;

   // Per Verified Updates: LineColor1=Orange (Thickness1=1) — primary marker.
   //                      LineColor2=Red    (Thickness2=2) — secondary marker.
   // Convention: Color1/Thickness1 → high+low boundaries; Color2/Thickness2 → mid.
   DrawHLine(InpObjectPrefix + "high", adr_high,
             InpLineColor1, InpLineThickness1);
   DrawHLine(InpObjectPrefix + "low",  adr_low,
             InpLineColor1, InpLineThickness1);
   DrawHLine(InpObjectPrefix + "mid",  adr_mid,
             InpLineColor2, InpLineThickness2);

   if(InpShowtext)
     {
      // v2.00: per-line price labels above each line + corner pip total.
      DrawPriceLabel(InpObjectPrefix + "high_lbl", adr_high,
                     "ADR Hi " + DoubleToString(adr_high, _Digits),
                     InpLineColor1);
      DrawPriceLabel(InpObjectPrefix + "low_lbl", adr_low,
                     "ADR Lo " + DoubleToString(adr_low, _Digits),
                     InpLineColor1);
      DrawPriceLabel(InpObjectPrefix + "mid_lbl", adr_mid,
                     "Open " + DoubleToString(adr_mid, _Digits),
                     InpLineColor2);
      DrawCornerLabel(adr);
     }

#ifdef DUMP_PARITY_CSV
   DumpParityRow(today_open, adr, adr_high, adr_low);
#endif

   if(InpDebugLogger)
      PrintFormat("SM_ADR_Marker: today_open=%.5f adr=%.5f high=%.5f low=%.5f",
                  today_open, adr, adr_high, adr_low);
  }

//+------------------------------------------------------------------+
void DrawHLine(string name, double price, color c, int thickness)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);

   ObjectSetDouble (0, name, OBJPROP_PRICE,    price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,    c);
   ObjectSetInteger(0, name, OBJPROP_STYLE,    InpLineStyle);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,    thickness);
   ObjectSetInteger(0, name, OBJPROP_BACK,     true);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN,   true);
  }

//+------------------------------------------------------------------+
//  v2.00 — chart-anchored price label sitting ABOVE the line.
//  ANCHOR_LEFT_LOWER places the bottom-left of text on the price,
//  so text rises above. Time anchor uses the most recent visible bar.
//+------------------------------------------------------------------+
void DrawPriceLabel(string name, double price, string text, color c)
  {
   datetime t = iTime(_Symbol, _Period, 0);
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, t, price);
   ObjectSetString (0, name, OBJPROP_TEXT,     text);
   ObjectSetInteger(0, name, OBJPROP_TIME,     t);
   ObjectSetDouble (0, name, OBJPROP_PRICE,    price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,    c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpLabelFontSize);
   ObjectSetString (0, name, OBJPROP_FONT,     "Arial");
   ObjectSetInteger(0, name, OBJPROP_ANCHOR,   ANCHOR_LEFT_LOWER);
   ObjectSetInteger(0, name, OBJPROP_BACK,     false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN,   true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
  }

//+------------------------------------------------------------------+
//  Corner pip-total summary label (e.g. "ADR(14): 92.3 pips").
//+------------------------------------------------------------------+
void DrawCornerLabel(double adr)
  {
   string name = InpObjectPrefix + "lbl";
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;
   double pips = (pip > 0.0) ? adr / pip : 0.0;
   string text = StringFormat("ADR(%d): %.1f pips", InpATRPeriod, pips);

   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);

   // Anchor must mirror corner — otherwise label text overshoots the chosen offset.
   ENUM_ANCHOR_POINT anchor = (InpCornerLabelCorner == CORNER_RIGHT_UPPER) ? ANCHOR_RIGHT_UPPER
                            : (InpCornerLabelCorner == CORNER_RIGHT_LOWER) ? ANCHOR_RIGHT_LOWER
                            : (InpCornerLabelCorner == CORNER_LEFT_LOWER)  ? ANCHOR_LEFT_LOWER
                                                                           : ANCHOR_LEFT_UPPER;
   ObjectSetString (0, name, OBJPROP_TEXT,      text);
   ObjectSetInteger(0, name, OBJPROP_CORNER,    InpCornerLabelCorner);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, InpCornerLabelX);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, InpCornerLabelY);
   ObjectSetInteger(0, name, OBJPROP_COLOR,     InpLineColor1);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE,  10);
   ObjectSetString (0, name, OBJPROP_FONT,      "Arial");
   ObjectSetInteger(0, name, OBJPROP_ANCHOR,    anchor);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN,    true);
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

//+------------------------------------------------------------------+
#ifdef DUMP_PARITY_CSV
void DumpParityRow(double today_open, double adr,
                   double adr_high, double adr_low)
  {
   // Per RESEARCH § Advisory Parity Check Tooling — emits one row per
   // Recompute() to MQL5/Files/parity_SM_ADR_Marker_<sym>_<tf>.csv.
   // Header is written once on first open.
   string fn = StringFormat("parity_SM_ADR_Marker_%s_%s.csv",
                            _Symbol, EnumToString(_Period));
   int handle = FileOpen(fn, FILE_WRITE | FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
      return;
   if(FileSize(handle) == 0)
      FileWrite(handle, "ts", "adr", "marker_high", "marker_low");
   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, TimeToString(iTime(_Symbol, PERIOD_D1, 0), TIME_DATE | TIME_MINUTES),
             DoubleToString(adr, 8),
             DoubleToString(adr_high, _Digits),
             DoubleToString(adr_low,  _Digits));
   FileClose(handle);
  }
#endif

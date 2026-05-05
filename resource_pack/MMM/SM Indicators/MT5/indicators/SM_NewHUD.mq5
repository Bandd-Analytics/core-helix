//+------------------------------------------------------------------+
//|  SM_NewHUD.mq5                                                   |
//|  Phase 12 Plan 03 — SM Indicators Implementation                 |
//|                                                                  |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/          |
//|        SM_NewHUD.md                                               |
//|  D-17 Built ⚠ Low confidence; implementation per Verified        |
//|  Updates 2026-04-27 18-field set incl. HYADR + Av_N EMA row.    |
//|  Internals [INFER] — every guessed branch tagged.                |
//|                                                                  |
//|  D-08: Wine MetaEditor compile target                            |
//|  D-09: indicator_chart_window (main window)                      |
//|  D-17: Low confidence — OBJ_LABEL HUD layout [INFER]            |
//|                                                                  |
//|  Pitfall 9: Arial font (Wine font cache — Pitfall 9 default)     |
//+------------------------------------------------------------------+
#property copyright   "Bandd Analytics — Phase 12 SM Indicators reconstruction"
#property link        "https://github.com/banddanalytics/helix"
#property version     "1.00"
#property description "SM_NewHUD — 18-field corner HUD (D-17 Low confidence; Verified Updates 2026-04-27)"

#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Inputs — verbatim from VERIFIED-DEFAULTS.md §4 (Verified Updates 2026-04-27)
input int    InpCodeVersion            = 1;
input double InpMaxSpread              = 1.75;          // Verified Updates: MaxSpread
input string InpRangeTodayText         = "TDR";
input string InpRangeYestText          = "YDR";
input string InpRangeWeekText          = "WR";
input int    InpFontSize               = 9;             // Verified Updates: FontSize
input color  InpFontColor              = clrWhite;      // Verified Updates: FontColor
input color  InpSymbolFontColor        = clrBlack;      // Verified Updates: Symbol_FontColor
input int    InpSymbolFontSize         = 14;            // Verified Updates: Symbol_Font_Size
input color  InpPriceColor             = clrBlack;      // [INFER]
input int    InpFontSizeADR3           = 9;             // [INFER]
input color  InpFontColorADR3          = clrYellow;     // [INFER]
input bool   InpShow4DigitPrice        = false;         // [INFER]
input bool   InpColorLastDigit         = false;         // [INFER]
input color  InpLastDigitColor         = C'90,90,90';   // [INFER]
input double InpHiLoAlertDistance1     = 10;            // Verified Updates: HiLoAlert_Distance1
input double InpHiLoAlertDistance2     = 20;            // Verified Updates: HiLoAlert_Distance2
input color  InpHODLODAlertClr         = clrDarkGreen;  // Verified Updates: HODLODAlertClr
input color  InpHODLODNearClr          = clrLawnGreen;  // Verified Updates: HODLODNearClr
input double InpWeekHiLoAlertDistance3 = 25;            // Verified Updates: Week_HiLo_Alert_Distance3
input double InpWeekHiLoAlertDistance4 = 50;            // Verified Updates: Week_HiLo_Alert_Distance4
input double InpADRAlertDistance       = 10;            // Verified Updates: adrAlert_Distance
input bool   InpUseDarkBackground      = false;         // [INFER]
input color  InpBackgroundColor        = clrGray;       // [INFER]
input int    InpBackgroundSize         = 120;           // [INFER]
input bool   InpXLBackgroundForNews    = true;          // [INFER]
input bool   InpOverviewMode           = false;         // [INFER]
input bool   InpTradeTrackMode         = false;         // [INFER]
input ENUM_BASE_CORNER InpCorner        = CORNER_RIGHT_UPPER; // Chart corner for HUD anchor
input int    InpX                      = 80;            // X offset from corner (right corner: must clear price scale, ~60-80px)
input int    InpY                      = 18;            // [INFER] Y position of HUD top
input int    InpYDistance              = 0;             // [INFER] Y spacing between rows
input int    InpAv1                    = 0;             // [INFER] unused/reserved
input int    InpAv2                    = 1;             // Verified Updates: Av_N period 1
input int    InpAv3                    = 4;             // Verified Updates: Av_N period 4
input int    InpAv4                    = 13;            // Verified Updates: Av_N period 13
input int    InpAv5                    = 26;            // Verified Updates: Av_N period 26
input int    InpAv6                    = 52;            // Verified Updates: Av_N period 52

//--- EMA indicator handles (Av_N row — RESEARCH Pattern 2)
int g_ema_handles[5];
int g_ema_periods[5];
static datetime g_last_bar_time = 0;

//--- HUD label names
string g_label_prefix = "smHUD_";

//+------------------------------------------------------------------+
//| Get pip size for current symbol                                  |
//+------------------------------------------------------------------+
double GetPip()
  {
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   return (digits == 3 || digits == 5) ? _Point * 10.0 : _Point;
  }

//+------------------------------------------------------------------+
//| Create or update an OBJ_LABEL HUD field                          |
//+------------------------------------------------------------------+
void SetLabel(const string name, const string text, const int x, const int y,
              const color clr, const int font_size)
  {
   if(ObjectFind(0, name) < 0)
     {
      // Anchor must match corner — otherwise right-corner labels of varying
      // text width left-align off the chosen offset and look ragged.
      ENUM_ANCHOR_POINT anchor = (InpCorner == CORNER_RIGHT_UPPER) ? ANCHOR_RIGHT_UPPER
                               : (InpCorner == CORNER_RIGHT_LOWER) ? ANCHOR_RIGHT_LOWER
                               : (InpCorner == CORNER_LEFT_LOWER)  ? ANCHOR_LEFT_LOWER
                                                                   : ANCHOR_LEFT_UPPER;
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, InpCorner);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetString(0, name,  OBJPROP_FONT, "Arial");  // Pitfall 9 — Wine font cache default
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetString(0, name,  OBJPROP_TEXT,      text);
   ObjectSetInteger(0, name, OBJPROP_COLOR,     clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE,  font_size);
  }

//+------------------------------------------------------------------+
//| Format pips value for display                                    |
//+------------------------------------------------------------------+
string FormatPips(double val, double pip)
  {
   return DoubleToString(val / pip, 1);
  }

//+------------------------------------------------------------------+
//| Recompute and refresh all 18 HUD fields                          |
//+------------------------------------------------------------------+
void Recompute()
  {
   double pip = GetPip();

//--- Live state
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double spread = (ask - bid) / pip;

//--- Spread filter [INFER] — [D-17] no display if spread > MaxSpread
   color spread_color = (spread <= InpMaxSpread) ? InpFontColor : clrRed;

//--- HOD / LOD
   double hod = iHigh(_Symbol, PERIOD_D1, 0);
   double lod  = iLow(_Symbol, PERIOD_D1, 0);
   double hod_dist = (hod - bid) / pip;
   double lod_dist = (bid - lod) / pip;

//--- HOD/LOD color logic per Verified Updates
   color hod_color = (hod_dist < InpHiLoAlertDistance1) ? InpHODLODAlertClr
                   : (hod_dist < InpHiLoAlertDistance2) ? InpHODLODNearClr
                   : InpFontColor;
   color lod_color = (lod_dist < InpHiLoAlertDistance1) ? InpHODLODAlertClr
                   : (lod_dist < InpHiLoAlertDistance2) ? InpHODLODNearClr
                   : InpFontColor;

//--- TDR / YDR
   double tdr = iHigh(_Symbol, PERIOD_D1, 0) - iLow(_Symbol, PERIOD_D1, 0);
   double ydr = iHigh(_Symbol, PERIOD_D1, 1) - iLow(_Symbol, PERIOD_D1, 1);

//--- ADR variants — [INFER] rolling means per Open Question #4
   double wadr = 0.0, madr = 0.0, hyadr = 0.0;
   for(int i = 0; i < 5; i++)   // WADR = 5-day mean [INFER]
      wadr += (iHigh(_Symbol, PERIOD_D1, i) - iLow(_Symbol, PERIOD_D1, i));
   wadr /= 5.0;
   for(int i = 0; i < 22; i++)  // MADR = 22-day mean [INFER]
      madr += (iHigh(_Symbol, PERIOD_D1, i) - iLow(_Symbol, PERIOD_D1, i));
   madr /= 22.0;
   for(int i = 0; i < 132; i++) // HYADR = 132-day mean (half-yearly) [INFER] (Verified Updates NEW)
      hyadr += (iHigh(_Symbol, PERIOD_D1, i) - iLow(_Symbol, PERIOD_D1, i));
   hyadr /= 132.0;

   double x3_adr = wadr * 3.0;  // [INFER] 3×ADR display

//--- Week H/L / WR [INFER]
   double wh = iHigh(_Symbol, PERIOD_W1, 0);
   double wl = iLow(_Symbol, PERIOD_W1, 0);
   double wr = wh - wl;
   double wh_dist = (wh - bid) / pip;
   double wl_dist = (bid - wl) / pip;

//--- PTO (Price-To-Open) [INFER]
   double day_open = iOpen(_Symbol, PERIOD_D1, 0);
   double pto = (bid - day_open) / pip;

//--- Candle countdown [INFER] — seconds remaining in current bar
   int bar_seconds = PeriodSeconds();
   int elapsed = (int)(TimeCurrent() % bar_seconds);
   int remaining = bar_seconds - elapsed;
   int mm = remaining / 60;
   int ss = remaining % 60;
   string candle_time = IntegerToString(mm, 2, '0') + ":" + IntegerToString(ss, 2, '0');

//--- Av_N EMA values per Verified Updates (1, 4, 13, 26, 52)
   int av_periods[] = {InpAv2, InpAv3, InpAv4, InpAv5, InpAv6};
   double ema_vals[5];
   for(int k = 0; k < 5; k++)
     {
      if(g_ema_handles[k] != INVALID_HANDLE)
        {
         double buf[1];
         if(CopyBuffer(g_ema_handles[k], 0, 0, 1, buf) > 0)
            ema_vals[k] = buf[0];
         else
            ema_vals[k] = 0.0;
        }
      else
         ema_vals[k] = 0.0;  // [INFER] fallback if handle not initialized
     }

//--- Build HUD display (18 rows, x from InpX, y starting at InpY, line height ~14px [INFER])
   int x = InpX;
   int y = InpY;
   int line_h = 14 + InpYDistance;  // [INFER] line height

   SetLabel(g_label_prefix+"sym",   _Symbol,                                     x, y,             InpSymbolFontColor, InpSymbolFontSize);
   y += InpSymbolFontSize + 4;
   SetLabel(g_label_prefix+"bid",   "BID: " + DoubleToString(bid, _Digits),      x, y, InpFontColor, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"ask",   "ASK: " + DoubleToString(ask, _Digits),      x, y, InpFontColor, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"spd",   "SPD: " + DoubleToString(spread, 1),         x, y, spread_color, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"hod",   "HOD: " + DoubleToString(hod, _Digits)
                                  + " (" + FormatPips(hod_dist * pip, pip) + "p)", x, y, hod_color, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"lod",   "LOD: " + DoubleToString(lod, _Digits)
                                  + " (" + FormatPips(lod_dist * pip, pip) + "p)", x, y, lod_color, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"tdr",   InpRangeTodayText+": " + FormatPips(tdr, pip) + "p", x, y, InpFontColor, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"ydr",   InpRangeYestText +": " + FormatPips(ydr, pip) + "p", x, y, InpFontColor, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"wadr",  "WADR: " + FormatPips(wadr, pip) + "p",      x, y, InpFontColor, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"madr",  "MADR: " + FormatPips(madr, pip) + "p",      x, y, InpFontColor, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"hyadr", "HYADR: " + FormatPips(hyadr, pip) + "p",   x, y, InpFontColor, InpFontSize); y += line_h;  // Verified Updates NEW
   SetLabel(g_label_prefix+"pto",   "PTO: " + DoubleToString(pto, 1) + "p",      x, y, InpFontColor, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"wh",    "WH: " + DoubleToString(wh, _Digits)
                                  + " (" + FormatPips(wh_dist * pip, pip) + "p)", x, y, InpFontColor, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"wl",    "WL: " + DoubleToString(wl, _Digits)
                                  + " (" + FormatPips(wl_dist * pip, pip) + "p)", x, y, InpFontColor, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"wr",    InpRangeWeekText+": " + FormatPips(wr, pip) + "p", x, y, InpFontColor, InpFontSize); y += line_h;
   SetLabel(g_label_prefix+"3adr",  "3xADR: " + FormatPips(x3_adr, pip) + "p",  x, y, InpFontColorADR3, InpFontSizeADR3); y += line_h;
   SetLabel(g_label_prefix+"time",  "Candle: " + candle_time,                    x, y, InpFontColor, InpFontSize); y += line_h;

//--- Av_N EMA row — Verified Updates periods 1, 4, 13, 26, 52
   for(int k = 0; k < 5; k++)
     {
      string lbl = g_label_prefix + "ema" + IntegerToString(av_periods[k]);
      string txt = "Av" + IntegerToString(av_periods[k]) + ": " + DoubleToString(ema_vals[k], _Digits);
      SetLabel(lbl, txt, x, y, InpFontColor, InpFontSize);
      y += line_h;
     }

   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Delete all HUD label objects                                     |
//+------------------------------------------------------------------+
void CleanupObjects()
  {
   int total = ObjectsTotal(0);
   for(int i = total - 1; i >= 0; i--)
     {
      string name = ObjectName(0, i);
      if(StringFind(name, g_label_prefix) == 0)
         ObjectDelete(0, name);
     }
  }

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   IndicatorSetString(INDICATOR_SHORTNAME, "SM_NewHUD");

//--- Initialize EMA handles for Av_N row per RESEARCH Pattern 2
   int av_periods[] = {InpAv2, InpAv3, InpAv4, InpAv5, InpAv6};
   for(int k = 0; k < 5; k++)
     {
      g_ema_periods[k] = av_periods[k];
      g_ema_handles[k] = iMA(_Symbol, PERIOD_CURRENT, av_periods[k], 0, MODE_EMA, PRICE_CLOSE);
      if(g_ema_handles[k] == INVALID_HANDLE)
        {
         Print("SM_NewHUD: WARN — cannot allocate EMA handle for period ", av_periods[k]);
         // [INFER] Non-fatal: continue without this EMA (degraded display)
        }
     }

   Recompute();
   EventSetTimer(1); // 1-second refresh for live countdown/spread display
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   CleanupObjects();
   EventKillTimer();
   for(int k = 0; k < 5; k++)
     {
      if(g_ema_handles[k] != INVALID_HANDLE)
         IndicatorRelease(g_ema_handles[k]);
     }
  }

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double   &open[],
                const double   &high[],
                const double   &low[],
                const double   &close[],
                const long     &tick_volume[],
                const long     &volume[],
                const int      &spread[])
  {
   return rates_total;
  }

//+------------------------------------------------------------------+
//| Timer event handler                                              |
//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
  }
//+------------------------------------------------------------------+

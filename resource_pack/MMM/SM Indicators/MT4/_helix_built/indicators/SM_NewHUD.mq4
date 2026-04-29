//+------------------------------------------------------------------+
//|  SM_NewHUD.mq4                                                   |
//|  Phase 12 Plan 03 — SM Indicators Implementation                 |
//|                                                                  |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/          |
//|        SM_NewHUD.md                                               |
//|  D-17 Built ⚠ Low confidence; Verified Updates 2026-04-27.      |
//|  18-field HUD incl. HYADR + Av_N EMA row (1,4,13,26,52).        |
//|  Internals [INFER] — every guessed branch tagged.                |
//|  D-20: MQL4 idioms — iMA/iHigh/iLow return double directly       |
//|  Pitfall 9: Arial font (Wine font cache default)                 |
//+------------------------------------------------------------------+
#property copyright   "Bandd Analytics — Phase 12 SM Indicators reconstruction"
#property link        "https://github.com/banddanalytics/helix"
#property version     "1.00"
#property description "SM_NewHUD — 18-field corner HUD (D-17 Built ⚠; Verified Updates 2026-04-27)"

#property indicator_chart_window
#property indicator_buffers 0

//--- Inputs — Verified Updates 2026-04-27
extern double MaxSpread              = 1.75;          // Verified Updates: MaxSpread
extern int    FontSize               = 9;             // Verified Updates: FontSize
extern color  FontColor              = White;         // Verified Updates: FontColor
extern color  SymbolFontColor        = Black;         // Verified Updates: Symbol_FontColor
extern int    SymbolFontSize         = 14;            // Verified Updates: Symbol_Font_Size
extern double HiLoAlertDistance1     = 10;            // Verified Updates: HiLoAlert_Distance1
extern double HiLoAlertDistance2     = 20;            // Verified Updates: HiLoAlert_Distance2
extern color  HODLODAlertClr         = DarkGreen;     // Verified Updates: HODLODAlertClr
extern color  HODLODNearClr          = LawnGreen;     // Verified Updates: HODLODNearClr
extern double WeekHiLoAlertDistance3 = 25;            // Verified Updates: Week_HiLo_Alert_Distance3
extern double WeekHiLoAlertDistance4 = 50;            // Verified Updates: Week_HiLo_Alert_Distance4
extern double ADRAlertDistance       = 10;            // Verified Updates: adrAlert_Distance
extern color  FontColorADR3          = Yellow;        // [INFER]
extern int    YStart                 = 18;            // [INFER] Y position of HUD top
extern int    YDistance              = 0;             // [INFER] extra Y spacing
extern int    Av2                    = 1;             // Verified Updates: Av_N period 1
extern int    Av3                    = 4;             // Verified Updates: Av_N period 4
extern int    Av4                    = 13;            // Verified Updates: Av_N period 13
extern int    Av5                    = 26;            // Verified Updates: Av_N period 26
extern int    Av6                    = 52;            // Verified Updates: Av_N period 52
extern string LabelPrefix            = "smHUD_";

//+------------------------------------------------------------------+
//| Get pip size                                                     |
//+------------------------------------------------------------------+
double GetPip()
  {
   int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
   return (digits == 3 || digits == 5) ? _Point * 10.0 : _Point;
  }

//+------------------------------------------------------------------+
//| Create or update an OBJ_LABEL                                    |
//+------------------------------------------------------------------+
void SetLabel(string name, string text, int x, int y, color clr, int fsize)
  {
   if(ObjectFind(name) < 0)
     {
      ObjectCreate(name, OBJ_LABEL, 0, 0, 0);
      ObjectSet(name, OBJPROP_CORNER, 0); // CORNER_LEFT_UPPER
      ObjectSet(name, OBJPROP_XDISTANCE, x);
      ObjectSet(name, OBJPROP_YDISTANCE, y);
      ObjectSetString(0, name, OBJPROP_FONT, "Arial"); // Pitfall 9 — Wine font cache default
      ObjectSet(name, OBJPROP_SELECTABLE, false);
     }
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSet(name, OBJPROP_COLOR,    clr);
   ObjectSet(name, OBJPROP_FONTSIZE, fsize);
  }

//+------------------------------------------------------------------+
//| Recompute and refresh all HUD fields                             |
//+------------------------------------------------------------------+
void Recompute()
  {
   double pip = GetPip();

//--- Live state (MQL4 idiom: MarketInfo returns double directly)
   double bid    = MarketInfo(_Symbol, MODE_BID);
   double ask    = MarketInfo(_Symbol, MODE_ASK);
   double spread = (ask - bid) / pip;

   color spread_color = (spread <= MaxSpread) ? FontColor : Red;

//--- HOD / LOD
   double hod = iHigh(_Symbol, PERIOD_D1, 0);
   double lod  = iLow(_Symbol, PERIOD_D1, 0);
   double hod_dist = (hod - bid) / pip;
   double lod_dist = (bid - lod) / pip;

   color hod_color = (hod_dist < HiLoAlertDistance1) ? HODLODAlertClr
                   : (hod_dist < HiLoAlertDistance2) ? HODLODNearClr
                   : FontColor;
   color lod_color = (lod_dist < HiLoAlertDistance1) ? HODLODAlertClr
                   : (lod_dist < HiLoAlertDistance2) ? HODLODNearClr
                   : FontColor;

//--- TDR / YDR
   double tdr = iHigh(_Symbol, PERIOD_D1, 0) - iLow(_Symbol, PERIOD_D1, 0);
   double ydr = iHigh(_Symbol, PERIOD_D1, 1) - iLow(_Symbol, PERIOD_D1, 1);

//--- ADR variants [INFER]
   double wadr = 0.0, madr = 0.0, hyadr = 0.0;
   for(int i = 0; i < 5; i++)   wadr  += (iHigh(_Symbol, PERIOD_D1, i) - iLow(_Symbol, PERIOD_D1, i));
   wadr /= 5.0;
   for(int i = 0; i < 22; i++)  madr  += (iHigh(_Symbol, PERIOD_D1, i) - iLow(_Symbol, PERIOD_D1, i));
   madr /= 22.0;
   for(int i = 0; i < 132; i++) hyadr += (iHigh(_Symbol, PERIOD_D1, i) - iLow(_Symbol, PERIOD_D1, i));
   hyadr /= 132.0;  // [INFER] HYADR = half-yearly mean H-L (Verified Updates NEW)

   double x3_adr = wadr * 3.0;  // [INFER]

//--- Week H/L (MQL4: PERIOD_W1)
   double wh = iHigh(_Symbol, PERIOD_W1, 0);
   double wl  = iLow(_Symbol, PERIOD_W1, 0);
   double wr = wh - wl;

//--- PTO (Price-To-Open) [INFER]
   double day_open = iOpen(_Symbol, PERIOD_D1, 0);
   double pto = (bid - day_open) / pip;

//--- Candle countdown [INFER]
   int bar_sec = Period() * 60;
   int rem = bar_sec - (int)(TimeCurrent() % bar_sec);
   int mm = rem / 60, ss = rem % 60;
   string candle_time = StringFormat("%02d:%02d", mm, ss);

//--- Av_N EMA row — MQL4 idiom: iMA returns double directly
   int av_periods[] = {Av2, Av3, Av4, Av5, Av6};
   double ema_vals[5];
   for(int k = 0; k < 5; k++)
      ema_vals[k] = iMA(_Symbol, PERIOD_CURRENT, av_periods[k], 0, MODE_EMA, PRICE_CLOSE, 0);

//--- Layout HUD labels
   int x = 5, y = YStart, lh = 14 + YDistance;

   SetLabel(LabelPrefix+"sym",   _Symbol,                              x, y, SymbolFontColor, SymbolFontSize); y += SymbolFontSize + 4;
   SetLabel(LabelPrefix+"bid",   "BID: " + DoubleToStr(bid, _Digits),  x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"ask",   "ASK: " + DoubleToStr(ask, _Digits),  x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"spd",   "SPD: " + DoubleToStr(spread, 1),     x, y, spread_color, FontSize); y += lh;
   SetLabel(LabelPrefix+"hod",   "HOD: " + DoubleToStr(hod, _Digits) + " (" + DoubleToStr(hod_dist, 1) + "p)", x, y, hod_color, FontSize); y += lh;
   SetLabel(LabelPrefix+"lod",   "LOD: " + DoubleToStr(lod, _Digits)  + " (" + DoubleToStr(lod_dist, 1) + "p)", x, y, lod_color, FontSize); y += lh;
   SetLabel(LabelPrefix+"tdr",   "TDR: " + DoubleToStr(tdr / pip, 1) + "p", x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"ydr",   "YDR: " + DoubleToStr(ydr / pip, 1) + "p", x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"wadr",  "WADR: " + DoubleToStr(wadr / pip, 1) + "p", x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"madr",  "MADR: " + DoubleToStr(madr / pip, 1) + "p", x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"hyadr", "HYADR: " + DoubleToStr(hyadr / pip, 1) + "p", x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"pto",   "PTO: " + DoubleToStr(pto, 1) + "p",  x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"wh",    "WH: " + DoubleToStr(wh, _Digits),    x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"wl",    "WL: " + DoubleToStr(wl, _Digits),    x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"wr",    "WR: " + DoubleToStr(wr / pip, 1) + "p", x, y, FontColor, FontSize); y += lh;
   SetLabel(LabelPrefix+"3adr",  "3xADR: " + DoubleToStr(x3_adr / pip, 1) + "p", x, y, FontColorADR3, FontSize); y += lh;
   SetLabel(LabelPrefix+"time",  "Candle: " + candle_time,             x, y, FontColor, FontSize); y += lh;

//--- Av_N EMA row
   for(int k = 0; k < 5; k++)
     {
      string lbl = LabelPrefix + "ema" + IntegerToString(av_periods[k]);
      string txt = "Av" + IntegerToString(av_periods[k]) + ": " + DoubleToStr(ema_vals[k], _Digits);
      SetLabel(lbl, txt, x, y, FontColor, FontSize);
      y += lh;
     }

   WindowRedraw();
  }

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int init()
  {
   IndicatorShortName("SM_NewHUD");
   Recompute();
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
int deinit()
  {
   // Clean up all HUD label objects
   int total = ObjectsTotal();
   for(int i = total - 1; i >= 0; i--)
     {
      string name = ObjectName(i);
      if(StringFind(name, LabelPrefix) == 0)
         ObjectDelete(name);
     }
   return 0;
  }

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int start()
  {
   Recompute();
   return 0;
  }
//+------------------------------------------------------------------+

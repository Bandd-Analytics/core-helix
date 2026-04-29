//+------------------------------------------------------------------+
//|  SM_ADR_Marker.mq4                                                |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (MQ4 idiomatic / D-20)|
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_ADR_Marker.md                                            |
//|  Verified Updates 2026-04-27: ATRPeriod=14 (was claimed 20)       |
//|                                                                   |
//|  MQL4 idiom: iATR returns double directly (no handle); ObjectCreate|
//|  uses MQL4 5-arg signature (no chart_id).                          |
//|                                                                   |
//|  v2.00 (operator-tuned 2026-04-28):                                |
//|    - Fixed disappear/reappear bug on TF/symbol switch:            |
//|      MQ4: no CHART_CHANGE — redraw on every 5-second timer tick.  |
//|    - Adds OBJ_TEXT price labels ABOVE each line ("ADR Hi 1.2540") |
//|    - Confirmed daily-anchored: ADR re-anchors to today_open every |
//|      D1 bar; the lines do NOT change between intra-day TF switches.|
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_ADR_Marker.ex4"
#property version   "2.00"
#property indicator_chart_window
#property strict

//--- Spec Section 3 inputs (Verified Updates 2026-04-27)
extern int    InpTimeZoneOfData     = 0;
extern int    InpTimeZoneOfSession  = 0;
extern int    InpATRPeriod          = 14;     // VERIFIED 2026-04-27 (was 20)
extern bool   InpUseManualADR       = false;
extern int    InpManualADRValuePips = 0;
extern int    InpLineStyle          = 2;      // STYLE_DOT (VERIFIED)
extern int    InpLineThickness1     = 1;
extern color  InpLineColor1         = clrOrange;
extern int    InpLineThickness2     = 2;
extern color  InpLineColor2         = clrRed;
extern int    InpBarForLabels       = -10;
extern bool   InpDebugLogger        = false;
extern bool   InpShowtext           = true;   // v2.00: price labels above lines (was false)
extern int    InpLabelFontSize      = 9;
extern color  InpLabelColor         = clrWhite;

string ObjectPrefix = "smADR_";
datetime g_last_d1_bar = 0;
bool g_needs_redraw = false;  // MQ4: no CHART_CHANGE — redraw on every timer tick

//+------------------------------------------------------------------+
int init()
  {
   IndicatorShortName("SM_ADR_Marker(" + IntegerToString(InpATRPeriod) + ")");
   Recompute();
   EventSetTimer(5);  // 5-second cycle; handles disappear/reappear on TF/symbol switch
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
   datetime cur_d1 = iTime(_Symbol, PERIOD_D1, 0);
   // v2.00: also recompute when our objects are missing (recovery
   // path for ATR-not-ready-on-load and TF-switch cases).
   bool need_redraw = (cur_d1 != g_last_d1_bar) ||
                      (ObjectFind(ObjectPrefix + "high") < 0);
   if(need_redraw)
     {
      Recompute();
      g_last_d1_bar = cur_d1;
     }
   return(0);
  }

//+------------------------------------------------------------------+
//  MQ4: no CHART_CHANGE — redraw on every timer tick.
//  Functionally equivalent to MQ5 OnChartEvent(CHART_CHANGE) on a
//  5-second cycle.
//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();  // MQ4: no CHART_CHANGE — redraw on every timer tick
  }

//+------------------------------------------------------------------+
void Recompute()
  {
   double adr = 0.0;
   int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
   double pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;

   if(InpUseManualADR)
     {
      adr = InpManualADRValuePips * pip;
     }
   else
     {
      // MQL4 iATR returns double directly (Pitfall 1 / D-20).
      // shift=1 → last completed D1 bar.
      adr = iATR(_Symbol, PERIOD_D1, InpATRPeriod, 1);
     }

   double today_open = iOpen(_Symbol, PERIOD_D1, 0);
   if(today_open <= 0.0)
      return;

   double adr_high = today_open + adr / 2.0;
   double adr_low  = today_open - adr / 2.0;
   double adr_mid  = today_open;

   // Per Verified Updates: LineColor1=Orange (Thickness1=1) — primary marker.
   //                       LineColor2=Red   (Thickness2=2) — secondary marker.
   // Convention: Color1/Thickness1 → high+low boundaries; Color2/Thickness2 → mid.
   DrawHLine(ObjectPrefix + "high", adr_high,
             InpLineColor1, InpLineThickness1);
   DrawHLine(ObjectPrefix + "low",  adr_low,
             InpLineColor1, InpLineThickness1);
   DrawHLine(ObjectPrefix + "mid",  adr_mid,
             InpLineColor2, InpLineThickness2);

   if(InpShowtext)
     {
      // v2.00: per-line price labels above each line + corner pip total.
      double label_offset = adr * 0.05;  // [INFER] 5% of ADR as vertical padding
      DrawPriceLabel("smADR_Hi_lbl",
                     adr_high + label_offset,
                     "ADR Hi " + DoubleToString(adr_high, _Digits));
      DrawPriceLabel("smADR_Mid_lbl",
                     adr_mid + label_offset,
                     "ADR Mid " + DoubleToString(today_open, _Digits));
      DrawPriceLabel("smADR_Lo_lbl",
                     adr_low + label_offset,
                     "ADR Lo " + DoubleToString(adr_low, _Digits));
      DrawCornerLabel(adr, pip);
     }

   if(InpDebugLogger)
      Print("SM_ADR_Marker: today_open=", DoubleToStr(today_open, digits),
            " adr=", DoubleToStr(adr, digits),
            " high=", DoubleToStr(adr_high, digits),
            " low=", DoubleToStr(adr_low, digits));
  }

//+------------------------------------------------------------------+
void DrawHLine(string name, double price, color c, int thickness)
  {
   // MQL4 ObjectCreate signature: name, type, sub_window, time, price (D-20).
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_HLINE, 0, 0, price);

   ObjectSet(name, OBJPROP_PRICE1, price);
   ObjectSet(name, OBJPROP_COLOR,  c);
   ObjectSet(name, OBJPROP_STYLE,  InpLineStyle);
   ObjectSet(name, OBJPROP_WIDTH,  thickness);
   ObjectSet(name, OBJPROP_BACK,   true);
  }

//+------------------------------------------------------------------+
//  v2.00 — chart-anchored price label sitting ABOVE the line.
//  price argument already includes the label_offset computed in Recompute().
//+------------------------------------------------------------------+
void DrawPriceLabel(string name, double price, string text)
  {
   // MQL4 ObjectCreate: name, type, sub_window, time, price (no chart_id).
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_TEXT, 0, TimeCurrent(), price);

   ObjectSetString (0, name, OBJPROP_TEXT,     text);
   ObjectSetInteger(0, name, OBJPROP_COLOR,    InpLabelColor);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpLabelFontSize);
  }

//+------------------------------------------------------------------+
//  Corner pip-total summary label (e.g. "ADR(14): 92.3 pips").
//+------------------------------------------------------------------+
void DrawCornerLabel(double adr, double pip)
  {
   string name = ObjectPrefix + "lbl";
   double pips = (pip > 0.0) ? adr / pip : 0.0;
   string text = "ADR(" + IntegerToString(InpATRPeriod) + "): "
                 + DoubleToStr(pips, 1) + " pips";

   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_LABEL, 0, 0, 0);

   ObjectSetText(name, text, 10, "Arial", InpLineColor1);
   ObjectSet(name, OBJPROP_CORNER,    1);   // RIGHT_UPPER
   ObjectSet(name, OBJPROP_XDISTANCE, 8);
   ObjectSet(name, OBJPROP_YDISTANCE, 40);
  }

//+------------------------------------------------------------------+
void CleanupObjects()
  {
   // Delete named label objects explicitly before prefix-sweep.
   ObjectDelete("smADR_Hi_lbl");
   ObjectDelete("smADR_Mid_lbl");
   ObjectDelete("smADR_Lo_lbl");

   for(int i = ObjectsTotal() - 1; i >= 0; i--)
     {
      string n = ObjectName(i);
      if(StringFind(n, ObjectPrefix) == 0)
         ObjectDelete(n);
     }
  }

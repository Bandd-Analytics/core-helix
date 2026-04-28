//+------------------------------------------------------------------+
//|  SM_ADR_Marker.mq4                                                |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (MQ4 idiomatic / D-20)|
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_ADR_Marker.md                                            |
//|  Verified Updates 2026-04-27: ATRPeriod=14 (was claimed 20)       |
//|                                                                   |
//|  MQL4 idiom: iATR returns double directly (no handle); ObjectCreate|
//|  uses MQL4 5-arg signature (no chart_id).                          |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_ADR_Marker.ex4"
#property version   "1.00"
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
extern bool   InpShowtext           = false;

string ObjectPrefix = "smADR_";
datetime g_last_d1_bar = 0;

//+------------------------------------------------------------------+
int init()
  {
   IndicatorShortName("SM_ADR_Marker(" + IntegerToString(InpATRPeriod) + ")");
   Recompute();
   EventSetTimer(60);
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
   if(cur_d1 != g_last_d1_bar)
     {
      Recompute();
      g_last_d1_bar = cur_d1;
     }
   return(0);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
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

   DrawHLine(ObjectPrefix + "high", adr_high,
             InpLineColor1, InpLineThickness1);
   DrawHLine(ObjectPrefix + "low",  adr_low,
             InpLineColor1, InpLineThickness1);
   DrawHLine(ObjectPrefix + "mid",  adr_mid,
             InpLineColor2, InpLineThickness2);

   if(InpShowtext)
      DrawLabel(adr, pip);

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
void DrawLabel(double adr, double pip)
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
   for(int i = ObjectsTotal() - 1; i >= 0; i--)
     {
      string n = ObjectName(i);
      if(StringFind(n, ObjectPrefix) == 0)
         ObjectDelete(n);
     }
  }

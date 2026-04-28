//+------------------------------------------------------------------+
//|  SM_Daily_HiLo.mq4                                                |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (MQ4 idiomatic / D-20)|
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_Daily_HiLo.md                                            |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_Daily_HiLo.ex4"
#property version   "1.00"
#property indicator_chart_window
#property strict

extern int    InpDaysBack    = 1;
extern color  InpHighColor   = clrRed;
extern color  InpLowColor    = clrLimeGreen;
extern int    InpLineStyle   = STYLE_DASH;
extern int    InpLineWidth   = 1;
extern bool   InpShowLabel   = true;

string ObjectPrefix = "smHL_";
datetime g_last_d1_bar = 0;

//+------------------------------------------------------------------+
int init()
  {
   IndicatorShortName("SM_Daily_HiLo(D-" + IntegerToString(InpDaysBack) + ")");
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
   double phod = iHigh(_Symbol, PERIOD_D1, InpDaysBack);
   double plod = iLow (_Symbol, PERIOD_D1, InpDaysBack);
   if(phod <= 0.0 || plod <= 0.0)
      return;

   DrawHLine(ObjectPrefix + "phod", phod, InpHighColor);
   DrawHLine(ObjectPrefix + "plod", plod, InpLowColor);

   if(InpShowLabel)
     {
      DrawLabel(ObjectPrefix + "phod_lbl", "PHOD", phod, InpHighColor);
      DrawLabel(ObjectPrefix + "plod_lbl", "PLOD", plod, InpLowColor);
     }
  }

//+------------------------------------------------------------------+
void DrawHLine(string name, double price, color c)
  {
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_HLINE, 0, 0, price);
   ObjectSet(name, OBJPROP_PRICE1, price);
   ObjectSet(name, OBJPROP_COLOR,  c);
   ObjectSet(name, OBJPROP_STYLE,  InpLineStyle);
   ObjectSet(name, OBJPROP_WIDTH,  InpLineWidth);
   ObjectSet(name, OBJPROP_BACK,   true);
  }

//+------------------------------------------------------------------+
void DrawLabel(string name, string text, double price, color c)
  {
   datetime label_time = iTime(_Symbol, _Period, 0);
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_TEXT, 0, label_time, price);
   ObjectSetText(name, text, 9, "Arial", c);
   ObjectSet(name, OBJPROP_TIME1,  label_time);
   ObjectSet(name, OBJPROP_PRICE1, price);
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

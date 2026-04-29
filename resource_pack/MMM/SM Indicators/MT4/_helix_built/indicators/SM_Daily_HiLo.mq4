//+------------------------------------------------------------------+
//|  SM_Daily_HiLo.mq4                                                |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (MQ4 idiomatic / D-20)|
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_Daily_HiLo.md                                            |
//|                                                                   |
//|  v2.01 — trailing N-day snake pattern (operator-tuned 2026-04-29).|
//|  For each completed D1 bar i (i=1..InpDaysBack) the H/L is        |
//|  PROJECTED INTO THE FOLLOWING DAY'S bar — yesterday's H/L         |
//|  becomes a reference line drawn through today's price action,    |
//|  the day-before-yesterday's H/L overlays yesterday's bar, etc.   |
//|  This is the classic SM "previous-day pivot" pattern: the most   |
//|  recent completed bar provides today's psychological S/R.        |
//|                                                                   |
//|  Both high and low lines: dotted Aqua (operator-tuned).           |
//|                                                                   |
//|  Most recent (i=1, yesterday's H/L projected into today) gets    |
//|  "PHOD <price>" / "PLOD <price>" labels above each line.          |
//|                                                                   |
//|  Pitfall 5 guard: i=0 is the still-forming D1 bar — start at i=1.|
//|                                                                   |
//|  MQ4 notes: no ChartTimePriceToXY / CHARTEVENT_CHART_CHANGE.      |
//|  OBJ_TREND with OBJPROP_RAY=false used for bounded segments.      |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_Daily_HiLo.ex4"
#property version   "2.01"
#property indicator_chart_window
#property strict

//--- v2.01 inputs
extern int    InpDaysBack      = 14;          // Number of trailing D1 bars
extern color  InpHighColor     = clrAqua;     // v2.01 daily high segment color
extern color  InpLowColor      = clrAqua;     // v2.01 daily low segment color
extern int    InpLineStyle     = STYLE_DOT;   // Dotted lines per operator request
extern int    InpLineWidth     = 1;
extern bool   InpShowLabel     = true;        // PHOD/PLOD label on most recent day
extern int    InpLabelFontSize = 9;

const string ObjectPrefix = "smHL_";
datetime g_last_d1_bar = 0;

//+------------------------------------------------------------------+
int init()
  {
   IndicatorShortName("SM_Daily_HiLo(" + IntegerToString(InpDaysBack) + "d trail)");
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
//  v2.01: project each completed bar i's H/L into bar (i-1)'s time
//  range. For i=1 this means yesterday's H/L appears as a line
//  through today's bar. For i=N this means N-days-ago's H/L appears
//  as a line through (N-1)-days-ago's bar.
//+------------------------------------------------------------------+
void Recompute()
  {
   CleanupObjects();   // wipe previous frame — simplest correct approach
                       // for variable-day trail since bars age out

   for(int i = 1; i <= InpDaysBack; i++)
     {
      double hi = iHigh(_Symbol, PERIOD_D1, i);
      double lo = iLow (_Symbol, PERIOD_D1, i);
      if(hi <= 0.0 || lo <= 0.0) continue;

      //--- t_open = open of following day (bar i-1); t_end = its close
      datetime t_open = iTime(_Symbol, PERIOD_D1, i - 1);
      datetime t_end;
      if(i >= 2)
         t_end = iTime(_Symbol, PERIOD_D1, i - 2);   // close of following day
      else
         t_end = t_open + 86400;                     // i=1 → today still in progress
      if(t_open <= 0 || t_end <= t_open) continue;

      string n_hi = StringFormat("%shi_%d", ObjectPrefix, (int)t_open);
      string n_lo = StringFormat("%slo_%d", ObjectPrefix, (int)t_open);

      DrawSegment(n_hi, t_open, t_end, hi, InpHighColor);
      DrawSegment(n_lo, t_open, t_end, lo, InpLowColor);

      if(InpShowLabel && i == 1)
        {
         string l_hi = ObjectPrefix + "phod_lbl";
         string l_lo = ObjectPrefix + "plod_lbl";
         DrawLabel(l_hi, t_open, hi,
                   "PHOD " + DoubleToString(hi, _Digits), InpHighColor);
         DrawLabel(l_lo, t_open, lo,
                   "PLOD " + DoubleToString(lo, _Digits), InpLowColor);
        }
     }
  }

//+------------------------------------------------------------------+
//  Draw a bounded horizontal segment using OBJ_TREND with RAY=false.
//  MQ4 ObjectCreate: no chart_id prefix.
//+------------------------------------------------------------------+
void DrawSegment(string name, datetime t1, datetime t2, double price, color c)
  {
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_TREND, 0, t1, price, t2, price);
   ObjectSet(name, OBJPROP_TIME1,  t1);
   ObjectSet(name, OBJPROP_TIME2,  t2);
   ObjectSet(name, OBJPROP_PRICE1, price);
   ObjectSet(name, OBJPROP_PRICE2, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_STYLE, InpLineStyle);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, InpLineWidth);
   ObjectSetInteger(0, name, OBJPROP_RAY,   false);
   ObjectSetInteger(0, name, OBJPROP_BACK,  true);
  }

//+------------------------------------------------------------------+
//  Label sits above the line; ANCHOR_LEFT_LOWER aligns text bottom-
//  left to the anchor point so text rises above the price.
//+------------------------------------------------------------------+
void DrawLabel(string name, datetime t, double price, string text, color c)
  {
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_TEXT, 0, t, price);
   ObjectSetText(name, text, InpLabelFontSize, "Arial", c);
   ObjectSet(name, OBJPROP_TIME1,  t);
   ObjectSet(name, OBJPROP_PRICE1, price);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
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
//+------------------------------------------------------------------+

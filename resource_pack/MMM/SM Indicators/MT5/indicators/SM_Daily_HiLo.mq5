//+------------------------------------------------------------------+
//|  SM_Daily_HiLo.mq5                                                |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (v2.00)               |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_Daily_HiLo.md                                            |
//|                                                                   |
//|  v2.00 — trailing N-day snake pattern (operator-tuned 2026-04-28).|
//|  For each of the last InpDaysBack D1 bars, draws two short        |
//|  dotted OBJ_TREND segments spanning that day's bar width:         |
//|    HIGH segment at iHigh(D1, i) — red                             |
//|    LOW  segment at iLow (D1, i) — lime green                      |
//|  Together they form a stair-step / zigzag visualization tracking  |
//|  the recent daily H/L topology like a snake.                      |
//|                                                                   |
//|  Most recent day (i=1) gets text labels above each line showing   |
//|  "PHOD <price>" / "PLOD <price>".                                 |
//|                                                                   |
//|  Pitfall 5 guard: i=0 is the still-forming D1 bar — start at i=1. |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_Daily_HiLo.ex4"
#property version   "2.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- v2.00 inputs
input int             InpDaysBack    = 14;             // Number of trailing D1 bars
input color           InpHighColor   = clrRed;         // Daily high segment color
input color           InpLowColor    = clrLimeGreen;   // Daily low segment color
input ENUM_LINE_STYLE InpLineStyle   = STYLE_DOT;      // Dotted lines per operator request
input int             InpLineWidth   = 2;
input bool            InpShowLabel   = true;           // PHOD/PLOD label on most recent day
input int             InpLabelFontSize = 9;

const string InpObjectPrefix = "smHL_";

datetime g_last_d1_bar = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("SM_Daily_HiLo(%dd trail)", InpDaysBack));
   Recompute();
   EventSetTimer(60);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   CleanupObjects();
   EventKillTimer();
  }

//+------------------------------------------------------------------+
void OnTimer()                         { Recompute(); ChartRedraw(0); }
void OnChartEvent(const int id, const long &lp, const double &dp, const string &sp)
  {
   if(id == CHARTEVENT_CHART_CHANGE) { Recompute(); ChartRedraw(0); }
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tv[],
                const long &v[], const int &sp[])
  {
   datetime cur_d1 = iTime(_Symbol, PERIOD_D1, 0);
   if(cur_d1 != g_last_d1_bar)
     {
      Recompute();
      g_last_d1_bar = cur_d1;
     }
   return(rates_total);
  }

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

      datetime t_open = iTime(_Symbol, PERIOD_D1, i);
      datetime t_end  = (i > 0) ? iTime(_Symbol, PERIOD_D1, i - 1) : (t_open + 86400);
      if(t_end <= t_open) t_end = t_open + 86400;

      string n_hi = StringFormat("%shi_%d", InpObjectPrefix, (int)t_open);
      string n_lo = StringFormat("%slo_%d", InpObjectPrefix, (int)t_open);

      DrawSegment(n_hi, t_open, t_end, hi, InpHighColor);
      DrawSegment(n_lo, t_open, t_end, lo, InpLowColor);

      if(InpShowLabel && i == 1)
        {
         string l_hi = InpObjectPrefix + "phod_lbl";
         string l_lo = InpObjectPrefix + "plod_lbl";
         DrawLabelAbove(l_hi, t_end, hi,
                        "PHOD " + DoubleToString(hi, _Digits), InpHighColor);
         DrawLabelAbove(l_lo, t_end, lo,
                        "PLOD " + DoubleToString(lo, _Digits), InpLowColor);
        }
     }
  }

//+------------------------------------------------------------------+
void DrawSegment(string name, datetime t1, datetime t2, double price, color c)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TREND, 0, t1, price, t2, price);
   ObjectSetInteger(0, name, OBJPROP_TIME,  0, t1);
   ObjectSetInteger(0, name, OBJPROP_TIME,  1, t2);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 0, price);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 1, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,      c);
   ObjectSetInteger(0, name, OBJPROP_STYLE,      InpLineStyle);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,      InpLineWidth);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT,  false);
   ObjectSetInteger(0, name, OBJPROP_BACK,       true);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN,     true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
  }

//+------------------------------------------------------------------+
//  Label sits ABOVE the line (ANCHOR_LEFT_LOWER -> bottom-left of
//  text aligns to the anchor point, so text rises above the price).
//+------------------------------------------------------------------+
void DrawLabelAbove(string name, datetime t, double price, string text, color c)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, t, price);
   ObjectSetString (0, name, OBJPROP_TEXT,     text);
   ObjectSetInteger(0, name, OBJPROP_TIME,     t);
   ObjectSetDouble (0, name, OBJPROP_PRICE,    price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,    c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, InpLabelFontSize);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR,   ANCHOR_LEFT_LOWER);
   ObjectSetString (0, name, OBJPROP_FONT,     "Arial");
   ObjectSetInteger(0, name, OBJPROP_BACK,     false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN,   true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
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

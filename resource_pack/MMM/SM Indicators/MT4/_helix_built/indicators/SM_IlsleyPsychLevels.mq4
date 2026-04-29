//+------------------------------------------------------------------+
//|  SM_IlsleyPsychLevels.mq4                                         |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (MQ4 idiomatic v2.00) |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_IlsleyPsychLevels.md                                     |
//|                                                                   |
//|  Two independent psychological-level systems that can be toggled  |
//|  separately:                                                       |
//|                                                                   |
//|  1. ROUND-NUMBER LEVELS (classic SM convention).                   |
//|     50-pip / 100-pip increments anchored to the nearest round     |
//|     level below current price. Major lines at every InpMajorPips. |
//|     JPY/3-digit pip detection via MarketInfo MODE_DIGITS.         |
//|                                                                   |
//|  2. WEEKLY FIRST-4HR H/L LEVELS  (v2.00 new feature).             |
//|     For each of the last InpWeeksBack weeks, computes the H/L of  |
//|     the first InpWeekFirstHours hours of trading after the week's  |
//|     open (Monday 00:00 broker server time) and draws two dotted   |
//|     segments running from week-open through week-end.             |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_IlsleyPsychLevels.ex4"
#property version   "2.00"
#property indicator_chart_window
#property strict

//--- Round-number levels (existing v1 behavior)
extern bool   InpShowRound       = true;
extern int    InpStepPips        = 50;
extern int    InpMajorPips       = 100;
extern int    InpLevelsAbove     = 5;
extern int    InpLevelsBelow     = 5;
extern color  InpMinorColor      = clrDimGray;
extern color  InpMajorColor      = clrDarkGray;
extern int    InpRoundLineStyle  = STYLE_DOT;
extern int    InpRoundLineWidth  = 1;

//--- Weekly first-4hr H/L levels (v2.00 new feature)
extern bool   InpShowWeeklyLevels  = true;      // Master toggle for weekly system
extern int    InpWeeksBack         = 4;          // Lookback weeks
extern int    InpWeekFirstHours    = 4;          // First N hours of each week
extern color  InpWeeklyHighColor   = clrMagenta; // Weekly H line colour
extern color  InpWeeklyLowColor    = clrYellow;  // Weekly L line colour
extern int    InpWeeklyLineStyle   = STYLE_DOT;

//--- Labels (apply to both systems)
extern bool   InpShowLabel       = true;
extern int    InpLabelFontSize   = 9;

string ObjectPrefix  = "smPsych_";
string WeeklyPrefix  = "smIPW_";
double g_pip         = 0.0;
datetime g_last_d1_bar = 0;

//+------------------------------------------------------------------+
int init()
  {
   int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
   g_pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;
   IndicatorShortName("SM_IlsleyPsychLevels(R" + IntegerToString(InpStepPips)
                      + "/W" + IntegerToString(InpWeekFirstHours)
                      + "h-" + IntegerToString(InpWeeksBack) + "wk)");
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
   CleanupObjects();
   if(InpShowRound)        DrawRoundNumberLevels();
   if(InpShowWeeklyLevels) DrawWeeklyLevels();
  }

//+------------------------------------------------------------------+
void DrawRoundNumberLevels()
  {
   if(g_pip <= 0.0) return;
   double bid = MarketInfo(_Symbol, MODE_BID);
   if(bid <= 0.0) return;

   double step  = InpStepPips  * g_pip;
   double major = InpMajorPips * g_pip;
   double base  = MathFloor(bid / step) * step;

   for(int i = -InpLevelsBelow; i <= InpLevelsAbove; i++)
     {
      double level = base + i * step;
      bool is_major = (MathAbs(level - MathRound(level / major) * major) < step * 0.01);

      string suffix = "L_" + IntegerToString(i + InpLevelsBelow);
      string name   = ObjectPrefix + suffix;
      color  c      = is_major ? InpMajorColor : InpMinorColor;
      int    w      = is_major ? (InpRoundLineWidth + 1) : InpRoundLineWidth;

      DrawHLine(name, level, c, w);

      if(InpShowLabel)
        {
         int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
         string lbl_name = ObjectPrefix + "lbl_" + suffix;
         DrawLabel(lbl_name, iTime(_Symbol, _Period, 0), level,
                   DoubleToStr(level, digits), c);
        }
     }
  }

//+------------------------------------------------------------------+
//  v2.00 — weekly first-4hr H/L levels.
//
//  Algorithm:
//  - Walk backward through D1 bars to find Monday (TimeDayOfWeek == 1).
//  - For each of InpWeeksBack Mondays:
//      week_start = iTime of that Monday (00:00 broker time)
//      first4_end = week_start + InpWeekFirstHours * 3600
//      week_end   = week_start + 7 * 86400  (or TimeCurrent for current week)
//    Scan H1 bars in [week_start, first4_end) for H/L.
//    Draw two OBJ_TREND segments spanning [week_start, week_end].
//+------------------------------------------------------------------+
void DrawWeeklyLevels()
  {
   datetime now = TimeCurrent();
   int weeks_found = 0;

   // Walk D1 bars backward to collect InpWeeksBack Monday opens
   int total_d1 = iBars(_Symbol, PERIOD_D1);
   datetime week_starts[];
   ArrayResize(week_starts, InpWeeksBack);

   for(int d = 0; d < total_d1 && weeks_found < InpWeeksBack; d++)
     {
      datetime day_time = iTime(_Symbol, PERIOD_D1, d);
      if(day_time <= 0) break;
      if(TimeDayOfWeek(day_time) == 1)  // Monday
        {
         week_starts[weeks_found] = day_time;
         weeks_found++;
        }
     }

   for(int wk = 0; wk < weeks_found; wk++)
     {
      datetime week_start = week_starts[wk];
      datetime first4_end = week_start + InpWeekFirstHours * 3600;
      datetime week_end   = (wk == 0) ? now : (week_start + 7 * 86400);
      if(week_end <= week_start) continue;

      double hi = -DBL_MAX, lo = DBL_MAX;
      bool found = false;

      // Scan H1 bars in [week_start, first4_end)
      int total_h1 = iBars(_Symbol, PERIOD_H1);
      for(int h = total_h1 - 1; h >= 0; h--)
        {
         datetime bar_time = iTime(_Symbol, PERIOD_H1, h);
         if(bar_time < week_start) continue;
         if(bar_time >= first4_end) continue;
         double bhi = iHigh(_Symbol, PERIOD_H1, h);
         double blo = iLow (_Symbol, PERIOD_H1, h);
         if(bhi > hi) hi = bhi;
         if(blo < lo) lo = blo;
         found = true;
        }

      if(!found || hi <= -DBL_MAX || lo >= DBL_MAX) continue;

      string suffix = "W" + IntegerToString(wk);
      string n_hi   = WeeklyPrefix + suffix + "_hi";
      string n_lo   = WeeklyPrefix + suffix + "_lo";

      DrawSegment(n_hi, week_start, week_end, hi, InpWeeklyHighColor);
      DrawSegment(n_lo, week_start, week_end, lo, InpWeeklyLowColor);

      if(InpShowLabel)
        {
         int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
         string txt_hi = "Wk" + (wk == 0 ? "0" : "-" + IntegerToString(wk))
                         + " Hi " + DoubleToStr(hi, digits);
         string txt_lo = "Wk" + (wk == 0 ? "0" : "-" + IntegerToString(wk))
                         + " Lo " + DoubleToStr(lo, digits);
         DrawLabel(n_hi + "_lbl", week_start, hi, txt_hi, InpWeeklyHighColor);
         DrawLabel(n_lo + "_lbl", week_start, lo, txt_lo, InpWeeklyLowColor);
        }
     }
  }

//+------------------------------------------------------------------+
void DrawHLine(string name, double price, color c, int width)
  {
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_HLINE, 0, 0, price);
   ObjectSet(name, OBJPROP_PRICE1, price);
   ObjectSet(name, OBJPROP_COLOR,  c);
   ObjectSet(name, OBJPROP_STYLE,  InpRoundLineStyle);
   ObjectSet(name, OBJPROP_WIDTH,  width);
   ObjectSet(name, OBJPROP_BACK,   true);
  }

//+------------------------------------------------------------------+
void DrawSegment(string name, datetime t1, datetime t2, double price, color c)
  {
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_TREND, 0, t1, price, t2, price);
   ObjectSet(name, OBJPROP_TIME1,  t1);
   ObjectSet(name, OBJPROP_TIME2,  t2);
   ObjectSet(name, OBJPROP_PRICE1, price);
   ObjectSet(name, OBJPROP_PRICE2, price);
   ObjectSet(name, OBJPROP_COLOR,  c);
   ObjectSet(name, OBJPROP_STYLE,  InpWeeklyLineStyle);
   ObjectSet(name, OBJPROP_WIDTH,  1);
   ObjectSet(name, OBJPROP_RAY,    false);
   ObjectSet(name, OBJPROP_BACK,   true);
  }

//+------------------------------------------------------------------+
void DrawLabel(string name, datetime t, double price, string text, color c)
  {
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_TEXT, 0, t, price);
   ObjectSetText(name, text, InpLabelFontSize, "Arial", c);
   ObjectSet(name, OBJPROP_TIME1,  t);
   ObjectSet(name, OBJPROP_PRICE1, price);
  }

//+------------------------------------------------------------------+
void CleanupObjects()
  {
   // Remove round-level objects
   for(int i = ObjectsTotal() - 1; i >= 0; i--)
     {
      string n = ObjectName(i);
      if(StringFind(n, ObjectPrefix) == 0)
         ObjectDelete(n);
     }
   // Remove weekly-level objects
   for(int i = ObjectsTotal() - 1; i >= 0; i--)
     {
      string n = ObjectName(i);
      if(StringFind(n, WeeklyPrefix) == 0)
         ObjectDelete(n);
     }
  }

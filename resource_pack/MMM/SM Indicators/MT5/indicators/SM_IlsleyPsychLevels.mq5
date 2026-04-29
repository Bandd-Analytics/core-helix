//+------------------------------------------------------------------+
//|  SM_IlsleyPsychLevels.mq5                                         |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (v2.00)               |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_IlsleyPsychLevels.md                                     |
//|                                                                   |
//|  Two independent psychological-level systems that can be toggled  |
//|  separately:                                                       |
//|                                                                   |
//|  1. ROUND-NUMBER LEVELS (classic SM convention).                   |
//|     50-pip / 100-pip increments anchored to the nearest round     |
//|     level below current price. Major lines at every InpMajorPips. |
//|     JPY/3-digit pip detection via SYMBOL_DIGITS.                  |
//|                                                                   |
//|  2. WEEKLY FIRST-4HR H/L LEVELS  (operator-tuned 2026-04-28).      |
//|     For each of the last InpWeeksBack weeks, computes the H/L of  |
//|     the first 4 hours of trading after the week's open (Monday    |
//|     00:00 broker server time + InpWeekFirstHours) and draws two   |
//|     dotted segments running from week-open through week-end. The  |
//|     hypothesis: those 4 hours establish weekly psychological S/R  |
//|     that price respects across the rest of the week.              |
//|                                                                   |
//|  All labels positioned ABOVE each line (ANCHOR_LEFT_LOWER).       |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_IlsleyPsychLevels.ex4"
#property version   "2.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Round-number levels (existing v1 behavior, optional)
input bool            InpShowRound       = true;
input int             InpStepPips        = 50;
input int             InpMajorPips       = 100;
input int             InpLevelsAbove     = 5;
input int             InpLevelsBelow     = 5;
input color           InpMinorColor      = clrDimGray;
input color           InpMajorColor      = clrDarkGray;
input ENUM_LINE_STYLE InpRoundLineStyle  = STYLE_DOT;
input int             InpRoundLineWidth  = 1;

//--- Weekly first-4hr H/L levels (v2.00 new feature)
input bool            InpShowWeekly      = true;        // Master toggle for weekly system
input int             InpWeeksBack       = 12;          // Lookback weeks
input int             InpWeekFirstHours  = 4;           // First N hours of week
input int             InpWeekStartDOW    = 1;           // 0=Sun 1=Mon ... 6=Sat
input color           InpWeekHighColor   = clrDeepSkyBlue;
input color           InpWeekLowColor    = clrOrange;
input ENUM_LINE_STYLE InpWeekLineStyle   = STYLE_DOT;
input int             InpWeekLineWidth   = 2;

//--- Labels (apply to both systems)
input bool            InpShowLabel       = true;
input int             InpLabelFontSize   = 9;

const string InpObjectPrefix = "smPsych_";

double   g_pip          = 0.0;
datetime g_last_d1_bar  = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   g_pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;

   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("SM_IlsleyPsychLevels(R%d/W%dh-%dwk)",
                                   InpStepPips, InpWeekFirstHours, InpWeeksBack));
   Recompute();
   EventSetTimer(60);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)        { CleanupObjects(); EventKillTimer(); }
void OnTimer()                          { Recompute(); ChartRedraw(0); }
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
   CleanupObjects();
   if(InpShowRound)  DrawRoundNumberLevels();
   if(InpShowWeekly) DrawWeeklyLevels();
  }

//+------------------------------------------------------------------+
void DrawRoundNumberLevels()
  {
   if(g_pip <= 0.0) return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0.0) return;

   double step  = InpStepPips  * g_pip;
   double major = InpMajorPips * g_pip;

   double base = MathFloor(bid / step) * step;
   datetime t_label = iTime(_Symbol, _Period, 0);

   for(int i = -InpLevelsBelow; i <= InpLevelsAbove; i++)
     {
      double level = base + i * step;
      bool is_major = (MathAbs(level - MathRound(level / major) * major) < step * 0.01);

      string suffix = StringFormat("R_%d", i + InpLevelsBelow);
      string name   = InpObjectPrefix + suffix;
      color  c      = is_major ? InpMajorColor : InpMinorColor;
      int    w      = is_major ? (InpRoundLineWidth + 1) : InpRoundLineWidth;

      DrawHLine(name, level, c, w, InpRoundLineStyle);
      if(InpShowLabel)
         DrawPriceLabel(name + "_lbl", t_label, level,
                        DoubleToString(level, _Digits), c);
     }
  }

//+------------------------------------------------------------------+
//  v2.00 — weekly first-4hr H/L levels.
//
//  Algorithm:
//  - Find the most recent week-start datetime (Monday 00:00 broker time).
//  - For each of InpWeeksBack weeks back:
//      first4_t1 = week_start
//      first4_t2 = week_start + InpWeekFirstHours hours
//      week_end  = week_start + 7 days  (or current time for in-progress week)
//    Compute H/L of bars in [first4_t1, first4_t2] using CopyRates,
//    then draw two OBJ_TREND segments at those prices spanning
//    [week_start, week_end].
//+------------------------------------------------------------------+
void DrawWeeklyLevels()
  {
   datetime now = TimeCurrent();
   datetime current_week_start = MostRecentDOW(now, InpWeekStartDOW);

   for(int wk = 0; wk < InpWeeksBack; wk++)
     {
      datetime week_start = current_week_start - wk * 7 * 86400;
      datetime first4_end = week_start + InpWeekFirstHours * 3600;
      datetime week_end   = (wk == 0) ? now : (week_start + 7 * 86400);
      if(week_end <= week_start) continue;

      double hi, lo;
      if(!RangeHiLo(week_start, first4_end, hi, lo)) continue;

      string suffix = StringFormat("W%d", wk);
      string n_hi = InpObjectPrefix + suffix + "_hi";
      string n_lo = InpObjectPrefix + suffix + "_lo";

      DrawSegment(n_hi, week_start, week_end, hi,
                  InpWeekHighColor, InpWeekLineStyle, InpWeekLineWidth);
      DrawSegment(n_lo, week_start, week_end, lo,
                  InpWeekLowColor,  InpWeekLineStyle, InpWeekLineWidth);

      if(InpShowLabel)
        {
         // Label sits at the start of the week, ABOVE the line.
         string txt_hi = StringFormat("Wk%s Hi %s",
                                      (wk == 0 ? "0" : "-" + IntegerToString(wk)),
                                      DoubleToString(hi, _Digits));
         string txt_lo = StringFormat("Wk%s Lo %s",
                                      (wk == 0 ? "0" : "-" + IntegerToString(wk)),
                                      DoubleToString(lo, _Digits));
         DrawPriceLabel(n_hi + "_lbl", week_start, hi, txt_hi, InpWeekHighColor);
         DrawPriceLabel(n_lo + "_lbl", week_start, lo, txt_lo, InpWeekLowColor);
        }
     }
  }

//+------------------------------------------------------------------+
//  Floor `t` to midnight of the most recent target-DOW (default Mon).
//+------------------------------------------------------------------+
datetime MostRecentDOW(datetime t, int target_dow)
  {
   long s = (long)t;
   long anchor = (s / 86400) * 86400;       // floor to UTC midnight
   datetime day = (datetime)anchor;
   for(int i = 0; i < 7; i++)
     {
      MqlDateTime mdt;
      TimeToStruct(day, mdt);
      if(mdt.day_of_week == target_dow) return(day);
      day -= 86400;
     }
   return((datetime)anchor);  // fallback — shouldn't happen
  }

//+------------------------------------------------------------------+
bool RangeHiLo(datetime t1, datetime t2, double &hi, double &lo)
  {
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
void DrawHLine(string name, double price, color c, int width, ENUM_LINE_STYLE style)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
   ObjectSetDouble (0, name, OBJPROP_PRICE,    price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,    c);
   ObjectSetInteger(0, name, OBJPROP_STYLE,    style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,    width);
   ObjectSetInteger(0, name, OBJPROP_BACK,     true);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN,   true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
  }

//+------------------------------------------------------------------+
void DrawSegment(string name, datetime t1, datetime t2, double price,
                 color c, ENUM_LINE_STYLE style, int width)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TREND, 0, t1, price, t2, price);
   ObjectSetInteger(0, name, OBJPROP_TIME,  0, t1);
   ObjectSetInteger(0, name, OBJPROP_TIME,  1, t2);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 0, price);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 1, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,      c);
   ObjectSetInteger(0, name, OBJPROP_STYLE,      style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,      width);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT,  false);
   ObjectSetInteger(0, name, OBJPROP_BACK,       true);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN,     true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
  }

//+------------------------------------------------------------------+
//  Label sits ABOVE the line via ANCHOR_LEFT_LOWER.
//+------------------------------------------------------------------+
void DrawPriceLabel(string name, datetime t, double price, string text, color c)
  {
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

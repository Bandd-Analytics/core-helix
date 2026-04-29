//+------------------------------------------------------------------+
//|  BandD_WorktimeRibbon.mq5                                        |
//|  Bandd Analytics — 2026                                          |
//|                                                                  |
//|  Session-shading ribbon — replicates Worktime Ribbon v1.0        |
//|  Draws coloured background rectangles for each trading session,   |
//|  with optional pip-range labels and an Asia high/low range line.  |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property version   "1.0"
#property indicator_chart_window
#property indicator_plots 0

//--- General
input int    InpDays           = 50;        // Days of history to shade

//--- Asia session
input bool   InpAsia           = true;      // Show Asia
input string InpAsiaStart      = "00:00";   // Asia start (server time HH:MM)
input string InpAsiaEnd        = "07:00";   // Asia end
input color  InpAsiaClr        = clrLightBlue;   // Asia fill colour
input int    InpAsiaOpacity    = 20;        // Asia opacity 0-100
input color  InpAsiaPipClr     = clrWhite;  // Asia range label colour
input int    InpAsiaPipSz      = 10;        // Asia range label font size

//--- Asia range line (extends past session end)
input bool             InpARLine      = false;       // Show Asia range line
input color            InpARLineClr   = clrWhite;
input int              InpARLineWidth = 1;
input ENUM_LINE_STYLE  InpARLineStyle = STYLE_DOT;
input int              InpARExtend    = 6;           // Bars beyond session end

//--- London Gap (manipulation window)
input bool   InpLGap           = true;      // Show London Gap
input string InpLGapStart      = "09:00";
input string InpLGapEnd        = "09:30";
input color  InpLGapClr        = clrLightGray;
input int    InpLGapOpacity    = 20;

//--- London session
input bool   InpLondon         = false;     // Show London
input string InpLondonStart    = "09:30";
input string InpLondonEnd      = "12:00";
input color  InpLondonClr      = clrLightGray;
input int    InpLondonOpacity  = 20;

//--- NY Gap (manipulation window)
input bool   InpNYGap          = true;      // Show NY Gap
input string InpNYGapStart     = "15:00";
input string InpNYGapEnd       = "15:30";
input color  InpNYGapClr       = clrLightGray;
input int    InpNYGapOpacity   = 20;

//--- New York session
input bool   InpNY             = true;      // Show New York
input string InpNYStart        = "15:30";
input string InpNYEnd          = "19:00";
input color  InpNYClr          = clrBrown;
input int    InpNYOpacity      = 20;
input color  InpNYPipClr       = clrWhite;  // NY range label colour
input int    InpNYPipSz        = 10;        // NY range label font size

//+------------------------------------------------------------------+
//  Globals
//+------------------------------------------------------------------+
string   g_pfx;       // unique object-name prefix for this chart instance
double   g_pipSz;     // size of one pip in price units
datetime g_lastBar;   // last bar time seen; drives new-bar detection

//+------------------------------------------------------------------+
int OnInit()
  {
   // prefix includes ChartID so multi-chart use doesn't share objects
   g_pfx     = "WR_" + IntegerToString(ChartID()) + "_";
   // pip size: 5/3-digit brokers have an extra decimal — pip = 10 × _Point
   g_pipSz   = (_Digits == 5 || _Digits == 3) ? 10.0 * _Point : _Point;
   g_lastBar = 0;
   EventSetMillisecondTimer(500);  // keep current session live-updating
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   DeleteAll();
   ChartRedraw();
  }

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
   if(rates_total < 1) return 0;
   datetime latest = time[rates_total - 1];
   if(latest != g_lastBar)
     {
      g_lastBar = latest;
      Redraw();
      ChartRedraw();
     }
   return rates_total;
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   // refreshes the current (live) session box on every 500 ms tick
   Redraw();
   ChartRedraw();
  }

//+------------------------------------------------------------------+
void OnChartEvent(const int    id,
                  const long   &lparam,
                  const double &dparam,
                  const string &sparam)
  {
   if(id == CHARTEVENT_CHART_CHANGE)
     {
      Redraw();
      ChartRedraw();
     }
  }

//+------------------------------------------------------------------+
//  Redraw: iterate InpDays days back and paint all sessions
//+------------------------------------------------------------------+
void Redraw()
  {
   datetime now   = TimeCurrent();
   datetime today = DayFloor(now);

   for(int d = 0; d < InpDays; d++)
     {
      datetime day = today - (datetime)(d * 86400);
      // skip Saturday (6) and Sunday (0) — no session boxes on weekends
      MqlDateTime mdt;
      TimeToStruct(day, mdt);
      if(mdt.day_of_week == 0 || mdt.day_of_week == 6) continue;

      if(InpAsia)
         DrawBox("A",  day, ParseHHMM(InpAsiaStart),    ParseHHMM(InpAsiaEnd),
                 InpAsiaClr,    InpAsiaOpacity,    true,  InpAsiaPipClr, InpAsiaPipSz);

      if(InpARLine)
         DrawARLine(day, ParseHHMM(InpAsiaStart), ParseHHMM(InpAsiaEnd));

      if(InpLGap)
         DrawBox("LG", day, ParseHHMM(InpLGapStart),    ParseHHMM(InpLGapEnd),
                 InpLGapClr,    InpLGapOpacity,    false, clrNONE, 0);

      if(InpLondon)
         DrawBox("L",  day, ParseHHMM(InpLondonStart),  ParseHHMM(InpLondonEnd),
                 InpLondonClr,  InpLondonOpacity,  false, clrNONE, 0);

      if(InpNYGap)
         DrawBox("NG", day, ParseHHMM(InpNYGapStart),   ParseHHMM(InpNYGapEnd),
                 InpNYGapClr,   InpNYGapOpacity,   false, clrNONE, 0);

      if(InpNY)
         DrawBox("NY", day, ParseHHMM(InpNYStart),      ParseHHMM(InpNYEnd),
                 InpNYClr,      InpNYOpacity,      true,  InpNYPipClr, InpNYPipSz);
     }
  }

//+------------------------------------------------------------------+
//  DrawBox: creates/updates one session rectangle + optional pip label
//+------------------------------------------------------------------+
void DrawBox(const string tag,
             datetime     dayStart,
             int          startMin,
             int          endMin,
             color        clr,
             int          opacity,
             bool         showPip,
             color        pipClr,
             int          pipSz)
  {
   datetime t1 = dayStart + (datetime)(startMin * 60);
   datetime t2 = dayStart + (datetime)(endMin   * 60);

   // fetch all bars in the session window
   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int n = CopyRates(_Symbol, _Period, t1, t2, rates);
   if(n <= 0) return;

   // session high/low
   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int i = 0; i < n; i++)
     {
      if(rates[i].high > hi) hi = rates[i].high;
      if(rates[i].low  < lo) lo = rates[i].low;
     }
   if(lo == DBL_MAX || hi == -DBL_MAX) return;

   string boxName = g_pfx + tag + "_" + IntegerToString((long)t1);
   uchar  alpha   = (uchar)MathRound(opacity * 255.0 / 100.0);
   long   argb    = (long)ColorToARGB(clr, alpha);

   if(ObjectFind(0, boxName) < 0)
      ObjectCreate(0, boxName, OBJ_RECTANGLE, 0, t1, hi, t2, lo);

   ObjectSetInteger(0, boxName, OBJPROP_TIME,       0, t1);
   ObjectSetInteger(0, boxName, OBJPROP_TIME,       1, t2);
   ObjectSetDouble (0, boxName, OBJPROP_PRICE,      0, hi);
   ObjectSetDouble (0, boxName, OBJPROP_PRICE,      1, lo);
   ObjectSetInteger(0, boxName, OBJPROP_COLOR,      argb);
   ObjectSetInteger(0, boxName, OBJPROP_FILL,       true);
   ObjectSetInteger(0, boxName, OBJPROP_BACK,       true);
   ObjectSetInteger(0, boxName, OBJPROP_SELECTED,   false);
   ObjectSetInteger(0, boxName, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, boxName, OBJPROP_HIDDEN,     true);

   // pip range label — e.g. "R=92.4"
   string pipName = g_pfx + tag + "P_" + IntegerToString((long)t1);
   if(showPip && pipClr != clrNONE)
     {
      double   range_pips = (hi - lo) / g_pipSz;
      string   txt        = StringFormat("R=%.1f", range_pips);
      datetime lblTime    = t1 + (datetime)PeriodSeconds();          // 1 bar in
      double   lblPrice   = lo + 0.1 * (hi - lo);                   // 10% from bottom

      if(ObjectFind(0, pipName) < 0)
         ObjectCreate(0, pipName, OBJ_TEXT, 0, lblTime, lblPrice);

      ObjectSetString (0, pipName, OBJPROP_TEXT,       txt);
      ObjectSetInteger(0, pipName, OBJPROP_TIME,    0, lblTime);
      ObjectSetDouble (0, pipName, OBJPROP_PRICE,   0, lblPrice);
      ObjectSetInteger(0, pipName, OBJPROP_COLOR,      (long)pipClr);
      ObjectSetInteger(0, pipName, OBJPROP_FONTSIZE,   pipSz);
      ObjectSetString (0, pipName, OBJPROP_FONT,       "Arial");
      ObjectSetInteger(0, pipName, OBJPROP_ANCHOR,     ANCHOR_LEFT_LOWER);
      ObjectSetInteger(0, pipName, OBJPROP_BACK,       true);
      ObjectSetInteger(0, pipName, OBJPROP_HIDDEN,     true);
      ObjectSetInteger(0, pipName, OBJPROP_SELECTABLE, false);
     }
   else
     {
      if(ObjectFind(0, pipName) >= 0) ObjectDelete(0, pipName);
     }
  }

//+------------------------------------------------------------------+
//  DrawARLine: horizontal High/Low lines extending past Asia session
//+------------------------------------------------------------------+
void DrawARLine(datetime dayStart, int startMin, int endMin)
  {
   datetime t1 = dayStart + (datetime)(startMin * 60);
   datetime t2 = dayStart + (datetime)(endMin   * 60);

   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int n = CopyRates(_Symbol, _Period, t1, t2, rates);
   if(n <= 0) return;

   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int i = 0; i < n; i++)
     {
      if(rates[i].high > hi) hi = rates[i].high;
      if(rates[i].low  < lo) lo = rates[i].low;
     }
   if(lo == DBL_MAX) return;

   datetime t_ext = t2 + (datetime)(InpARExtend * PeriodSeconds());

   for(int lvl = 0; lvl < 2; lvl++)
     {
      double price = (lvl == 0) ? hi : lo;
      string nm    = g_pfx + "AR" + (lvl == 0 ? "H" : "L") + "_" + IntegerToString((long)t1);

      if(ObjectFind(0, nm) < 0)
         ObjectCreate(0, nm, OBJ_TREND, 0, t2, price, t_ext, price);

      ObjectSetInteger(0, nm, OBJPROP_TIME,       0, t2);
      ObjectSetInteger(0, nm, OBJPROP_TIME,       1, t_ext);
      ObjectSetDouble (0, nm, OBJPROP_PRICE,      0, price);
      ObjectSetDouble (0, nm, OBJPROP_PRICE,      1, price);
      ObjectSetInteger(0, nm, OBJPROP_COLOR,      (long)InpARLineClr);
      ObjectSetInteger(0, nm, OBJPROP_WIDTH,      InpARLineWidth);
      ObjectSetInteger(0, nm, OBJPROP_STYLE,      InpARLineStyle);
      ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT,  false);
      ObjectSetInteger(0, nm, OBJPROP_BACK,       true);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN,     true);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
     }
  }

//+------------------------------------------------------------------+
//  DayFloor: truncate datetime to midnight of the same server day
//+------------------------------------------------------------------+
datetime DayFloor(datetime t)
  {
   MqlDateTime mdt;
   TimeToStruct(t, mdt);
   mdt.hour = 0;
   mdt.min  = 0;
   mdt.sec  = 0;
   return StructToTime(mdt);
  }

//+------------------------------------------------------------------+
//  ParseHHMM: "HH:MM" string -> minutes from midnight (int)
//+------------------------------------------------------------------+
int ParseHHMM(const string hhmm)
  {
   string parts[];
   if(StringSplit(hhmm, ':', parts) < 2) return 0;
   return (int)StringToInteger(parts[0]) * 60 + (int)StringToInteger(parts[1]);
  }

//+------------------------------------------------------------------+
//  DeleteAll: remove every chart object belonging to this indicator
//+------------------------------------------------------------------+
void DeleteAll()
  {
   for(int i = ObjectsTotal(0, 0, -1) - 1; i >= 0; i--)
     {
      string nm = ObjectName(0, i, 0, -1);
      if(StringFind(nm, g_pfx) == 0)
         ObjectDelete(0, nm);
     }
  }
//+------------------------------------------------------------------+

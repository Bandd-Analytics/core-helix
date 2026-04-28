//+------------------------------------------------------------------+
//|  sm_WorkTime_no_autogmt.mq5                                       |
//|  Phase 12 Plan 01 — Tier 0 helper (manual-BrokerGMT variant)      |
//|  Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md |
//|                                                                   |
//|  D-19 architectural distinction — NO sm_gmtoffset dependency by   |
//|  design; broker offset comes from manual InpBrokerGMT input only. |
//|                                                                   |
//|  Visual behavior is otherwise identical to sm_WorkTime v2.00:     |
//|  session-H/L-bounded boxes, light colors, gap boxes, ColorToARGB  |
//|  opacity blending, optional AR Line, pip-range labels.            |
//|                                                                   |
//|  Reference: V2/indicators/BandD_WorktimeRibbon.mq5                |
//|  (operator-confirmed via screenshot 2026-04-28).                  |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !sm_WorkTime_no_autogmt.ex4"
#property version   "2.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- General
input int    InpDays           = 50;        // Number of days to display

//--- Manual broker GMT offset (D-19: no GlobalVariable read)
input int    InpBrokerGMT      = 0;         // Manual broker GMT offset in hours
input bool   InpBrokerDSTAdjust= false;     // +1 h during NH DST window (Mar-Oct)

//--- Asia session
input bool   InpAsia           = true;      // Show Asia session
input string InpAsiaStart      = "00:00";   // Asia start (HH:MM)
input string InpAsiaEnd        = "07:00";   // Asia end   (HH:MM)
input color  InpAsiaClr        = clrLightBlue;  // Asia session color
input int    InpAsiaOpacity    = 20;        // Asia opacity (0-100)
input color  InpAsiaPipClr     = clrWhite;  // Asia pip value color
input int    InpAsiaPipSz      = 10;        // Asia pip value font size

//--- Asia Range Line (extends past Asia close)
input bool             InpARLine      = false;       // Show AR Line
input color            InpARLineClr   = clrWhite;    // AR Line color
input int              InpARLineWidth = 1;           // AR Line width
input ENUM_LINE_STYLE  InpARLineStyle = STYLE_DASH;  // AR Line style
input int              InpARExtend    = 6;           // Hours to extend AR Line after Asia session

//--- London Gap (changeover overlay: 30m before + 30m after London open)
input bool   InpLGap           = true;          // Show London Gap
input string InpLGapStart      = "09:00";       // London Gap start (HH:MM)
input string InpLGapEnd        = "10:00";       // London Gap end   (HH:MM)
input color  InpLGapClr        = clrLightGray;  // London Gap color
input int    InpLGapOpacity    = 20;            // London Gap opacity (0-100)

//--- London session
input bool   InpLondon         = false;         // Show London session
input string InpLondonStart    = "09:30";       // London session start (HH:MM)
input string InpLondonEnd      = "12:00";       // London session end   (HH:MM)
input color  InpLondonClr      = clrLightGray;  // London session color
input int    InpLondonOpacity  = 20;            // London opacity (0-100)

//--- NY Gap (changeover overlay: 30m before + 30m after NY open)
input bool   InpNYGap          = true;          // Show NY Gap
input string InpNYGapStart     = "15:00";       // NY Gap start (HH:MM)
input string InpNYGapEnd       = "16:00";       // NY Gap end   (HH:MM)
input color  InpNYGapClr       = clrLightGray;  // NY Gap color
input int    InpNYGapOpacity   = 20;            // NY Gap opacity (0-100)

//--- NY session
input bool   InpNY             = true;          // Show NY session
input string InpNYStart        = "15:30";       // NY session start (HH:MM)
input string InpNYEnd          = "19:00";       // NY session end   (HH:MM)
input color  InpNYClr          = clrBrown;      // NY session color
input int    InpNYOpacity      = 20;            // NY opacity (0-100)
input color  InpNYPipClr       = clrWhite;      // NY pip value color
input int    InpNYPipSz        = 10;            // NY pip value font size

//+------------------------------------------------------------------+
//  Globals
//+------------------------------------------------------------------+
string   g_pfx;       // unique object-name prefix for this chart instance
double   g_pipSz;     // size of one pip in price units
datetime g_lastBar;
int      g_offsetSec; // resolved offset in seconds (manual-input source)

//+------------------------------------------------------------------+
bool IsNorthernHemisphereDSTActive()
  {
   MqlDateTime now;
   TimeGMT(now);
   return(now.mon >= 3 && now.mon <= 10);
  }

//+------------------------------------------------------------------+
void ResolveOffset()
  {
   //--- D-19 architectural distinction: NO sm_gmtoffset dependency,
   //--- manual InpBrokerGMT input only. No GlobalVariableGet read.
   int o = InpBrokerGMT;
   if(InpBrokerDSTAdjust && IsNorthernHemisphereDSTActive())
      o = o + 1;
   g_offsetSec = o * 3600;
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   g_pfx     = "smWTnoauto_" + IntegerToString(ChartID()) + "_";
   g_pipSz   = (_Digits == 5 || _Digits == 3) ? 10.0 * _Point : _Point;
   g_lastBar = 0;
   ResolveOffset();
   EventSetMillisecondTimer(500);
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
      ResolveOffset();
      Redraw();
      ChartRedraw();
     }
   return rates_total;
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
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
void Redraw()
  {
   datetime now   = TimeCurrent();
   datetime today = DayFloor(now);

   for(int d = 0; d < InpDays; d++)
     {
      datetime day = today - (datetime)(d * 86400);
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
   datetime t1 = dayStart + (datetime)(startMin * 60) + (datetime)g_offsetSec;
   datetime t2 = dayStart + (datetime)(endMin   * 60) + (datetime)g_offsetSec;

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

   string pipName = g_pfx + tag + "P_" + IntegerToString((long)t1);
   if(showPip && pipClr != clrNONE)
     {
      double   range_pips = (hi - lo) / g_pipSz;
      string   txt        = StringFormat("R=%.1f", range_pips);
      datetime lblTime    = t1 + (datetime)PeriodSeconds();
      double   lblPrice   = lo + 0.1 * (hi - lo);

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
void DrawARLine(datetime dayStart, int startMin, int endMin)
  {
   datetime t1 = dayStart + (datetime)(startMin * 60) + (datetime)g_offsetSec;
   datetime t2 = dayStart + (datetime)(endMin   * 60) + (datetime)g_offsetSec;

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

   datetime t_ext = t2 + (datetime)(InpARExtend * 3600);

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
int ParseHHMM(const string hhmm)
  {
   string parts[];
   if(StringSplit(hhmm, ':', parts) < 2) return 0;
   return (int)StringToInteger(parts[0]) * 60 + (int)StringToInteger(parts[1]);
  }

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

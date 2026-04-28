//+------------------------------------------------------------------+
//|  sm_WorkTime_no_autogmt.mq4                                       |
//|  Phase 12 Plan 01 — Tier 0 helper (manual-BrokerGMT, MQ4, D-20)   |
//|  Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md |
//|                                                                   |
//|  D-19 architectural distinction — NO sm_gmtoffset dependency by   |
//|  design; broker offset comes from manual InpBrokerGMT input only. |
//|                                                                   |
//|  Otherwise behaviorally identical to sm_WorkTime.mq4 v2.00:       |
//|  session-H/L boxes, gap windows, AR Line, pip labels.             |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !sm_WorkTime_no_autogmt.ex4"
#property version   "2.00"
#property indicator_chart_window

//--- General
input int    InpDays           = 50;

//--- Manual broker offset (D-19: no GlobalVariable read)
input int    InpBrokerGMT      = 0;
input bool   InpBrokerDSTAdjust= false;

//--- Asia
input bool   InpAsia           = true;
input string InpAsiaStart      = "00:00";
input string InpAsiaEnd        = "07:00";
input color  InpAsiaClr        = clrLightBlue;
input int    InpAsiaOpacity    = 20;
input color  InpAsiaPipClr     = clrWhite;
input int    InpAsiaPipSz      = 10;

//--- AR Line
input bool   InpARLine         = false;
input color  InpARLineClr      = clrWhite;
input int    InpARLineWidth    = 1;
input int    InpARLineStyle    = STYLE_DASH;
input int    InpARExtend       = 6;

//--- London Gap
input bool   InpLGap           = true;
input string InpLGapStart      = "09:00";
input string InpLGapEnd        = "10:00";
input color  InpLGapClr        = clrLightGray;
input int    InpLGapOpacity    = 20;

//--- London
input bool   InpLondon         = false;
input string InpLondonStart    = "09:30";
input string InpLondonEnd      = "12:00";
input color  InpLondonClr      = clrLightGray;
input int    InpLondonOpacity  = 20;

//--- NY Gap
input bool   InpNYGap          = true;
input string InpNYGapStart     = "15:00";
input string InpNYGapEnd       = "16:00";
input color  InpNYGapClr       = clrLightGray;
input int    InpNYGapOpacity   = 20;

//--- NY
input bool   InpNY             = true;
input string InpNYStart        = "15:30";
input string InpNYEnd          = "19:00";
input color  InpNYClr          = clrBrown;
input int    InpNYOpacity      = 20;
input color  InpNYPipClr       = clrWhite;
input int    InpNYPipSz        = 10;

//--- Globals
string   g_pfx;
double   g_pipSz;
datetime g_lastBar;
int      g_offsetSec;

//+------------------------------------------------------------------+
bool IsNorthernHemisphereDSTActive()
  {
   int mon = TimeMonth(TimeGMT());
   return(mon >= 3 && mon <= 10);
  }

//+------------------------------------------------------------------+
void ResolveOffset()
  {
   //--- D-19: NO GlobalVariableGet — manual InpBrokerGMT only.
   int o = InpBrokerGMT;
   if(InpBrokerDSTAdjust && IsNorthernHemisphereDSTActive())
      o = o + 1;
   g_offsetSec = o * 3600;
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   g_pfx     = "smWTnoauto_" + IntegerToString(ChartID()) + "_";
   g_pipSz   = (Digits == 5 || Digits == 3) ? 10.0 * Point : Point;
   g_lastBar = 0;
   ResolveOffset();
   EventSetMillisecondTimer(500);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   DeleteAll();
   WindowRedraw();
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long   &tick_volume[],
                const long   &volume[],
                const int    &spread[])
  {
   if(rates_total < 1) return(0);
   datetime latest = time[rates_total - 1];
   if(latest != g_lastBar)
     {
      g_lastBar = latest;
      ResolveOffset();
      Redraw();
      WindowRedraw();
     }
   return(rates_total);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Redraw();
   WindowRedraw();
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
      WindowRedraw();
     }
  }

//+------------------------------------------------------------------+
int ParseHHMM(string hhmm)
  {
   string parts[];
   if(StringSplit(hhmm, ':', parts) < 2) return(0);
   return ((int)StrToInteger(parts[0]) * 60 + (int)StrToInteger(parts[1]));
  }

//+------------------------------------------------------------------+
datetime DayFloor(datetime t)
  {
   long s = (long)t;
   long anchor = (s / 86400) * 86400;
   return((datetime)anchor);
  }

//+------------------------------------------------------------------+
bool SessionHiLo(datetime t1, datetime t2, double &hi, double &lo)
  {
   int shift_t1 = iBarShift(_Symbol, _Period, t1, false);
   int shift_t2 = iBarShift(_Symbol, _Period, t2, false);
   if(shift_t1 < 0 || shift_t2 < 0) return(false);
   hi = -DBL_MAX; lo = DBL_MAX;
   for(int s = shift_t2; s <= shift_t1; s++)
     {
      double h = iHigh(_Symbol, _Period, s);
      double l = iLow (_Symbol, _Period, s);
      if(h > hi) hi = h;
      if(l < lo) lo = l;
     }
   return(hi > -DBL_MAX && lo < DBL_MAX);
  }

//+------------------------------------------------------------------+
void Redraw()
  {
   datetime now   = TimeCurrent();
   datetime today = DayFloor(now);

   for(int d = 0; d < InpDays; d++)
     {
      datetime day = today - d * 86400;
      int dow = TimeDayOfWeek(day);
      if(dow == 0 || dow == 6) continue;

      if(InpAsia)
         DrawBox("A",  day, ParseHHMM(InpAsiaStart),    ParseHHMM(InpAsiaEnd),
                 InpAsiaClr,    true,  InpAsiaPipClr, InpAsiaPipSz);

      if(InpARLine)
         DrawARLine(day, ParseHHMM(InpAsiaStart), ParseHHMM(InpAsiaEnd));

      if(InpLGap)
         DrawBox("LG", day, ParseHHMM(InpLGapStart),    ParseHHMM(InpLGapEnd),
                 InpLGapClr,    false, clrNONE, 0);

      if(InpLondon)
         DrawBox("L",  day, ParseHHMM(InpLondonStart),  ParseHHMM(InpLondonEnd),
                 InpLondonClr,  false, clrNONE, 0);

      if(InpNYGap)
         DrawBox("NG", day, ParseHHMM(InpNYGapStart),   ParseHHMM(InpNYGapEnd),
                 InpNYGapClr,   false, clrNONE, 0);

      if(InpNY)
         DrawBox("NY", day, ParseHHMM(InpNYStart),      ParseHHMM(InpNYEnd),
                 InpNYClr,      true,  InpNYPipClr, InpNYPipSz);
     }
  }

//+------------------------------------------------------------------+
void DrawBox(string tag, datetime dayStart, int startMin, int endMin,
             color clr, bool showPip, color pipClr, int pipSz)
  {
   datetime t1 = dayStart + startMin * 60 + g_offsetSec;
   datetime t2 = dayStart + endMin   * 60 + g_offsetSec;

   double hi, lo;
   if(!SessionHiLo(t1, t2, hi, lo)) return;

   string boxName = g_pfx + tag + "_" + IntegerToString((long)t1);
   if(ObjectFind(boxName) < 0)
      ObjectCreate(boxName, OBJ_RECTANGLE, 0, t1, hi, t2, lo);

   ObjectSet(boxName, OBJPROP_TIME1,      t1);
   ObjectSet(boxName, OBJPROP_PRICE1,     hi);
   ObjectSet(boxName, OBJPROP_TIME2,      t2);
   ObjectSet(boxName, OBJPROP_PRICE2,     lo);
   ObjectSet(boxName, OBJPROP_COLOR,      clr);
   ObjectSet(boxName, OBJPROP_BACK,       true);
   ObjectSet(boxName, OBJPROP_SELECTABLE, false);

   string pipName = g_pfx + tag + "P_" + IntegerToString((long)t1);
   if(showPip && pipClr != clrNONE)
     {
      double range_pips = (hi - lo) / g_pipSz;
      string txt        = "R=" + DoubleToStr(range_pips, 1);
      datetime lblTime  = t1 + PeriodSeconds();
      double   lblPrice = lo + 0.1 * (hi - lo);

      if(ObjectFind(pipName) < 0)
         ObjectCreate(pipName, OBJ_TEXT, 0, lblTime, lblPrice);

      ObjectSet     (pipName, OBJPROP_TIME1, lblTime);
      ObjectSet     (pipName, OBJPROP_PRICE1, lblPrice);
      ObjectSetText (pipName, txt, pipSz, "Arial", pipClr);
      ObjectSet     (pipName, OBJPROP_BACK,       true);
      ObjectSet     (pipName, OBJPROP_SELECTABLE, false);
     }
   else
     {
      if(ObjectFind(pipName) >= 0) ObjectDelete(pipName);
     }
  }

//+------------------------------------------------------------------+
void DrawARLine(datetime dayStart, int startMin, int endMin)
  {
   datetime t1 = dayStart + startMin * 60 + g_offsetSec;
   datetime t2 = dayStart + endMin   * 60 + g_offsetSec;

   double hi, lo;
   if(!SessionHiLo(t1, t2, hi, lo)) return;

   datetime t_ext = t2 + InpARExtend * 3600;

   for(int lvl = 0; lvl < 2; lvl++)
     {
      double price = (lvl == 0) ? hi : lo;
      string nm    = g_pfx + "AR" + ((lvl == 0) ? "H" : "L") + "_" + IntegerToString((long)t1);

      if(ObjectFind(nm) < 0)
         ObjectCreate(nm, OBJ_TREND, 0, t2, price, t_ext, price);

      ObjectSet(nm, OBJPROP_TIME1,     t2);
      ObjectSet(nm, OBJPROP_PRICE1,    price);
      ObjectSet(nm, OBJPROP_TIME2,     t_ext);
      ObjectSet(nm, OBJPROP_PRICE2,    price);
      ObjectSet(nm, OBJPROP_COLOR,     InpARLineClr);
      ObjectSet(nm, OBJPROP_WIDTH,     InpARLineWidth);
      ObjectSet(nm, OBJPROP_STYLE,     InpARLineStyle);
      ObjectSet(nm, OBJPROP_RAY,       false);
      ObjectSet(nm, OBJPROP_BACK,      true);
      ObjectSet(nm, OBJPROP_SELECTABLE,false);
     }
  }

//+------------------------------------------------------------------+
int PeriodSeconds()
  {
   return(Period() * 60);
  }

//+------------------------------------------------------------------+
void DeleteAll()
  {
   for(int i = ObjectsTotal() - 1; i >= 0; i--)
     {
      string nm = ObjectName(i);
      if(StringFind(nm, g_pfx) == 0)
         ObjectDelete(nm);
     }
  }
//+------------------------------------------------------------------+

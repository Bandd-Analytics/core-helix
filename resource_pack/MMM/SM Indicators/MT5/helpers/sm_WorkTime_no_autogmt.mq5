//+------------------------------------------------------------------+
//|  sm_WorkTime_no_autogmt.mq5                                       |
//|  Phase 12 Plan 01 — Tier 0 helper (manual-BrokerGMT variant)      |
//|  Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md |
//|                                                                   |
//|  Color-coded MMM session-window overlay (Asia/London/US).         |
//|  D-19 architectural distinction — NO sm_gmtoffset dependency by   |
//|  design; broker offset comes from manual InpBrokerGMT input only. |
//|                                                                   |
//|  CONTEXT D-06 / D-19 (MQ5 idiomatic).                             |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !sm_WorkTime_no_autogmt.ex4"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Spec Section 3 inputs
input int    InpBrokerGMT       = 2;            // manual broker GMT offset (hours)
input bool   InpBrokerDSTAdjust = false;        // +1 h during NH DST window

input int    InpAsiaStartH      = 0;
input int    InpAsiaStartM      = 30;
input int    InpAsiaEndH        = 7;
input int    InpAsiaEndM        = 30;
input int    InpLondonStartH    = 7;
input int    InpLondonStartM    = 30;
input int    InpLondonEndH      = 13;
input int    InpLondonEndM      = 30;
input int    InpUSStartH        = 13;
input int    InpUSStartM        = 30;
input int    InpUSEndH          = 22;
input int    InpUSEndM          = 0;

input bool   InpShowAsia        = true;
input bool   InpShowLondon      = true;
input bool   InpShowUS          = true;

input color  InpAsiaColor       = C'40,40,40';
input color  InpLondonColor     = C'0,40,80';
input color  InpUSColor         = C'0,80,40';

input int    InpHistoryDays     = 5;
input bool   InpShowNYReversal  = true;
input color  InpNYRevColor      = C'120,40,0';

const string ObjPrefix = "smWTnoauto_";

//--- Module state
int      g_offset_hours = 0;
datetime g_last_d1_bar  = 0;

//+------------------------------------------------------------------+
bool IsNorthernHemisphereDSTActive()
  {
   MqlDateTime now;
   TimeGMT(now);
   return(now.mon >= 3 && now.mon <= 10);
  }

//+------------------------------------------------------------------+
int ResolveOffset()
  {
   //--- D-19 architectural distinction: NO sm_gmtoffset dependency,
   //--- manual InpBrokerGMT input only. Spec Section 8 explicitly forbids
   //--- the GlobalVariableGet read here.
   int o = InpBrokerGMT;
   if(InpBrokerDSTAdjust && IsNorthernHemisphereDSTActive())
      o = o + 1;
   return(o);
  }

//+------------------------------------------------------------------+
void DeleteAllPrefixed(const string prefix)
  {
   int total = ObjectsTotal(0, -1, -1);
   for(int i = total - 1; i >= 0; i--)
     {
      string name = ObjectName(0, i, -1, -1);
      if(StringFind(name, prefix) == 0)
         ObjectDelete(0, name);
     }
  }

//+------------------------------------------------------------------+
datetime DayAnchorUTC(datetime t)
  {
   long s = (long)t;
   long anchor = (s / 86400) * 86400;
   return((datetime)anchor);
  }

//+------------------------------------------------------------------+
void DrawSessionRect(const string name,
                     const datetime t1,
                     const datetime t2,
                     const color    clr)
  {
   double price_hi = ChartGetDouble(0, CHART_PRICE_MAX, 0);
   double price_lo = ChartGetDouble(0, CHART_PRICE_MIN, 0);
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, price_hi, t2, price_lo);
   else
     {
      ObjectSetInteger(0, name, OBJPROP_TIME, 0, t1);
      ObjectSetInteger(0, name, OBJPROP_TIME, 1, t2);
      ObjectSetDouble (0, name, OBJPROP_PRICE, 0, price_hi);
      ObjectSetDouble (0, name, OBJPROP_PRICE, 1, price_lo);
     }
   ObjectSetInteger(0, name, OBJPROP_COLOR,    clr);
   ObjectSetInteger(0, name, OBJPROP_BACK,     true);
   ObjectSetInteger(0, name, OBJPROP_FILL,     true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetString (0, name, OBJPROP_FONT,     "Arial");
  }

//+------------------------------------------------------------------+
void Recompute()
  {
   g_offset_hours = ResolveOffset();
   DeleteAllPrefixed(ObjPrefix);

   datetime today = DayAnchorUTC(TimeGMT());
   for(int d = -InpHistoryDays; d <= 0; d++)
     {
      datetime day = today + d * 86400;
      string   ds  = TimeToString(day, TIME_DATE);
      StringReplace(ds, ".", "");

      if(InpShowAsia)
        {
         datetime t1 = day + InpAsiaStartH * 3600 + InpAsiaStartM * 60 + g_offset_hours * 3600;
         datetime t2 = day + InpAsiaEndH   * 3600 + InpAsiaEndM   * 60 + g_offset_hours * 3600;
         DrawSessionRect(ObjPrefix + "Asia_" + ds, t1, t2, InpAsiaColor);
        }
      if(InpShowLondon)
        {
         datetime t1 = day + InpLondonStartH * 3600 + InpLondonStartM * 60 + g_offset_hours * 3600;
         datetime t2 = day + InpLondonEndH   * 3600 + InpLondonEndM   * 60 + g_offset_hours * 3600;
         DrawSessionRect(ObjPrefix + "London_" + ds, t1, t2, InpLondonColor);
        }
      if(InpShowUS)
        {
         datetime t1 = day + InpUSStartH * 3600 + InpUSStartM * 60 + g_offset_hours * 3600;
         datetime t2 = day + InpUSEndH   * 3600 + InpUSEndM   * 60 + g_offset_hours * 3600;
         DrawSessionRect(ObjPrefix + "US_" + ds, t1, t2, InpUSColor);
        }
      if(InpShowNYReversal)
        {
         datetime t1 = day + 13 * 3600 + 30 * 60 + g_offset_hours * 3600;
         datetime t2 = day + 16 * 3600 + 30 * 60 + g_offset_hours * 3600;
         DrawSessionRect(ObjPrefix + "NYRev_" + ds, t1, t2, InpNYRevColor);
        }
     }
   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   Recompute();
   EventSetTimer(60);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   DeleteAllPrefixed(ObjPrefix);
   ChartRedraw(0);
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
   datetime cur_d1 = iTime(_Symbol, PERIOD_D1, 0);
   if(cur_d1 != g_last_d1_bar)
     {
      Recompute();
      g_last_d1_bar = cur_d1;
     }
   return(rates_total);
  }
//+------------------------------------------------------------------+

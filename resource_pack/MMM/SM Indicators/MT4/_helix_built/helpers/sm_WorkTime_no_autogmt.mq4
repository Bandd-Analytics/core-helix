//+------------------------------------------------------------------+
//|  sm_WorkTime_no_autogmt.mq4                                       |
//|  Phase 12 Plan 01 — Tier 0 helper (manual-BrokerGMT, MQ4, D-20)   |
//|  Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_WorkTime_no_autogmt.md |
//|                                                                   |
//|  D-19 architectural distinction — NO sm_gmtoffset dependency by   |
//|  design; broker offset comes from manual InpBrokerGMT input only. |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !sm_WorkTime_no_autogmt.ex4"
#property version   "1.00"
#property indicator_chart_window

//--- Spec Section 3 inputs
input int    InpBrokerGMT       = 2;
input bool   InpBrokerDSTAdjust = false;

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

string ObjPrefix = "smWTnoauto_";

//--- Module state
int      g_offset_hours = 0;
datetime g_last_d1_bar  = 0;

//+------------------------------------------------------------------+
bool IsNorthernHemisphereDSTActive()
  {
   int mon = TimeMonth(TimeGMT());
   return(mon >= 3 && mon <= 10);
  }

//+------------------------------------------------------------------+
int ResolveOffset()
  {
   //--- D-19 architectural distinction: manual InpBrokerGMT only.
   int o = InpBrokerGMT;
   if(InpBrokerDSTAdjust && IsNorthernHemisphereDSTActive())
      o = o + 1;
   return(o);
  }

//+------------------------------------------------------------------+
void DeleteAllPrefixed(string prefix)
  {
   int total = ObjectsTotal();
   for(int i = total - 1; i >= 0; i--)
     {
      string name = ObjectName(i);
      if(StringFind(name, prefix) == 0)
         ObjectDelete(name);
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
void DrawSessionRect(string name, datetime t1, datetime t2, color clr)
  {
   double price_hi = WindowPriceMax();
   double price_lo = WindowPriceMin();
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_RECTANGLE, 0, t1, price_hi, t2, price_lo);
   else
     {
      ObjectSet(name, OBJPROP_TIME1,  t1);
      ObjectSet(name, OBJPROP_PRICE1, price_hi);
      ObjectSet(name, OBJPROP_TIME2,  t2);
      ObjectSet(name, OBJPROP_PRICE2, price_lo);
     }
   ObjectSet(name, OBJPROP_COLOR,      clr);
   ObjectSet(name, OBJPROP_BACK,       true);
   ObjectSet(name, OBJPROP_SELECTABLE, false);
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
      string   ds  = TimeToStr(day, TIME_DATE);
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
   WindowRedraw();
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
   datetime cur_d1 = iTime(_Symbol, PERIOD_D1, 0);
   if(cur_d1 != g_last_d1_bar)
     {
      Recompute();
      g_last_d1_bar = cur_d1;
     }
   return(rates_total);
  }
//+------------------------------------------------------------------+

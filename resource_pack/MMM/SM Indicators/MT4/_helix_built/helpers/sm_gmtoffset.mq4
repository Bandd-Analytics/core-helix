//+------------------------------------------------------------------+
//|  sm_gmtoffset.mq4                                                 |
//|  Phase 12 Plan 01 — Tier 0 helper (MQ4 reconstruction)            |
//|  Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md|
//|                                                                   |
//|  MQL4 idiomatic port (D-20). Detects broker GMT offset and        |
//|  publishes it as GlobalVariable "sm_GMTOffset" for consumption    |
//|  by sm_WorkTime and other session-aware indicators.               |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !sm_gmtoffset.ex4"
#property version   "1.00"
#property indicator_chart_window

//--- Spec Section 3 inputs (MQL4 5xx accepts `input` and `extern`; use input)
input bool   InpAutoDetect    = true;
input int    InpManualGMT     = 0;
input bool   InpDSTAdjust     = true;
input string InpGlobalVarName = "sm_GMTOffset";

//--- Module state
int g_offset_hours = 0;

//+------------------------------------------------------------------+
int ComputeOffset()
  {
   if(!InpAutoDetect)
      return((int)InpManualGMT);

   //--- delta_seconds = TimeCurrent() - TimeGMT()
   //--- Note: in MQL4, TimeCurrent() and TimeGMT() return datetime
   //--- (POSIX seconds). int subtraction is safe within ±100 yr range.
   int delta = (int)(TimeCurrent() - TimeGMT());
   int raw   = (int)MathRound(delta / 3600.0);

   if(InpDSTAdjust)
     {
      // MQL4: TimeMonth(TimeGMT()) gives current GMT month
      int mon = TimeMonth(TimeGMT());
      if(mon >= 3 && mon <= 10)
         raw = raw - 1;
     }
   return(raw);
  }

//+------------------------------------------------------------------+
void Publish()
  {
   g_offset_hours = ComputeOffset();
   GlobalVariableSet(InpGlobalVarName, (double)g_offset_hours);
   Comment("GMT Offset detected: ", IntegerToString(g_offset_hours));
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   Publish();
   //--- Hourly refresh — MQL4 5xx supports EventSetTimer + OnTimer
   EventSetTimer(3600);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Publish();
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
   //--- Spec Section 5 step 4: do NOT delete GlobalVariable on deinit.
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
   //--- D-20 MQ4 OnCalculate signature; no per-bar work — refresh via OnTimer.
   return(rates_total);
  }
//+------------------------------------------------------------------+

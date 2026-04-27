//+------------------------------------------------------------------+
//|  sm_gmtoffset.mq5                                                 |
//|  Phase 12 Plan 01 — Tier 0 helper                                 |
//|  Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md|
//|                                                                   |
//|  Detects the broker's effective GMT offset in integer hours and   |
//|  publishes it as a MetaTrader GlobalVariable (default name        |
//|  "sm_GMTOffset") for consumption by sm_WorkTime, SM_PivotPoints,  |
//|  SM_NewHUD, and other session-aware indicators.                   |
//|                                                                   |
//|  CONTEXT D-06 (output path) / D-19 (MQ5 idiomatic).               |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !sm_gmtoffset.ex4"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Spec Section 3 inputs
input bool   InpAutoDetect    = true;          // Auto-detect via TimeCurrent-TimeGMT
input int    InpManualGMT     = 0;             // Fallback offset when AutoDetect=false
input bool   InpDSTAdjust     = true;          // Strip broker DST from raw delta
input string InpGlobalVarName = "sm_GMTOffset"; // GlobalVariable name (downstream contract)

//--- Module state
int g_offset_hours = 0;

//+------------------------------------------------------------------+
int ComputeOffset()
  {
   if(!InpAutoDetect)
      return((int)InpManualGMT);

   //--- delta_seconds = TimeCurrent() - TimeGMT()  (spec Section 5 step 1b)
   long delta = (long)TimeCurrent() - (long)TimeGMT();
   int  raw   = (int)MathRound(delta / 3600.0);

   if(InpDSTAdjust)
     {
      MqlDateTime now;
      TimeGMT(now);
      // Spec Section 5 step 1e + Pseudocode broker_appears_dst_shifted():
      // rough Northern Hemisphere DST window (March..October) — strip 1 h
      // when broker has already applied DST so downstream indicators
      // anchor sessions to "standard winter" GMT.
      if(now.mon >= 3 && now.mon <= 10)
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
   //--- Hourly refresh per spec Section 5 step 3 (cleaner MQ5 idiom — see
   //--- Section 11 MQ4→MQ5 deltas)
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
   //--- Spec Section 5 step 4: deliberately do NOT delete the GlobalVariable
   //--- — downstream indicators rely on the cached offset surviving sm_gmtoffset
   //--- chart removal.
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
   //--- D-19 full MQ5 OnCalculate signature; no per-bar work for this
   //--- utility — the periodic refresh runs from OnTimer.
   return(rates_total);
  }
//+------------------------------------------------------------------+

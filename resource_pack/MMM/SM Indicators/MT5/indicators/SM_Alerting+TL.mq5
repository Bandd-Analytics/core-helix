//+------------------------------------------------------------------+
//|  SM_Alerting+TL.mq5                                              |
//|  Phase 12 Plan 03 — SM Indicators Implementation                 |
//|                                                                  |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/          |
//|        SM_Alerting+TL.md                                         |
//|  Primary reference: MMM Book p. 55 + Anatomy of Stop Hunts PDF   |
//|                                                                  |
//|  Trendline-touch alerter: monitors all OBJ_TREND chart objects   |
//|  drawn by the operator; fires alert when price approaches within  |
//|  touch_pips of any trendline projected to the current bar time.  |
//|                                                                  |
//|  D-08: Wine MetaEditor compile target                            |
//|  D-09: indicator_chart_window (main window)                      |
//+------------------------------------------------------------------+
#property copyright   "Bandd Analytics — Phase 12 SM Indicators reconstruction"
#property link        "https://github.com/banddanalytics/helix"
#property version     "1.00"
#property description "SM_Alerting+TL — trendline-touch alerter for MMM stop-hunt setups"

#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Inputs (spec Section 3 — [INFER] parameters)
input double InpTouchPips    = 5.0;         // Touch tolerance in pips [INFER]
input bool   InpEnableAlert  = true;        // Fire alert on TL touch
input string InpSoundFile    = "alert.wav"; // [INFER] Alert sound file
input bool   InpAlertOnce    = true;        // [INFER] One-shot alert per trendline per session
input string InpObjectFilter = "*";         // [INFER] Trendline name filter (* = all OBJ_TREND)

//--- Fired trendline tracking (one-shot guard per trendline name)
string  g_fired_tls[];      // [INFER] tracks TLs that already fired this session
int     g_fired_count = 0;

//+------------------------------------------------------------------+
//| Get the pip size for the current symbol                          |
//+------------------------------------------------------------------+
double GetPip()
  {
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   return (digits == 3 || digits == 5) ? _Point * 10.0 : _Point;
  }

//+------------------------------------------------------------------+
//| Check if a trendline name has already fired                      |
//+------------------------------------------------------------------+
bool HasFired(const string name)
  {
   for(int i = 0; i < g_fired_count; i++)
      if(g_fired_tls[i] == name)
         return true;
   return false;
  }

//+------------------------------------------------------------------+
//| Mark a trendline as fired                                        |
//+------------------------------------------------------------------+
void MarkFired(const string name)
  {
   ArrayResize(g_fired_tls, g_fired_count + 1);
   g_fired_tls[g_fired_count] = name;
   g_fired_count++;
  }

//+------------------------------------------------------------------+
//| Check all OBJ_TREND objects for touch condition                  |
//+------------------------------------------------------------------+
void CheckTrendlines()
  {
   double pip       = GetPip();
   double tolerance = InpTouchPips * pip;
   double bid       = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask       = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double mid       = (bid + ask) / 2.0;
   datetime now     = TimeCurrent();

   int obj_count = ObjectsTotal(0);
   for(int i = 0; i < obj_count; i++)
     {
      string name = ObjectName(0, i);
      long   obj_type = ObjectGetInteger(0, name, OBJPROP_TYPE);

      if(obj_type != OBJ_TREND)
         continue;

      // Apply name filter [INFER]
      if(InpObjectFilter != "*" && StringFind(name, InpObjectFilter) < 0)
         continue;

      // Check one-shot guard
      if(InpAlertOnce && HasFired(name))
         continue;

      // Read trendline endpoints
      datetime t1 = (datetime)ObjectGetInteger(0, name, OBJPROP_TIME, 0);
      datetime t2 = (datetime)ObjectGetInteger(0, name, OBJPROP_TIME, 1);
      double   p1 = ObjectGetDouble(0, name, OBJPROP_PRICE, 0);
      double   p2 = ObjectGetDouble(0, name, OBJPROP_PRICE, 1);

      if(t1 == t2)
         continue; // Vertical line — undefined slope

      // Linear interpolation: project trendline to current time
      double total_seconds = (double)(t2 - t1);
      double elapsed       = (double)(now - t1);
      double alpha         = elapsed / total_seconds;
      double expected      = p1 + (p2 - p1) * alpha;

      // Touch check: bid/ask within tolerance of projected price
      if(MathAbs(mid - expected) <= tolerance)
        {
         if(InpEnableAlert)
           {
            Alert("SM_Alerting+TL: TL_TOUCH [", _Symbol, "] TL=", name,
                  " Expected=", DoubleToString(expected, _Digits),
                  " Price=", DoubleToString(mid, _Digits));
            if(StringLen(InpSoundFile) > 0)
               PlaySound(InpSoundFile);
           }
         if(InpAlertOnce)
            MarkFired(name);
        }
     }
  }

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   IndicatorSetString(INDICATOR_SHORTNAME, "SM_Alerting+TL");
   EventSetTimer(1); // 1-second check for responsive trendline monitoring
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   ArrayResize(g_fired_tls, 0);
   g_fired_count = 0;
  }

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
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
   return rates_total;
  }

//+------------------------------------------------------------------+
//| Timer event handler — check trendline touches every second       |
//+------------------------------------------------------------------+
void OnTimer()
  {
   CheckTrendlines();
  }
//+------------------------------------------------------------------+

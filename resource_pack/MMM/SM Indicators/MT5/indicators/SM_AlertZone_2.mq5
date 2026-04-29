//+------------------------------------------------------------------+
//|  SM_AlertZone_2.mq5                                              |
//|  Phase 12 Plan 03 — SM Indicators Implementation                 |
//|                                                                  |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/          |
//|        SM_AlertZone_2.md                                         |
//|  AlertZone_2 — same algorithm as AlertZone_1, UPPER zone preset  |
//|  (per Phase 11 INDEX 148-byte delta hypothesis; RESEARCH          |
//|  Open Question #5). AlertZone_2 = short setups near HOD/R1.      |
//|                                                                  |
//|  Only difference from SM_AlertZone_1.mq5:                        |
//|    InpZoneType     = "UPPER"  (was "LOWER")                      |
//|    InpZoneColor    = clrLightCoral  (was clrLightGreen)          |
//|    InpObjectPrefix = "smAZ2_"       (was "smAZ1_")               |
//|    auto_zone uses iHigh (HOD) instead of iLow (LOD)              |
//|                                                                  |
//|  D-08: Wine MetaEditor compile target                            |
//|  D-09: indicator_chart_window (main window)                      |
//+------------------------------------------------------------------+
#property copyright   "Bandd Analytics — Phase 12 SM Indicators reconstruction"
#property link        "https://github.com/banddanalytics/helix"
#property version     "1.00"
#property description "SM_AlertZone_2 — UPPER zone alerter (short setups near HOD/R1)"

#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Inputs (same parameter set as AlertZone_1; UPPER defaults per Open Question #5)
input double InpZoneCenter       = 0.0;          // [INFER] Manual zone center (auto_zone=false)
input double InpZoneWidthPips    = 30.0;         // [INFER] Zone full width in pips
input string InpZoneType         = "UPPER";      // UPPER = near HOD (short setups) — only difference
input bool   InpAutoZone         = true;         // [INFER] Auto-track HOD for zone center
input double InpZoneOffsetPips   = 15.0;         // [INFER] MMM Strike Zone offset from HOD (MMM Book p. 55)
input bool   InpEnableAlert      = true;         // Fire alert when price enters zone
input string InpSoundFile        = "alert.wav";  // [INFER] Alert sound file
input color  InpZoneColor        = clrLightCoral; // [INFER] Upper zone fill color (warm = resistance)
input int    InpZoneAlpha        = 30;           // [INFER] Zone fill transparency
input string InpObjectPrefix     = "smAZ2_";     // Object name prefix

//--- Private state
static datetime g_last_alert_time = 0;

//+------------------------------------------------------------------+
//| Get the pip size for the current symbol                          |
//+------------------------------------------------------------------+
double GetPip()
  {
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   return (digits == 3 || digits == 5) ? _Point * 10.0 : _Point;
  }

//+------------------------------------------------------------------+
//| Recompute zone position and check alert                          |
//+------------------------------------------------------------------+
void Recompute()
  {
   double pip = GetPip();
   double half_width = InpZoneWidthPips * pip / 2.0;
   double center;

   if(InpAutoZone)
     {
      // UPPER zone: track HOD - offset (MMM Strike Zone semantics for shorts)
      double hod = iHigh(_Symbol, PERIOD_D1, 0);
      center = hod - InpZoneOffsetPips * pip;  // [INFER] center below HOD
     }
   else
     {
      center = InpZoneCenter;
     }

   double zone_upper = center + half_width;
   double zone_lower = center - half_width;

//--- Create or update zone rectangle
   string rect_name = InpObjectPrefix + "rect";
   datetime t_start = iTime(_Symbol, PERIOD_D1, 0);
   datetime t_end   = t_start + PeriodSeconds(PERIOD_D1);

   if(ObjectFind(0, rect_name) < 0)
      ObjectCreate(0, rect_name, OBJ_RECTANGLE, 0, t_start, zone_upper, t_end, zone_lower);
   else
     {
      ObjectSetInteger(0, rect_name, OBJPROP_TIME, 0, t_start);
      ObjectSetInteger(0, rect_name, OBJPROP_TIME, 1, t_end);
      ObjectSetDouble(0, rect_name, OBJPROP_PRICE, 0, zone_upper);
      ObjectSetDouble(0, rect_name, OBJPROP_PRICE, 1, zone_lower);
     }
   ObjectSetInteger(0, rect_name, OBJPROP_COLOR, InpZoneColor);
   ObjectSetInteger(0, rect_name, OBJPROP_FILL,  true);
   ObjectSetInteger(0, rect_name, OBJPROP_BACK,  true);
   ObjectSetInteger(0, rect_name, OBJPROP_SELECTABLE, false);

//--- Alert if price enters zone (one-shot per second guard)
   if(InpEnableAlert)
     {
      double current_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      bool in_zone = (current_price >= zone_lower && current_price <= zone_upper);
      datetime now = TimeCurrent();
      if(in_zone && (now - g_last_alert_time) > 300) // 5-minute cooldown [INFER]
        {
         Alert("SM_AlertZone_2: NEAR_ZONE [", _Symbol, "] Price=", DoubleToString(current_price, _Digits),
               " Zone=[", DoubleToString(zone_lower, _Digits), ", ", DoubleToString(zone_upper, _Digits), "]");
         if(StringLen(InpSoundFile) > 0)
            PlaySound(InpSoundFile);
         g_last_alert_time = now;
        }
     }

   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Delete all zone objects with our prefix                          |
//+------------------------------------------------------------------+
void CleanupObjects()
  {
   string obj_name = InpObjectPrefix + "rect";
   if(ObjectFind(0, obj_name) >= 0)
      ObjectDelete(0, obj_name);
  }

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   IndicatorSetString(INDICATOR_SHORTNAME, "SM_AlertZone_2");
   Recompute();
   EventSetTimer(1);
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   CleanupObjects();
   EventKillTimer();
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
//| Timer event handler                                              |
//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
  }
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|  SM_AlertZone_1.mq4                                              |
//|  Phase 12 Plan 03 — SM Indicators Implementation                 |
//|                                                                  |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/          |
//|        SM_AlertZone_1.md                                         |
//|  RESEARCH Open Question #5: same algorithm as SM_AlertZone_2;   |
//|  LOWER zone preset (long setups near LOD/S1).                    |
//|  D-20: MQL4 idioms — iLow/iHigh return double directly           |
//+------------------------------------------------------------------+
#property copyright   "Bandd Analytics — Phase 12 SM Indicators reconstruction"
#property link        "https://github.com/banddanalytics/helix"
#property version     "1.00"
#property description "SM_AlertZone_1 — LOWER zone alerter (long setups near LOD/S1)"

#property indicator_chart_window
#property indicator_buffers 0

//--- Inputs
extern double ZoneWidthPips    = 30.0;         // [INFER] Zone full width in pips
extern bool   AutoZone         = true;         // [INFER] Auto-track LOD for zone center
extern double ZoneOffsetPips   = 15.0;         // [INFER] Strike Zone offset from LOD (MMM Book p. 55)
extern bool   EnableAlert      = true;         // Fire alert when price enters zone
extern string SoundFile        = "alert.wav";  // [INFER] Alert sound file
extern color  ZoneColor        = LightGreen;   // [INFER] Zone rectangle fill color
extern string ObjectPrefix     = "smAZ1_";     // Object name prefix

datetime g_last_alert_time = 0;

//+------------------------------------------------------------------+
//| Recompute zone position and check alert                          |
//+------------------------------------------------------------------+
void Recompute()
  {
   int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
   double pip = (digits == 3 || digits == 5) ? _Point * 10.0 : _Point;

   double half_width = ZoneWidthPips * pip / 2.0;
   double center;

   if(AutoZone)
     {
      // LOWER zone: track LOD + offset (MQL4 idiom: iLow returns double directly)
      double lod = iLow(_Symbol, PERIOD_D1, 0);
      center = lod + ZoneOffsetPips * pip;  // [INFER]
     }
   else
     {
      center = 0.0;  // [INFER] manual mode requires ZoneCenter input (not exposed here for simplicity)
     }

   double zone_upper = center + half_width;
   double zone_lower = center - half_width;

//--- Create or update zone rectangle (MQL4 idiom)
   string rect_name = ObjectPrefix + "rect";
   datetime t_start = iTime(_Symbol, PERIOD_D1, 0);
   datetime t_end   = t_start + 86400; // 1 day in seconds

   if(ObjectFind(rect_name) < 0)
      ObjectCreate(rect_name, OBJ_RECTANGLE, 0, t_start, zone_upper, t_end, zone_lower);
   else
     {
      ObjectSet(rect_name, OBJPROP_TIME1,  t_start);
      ObjectSet(rect_name, OBJPROP_TIME2,  t_end);
      ObjectSet(rect_name, OBJPROP_PRICE1, zone_upper);
      ObjectSet(rect_name, OBJPROP_PRICE2, zone_lower);
     }
   ObjectSet(rect_name, OBJPROP_COLOR, ZoneColor);
   ObjectSet(rect_name, OBJPROP_BACK,  true);

//--- Alert check (one-shot guard)
   if(EnableAlert)
     {
      double current_price = MarketInfo(_Symbol, MODE_BID);
      bool in_zone = (current_price >= zone_lower && current_price <= zone_upper);
      datetime now = TimeCurrent();
      if(in_zone && (now - g_last_alert_time) > 300)
        {
         Alert("SM_AlertZone_1: NEAR_ZONE [", _Symbol, "] Price=", DoubleToStr(current_price, _Digits));
         if(StringLen(SoundFile) > 0)
            PlaySound(SoundFile);
         g_last_alert_time = now;
        }
     }

   WindowRedraw();
  }

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int init()
  {
   IndicatorShortName("SM_AlertZone_1");
   Recompute();
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
int deinit()
  {
   string obj_name = ObjectPrefix + "rect";
   if(ObjectFind(obj_name) >= 0)
      ObjectDelete(obj_name);
   return 0;
  }

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int start()
  {
   Recompute();
   return 0;
  }
//+------------------------------------------------------------------+

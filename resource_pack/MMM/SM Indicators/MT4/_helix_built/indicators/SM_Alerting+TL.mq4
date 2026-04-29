//+------------------------------------------------------------------+
//|  SM_Alerting+TL.mq4                                              |
//|  Phase 12 Plan 03 — SM Indicators Implementation                 |
//|                                                                  |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/          |
//|        SM_Alerting+TL.md                                         |
//|  Primary reference: MMM Book p. 55 + Anatomy of Stop Hunts PDF   |
//|  D-20: MQL4 idioms — ObjectsTotal/ObjectName/ObjectGet*          |
//+------------------------------------------------------------------+
#property copyright   "Bandd Analytics — Phase 12 SM Indicators reconstruction"
#property link        "https://github.com/banddanalytics/helix"
#property version     "1.00"
#property description "SM_Alerting+TL — trendline-touch alerter for MMM stop-hunt setups"

#property indicator_chart_window
#property indicator_buffers 0

//--- Inputs
extern double TouchPips    = 5.0;         // Touch tolerance in pips [INFER]
extern bool   EnableAlert  = true;        // Fire alert on TL touch
extern string SoundFile    = "alert.wav"; // [INFER] Alert sound file
extern bool   AlertOnce    = true;        // [INFER] One-shot alert per trendline

//--- Fired trendline tracking
string  g_fired_tls[];
int     g_fired_count = 0;

//+------------------------------------------------------------------+
//| Check if a trendline name has already fired                      |
//+------------------------------------------------------------------+
bool HasFired(string name)
  {
   for(int i = 0; i < g_fired_count; i++)
      if(g_fired_tls[i] == name)
         return true;
   return false;
  }

//+------------------------------------------------------------------+
//| Mark a trendline as fired                                        |
//+------------------------------------------------------------------+
void MarkFired(string name)
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
   int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
   double pip = (digits == 3 || digits == 5) ? _Point * 10.0 : _Point;
   double tolerance = TouchPips * pip;
   double bid = MarketInfo(_Symbol, MODE_BID);
   double ask = MarketInfo(_Symbol, MODE_ASK);
   double mid = (bid + ask) / 2.0;
   datetime now = TimeCurrent();

   int obj_count = ObjectsTotal();
   for(int i = 0; i < obj_count; i++)
     {
      string name = ObjectName(i);

      if(ObjectType(name) != OBJ_TREND)
         continue;

      if(AlertOnce && HasFired(name))
         continue;

      // Read trendline endpoints (MQL4 idiom: ObjectGetValueByShift not applicable; use ObjectGet)
      datetime t1 = (datetime)ObjectGet(name, OBJPROP_TIME1);
      datetime t2 = (datetime)ObjectGet(name, OBJPROP_TIME2);
      double   p1 = ObjectGet(name, OBJPROP_PRICE1);
      double   p2 = ObjectGet(name, OBJPROP_PRICE2);

      if(t1 == t2)
         continue;

      // Linear interpolation: project trendline to current time
      double total_seconds = (double)(t2 - t1);
      double elapsed       = (double)(now - t1);
      double alpha         = elapsed / total_seconds;
      double expected      = p1 + (p2 - p1) * alpha;

      if(MathAbs(mid - expected) <= tolerance)
        {
         if(EnableAlert)
           {
            Alert("SM_Alerting+TL: TL_TOUCH [", _Symbol, "] TL=", name,
                  " Expected=", DoubleToStr(expected, _Digits),
                  " Price=", DoubleToStr(mid, _Digits));
            if(StringLen(SoundFile) > 0)
               PlaySound(SoundFile);
           }
         if(AlertOnce)
            MarkFired(name);
        }
     }
  }

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int init()
  {
   IndicatorShortName("SM_Alerting+TL");
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
int deinit()
  {
   ArrayResize(g_fired_tls, 0);
   g_fired_count = 0;
   return 0;
  }

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int start()
  {
   CheckTrendlines();
   return 0;
  }
//+------------------------------------------------------------------+

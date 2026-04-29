//+------------------------------------------------------------------+
//|  SM_Crossover_Arrows.mq5                                          |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (v2.10)               |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_Crossover_Arrows.md                                      |
//|                                                                   |
//|  Two independent EMA crossover systems:                            |
//|                                                                    |
//|  Short-term pair (default 7/13 — operator-tuned 2026-04-28):       |
//|     EMA(InpFastPeriod)  Lime,  width 2                             |
//|     EMA(InpSlowPeriod)  Red,   width 2                             |
//|     Arrows prefixed "smXarrow_S_"                                  |
//|                                                                    |
//|  Long-term pair (default 50/200 — golden/death cross, v2.10):      |
//|     EMA(InpLongFastPeriod)  Aqua,  width 2                         |
//|     EMA(InpLongSlowPeriod)  White, width 2                         |
//|     Arrows prefixed "smXarrow_L_"                                  |
//|                                                                    |
//|  Cross detection on bar i vs bar i-1 (NEVER bar 0 — Pitfall 5).    |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_Crossover_Arrows.ex4"
#property version   "2.10"
#property indicator_chart_window
#property indicator_buffers 4
#property indicator_plots   4

#property indicator_label1   "EMA Fast (short)"
#property indicator_type1    DRAW_LINE
#property indicator_color1   clrLime
#property indicator_width1   2
#property indicator_label2   "EMA Slow (short)"
#property indicator_type2    DRAW_LINE
#property indicator_color2   clrRed
#property indicator_width2   2
#property indicator_label3   "EMA 50"
#property indicator_type3    DRAW_LINE
#property indicator_color3   clrAqua
#property indicator_width3   2
#property indicator_label4   "EMA 200"
#property indicator_type4    DRAW_LINE
#property indicator_color4   clrWhite
#property indicator_width4   2

//--- Short-term pair (v2.00 operator-tuned 2026-04-28)
input int                InpFastPeriod        = 7;
input int                InpSlowPeriod        = 13;
input bool               InpEnableShortAlert  = true;
input color              InpBuyArrowColor     = clrLime;
input color              InpSellArrowColor    = clrRed;

//--- Long-term pair (v2.10 — golden/death cross)
input bool               InpEnableLongPair    = true;
input int                InpLongFastPeriod    = 50;
input int                InpLongSlowPeriod    = 200;
input bool               InpEnableLongAlert   = true;
input color              InpLongBuyArrowColor = clrAqua;
input color              InpLongSellArrowColor= clrWhite;

input ENUM_MA_METHOD     InpMAMethod          = MODE_EMA;
input ENUM_APPLIED_PRICE InpAppliedPrice      = PRICE_CLOSE;

const string InpObjectPrefix     = "smXarrow_";
const string InpObjectPrefixLong = "smXarrow_L_";
const string InpObjectPrefixShort= "smXarrow_S_";

//--- Buffers
double FastEMA[];
double SlowEMA[];
double LongFastEMA[];
double LongSlowEMA[];

//--- Handles
int g_handle_fast       = INVALID_HANDLE;
int g_handle_slow       = INVALID_HANDLE;
int g_handle_long_fast  = INVALID_HANDLE;
int g_handle_long_slow  = INVALID_HANDLE;
int g_last_alert_bar       = -1;
int g_last_long_alert_bar  = -1;

//+------------------------------------------------------------------+
int OnInit()
  {
   SetIndexBuffer(0, FastEMA, INDICATOR_DATA);
   SetIndexBuffer(1, SlowEMA, INDICATOR_DATA);
   SetIndexBuffer(2, LongFastEMA, INDICATOR_DATA);
   SetIndexBuffer(3, LongSlowEMA, INDICATOR_DATA);
   ArraySetAsSeries(FastEMA,     false);
   ArraySetAsSeries(SlowEMA,     false);
   ArraySetAsSeries(LongFastEMA, false);
   ArraySetAsSeries(LongSlowEMA, false);

   g_handle_fast = iMA(_Symbol, PERIOD_CURRENT, InpFastPeriod, 0,
                       InpMAMethod, InpAppliedPrice);
   g_handle_slow = iMA(_Symbol, PERIOD_CURRENT, InpSlowPeriod, 0,
                       InpMAMethod, InpAppliedPrice);
   if(g_handle_fast == INVALID_HANDLE || g_handle_slow == INVALID_HANDLE)
     {
      Print("SM_Crossover_Arrows: short-pair iMA handle creation failed");
      return(INIT_FAILED);
     }

   if(InpEnableLongPair)
     {
      g_handle_long_fast = iMA(_Symbol, PERIOD_CURRENT, InpLongFastPeriod, 0,
                               InpMAMethod, InpAppliedPrice);
      g_handle_long_slow = iMA(_Symbol, PERIOD_CURRENT, InpLongSlowPeriod, 0,
                               InpMAMethod, InpAppliedPrice);
      if(g_handle_long_fast == INVALID_HANDLE ||
         g_handle_long_slow == INVALID_HANDLE)
        {
         Print("SM_Crossover_Arrows: long-pair iMA handle creation failed");
         return(INIT_FAILED);
        }
     }

   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("SM_Crossover_Arrows(%d/%d, %d/%d)",
                                   InpFastPeriod, InpSlowPeriod,
                                   InpLongFastPeriod, InpLongSlowPeriod));
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   CleanupObjects();
   if(g_handle_fast      != INVALID_HANDLE) IndicatorRelease(g_handle_fast);
   if(g_handle_slow      != INVALID_HANDLE) IndicatorRelease(g_handle_slow);
   if(g_handle_long_fast != INVALID_HANDLE) IndicatorRelease(g_handle_long_fast);
   if(g_handle_long_slow != INVALID_HANDLE) IndicatorRelease(g_handle_long_slow);
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tv[],
                const long &v[], const int &sp[])
  {
   int min_required = MathMax(InpSlowPeriod, InpEnableLongPair ? InpLongSlowPeriod : 0) + 2;
   if(rates_total < min_required) return(0);

   if(CopyBuffer(g_handle_fast, 0, 0, rates_total, FastEMA) < rates_total) return(prev_calculated);
   if(CopyBuffer(g_handle_slow, 0, 0, rates_total, SlowEMA) < rates_total) return(prev_calculated);

   if(InpEnableLongPair)
     {
      if(CopyBuffer(g_handle_long_fast, 0, 0, rates_total, LongFastEMA) < rates_total)
         return(prev_calculated);
      if(CopyBuffer(g_handle_long_slow, 0, 0, rates_total, LongSlowEMA) < rates_total)
         return(prev_calculated);
     }

   int start = (prev_calculated > 0) ? prev_calculated - 1 : min_required;
   if(start < 2) start = 2;

   for(int i = start; i < rates_total - 1; i++)
     {
      // Short-term pair
      if(CrossUp  (FastEMA, SlowEMA, i))
         CreateArrow(InpObjectPrefixShort, i, time[i], low[i],  true,
                     InpBuyArrowColor);
      else if(CrossDown(FastEMA, SlowEMA, i))
         CreateArrow(InpObjectPrefixShort, i, time[i], high[i], false,
                     InpSellArrowColor);

      // Long-term pair (independent)
      if(InpEnableLongPair)
        {
         if(CrossUp  (LongFastEMA, LongSlowEMA, i))
            CreateArrow(InpObjectPrefixLong, i, time[i], low[i],  true,
                        InpLongBuyArrowColor);
         else if(CrossDown(LongFastEMA, LongSlowEMA, i))
            CreateArrow(InpObjectPrefixLong, i, time[i], high[i], false,
                        InpLongSellArrowColor);
        }
     }

   // Alerts on most recent confirmed cross (bar rates_total - 2)
   if(rates_total >= 3)
     {
      int last = rates_total - 2;

      if(InpEnableShortAlert && last != g_last_alert_bar)
        {
         if(CrossUp(FastEMA, SlowEMA, last))
           {
            Alert("SM_Crossover_Arrows: BUY EMA "
                  + IntegerToString(InpFastPeriod) + "/"
                  + IntegerToString(InpSlowPeriod) + " " + _Symbol);
            g_last_alert_bar = last;
           }
         else if(CrossDown(FastEMA, SlowEMA, last))
           {
            Alert("SM_Crossover_Arrows: SELL EMA "
                  + IntegerToString(InpFastPeriod) + "/"
                  + IntegerToString(InpSlowPeriod) + " " + _Symbol);
            g_last_alert_bar = last;
           }
        }

      if(InpEnableLongPair && InpEnableLongAlert && last != g_last_long_alert_bar)
        {
         if(CrossUp(LongFastEMA, LongSlowEMA, last))
           {
            Alert("SM_Crossover_Arrows: GOLDEN EMA "
                  + IntegerToString(InpLongFastPeriod) + "/"
                  + IntegerToString(InpLongSlowPeriod) + " " + _Symbol);
            g_last_long_alert_bar = last;
           }
         else if(CrossDown(LongFastEMA, LongSlowEMA, last))
           {
            Alert("SM_Crossover_Arrows: DEATH EMA "
                  + IntegerToString(InpLongFastPeriod) + "/"
                  + IntegerToString(InpLongSlowPeriod) + " " + _Symbol);
            g_last_long_alert_bar = last;
           }
        }
     }
   return(rates_total);
  }

//+------------------------------------------------------------------+
bool CrossUp(const double &fast[], const double &slow[], int i)
  { return(fast[i] > slow[i] && fast[i - 1] <= slow[i - 1]); }

bool CrossDown(const double &fast[], const double &slow[], int i)
  { return(fast[i] < slow[i] && fast[i - 1] >= slow[i - 1]); }

//+------------------------------------------------------------------+
void CreateArrow(string prefix, int bar_idx, datetime t, double price,
                 bool is_buy, color c)
  {
   string name = StringFormat("%s%d", prefix, bar_idx);
   ENUM_OBJECT type = is_buy ? OBJ_ARROW_BUY : OBJ_ARROW_SELL;
   double offset = SymbolInfoDouble(_Symbol, SYMBOL_POINT) * 30.0;
   double y = is_buy ? (price - offset) : (price + offset);
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, type, 0, t, y);
   ObjectSetInteger(0, name, OBJPROP_TIME,    t);
   ObjectSetDouble (0, name, OBJPROP_PRICE,   y);
   ObjectSetInteger(0, name, OBJPROP_COLOR,   c);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,   2);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN,  true);
  }

//+------------------------------------------------------------------+
void CleanupObjects()
  {
   for(int i = ObjectsTotal(0, 0, -1) - 1; i >= 0; i--)
     {
      string n = ObjectName(0, i, 0, -1);
      if(StringFind(n, InpObjectPrefix) == 0)
         ObjectDelete(0, n);
     }
  }

//+------------------------------------------------------------------+
//|  SM_Crossover_Arrows.mq5                                          |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (v2.00)               |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_Crossover_Arrows.md                                      |
//|                                                                   |
//|  EMA(7)/EMA(13) crossover arrows (operator-tuned 2026-04-28).     |
//|  Bar[1] vs bar[2] cross detection (NEVER bar[0] — Pitfall 5).     |
//|  Two indicator buffers per spec Section 4 (Pitfall 7).             |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_Crossover_Arrows.ex4"
#property version   "2.00"
#property indicator_chart_window
#property indicator_buffers 2  // Pitfall 7: must declare buffer count
#property indicator_plots   2

#property indicator_label1   "EMA Fast"
#property indicator_type1    DRAW_LINE
#property indicator_color1   clrLime
#property indicator_width1   2
#property indicator_label2   "EMA Slow"
#property indicator_type2    DRAW_LINE
#property indicator_color2   clrRed
#property indicator_width2   2

//--- Spec Section 3 inputs (operator-tuned 2026-04-28: EMA 7/13)
input int                InpFastPeriod    = 7;
input int                InpSlowPeriod    = 13;
input ENUM_MA_METHOD     InpMAMethod      = MODE_EMA;
input ENUM_APPLIED_PRICE InpAppliedPrice  = PRICE_CLOSE;
input bool               InpEnableAlert   = true;
input color              InpBuyArrowColor = clrLime;
input color              InpSellArrowColor= clrRed;

const string InpObjectPrefix = "smXarrow_";

//--- Buffers
double FastEMA[];
double SlowEMA[];

//--- Handles (Pattern 2 indicator-handle composition)
int g_handle_fast = INVALID_HANDLE;
int g_handle_slow = INVALID_HANDLE;
int g_last_alert_bar = -1;

//+------------------------------------------------------------------+
int OnInit()
  {
   SetIndexBuffer(0, FastEMA, INDICATOR_DATA);
   SetIndexBuffer(1, SlowEMA, INDICATOR_DATA);
   ArraySetAsSeries(FastEMA, false);
   ArraySetAsSeries(SlowEMA, false);

   g_handle_fast = iMA(_Symbol, PERIOD_CURRENT, InpFastPeriod, 0,
                       InpMAMethod, InpAppliedPrice);
   g_handle_slow = iMA(_Symbol, PERIOD_CURRENT, InpSlowPeriod, 0,
                       InpMAMethod, InpAppliedPrice);
   if(g_handle_fast == INVALID_HANDLE || g_handle_slow == INVALID_HANDLE)
     {
      Print("SM_Crossover_Arrows: iMA handle creation failed");
      return(INIT_FAILED);
     }

   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("SM_Crossover_Arrows(%d/%d)",
                                   InpFastPeriod, InpSlowPeriod));
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   CleanupObjects();
   if(g_handle_fast != INVALID_HANDLE) IndicatorRelease(g_handle_fast);
   if(g_handle_slow != INVALID_HANDLE) IndicatorRelease(g_handle_slow);
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tv[],
                const long &v[], const int &sp[])
  {
   if(rates_total < InpSlowPeriod + 2)
      return(0);  // not enough bars yet

   // Fill buffers from MQ5 iMA handles.
   int copied_fast = CopyBuffer(g_handle_fast, 0, 0, rates_total, FastEMA);
   int copied_slow = CopyBuffer(g_handle_slow, 0, 0, rates_total, SlowEMA);
   if(copied_fast < rates_total || copied_slow < rates_total)
      return(prev_calculated);

   // Iterate from prev_calculated - 1 (re-check the last bar that was
   // partial last call — Pitfall 5 / proper restart pattern).
   int start = (prev_calculated > 0) ? prev_calculated - 1 : InpSlowPeriod + 1;
   if(start < 2) start = 2;

   for(int i = start; i < rates_total - 1; i++)
     {
      // Cross detected on bar i using bar i vs bar i-1 transition.
      // Arrows placed at bar i (closed bar). Bar (rates_total-1) is the
      // current incomplete bar — we only finalize on bar rates_total-2.
      bool bull = FastEMA[i] > SlowEMA[i] && FastEMA[i - 1] <= SlowEMA[i - 1];
      bool bear = FastEMA[i] < SlowEMA[i] && FastEMA[i - 1] >= SlowEMA[i - 1];

      if(bull)
         CreateArrow(i, time[i], low[i],  true);
      else if(bear)
         CreateArrow(i, time[i], high[i], false);
     }

   // Alert on the most recent confirmed cross (bar rates_total - 2).
   if(InpEnableAlert && rates_total >= 3)
     {
      int last = rates_total - 2;
      if(last != g_last_alert_bar)
        {
         bool bull = FastEMA[last] > SlowEMA[last]
                     && FastEMA[last - 1] <= SlowEMA[last - 1];
         bool bear = FastEMA[last] < SlowEMA[last]
                     && FastEMA[last - 1] >= SlowEMA[last - 1];
         if(bull)
           {
            Alert("SM_Crossover_Arrows: BUY EMA "
                  + IntegerToString(InpFastPeriod) + "/"
                  + IntegerToString(InpSlowPeriod) + " " + _Symbol);
            g_last_alert_bar = last;
           }
         else if(bear)
           {
            Alert("SM_Crossover_Arrows: SELL EMA "
                  + IntegerToString(InpFastPeriod) + "/"
                  + IntegerToString(InpSlowPeriod) + " " + _Symbol);
            g_last_alert_bar = last;
           }
        }
     }

   return(rates_total);
  }

//+------------------------------------------------------------------+
void CreateArrow(int bar_idx, datetime t, double price, bool is_buy)
  {
   string name = StringFormat("%s%d", InpObjectPrefix, bar_idx);
   ENUM_OBJECT type = is_buy ? OBJ_ARROW_BUY : OBJ_ARROW_SELL;
   double offset = SymbolInfoDouble(_Symbol, SYMBOL_POINT) * 30.0;
   double y = is_buy ? (price - offset) : (price + offset);
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, type, 0, t, y);
   ObjectSetInteger(0, name, OBJPROP_TIME,    t);
   ObjectSetDouble (0, name, OBJPROP_PRICE,   y);
   ObjectSetInteger(0, name, OBJPROP_COLOR,
                    is_buy ? InpBuyArrowColor : InpSellArrowColor);
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

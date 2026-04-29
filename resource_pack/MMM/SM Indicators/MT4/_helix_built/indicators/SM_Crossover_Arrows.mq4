//+------------------------------------------------------------------+
//|  SM_Crossover_Arrows.mq4                                          |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (MQ4 idiomatic / D-20)|
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_Crossover_Arrows.md                                      |
//|                                                                   |
//|  EMA(5)/EMA(13) crossover arrows. Bar[1] vs bar[2] cross detection|
//|  (NEVER bar[0] — Pitfall 5 repaint guard).                        |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_Crossover_Arrows.ex4"
#property version   "2.00"
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_color1  clrLime
#property indicator_color2  clrRed
#property indicator_width1  2
#property indicator_width2  2
#property strict

extern int    InpFastPeriod    = 7;   // v2.00 operator-tuned 2026-04-28
extern int    InpSlowPeriod    = 13;
extern int    InpMAMethod      = MODE_EMA;
extern int    InpAppliedPrice  = PRICE_CLOSE;
extern bool   InpEnableAlert   = true;
extern color  InpBuyArrowColor = clrLime;
extern color  InpSellArrowColor= clrRed;

double FastBuf[];
double SlowBuf[];

string ObjectPrefix = "smXarrow_";
int g_last_alert_bar = -1;

//+------------------------------------------------------------------+
int init()
  {
   SetIndexBuffer(0, FastBuf);
   SetIndexBuffer(1, SlowBuf);
   SetIndexStyle(0, DRAW_LINE, STYLE_SOLID, 2);   // v2.00 width 2
   SetIndexStyle(1, DRAW_LINE, STYLE_SOLID, 2);
   IndicatorShortName("SM_Crossover_Arrows("
                      + IntegerToString(InpFastPeriod) + "/"
                      + IntegerToString(InpSlowPeriod) + ")");
   return(0);
  }

//+------------------------------------------------------------------+
int deinit()
  {
   CleanupObjects();
   return(0);
  }

//+------------------------------------------------------------------+
int start()
  {
   int rates_total  = Bars;
   int prev_counted = IndicatorCounted();
   if(rates_total < InpSlowPeriod + 2)
      return(0);

   int limit = rates_total - prev_counted;
   if(prev_counted > 0)
      limit++;

   // MQL4 series-indexed arrays (bar 0 = latest). MQL4 iMA returns double directly.
   for(int i = limit - 1; i >= 0; i--)
     {
      FastBuf[i] = iMA(_Symbol, 0, InpFastPeriod, 0, InpMAMethod, InpAppliedPrice, i);
      SlowBuf[i] = iMA(_Symbol, 0, InpSlowPeriod, 0, InpMAMethod, InpAppliedPrice, i);
     }

   // MQL4 series indexing: bar 0 = current incomplete, bar 1 = last completed.
   // Cross at bar i vs bar i+1 (one bar older).
   for(int i = limit - 2; i >= 1; i--)
     {
      bool bull = FastBuf[i] > SlowBuf[i] && FastBuf[i + 1] <= SlowBuf[i + 1];
      bool bear = FastBuf[i] < SlowBuf[i] && FastBuf[i + 1] >= SlowBuf[i + 1];

      if(bull)
         CreateArrow(i, Time[i], Low[i],  true);
      else if(bear)
         CreateArrow(i, Time[i], High[i], false);
     }

   // Alert on the most recent confirmed cross (bar 1 — last completed).
   if(InpEnableAlert)
     {
      bool bull1 = FastBuf[1] > SlowBuf[1] && FastBuf[2] <= SlowBuf[2];
      bool bear1 = FastBuf[1] < SlowBuf[1] && FastBuf[2] >= SlowBuf[2];
      if((bull1 || bear1) && Bars != g_last_alert_bar)
        {
         g_last_alert_bar = Bars;
         Alert("SM_Crossover_Arrows: " + (bull1 ? "BUY" : "SELL")
               + " EMA " + IntegerToString(InpFastPeriod) + "/"
               + IntegerToString(InpSlowPeriod) + " " + _Symbol);
        }
     }

   return(0);
  }

//+------------------------------------------------------------------+
void CreateArrow(int bar_idx, datetime t, double price, bool is_buy)
  {
   string name = ObjectPrefix + IntegerToString(bar_idx) + "_" + IntegerToString((int)t);
   int type = is_buy ? OBJ_ARROW_BUY : OBJ_ARROW_SELL;
   double offset = _Point * 30.0;
   double y = is_buy ? (price - offset) : (price + offset);
   if(ObjectFind(name) < 0)
      ObjectCreate(name, type, 0, t, y);
   ObjectSet(name, OBJPROP_TIME1,  t);
   ObjectSet(name, OBJPROP_PRICE1, y);
   ObjectSet(name, OBJPROP_COLOR,
             is_buy ? InpBuyArrowColor : InpSellArrowColor);
   ObjectSet(name, OBJPROP_WIDTH, 2);
  }

//+------------------------------------------------------------------+
void CleanupObjects()
  {
   for(int i = ObjectsTotal() - 1; i >= 0; i--)
     {
      string n = ObjectName(i);
      if(StringFind(n, ObjectPrefix) == 0)
         ObjectDelete(n);
     }
  }

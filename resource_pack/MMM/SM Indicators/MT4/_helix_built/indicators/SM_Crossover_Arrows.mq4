//+------------------------------------------------------------------+
//|  SM_Crossover_Arrows.mq4                                          |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (MQ4 idiomatic / D-20)|
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_Crossover_Arrows.md                                      |
//|                                                                   |
//|  Two independent EMA crossover systems:                            |
//|                                                                    |
//|  Short-term pair (default 7/13 — operator-tuned 2026-04-28):       |
//|     EMA(InpFastPeriod)  Lime  — fast line                          |
//|     EMA(InpSlowPeriod)  Red   — slow line                          |
//|     Arrows prefixed "smXarrow_S_"                                  |
//|                                                                    |
//|  Long-term pair (default 50/200 — golden/death cross, v2.10):      |
//|     EMA(InpLongFastPeriod)  Aqua  — fast line                      |
//|     EMA(InpLongSlowPeriod)  White — slow line                      |
//|     Arrows prefixed "smXarrow_L_"                                  |
//|                                                                    |
//|  Cross detection: bar[i] vs bar[i+1] (MQL4 series-indexing;        |
//|  NEVER bar[0] — Pitfall 5 repaint guard).                          |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_Crossover_Arrows.ex4"
#property version   "2.10"
#property indicator_chart_window
#property indicator_buffers 4
#property indicator_color1  clrLime
#property indicator_color2  clrRed
#property indicator_color3  clrAqua
#property indicator_color4  clrWhite
#property indicator_width1  2
#property indicator_width2  2
#property indicator_width3  2
#property indicator_width4  2
#property strict

//--- Short-term pair (v2.00 operator-tuned 2026-04-28)
extern int    InpFastPeriod        = 7;
extern int    InpSlowPeriod        = 13;
extern bool   InpEnableAlert       = true;
extern color  InpBuyArrowColor     = clrLime;
extern color  InpSellArrowColor    = clrRed;

//--- Long-term pair (v2.10 — golden/death cross)
extern bool   InpEnableLongCross   = true;
extern int    InpLongFastPeriod    = 50;
extern int    InpLongSlowPeriod    = 200;
extern color  InpLongBuyColor      = clrAqua;
extern color  InpLongSellColor     = clrWhite;

extern int    InpMAMethod          = MODE_EMA;
extern int    InpAppliedPrice      = PRICE_CLOSE;

//--- Short-term EMA buffers
double FastBuf[];
double SlowBuf[];

//--- Long-term EMA buffers
double LongFastBuf[];
double LongSlowBuf[];

string ObjectPrefixShort = "smXarrow_S_";
string ObjectPrefixLong  = "smXarrow_L_";
string ObjectPrefixAll   = "smXarrow_";

int g_last_alert_bar      = -1;
int g_last_long_alert_bar = -1;

//+------------------------------------------------------------------+
int init()
  {
   SetIndexBuffer(0, FastBuf);
   SetIndexBuffer(1, SlowBuf);
   SetIndexBuffer(2, LongFastBuf);
   SetIndexBuffer(3, LongSlowBuf);
   SetIndexStyle(0, DRAW_LINE, STYLE_SOLID, 2);
   SetIndexStyle(1, DRAW_LINE, STYLE_SOLID, 2);
   SetIndexStyle(2, DRAW_LINE, STYLE_SOLID, 2);
   SetIndexStyle(3, DRAW_LINE, STYLE_SOLID, 2);
   IndicatorShortName("SM_Crossover_Arrows("
                      + IntegerToString(InpFastPeriod) + "/"
                      + IntegerToString(InpSlowPeriod) + ", "
                      + IntegerToString(InpLongFastPeriod) + "/"
                      + IntegerToString(InpLongSlowPeriod) + ")");
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

   int min_required = InpSlowPeriod;
   if(InpEnableLongCross && InpLongSlowPeriod > min_required)
      min_required = InpLongSlowPeriod;
   if(rates_total < min_required + 2)
      return(0);

   int limit = rates_total - prev_counted;
   if(prev_counted > 0)
      limit++;

   // MQL4 series-indexed arrays (bar 0 = latest). iMA returns double directly.
   for(int i = limit - 1; i >= 0; i--)
     {
      FastBuf[i] = iMA(_Symbol, 0, InpFastPeriod, 0, InpMAMethod, InpAppliedPrice, i);
      SlowBuf[i] = iMA(_Symbol, 0, InpSlowPeriod, 0, InpMAMethod, InpAppliedPrice, i);
      if(InpEnableLongCross)
        {
         LongFastBuf[i] = iMA(_Symbol, 0, InpLongFastPeriod, 0, InpMAMethod, InpAppliedPrice, i);
         LongSlowBuf[i] = iMA(_Symbol, 0, InpLongSlowPeriod, 0, InpMAMethod, InpAppliedPrice, i);
        }
     }

   // MQL4 series indexing: bar 0 = current incomplete, bar 1 = last completed.
   // Cross at bar i vs bar i+1 (one bar older). Stop at i=1 (never bar 0).
   for(int i = limit - 2; i >= 1; i--)
     {
      // Short-term pair
      bool bull = FastBuf[i] > SlowBuf[i] && FastBuf[i + 1] <= SlowBuf[i + 1];
      bool bear = FastBuf[i] < SlowBuf[i] && FastBuf[i + 1] >= SlowBuf[i + 1];

      if(bull)
         CreateArrow(ObjectPrefixShort, i, Time[i], Low[i],  true,
                     InpBuyArrowColor);
      else if(bear)
         CreateArrow(ObjectPrefixShort, i, Time[i], High[i], false,
                     InpSellArrowColor);

      // Long-term pair (independent)
      if(InpEnableLongCross)
        {
         bool lbull = LongFastBuf[i] > LongSlowBuf[i] && LongFastBuf[i + 1] <= LongSlowBuf[i + 1];
         bool lbear = LongFastBuf[i] < LongSlowBuf[i] && LongFastBuf[i + 1] >= LongSlowBuf[i + 1];

         if(lbull)
            CreateArrow(ObjectPrefixLong, i, Time[i], Low[i],  true,
                        InpLongBuyColor);
         else if(lbear)
            CreateArrow(ObjectPrefixLong, i, Time[i], High[i], false,
                        InpLongSellColor);
        }
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

   if(InpEnableLongCross && rates_total >= 3)
     {
      bool lbull1 = LongFastBuf[1] > LongSlowBuf[1] && LongFastBuf[2] <= LongSlowBuf[2];
      bool lbear1 = LongFastBuf[1] < LongSlowBuf[1] && LongFastBuf[2] >= LongSlowBuf[2];
      if((lbull1 || lbear1) && Bars != g_last_long_alert_bar)
        {
         g_last_long_alert_bar = Bars;
         Alert("SM_Crossover_Arrows: " + (lbull1 ? "GOLDEN" : "DEATH")
               + " EMA " + IntegerToString(InpLongFastPeriod) + "/"
               + IntegerToString(InpLongSlowPeriod) + " " + _Symbol);
        }
     }

   return(0);
  }

//+------------------------------------------------------------------+
void CreateArrow(string prefix, int bar_idx, datetime t, double price,
                 bool is_buy, color c)
  {
   string name = prefix + IntegerToString(bar_idx) + "_" + IntegerToString((int)t);
   int type = is_buy ? OBJ_ARROW_BUY : OBJ_ARROW_SELL;
   double offset = _Point * 30.0;
   double y = is_buy ? (price - offset) : (price + offset);
   if(ObjectFind(name) < 0)
      ObjectCreate(name, type, 0, t, y);
   ObjectSet(name, OBJPROP_TIME1,  t);
   ObjectSet(name, OBJPROP_PRICE1, y);
   ObjectSet(name, OBJPROP_COLOR,  c);
   ObjectSet(name, OBJPROP_WIDTH,  2);
  }

//+------------------------------------------------------------------+
void CleanupObjects()
  {
   for(int i = ObjectsTotal() - 1; i >= 0; i--)
     {
      string n = ObjectName(i);
      if(StringFind(n, ObjectPrefixAll) == 0)
         ObjectDelete(n);
     }
  }

//+------------------------------------------------------------------+
//|  SM_IlsleyPsychLevels.mq4                                         |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (MQ4 idiomatic / D-20)|
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_IlsleyPsychLevels.md                                     |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_IlsleyPsychLevels.ex4"
#property version   "1.00"
#property indicator_chart_window
#property strict

extern int    InpStepPips     = 50;
extern int    InpMajorPips    = 100;
extern int    InpLevelsAbove  = 5;
extern int    InpLevelsBelow  = 5;
extern color  InpMinorColor   = clrDimGray;
extern color  InpMajorColor   = clrDarkGray;
extern int    InpLineStyle    = STYLE_DOT;
extern int    InpLineWidth    = 1;
extern bool   InpShowLabel    = true;

string ObjectPrefix = "smPsych_";
double g_pip = 0.0;
datetime g_last_d1_bar = 0;

//+------------------------------------------------------------------+
int init()
  {
   int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
   g_pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;
   IndicatorShortName("SM_IlsleyPsychLevels(" + IntegerToString(InpStepPips)
                      + "/" + IntegerToString(InpMajorPips) + ")");
   Recompute();
   EventSetTimer(60);
   return(0);
  }

//+------------------------------------------------------------------+
int deinit()
  {
   CleanupObjects();
   EventKillTimer();
   return(0);
  }

//+------------------------------------------------------------------+
int start()
  {
   datetime cur_d1 = iTime(_Symbol, PERIOD_D1, 0);
   if(cur_d1 != g_last_d1_bar)
     {
      Recompute();
      g_last_d1_bar = cur_d1;
     }
   return(0);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
  }

//+------------------------------------------------------------------+
void Recompute()
  {
   if(g_pip <= 0.0)
      return;
   double bid = MarketInfo(_Symbol, MODE_BID);
   if(bid <= 0.0)
      return;

   double step  = InpStepPips  * g_pip;
   double major = InpMajorPips * g_pip;
   double base  = MathFloor(bid / step) * step;

   for(int i = -InpLevelsBelow; i <= InpLevelsAbove; i++)
     {
      double level = base + i * step;
      bool is_major = (MathAbs(level - MathRound(level / major) * major) < step * 0.01);

      string suffix = "L_" + IntegerToString(i + InpLevelsBelow);
      string name   = ObjectPrefix + suffix;
      DrawHLine(name, level,
                is_major ? InpMajorColor : InpMinorColor,
                is_major ? (InpLineWidth + 1) : InpLineWidth);

      if(InpShowLabel)
        {
         string label_name = ObjectPrefix + "lbl_" + suffix;
         DrawLabel(label_name, level,
                   is_major ? InpMajorColor : InpMinorColor);
        }
     }
  }

//+------------------------------------------------------------------+
void DrawHLine(string name, double price, color c, int width)
  {
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_HLINE, 0, 0, price);
   ObjectSet(name, OBJPROP_PRICE1, price);
   ObjectSet(name, OBJPROP_COLOR,  c);
   ObjectSet(name, OBJPROP_STYLE,  InpLineStyle);
   ObjectSet(name, OBJPROP_WIDTH,  width);
   ObjectSet(name, OBJPROP_BACK,   true);
  }

//+------------------------------------------------------------------+
void DrawLabel(string name, double price, color c)
  {
   datetime label_time = iTime(_Symbol, _Period, 0);
   int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
   string text = DoubleToStr(price, digits);
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_TEXT, 0, label_time, price);
   ObjectSetText(name, text, 8, "Arial", c);
   ObjectSet(name, OBJPROP_TIME1,  label_time);
   ObjectSet(name, OBJPROP_PRICE1, price);
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

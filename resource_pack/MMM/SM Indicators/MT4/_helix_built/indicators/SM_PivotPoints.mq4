//+------------------------------------------------------------------+
//|  SM_PivotPoints.mq4                                              |
//|  Phase 12 Plan 03 — SM Indicators Implementation                 |
//|                                                                  |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/          |
//|        SM_PivotPoints.md                                         |
//|  Primary reference: MMM Book pp. 42-43 (M1-M4 mid-pivot defs)   |
//|  D-20: MQL4 idioms — iHigh/iLow/iClose return double directly    |
//|                                                                  |
//|  Standard floor pivots (PP, R1-R3, S1-S3) + MMM Book M1-M4.     |
//|  Draws OBJ_HLINE objects — no indicator buffers.                 |
//|                                                                  |
//|  Pitfall 5 guard: reads prior bar with shift=1                   |
//+------------------------------------------------------------------+
#property copyright   "Bandd Analytics — Phase 12 SM Indicators reconstruction"
#property link        "https://github.com/banddanalytics/helix"
#property version     "1.00"
#property description "SM_PivotPoints — daily floor pivots + MMM M1-M4 mid-pivots"

#property indicator_chart_window
#property indicator_buffers 0

//--- Inputs
extern bool   ShowMidPivots  = true;         // Show MMM M1-M4 mid-pivots
extern bool   ShowWeekly     = false;        // [INFER] Show weekly pivots
extern color  PPColor        = Yellow;       // PP line color
extern color  ResistColor    = Red;          // R1-R3 line color
extern color  SupportColor   = Lime;         // S1-S3 line color
extern color  MidColor       = Cyan;         // M1-M4 mid-pivot color
extern int    LineWidth       = 1;           // [INFER] line width
extern string ObjectPrefix   = "smPVT_";    // Object name prefix

//+------------------------------------------------------------------+
//| Create or update a single OBJ_HLINE pivot level                  |
//+------------------------------------------------------------------+
void DrawLevel(string name, double price, color clr, int style, int width, string label)
  {
   if(ObjectFind(name) < 0)
     {
      ObjectCreate(name, OBJ_HLINE, 0, 0, price);
      ObjectSetString(0, name, OBJPROP_TEXT, label);
     }
   ObjectSet(name, OBJPROP_PRICE1, price);
   ObjectSet(name, OBJPROP_COLOR,  clr);
   ObjectSet(name, OBJPROP_STYLE,  style);
   ObjectSet(name, OBJPROP_WIDTH,  width);
   ObjectSet(name, OBJPROP_BACK,   true);
  }

//+------------------------------------------------------------------+
//| Delete all pivot objects with our prefix                         |
//+------------------------------------------------------------------+
void CleanupObjects()
  {
   string levels[] = {"PP","R1","R2","R3","S1","S2","S3","M1","M2","M3","M4"};
   for(int i = 0; i < ArraySize(levels); i++)
     {
      string name = ObjectPrefix + levels[i];
      if(ObjectFind(name) >= 0)
         ObjectDelete(name);
     }
  }

//+------------------------------------------------------------------+
//| Compute and draw all pivot levels                                 |
//+------------------------------------------------------------------+
void Recompute()
  {
//--- Read prior completed daily bar (shift=1 — Pitfall 5 guard; MQL4 idiom: returns double directly)
   double prior_high  = iHigh(_Symbol, PERIOD_D1, 1);
   double prior_low   = iLow(_Symbol, PERIOD_D1, 1);
   double prior_close = iClose(_Symbol, PERIOD_D1, 1);

   if(prior_high <= 0.0 || prior_low <= 0.0 || prior_close <= 0.0)
      return;

   double pp = (prior_high + prior_low + prior_close) / 3.0;
   double r1 = 2.0 * pp - prior_low;
   double s1 = 2.0 * pp - prior_high;
   double r2 = pp + (prior_high - prior_low);
   double s2 = pp - (prior_high - prior_low);
   double r3 = prior_high + 2.0 * (pp - prior_low);
   double s3 = prior_low  - 2.0 * (prior_high - pp);

//--- Draw standard levels
   DrawLevel(ObjectPrefix+"PP", pp, PPColor,      STYLE_SOLID, LineWidth, "PP");
   DrawLevel(ObjectPrefix+"R1", r1, ResistColor,  STYLE_SOLID, LineWidth, "R1");
   DrawLevel(ObjectPrefix+"R2", r2, ResistColor,  STYLE_SOLID, LineWidth, "R2");
   DrawLevel(ObjectPrefix+"R3", r3, ResistColor,  STYLE_SOLID, LineWidth, "R3");
   DrawLevel(ObjectPrefix+"S1", s1, SupportColor, STYLE_SOLID, LineWidth, "S1");
   DrawLevel(ObjectPrefix+"S2", s2, SupportColor, STYLE_SOLID, LineWidth, "S2");
   DrawLevel(ObjectPrefix+"S3", s3, SupportColor, STYLE_SOLID, LineWidth, "S3");

//--- Draw MMM M1-M4 mid-pivots per MMM Book pp. 42-43
   if(ShowMidPivots)
     {
      double m1 = (s2 + s1) / 2.0;
      double m2 = (s1 + pp) / 2.0;
      double m3 = (pp + r1) / 2.0;
      double m4 = (r1 + r2) / 2.0;
      DrawLevel(ObjectPrefix+"M1", m1, MidColor, STYLE_DOT, LineWidth, "M1");
      DrawLevel(ObjectPrefix+"M2", m2, MidColor, STYLE_DOT, LineWidth, "M2");
      DrawLevel(ObjectPrefix+"M3", m3, MidColor, STYLE_DOT, LineWidth, "M3");
      DrawLevel(ObjectPrefix+"M4", m4, MidColor, STYLE_DOT, LineWidth, "M4");
     }

   WindowRedraw();
  }

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int init()
  {
   IndicatorShortName("SM_PivotPoints");
   Recompute();
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
int deinit()
  {
   CleanupObjects();
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

//+------------------------------------------------------------------+
//|  SM_PivotPoints.mq5                                              |
//|  Phase 12 Plan 03 — SM Indicators Implementation                 |
//|                                                                  |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/          |
//|        SM_PivotPoints.md                                         |
//|  Primary reference: MMM Book pp. 42-43 (M1-M4 mid-pivot defs)   |
//|  D-08: Wine MetaEditor compile target                            |
//|  D-09: indicator_chart_window (main window)                      |
//|                                                                  |
//|  Standard floor pivots (PP, R1-R3, S1-S3) + MMM Book M1-M4.     |
//|  Draws OBJ_HLINE objects — no indicator buffers.                 |
//|  Pivot recalculated on each new D1 bar + timer tick.             |
//|                                                                  |
//|  Pitfall 5 guard: reads iHigh/iLow/iClose with shift=1          |
//|  (prior completed daily bar) to prevent lookahead.               |
//+------------------------------------------------------------------+
#property copyright   "Bandd Analytics — Phase 12 SM Indicators reconstruction"
#property link        "https://github.com/banddanalytics/helix"
#property version     "1.00"
#property description "SM_PivotPoints — daily floor pivots + MMM M1-M4 mid-pivots"

#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Inputs (spec Section 3 — [INFER] cosmetic parameters)
input ENUM_TIMEFRAMES InpPivotTimeframe       = PERIOD_D1;   // Pivot source timeframe
input bool            InpShowMidPivots        = true;         // Show MMM M1-M4 mid-pivots (MMM Book pp. 42-43)
input bool            InpShowWeekly           = false;        // [INFER] Show weekly pivots
input color           InpPPColor              = clrYellow;    // PP line color
input color           InpResistanceColor      = clrRed;       // R1-R3 line color
input color           InpSupportColor         = clrLime;      // S1-S3 line color
input color           InpMidColor             = clrCyan;      // M1-M4 mid-pivot color
input ENUM_LINE_STYLE InpLineStyle            = STYLE_SOLID;  // [INFER] line style for PP/R/S
input ENUM_LINE_STYLE InpMidLineStyle         = STYLE_DOT;    // [INFER] dotted for M1-M4
input int             InpLineWidth            = 1;            // [INFER] line width
input string          InpObjectPrefix         = "smPVT_";     // Object name prefix

//--- Private state
static datetime g_last_d1_time = 0;

//+------------------------------------------------------------------+
//| Compute and draw all pivot levels                                 |
//+------------------------------------------------------------------+
void Recompute()
  {
//--- Read prior completed daily bar (shift=1 — Pitfall 5 guard)
   double prior_high  = iHigh(_Symbol, PERIOD_D1, 1);
   double prior_low   = iLow(_Symbol, PERIOD_D1, 1);
   double prior_close = iClose(_Symbol, PERIOD_D1, 1);

   if(prior_high <= 0.0 || prior_low <= 0.0 || prior_close <= 0.0)
      return; // data not yet loaded

   double pp = (prior_high + prior_low + prior_close) / 3.0;
   double r1 = 2.0 * pp - prior_low;
   double s1 = 2.0 * pp - prior_high;
   double r2 = pp + (prior_high - prior_low);
   double s2 = pp - (prior_high - prior_low);
   double r3 = prior_high + 2.0 * (pp - prior_low);
   double s3 = prior_low  - 2.0 * (prior_high - pp);

//--- Draw standard levels
   DrawLevel(InpObjectPrefix + "PP", pp, InpPPColor,       InpLineStyle,    InpLineWidth, "PP");
   DrawLevel(InpObjectPrefix + "R1", r1, InpResistanceColor, InpLineStyle,  InpLineWidth, "R1");
   DrawLevel(InpObjectPrefix + "R2", r2, InpResistanceColor, InpLineStyle,  InpLineWidth, "R2");
   DrawLevel(InpObjectPrefix + "R3", r3, InpResistanceColor, InpLineStyle,  InpLineWidth, "R3");
   DrawLevel(InpObjectPrefix + "S1", s1, InpSupportColor,    InpLineStyle,  InpLineWidth, "S1");
   DrawLevel(InpObjectPrefix + "S2", s2, InpSupportColor,    InpLineStyle,  InpLineWidth, "S2");
   DrawLevel(InpObjectPrefix + "S3", s3, InpSupportColor,    InpLineStyle,  InpLineWidth, "S3");

//--- Draw MMM M1-M4 mid-pivots per MMM Book pp. 42-43
   if(InpShowMidPivots)
     {
      double m1 = (s2 + s1) / 2.0;
      double m2 = (s1 + pp) / 2.0;
      double m3 = (pp + r1) / 2.0;
      double m4 = (r1 + r2) / 2.0;
      DrawLevel(InpObjectPrefix + "M1", m1, InpMidColor, InpMidLineStyle, InpLineWidth, "M1");
      DrawLevel(InpObjectPrefix + "M2", m2, InpMidColor, InpMidLineStyle, InpLineWidth, "M2");
      DrawLevel(InpObjectPrefix + "M3", m3, InpMidColor, InpMidLineStyle, InpLineWidth, "M3");
      DrawLevel(InpObjectPrefix + "M4", m4, InpMidColor, InpMidLineStyle, InpLineWidth, "M4");
     }

   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Create or update a single OBJ_HLINE pivot level                  |
//+------------------------------------------------------------------+
void DrawLevel(const string name,
               const double price,
               const color  clr,
               const ENUM_LINE_STYLE style,
               const int    width,
               const string label)
  {
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
      ObjectSetString(0, name, OBJPROP_TEXT, label);
     }
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,     clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE,     style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,     width);
   ObjectSetInteger(0, name, OBJPROP_BACK,      true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE,false);
  }

//+------------------------------------------------------------------+
//| Delete all pivot objects with our prefix                         |
//+------------------------------------------------------------------+
void CleanupObjects()
  {
   string levels[] = {"PP","R1","R2","R3","S1","S2","S3","M1","M2","M3","M4"};
   for(int i = 0; i < ArraySize(levels); i++)
     {
      string name = InpObjectPrefix + levels[i];
      if(ObjectFind(0, name) >= 0)
         ObjectDelete(0, name);
     }
  }

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   IndicatorSetString(INDICATOR_SHORTNAME, "SM_PivotPoints");
   Recompute();
   EventSetTimer(60); // refresh every minute
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
//--- Recompute on each new D1 bar
   datetime cur_d1_time = iTime(_Symbol, PERIOD_D1, 0);
   if(cur_d1_time != g_last_d1_time)
     {
      g_last_d1_time = cur_d1_time;
      Recompute();
     }
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

//+------------------------------------------------------------------+
//|  sm_gmtoffset.mq5                                                 |
//|  Phase 12 Plan 01 — Tier 0 helper                                 |
//|  Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md|
//|                                                                   |
//|  Detects the broker's effective GMT offset in integer hours and   |
//|  publishes it as a MetaTrader GlobalVariable (default name        |
//|  "sm_GMTOffset") for consumption by sm_WorkTime, SM_PivotPoints,  |
//|  SM_NewHUD, and other session-aware indicators.                   |
//|                                                                   |
//|  CONTEXT D-06 (output path) / D-19 (MQ5 idiomatic).               |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !sm_gmtoffset.ex4"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Spec Section 3 inputs
input bool   InpAutoDetect    = true;          // Auto-detect via TimeCurrent-TimeGMT
input int    InpManualGMT     = 0;             // Fallback offset when AutoDetect=false
input bool   InpDSTAdjust     = true;          // Strip broker DST from raw delta
input string InpGlobalVarName = "sm_GMTOffset"; // GlobalVariable name (downstream contract)
input bool   InpShowLabel     = true;           // Draw persistent corner label
input color  InpLabelColor    = clrLightGreen;  // Label text color
input int    InpLabelFontSize = 11;
input ENUM_BASE_CORNER InpLabelCorner = CORNER_RIGHT_UPPER; // Label anchor corner
input int    InpLabelXOffset  = 8;
input int    InpLabelYOffset  = 22;

//--- Module state
int g_offset_hours = 0;
string g_label_name = "";

//+------------------------------------------------------------------+
int ComputeOffset()
  {
   if(!InpAutoDetect)
      return((int)InpManualGMT);

   //--- delta_seconds = TimeCurrent() - TimeGMT()  (spec Section 5 step 1b)
   long delta = (long)TimeCurrent() - (long)TimeGMT();
   int  raw   = (int)MathRound(delta / 3600.0);

   if(InpDSTAdjust)
     {
      MqlDateTime now;
      TimeGMT(now);
      // Spec Section 5 step 1e + Pseudocode broker_appears_dst_shifted():
      // rough Northern Hemisphere DST window (March..October) — strip 1 h
      // when broker has already applied DST so downstream indicators
      // anchor sessions to "standard winter" GMT.
      if(now.mon >= 3 && now.mon <= 10)
         raw = raw - 1;
     }
   return(raw);
  }

//+------------------------------------------------------------------+
void DrawLabel()
  {
   if(!InpShowLabel) return;
   string sign = (g_offset_hours >= 0) ? "+" : "";
   string text = StringFormat("sm_GMTOffset: %s%d h", sign, g_offset_hours);

   if(ObjectFind(0, g_label_name) < 0)
      ObjectCreate(0, g_label_name, OBJ_LABEL, 0, 0, 0);

   ObjectSetString (0, g_label_name, OBJPROP_TEXT,         text);
   ObjectSetInteger(0, g_label_name, OBJPROP_CORNER,       InpLabelCorner);
   ObjectSetInteger(0, g_label_name, OBJPROP_XDISTANCE,    InpLabelXOffset);
   ObjectSetInteger(0, g_label_name, OBJPROP_YDISTANCE,    InpLabelYOffset);
   ObjectSetInteger(0, g_label_name, OBJPROP_COLOR,        InpLabelColor);
   ObjectSetInteger(0, g_label_name, OBJPROP_FONTSIZE,     InpLabelFontSize);
   ObjectSetString (0, g_label_name, OBJPROP_FONT,         "Arial");
   ObjectSetInteger(0, g_label_name, OBJPROP_ANCHOR,
                    (InpLabelCorner == CORNER_RIGHT_UPPER || InpLabelCorner == CORNER_RIGHT_LOWER)
                       ? ANCHOR_RIGHT_UPPER : ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0, g_label_name, OBJPROP_BACK,         false);
   ObjectSetInteger(0, g_label_name, OBJPROP_HIDDEN,       true);
   ObjectSetInteger(0, g_label_name, OBJPROP_SELECTABLE,   false);
   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
void Publish()
  {
   g_offset_hours = ComputeOffset();
   GlobalVariableSet(InpGlobalVarName, (double)g_offset_hours);
   Comment("GMT Offset detected: ", IntegerToString(g_offset_hours));
   DrawLabel();
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   g_label_name = "smGMT_" + IntegerToString(ChartID());
   Publish();
   //--- Hourly refresh per spec Section 5 step 3 (cleaner MQ5 idiom — see
   //--- Section 11 MQ4→MQ5 deltas)
   EventSetTimer(3600);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Publish();
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
   if(StringLen(g_label_name) > 0 && ObjectFind(0, g_label_name) >= 0)
      ObjectDelete(0, g_label_name);
   ChartRedraw(0);
   //--- Spec Section 5 step 4: deliberately do NOT delete the GlobalVariable
   //--- — downstream indicators rely on the cached offset surviving sm_gmtoffset
   //--- chart removal.
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long   &tick_volume[],
                const long   &volume[],
                const int    &spread[])
  {
   //--- D-19 full MQ5 OnCalculate signature; no per-bar work for this
   //--- utility — the periodic refresh runs from OnTimer.
   return(rates_total);
  }
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|  sm_gmtoffset.mq4                                                 |
//|  Phase 12 Plan 01 — Tier 0 helper (MQ4 reconstruction, D-20)      |
//|  Spec: resource_pack/MMM/SM Indicators/docs/helpers/sm_gmtoffset.md|
//|                                                                   |
//|  MQL4 idiomatic port. Detects broker GMT offset, publishes via    |
//|  GlobalVariable "sm_GMTOffset", and renders a persistent corner   |
//|  label (v2.00 — Comment() alone gets buried by other indicators). |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !sm_gmtoffset.ex4"
#property version   "2.00"
#property indicator_chart_window

//--- Spec Section 3 inputs
input bool   InpAutoDetect    = true;
input int    InpManualGMT     = 0;
input bool   InpDSTAdjust     = true;
input string InpGlobalVarName = "sm_GMTOffset";

//--- v2.00 corner label
input bool   InpShowLabel     = true;
input color  InpLabelColor    = clrLightGreen;
input int    InpLabelFontSize = 11;
input int    InpLabelCorner   = 1;   // 0=LU 1=RU 2=LL 3=RL
input int    InpLabelXOffset  = 8;
input int    InpLabelYOffset  = 22;

//--- Module state
int    g_offset_hours = 0;
string g_label_name   = "";

//+------------------------------------------------------------------+
int ComputeOffset()
  {
   if(!InpAutoDetect)
      return((int)InpManualGMT);

   int delta = (int)(TimeCurrent() - TimeGMT());
   int raw   = (int)MathRound(delta / 3600.0);

   if(InpDSTAdjust)
     {
      int mon = TimeMonth(TimeGMT());
      if(mon >= 3 && mon <= 10)
         raw = raw - 1;
     }
   return(raw);
  }

//+------------------------------------------------------------------+
void DrawLabel()
  {
   if(!InpShowLabel) return;
   string sign = (g_offset_hours >= 0) ? "+" : "";
   string text = "sm_GMTOffset: " + sign + IntegerToString(g_offset_hours) + " h";

   if(ObjectFind(g_label_name) < 0)
      ObjectCreate(g_label_name, OBJ_LABEL, 0, 0, 0);

   ObjectSetText(g_label_name, text, InpLabelFontSize, "Arial", InpLabelColor);
   ObjectSet(g_label_name, OBJPROP_CORNER,    InpLabelCorner);
   ObjectSet(g_label_name, OBJPROP_XDISTANCE, InpLabelXOffset);
   ObjectSet(g_label_name, OBJPROP_YDISTANCE, InpLabelYOffset);
   ObjectSet(g_label_name, OBJPROP_BACK,      false);
   ObjectSet(g_label_name, OBJPROP_SELECTABLE,false);
   WindowRedraw();
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
   if(StringLen(g_label_name) > 0 && ObjectFind(g_label_name) >= 0)
      ObjectDelete(g_label_name);
   WindowRedraw();
   //--- Spec Section 5 step 4: do NOT delete GlobalVariable on deinit.
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
   return(rates_total);
  }
//+------------------------------------------------------------------+

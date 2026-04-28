//+------------------------------------------------------------------+
//|  SM_Daily_HiLo.mq5                                                |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator                       |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_Daily_HiLo.md                                            |
//|                                                                   |
//|  Draws two horizontal lines on the main chart:                    |
//|     PHOD = iHigh(_Symbol, PERIOD_D1, DaysBack)                     |
//|     PLOD = iLow (_Symbol, PERIOD_D1, DaysBack)                     |
//|  DaysBack=1 = yesterday's completed D1 bar (Pitfall 5 guard).      |
//|                                                                   |
//|  CONTEXT D-06 / D-19 (MQ5 idiomatic).                             |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_Daily_HiLo.ex4"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

// #define DUMP_PARITY_CSV  // Optional advisory parity dump (D-15)

//--- Spec Section 3 inputs ([INFER] defaults — see spec Uncertainty log)
input int             InpDaysBack    = 1;             // 1 = yesterday's completed bar
input color           InpHighColor   = clrRed;        // PHOD line color
input color           InpLowColor    = clrLimeGreen;  // PLOD line color
input ENUM_LINE_STYLE InpLineStyle   = STYLE_DASH;
input int             InpLineWidth   = 1;
input bool            InpShowLabel   = true;          // PHOD / PLOD text labels

const string InpObjectPrefix = "smHL_";

datetime g_last_d1_bar = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("SM_Daily_HiLo(D-%d)", InpDaysBack));
   Recompute();
   EventSetTimer(60);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   CleanupObjects();
   EventKillTimer();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tv[],
                const long &v[], const int &sp[])
  {
   datetime cur_d1 = iTime(_Symbol, PERIOD_D1, 0);
   if(cur_d1 != g_last_d1_bar)
     {
      Recompute();
      g_last_d1_bar = cur_d1;
     }
   return(rates_total);
  }

//+------------------------------------------------------------------+
void Recompute()
  {
   // Bar `InpDaysBack` (1 = last completed D1) — Pitfall 5 lookahead guard.
   double phod = iHigh(_Symbol, PERIOD_D1, InpDaysBack);
   double plod = iLow (_Symbol, PERIOD_D1, InpDaysBack);

   if(phod <= 0.0 || plod <= 0.0)
      return;

   DrawHLine(InpObjectPrefix + "phod", phod, InpHighColor);
   DrawHLine(InpObjectPrefix + "plod", plod, InpLowColor);

   if(InpShowLabel)
     {
      DrawLabel(InpObjectPrefix + "phod_lbl", "PHOD", phod, InpHighColor);
      DrawLabel(InpObjectPrefix + "plod_lbl", "PLOD", plod, InpLowColor);
     }

#ifdef DUMP_PARITY_CSV
   DumpParityRow(phod, plod);
#endif
  }

//+------------------------------------------------------------------+
void DrawHLine(string name, double price, color c)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);

   ObjectSetDouble (0, name, OBJPROP_PRICE,  price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,  c);
   ObjectSetInteger(0, name, OBJPROP_STYLE,  InpLineStyle);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,  InpLineWidth);
   ObjectSetInteger(0, name, OBJPROP_BACK,   true);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

//+------------------------------------------------------------------+
void DrawLabel(string name, string text, double price, color c)
  {
   datetime label_time = iTime(_Symbol, _Period, 0);
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, label_time, price);
   ObjectSetString (0, name, OBJPROP_TEXT,    text);
   ObjectSetInteger(0, name, OBJPROP_TIME,    label_time);
   ObjectSetDouble (0, name, OBJPROP_PRICE,   price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,   c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR,  ANCHOR_LEFT);
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

//+------------------------------------------------------------------+
#ifdef DUMP_PARITY_CSV
void DumpParityRow(double phod, double plod)
  {
   string fn = StringFormat("parity_SM_Daily_HiLo_%s_%s.csv",
                            _Symbol, EnumToString(_Period));
   int handle = FileOpen(fn, FILE_WRITE | FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
      return;
   if(FileSize(handle) == 0)
      FileWrite(handle, "ts", "phod", "plod");
   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, TimeToString(iTime(_Symbol, PERIOD_D1, 0), TIME_DATE | TIME_MINUTES),
             DoubleToString(phod, _Digits),
             DoubleToString(plod, _Digits));
   FileClose(handle);
  }
#endif

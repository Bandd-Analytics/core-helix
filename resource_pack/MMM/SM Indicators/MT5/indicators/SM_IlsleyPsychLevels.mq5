//+------------------------------------------------------------------+
//|  SM_IlsleyPsychLevels.mq5                                         |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator                       |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/           |
//|        SM_IlsleyPsychLevels.md                                     |
//|                                                                   |
//|  Round-number psychological levels at 50-pip intervals (MMM       |
//|  convention). JPY/3-digit pip detection via SYMBOL_DIGITS so that |
//|  USDJPY at 152.34 anchors lines at 152.00, 152.50, 153.00 (not    |
//|  every 5 points — Pitfall: pip math).                             |
//|                                                                   |
//|  CONTEXT D-06 / D-19.                                             |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_IlsleyPsychLevels.ex4"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

// #define DUMP_PARITY_CSV  // Optional advisory parity dump (D-15)

//--- Spec Section 3 inputs ([INFER] per Uncertainty log)
input int             InpStepPips     = 50;            // 50-pip step (MMM-typical)
input int             InpMajorPips    = 100;           // 100-pip "major" line emphasis
input int             InpLevelsAbove  = 5;
input int             InpLevelsBelow  = 5;
input color           InpMinorColor   = clrDimGray;    // [INFER]
input color           InpMajorColor   = clrDarkGray;   // [INFER]
input ENUM_LINE_STYLE InpLineStyle    = STYLE_DOT;
input int             InpLineWidth    = 1;
input bool            InpShowLabel    = true;          // 50/00 pip labels

const string InpObjectPrefix = "smPsych_";

double g_pip = 0.0;
datetime g_last_d1_bar = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   // Pitfall: pip math — JPY (3-digit) pip=0.01; majors (5-digit) pip=0.0001.
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   g_pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;

   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("SM_IlsleyPsychLevels(%d/%d)",
                                   InpStepPips, InpMajorPips));
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
   // Recompute on D1 bar change to keep level grid centered on price.
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
   if(g_pip <= 0.0)
      return;

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0.0)
      return;

   double step  = InpStepPips  * g_pip;
   double major = InpMajorPips * g_pip;

   // Nearest round-number below current price — anchor of the level grid.
   double base = MathFloor(bid / step) * step;

   // Sweep N below..N above of base.
   for(int i = -InpLevelsBelow; i <= InpLevelsAbove; i++)
     {
      double level = base + i * step;
      // Major line if level aligns with major step (e.g., every 100 pips).
      bool is_major = (MathAbs(level - MathRound(level / major) * major) < step * 0.01);

      string suffix = StringFormat("L_%d", i + InpLevelsBelow);
      string name = InpObjectPrefix + suffix;

      DrawHLine(name, level,
                is_major ? InpMajorColor : InpMinorColor,
                is_major ? (InpLineWidth + 1) : InpLineWidth);

      if(InpShowLabel)
        {
         string label_name = InpObjectPrefix + "lbl_" + suffix;
         DrawLabel(label_name, level,
                   is_major ? InpMajorColor : InpMinorColor);
        }
     }

#ifdef DUMP_PARITY_CSV
   double psych_below = base;
   double psych_above = base + step;
   DumpParityRow(psych_above, psych_below);
#endif
  }

//+------------------------------------------------------------------+
void DrawHLine(string name, double price, color c, int width)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
   ObjectSetDouble (0, name, OBJPROP_PRICE,  price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,  c);
   ObjectSetInteger(0, name, OBJPROP_STYLE,  InpLineStyle);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,  width);
   ObjectSetInteger(0, name, OBJPROP_BACK,   true);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

//+------------------------------------------------------------------+
void DrawLabel(string name, double price, color c)
  {
   datetime label_time = iTime(_Symbol, _Period, 0);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   string text = DoubleToString(price, digits);
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, label_time, price);
   ObjectSetString (0, name, OBJPROP_TEXT,    text);
   ObjectSetInteger(0, name, OBJPROP_TIME,    label_time);
   ObjectSetDouble (0, name, OBJPROP_PRICE,   price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,   c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
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
void DumpParityRow(double psych_above, double psych_below)
  {
   string fn = StringFormat("parity_SM_IlsleyPsychLevels_%s_%s.csv",
                            _Symbol, EnumToString(_Period));
   int handle = FileOpen(fn, FILE_WRITE | FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
      return;
   if(FileSize(handle) == 0)
      FileWrite(handle, "ts", "psych_level_above", "psych_level_below");
   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, TimeToString(iTime(_Symbol, PERIOD_D1, 0), TIME_DATE | TIME_MINUTES),
             DoubleToString(psych_above, _Digits),
             DoubleToString(psych_below, _Digits));
   FileClose(handle);
  }
#endif

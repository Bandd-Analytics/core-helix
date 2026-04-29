//+------------------------------------------------------------------+
//|  SM_TDI.mq5                                                       |
//|  Phase 12 Plan 03 — Tier 2 composite indicator (MQ5)              |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md  |
//|  Primary ref: MMM TDI Tradestation PDF                            |
//|  Verified Updates 2026-04-27:                                     |
//|    RSI_Period=21 (was claimed 13), Shark_Fin 63/37 (was 68/32),   |
//|    VB_High_Value=45.0 + VB_Low_Value=55.0 (NEW inputs),           |
//|    fixed_min=19.2182 fixed_max=77.5613 per Levels tab.           |
//|  Pattern: RESEARCH Pattern 2 indicator-handle composition         |
//|           (iRSI handle + CopyBuffer).                             |
//|  Pitfall 7: exactly 5 indicator buffers (not 6 — rsi_raw is       |
//|             internal, not an exposed buffer).                     |
//|  Anti-Patterns: alerts gated on bar[1] transitions ONLY.         |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_TDI.ex4"
#property version   "1.00"
#property indicator_separate_window
#property indicator_buffers 5
#property indicator_plots   5
#property indicator_minimum 19.2182   // Verified Updates Levels tab
#property indicator_maximum 77.5613   // Verified Updates Levels tab

// Optional advisory parity dump — operator defines DUMP_PARITY_CSV at top
// to emit per-bar CSV to MQL5/Files/parity_SM_TDI_<symbol>_<tf>.csv
// for use with scripts/parity_check_tdi.py (CONTEXT D-15 advisory).
// #define DUMP_PARITY_CSV

//--- Plot 0: RSI Price Line (Green) — fastest
#property indicator_label1  "RSI_PL"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrLime
#property indicator_style1  STYLE_SOLID
#property indicator_width1  1

//--- Plot 1: Trade Signal Line (Red)
#property indicator_label2  "TSL"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrRed
#property indicator_style2  STYLE_SOLID
#property indicator_width2  1

//--- Plot 2: Market Base Line (Yellow) — slightly thicker
#property indicator_label3  "MBL"
#property indicator_type3   DRAW_LINE
#property indicator_color3  clrYellow
#property indicator_style3  STYLE_SOLID
#property indicator_width3  2

//--- Plot 3: VB Upper (Blue)
#property indicator_label4  "VB_Upper"
#property indicator_type4   DRAW_LINE
#property indicator_color4  clrDodgerBlue
#property indicator_style4  STYLE_SOLID
#property indicator_width4  1

//--- Plot 4: VB Lower (Blue)
#property indicator_label5  "VB_Lower"
#property indicator_type5   DRAW_LINE
#property indicator_color5  clrDodgerBlue
#property indicator_style5  STYLE_SOLID
#property indicator_width5  1

//--- Inputs verbatim from Verified Updates 2026-04-27
input int                InpRSIPeriod           = 21;       // RSI Period (CORRECTED — was 13)
input ENUM_APPLIED_PRICE InpRSIPrice            = PRICE_CLOSE; // RSI Price type
input int                InpVolatilityBand      = 34;       // VB Bollinger period
input int                InpMarketBaseLine      = 34;       // MBL SMA period
input int                InpRSIPriceLine        = 2;        // RSI_PL Green SMA period
input ENUM_MA_METHOD     InpRSIPriceType        = MODE_SMA; // RSI_PL smoothing type
input int                InpTradeSignalLine     = 7;        // TSL Red SMA period
input ENUM_MA_METHOD     InpTradeSignalType     = MODE_SMA; // TSL smoothing type
input bool               InpSharkFinAlert       = false;    // Shark Fin alert toggle
input double             InpSharkFinUpperLevel  = 63.0;     // Shark Fin Upper (CORRECTED — was 68)
input double             InpSharkFinLowerLevel  = 37.0;     // Shark Fin Lower (CORRECTED — was 32)
input bool               InpSqueezeAlert        = false;    // VB Squeeze alert toggle
input bool               InpSqueezeEntryAlert   = false;    // Squeeze entry alert toggle
input double             InpVBHighValue         = 45.0;     // VB High HLINE level (NEW — Verified Updates)
input double             InpVBLowValue          = 55.0;     // VB Low HLINE level (NEW — Verified Updates)
input bool               InpPopUpAlert          = false;    // Pop-up alert toggle
input bool               InpDrawMBLSlope        = false;    // Draw MBL slope toggle
input double             InpSensitivity         = 0.0001;   // Alert epsilon / sensitivity

//--- Indicator buffer arrays (5 exposed buffers — Pitfall 7)
double g_rsi_pl[];     // Buffer 0: Green RSI Price Line
double g_tsl[];        // Buffer 1: Red Trade Signal Line
double g_mbl[];        // Buffer 2: Yellow Market Base Line
double g_vb_upper[];   // Buffer 3: Blue VB Upper
double g_vb_lower[];   // Buffer 4: Blue VB Lower

//--- Internal (private) raw RSI array — NOT an indicator buffer
double g_rsi_raw[];

//--- RSI handle (RESEARCH Pattern 2 — iRSI handle composition)
int g_handle_rsi = INVALID_HANDLE;

//--- Alert state (one-shot guard per bar per alert type)
datetime g_last_signal_cross_alert = 0;
datetime g_last_mbl_cross_alert    = 0;
datetime g_last_hook_alert         = 0;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
  {
//--- Buffer registration (Pitfall 7 — 5 SetIndexBuffer calls for 5 buffers)
   SetIndexBuffer(0, g_rsi_pl,    INDICATOR_DATA);
   SetIndexBuffer(1, g_tsl,       INDICATOR_DATA);
   SetIndexBuffer(2, g_mbl,       INDICATOR_DATA);
   SetIndexBuffer(3, g_vb_upper,  INDICATOR_DATA);
   SetIndexBuffer(4, g_vb_lower,  INDICATOR_DATA);

//--- Empty value (suppress drawing before warmup)
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(2, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(3, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(4, PLOT_EMPTY_VALUE, EMPTY_VALUE);

//--- RSI handle (RESEARCH Pattern 2)
   g_handle_rsi = iRSI(_Symbol, PERIOD_CURRENT, InpRSIPeriod, InpRSIPrice);
   if(g_handle_rsi == INVALID_HANDLE)
     {
      Print("SM_TDI: iRSI handle creation failed");
      return(INIT_FAILED);
     }

//--- Indicator short name
   IndicatorSetString(INDICATOR_SHORTNAME,
                      "SM_TDI(" + IntegerToString(InpRSIPeriod) + ")");

//--- VB_High_Value + VB_Low_Value as fixed HLINE levels in subwindow
//    (Verified Updates 2026-04-27 NEW inputs — display-only reference lines)
   IndicatorSetInteger(INDICATOR_LEVELS, 2);
   IndicatorSetDouble(INDICATOR_LEVELVALUE, 0, InpVBHighValue);
   IndicatorSetDouble(INDICATOR_LEVELVALUE, 1, InpVBLowValue);
   IndicatorSetInteger(INDICATOR_LEVELCOLOR, 0, clrSilver);
   IndicatorSetInteger(INDICATOR_LEVELCOLOR, 1, clrSilver);
   IndicatorSetInteger(INDICATOR_LEVELSTYLE, 0, STYLE_DOT);
   IndicatorSetInteger(INDICATOR_LEVELSTYLE, 1, STYLE_DOT);

   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(g_handle_rsi != INVALID_HANDLE)
      IndicatorRelease(g_handle_rsi);
  }

//+------------------------------------------------------------------+
//| Compute SMA over a portion of an array                           |
//+------------------------------------------------------------------+
double SMA(const double &arr[], int idx, int period)
  {
   if(idx < period - 1)
      return EMPTY_VALUE;
   double sum = 0.0;
   for(int k = idx - period + 1; k <= idx; k++)
      sum += arr[k];
   return sum / period;
  }

//+------------------------------------------------------------------+
//| Custom indicator calculation function                            |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
//--- Need at least rsi_period + market_base_line bars to produce output
   int warmup = InpRSIPeriod + InpMarketBaseLine + 2;
   if(rates_total < warmup)
      return(prev_calculated);

//--- Copy RSI values from handle (RESEARCH Pattern 2)
   ArrayResize(g_rsi_raw, rates_total);
   if(CopyBuffer(g_handle_rsi, 0, 0, rates_total, g_rsi_raw) <= 0)
      return(prev_calculated);

//--- Calculate start bar (skip already-computed bars for performance)
   int start = (prev_calculated > 0) ? prev_calculated - 1 : warmup;
   if(start < warmup) start = warmup;

//--- Main calculation loop
   for(int i = start; i < rates_total; i++)
     {
      //--- Green: RSI Price Line (SMA of rsi_raw, period=InpRSIPriceLine)
      g_rsi_pl[i] = SMA(g_rsi_raw, i, InpRSIPriceLine);

      //--- Red: Trade Signal Line (SMA of rsi_raw, period=InpTradeSignalLine)
      g_tsl[i]    = SMA(g_rsi_raw, i, InpTradeSignalLine);

      //--- Yellow: Market Base Line (SMA of rsi_raw, period=InpMarketBaseLine)
      g_mbl[i]    = SMA(g_rsi_raw, i, InpMarketBaseLine);

      //--- Volatility Bands: population stddev of rsi_raw over InpVolatilityBand bars
      if(i < InpVolatilityBand - 1)
        {
         g_vb_upper[i] = EMPTY_VALUE;
         g_vb_lower[i] = EMPTY_VALUE;
         continue;
        }
      double mean_val = g_mbl[i];
      double sq_sum   = 0.0;
      for(int k = i - InpVolatilityBand + 1; k <= i; k++)
         sq_sum += (g_rsi_raw[k] - mean_val) * (g_rsi_raw[k] - mean_val);
      double sigma = MathSqrt(sq_sum / InpVolatilityBand);  // population stddev (ddof=0)
      // [INFER] StdDev multiplier 1.6185 — Verified Updates: NOT in Inputs, internal constant
      // per spec Section 12 Uncertainty log. MMM TDI Tradestation PDF cites 1.6185.
      g_vb_upper[i] = mean_val + 1.6185 * sigma;
      g_vb_lower[i] = mean_val - 1.6185 * sigma;
     }

//--- Alert detection — bar[1] transitions ONLY (Anti-Patterns guard)
   if(rates_total < 3) return(rates_total);
   int last = rates_total - 2;   // bar[1] = most recently CLOSED bar
   int prev = rates_total - 3;   // bar[2] = prior closed bar

   if(g_rsi_pl[last] == EMPTY_VALUE || g_tsl[last] == EMPTY_VALUE) return(rates_total);

   datetime bar_time = time[last];

//--- 1. Signal Cross alert (Green × Red)
   if(InpPopUpAlert && g_last_signal_cross_alert != bar_time)
     {
      bool sc_bull = (g_rsi_pl[last] >  g_tsl[last]) && (g_rsi_pl[prev] <= g_tsl[prev]);
      bool sc_bear = (g_rsi_pl[last] <  g_tsl[last]) && (g_rsi_pl[prev] >= g_tsl[prev]);
      if(sc_bull)
        { Alert("SM_TDI: SIGNAL_CROSS_BULLISH — ", _Symbol, " ", EnumToString(PERIOD_CURRENT)); g_last_signal_cross_alert = bar_time; }
      else if(sc_bear)
        { Alert("SM_TDI: SIGNAL_CROSS_BEARISH — ", _Symbol, " ", EnumToString(PERIOD_CURRENT)); g_last_signal_cross_alert = bar_time; }
     }

//--- 2. MBL Cross (Blood in the Water) alert
   if(InpPopUpAlert && g_mbl[last] != EMPTY_VALUE && g_last_mbl_cross_alert != bar_time)
     {
      double avg_h6 = 0.0;
      for(int k = last - 5; k <= last; k++) avg_h6 += high[k];
      avg_h6 /= 6.0;
      bool mbl_bull = (g_rsi_pl[last] > g_mbl[last]) && (g_rsi_pl[prev] <= g_mbl[prev])
                   && (g_rsi_pl[last] > g_tsl[last]) && (high[last] > avg_h6);
      if(mbl_bull)
        { Alert("SM_TDI: MBL_CROSS_BULLISH (Blood in the Water) — ", _Symbol); g_last_mbl_cross_alert = bar_time; }
     }

//--- 3. Hook alert (counter-trend: Green re-enters VB from extreme)
   if(InpPopUpAlert && g_vb_lower[last] != EMPTY_VALUE && g_last_hook_alert != bar_time)
     {
      bool hook_bull = (g_rsi_pl[last] > g_vb_lower[last]) && (g_rsi_pl[prev] <= g_vb_lower[prev]) && (g_rsi_pl[last] < 40.0);
      bool hook_bear = (g_rsi_pl[last] < g_vb_upper[last]) && (g_rsi_pl[prev] >= g_vb_upper[prev]) && (g_rsi_pl[last] > 60.0);
      if(hook_bull)
        { Alert("SM_TDI: HOOK_BULLISH (counter-trend) — ", _Symbol); g_last_hook_alert = bar_time; }
      else if(hook_bear)
        { Alert("SM_TDI: HOOK_BEARISH (counter-trend) — ", _Symbol); g_last_hook_alert = bar_time; }
     }

//--- Shark Fin alert
   if(InpSharkFinAlert && g_last_signal_cross_alert != bar_time)
     {
      bool sf_bull = (g_rsi_pl[prev] < InpSharkFinLowerLevel) && (g_rsi_pl[last] >= InpSharkFinLowerLevel);
      bool sf_bear = (g_rsi_pl[prev] > InpSharkFinUpperLevel) && (g_rsi_pl[last] <= InpSharkFinUpperLevel);
      if(sf_bull || sf_bear)
        { Alert("SM_TDI: SHARK_FIN — ", _Symbol, " ", (sf_bull ? "BULLISH" : "BEARISH")); }
     }

#ifdef DUMP_PARITY_CSV
//--- Advisory parity CSV dump (CONTEXT D-15 advisory)
   {
      string filename = StringFormat("parity_SM_TDI_%s_%s.csv", _Symbol, EnumToString(PERIOD_CURRENT));
      int fh = FileOpen(filename, FILE_WRITE | FILE_CSV | FILE_ANSI);
      if(fh != INVALID_HANDLE)
        {
         FileWrite(fh, "ts,rsi_pl,tsl,mbl,vb_upper,vb_lower");
         for(int i = warmup; i < rates_total; i++)
            FileWrite(fh, TimeToString(time[i], TIME_DATE|TIME_MINUTES),
                      g_rsi_pl[i], g_tsl[i], g_mbl[i], g_vb_upper[i], g_vb_lower[i]);
         FileClose(fh);
        }
   }
#endif

   return(rates_total);
  }
//+------------------------------------------------------------------+

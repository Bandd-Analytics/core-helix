//+------------------------------------------------------------------+
//|  SM_TDI.mq4                                                       |
//|  Phase 12 Plan 03 — Tier 2 composite indicator (MQ4 idiomatic)    |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_TDI.md  |
//|  Verified Updates 2026-04-27: RSI_Period=21, Shark_Fin 63/37      |
//|                                                                   |
//|  MQ4 idiom: iRSI returns double directly (no handle composition). |
//|  Pitfall 1: SetIndexBuffer + SetIndexStyle (not PlotIndexSet).    |
//|  D-20: MQ4 uses MQL4 idioms (extern, init/deinit, ObjectCreate    |
//|        5-arg signature).                                          |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_TDI.ex4"
#property version   "1.00"
#property indicator_separate_window
#property indicator_buffers 5
#property strict

//--- Inputs verbatim from Verified Updates 2026-04-27
extern int    InpRSIPeriod          = 21;      // RSI Period (CORRECTED — was 13)
extern int    InpRSIPrice           = 0;       // 0 = PRICE_CLOSE
extern int    InpVolatilityBand     = 34;      // VB Bollinger period
extern int    InpMarketBaseLine     = 34;      // MBL SMA period
extern int    InpRSIPriceLine       = 2;       // RSI_PL Green SMA period
extern int    InpTradeSignalLine    = 7;       // TSL Red SMA period
extern bool   InpSharkFinAlert      = false;   // Shark Fin alert toggle
extern double InpSharkFinUpperLevel = 63.0;    // Shark Fin Upper (CORRECTED — was 68)
extern double InpSharkFinLowerLevel = 37.0;    // Shark Fin Lower (CORRECTED — was 32)
extern bool   InpSqueezeAlert       = false;   // VB Squeeze alert toggle
extern double InpVBHighValue        = 45.0;    // VB High reference level (NEW)
extern double InpVBLowValue         = 55.0;    // VB Low reference level (NEW)
extern bool   InpPopUpAlert         = false;   // Pop-up alert toggle

//--- Indicator buffer arrays (5 exposed — Pitfall 7)
double g_rsi_pl[];
double g_tsl[];
double g_mbl[];
double g_vb_upper[];
double g_vb_lower[];

//--- Alert state
datetime g_last_signal_alert = 0;
datetime g_last_mbl_alert    = 0;
datetime g_last_hook_alert   = 0;

//+------------------------------------------------------------------+
//| MQ4 init function                                                |
//+------------------------------------------------------------------+
int init()
  {
//--- Buffer registration (MQ4 idiom per Pitfall 1)
   SetIndexBuffer(0, g_rsi_pl);
   SetIndexStyle(0, DRAW_LINE, 0, 1, clrLime);
   SetIndexLabel(0, "RSI_PL");

   SetIndexBuffer(1, g_tsl);
   SetIndexStyle(1, DRAW_LINE, 0, 1, clrRed);
   SetIndexLabel(1, "TSL");

   SetIndexBuffer(2, g_mbl);
   SetIndexStyle(2, DRAW_LINE, 0, 2, clrYellow);
   SetIndexLabel(2, "MBL");

   SetIndexBuffer(3, g_vb_upper);
   SetIndexStyle(3, DRAW_LINE, 0, 1, clrDodgerBlue);
   SetIndexLabel(3, "VB_Upper");

   SetIndexBuffer(4, g_vb_lower);
   SetIndexStyle(4, DRAW_LINE, 0, 1, clrDodgerBlue);
   SetIndexLabel(4, "VB_Lower");

//--- Short name (MQ4 idiom)
   IndicatorShortName("SM_TDI(" + IntegerToString(InpRSIPeriod) + ")");

//--- Reference level HLINES at fixed Y values
   SetLevelValue(0, InpVBHighValue);
   SetLevelValue(1, InpVBLowValue);
   SetLevelStyle(STYLE_DOT, 1, clrSilver);

   return(0);
  }

//+------------------------------------------------------------------+
//| MQ4 deinit function                                              |
//+------------------------------------------------------------------+
int deinit()
  {
   return(0);
  }

//+------------------------------------------------------------------+
//| Helper: SMA over an index range                                  |
//+------------------------------------------------------------------+
double SMA_MQ4(int idx, int period, int applied_price)
  {
   if(idx < period - 1)
      return(EMPTY_VALUE);
   double sum = 0.0;
   for(int k = 0; k < period; k++)
      sum += iRSI(NULL, 0, InpRSIPeriod, InpRSIPrice, idx + k);
   return(sum / period);
  }

//+------------------------------------------------------------------+
//| MQ4 start function (called every tick + bar)                     |
//+------------------------------------------------------------------+
int start()
  {
   int bars    = Bars;
   int warmup  = InpRSIPeriod + InpMarketBaseLine + 2;
   if(bars < warmup) return(0);

   int counted = IndicatorCounted();
   if(counted < 0) return(-1);
   int limit = bars - counted - 1;
   if(limit > bars - warmup) limit = bars - warmup;

   for(int i = limit; i >= 0; i--)
     {
      //--- Raw RSI at each bar (MQ4 idiom: iRSI returns double directly)
      double rsi_raw_i = iRSI(NULL, 0, InpRSIPeriod, InpRSIPrice, i);

      //--- Compute SMA(rsi_raw, period) via loop over iRSI calls
      // Green: RSI Price Line (SMA period=2)
      if(i + InpRSIPriceLine - 1 < bars)
        {
         double sum_pl = 0.0;
         for(int k = 0; k < InpRSIPriceLine; k++)
            sum_pl += iRSI(NULL, 0, InpRSIPeriod, InpRSIPrice, i + k);
         g_rsi_pl[i] = sum_pl / InpRSIPriceLine;
        }
      else g_rsi_pl[i] = EMPTY_VALUE;

      // Red: Trade Signal Line (SMA period=7)
      if(i + InpTradeSignalLine - 1 < bars)
        {
         double sum_tsl = 0.0;
         for(int k = 0; k < InpTradeSignalLine; k++)
            sum_tsl += iRSI(NULL, 0, InpRSIPeriod, InpRSIPrice, i + k);
         g_tsl[i] = sum_tsl / InpTradeSignalLine;
        }
      else g_tsl[i] = EMPTY_VALUE;

      // Yellow: Market Base Line (SMA period=34)
      if(i + InpMarketBaseLine - 1 < bars)
        {
         double sum_mbl = 0.0;
         for(int k = 0; k < InpMarketBaseLine; k++)
            sum_mbl += iRSI(NULL, 0, InpRSIPeriod, InpRSIPrice, i + k);
         g_mbl[i] = sum_mbl / InpMarketBaseLine;
        }
      else { g_mbl[i] = EMPTY_VALUE; g_vb_upper[i] = EMPTY_VALUE; g_vb_lower[i] = EMPTY_VALUE; continue; }

      // VB: population stddev of rsi_raw over InpVolatilityBand bars
      if(i + InpVolatilityBand - 1 < bars)
        {
         double mean_val = g_mbl[i];
         double sq_sum   = 0.0;
         for(int k = 0; k < InpVolatilityBand; k++)
           {
            double r = iRSI(NULL, 0, InpRSIPeriod, InpRSIPrice, i + k);
            sq_sum += (r - mean_val) * (r - mean_val);
           }
         double sigma = MathSqrt(sq_sum / InpVolatilityBand);
         // [INFER] StdDev multiplier 1.6185 per spec Section 12 Uncertainty log
         g_vb_upper[i] = mean_val + 1.6185 * sigma;
         g_vb_lower[i] = mean_val - 1.6185 * sigma;
        }
      else { g_vb_upper[i] = EMPTY_VALUE; g_vb_lower[i] = EMPTY_VALUE; }
     }

//--- Alert detection on bar[1] (most recently closed bar)
   if(bars < 3) return(0);
   int last = 1;  // bar[1] = most recently closed bar in MQ4 convention
   int prev = 2;

   if(g_rsi_pl[last] == EMPTY_VALUE || g_tsl[last] == EMPTY_VALUE) return(0);
   datetime bar_time = Time[last];

//--- Signal Cross
   if(InpPopUpAlert && g_last_signal_alert != bar_time)
     {
      bool sc_bull = (g_rsi_pl[last] > g_tsl[last]) && (g_rsi_pl[prev] <= g_tsl[prev]);
      bool sc_bear = (g_rsi_pl[last] < g_tsl[last]) && (g_rsi_pl[prev] >= g_tsl[prev]);
      if(sc_bull) { Alert("SM_TDI: SIGNAL_CROSS_BULLISH — ", Symbol()); g_last_signal_alert = bar_time; }
      else if(sc_bear) { Alert("SM_TDI: SIGNAL_CROSS_BEARISH — ", Symbol()); g_last_signal_alert = bar_time; }
     }

   return(0);
  }
//+------------------------------------------------------------------+

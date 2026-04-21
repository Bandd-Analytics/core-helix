//+------------------------------------------------------------------+
//|                                               RegimeClassifier.mq5 |
//|                    MT5 POC - Unified Market Regime Classification |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 1
#property indicator_plots   1
#property indicator_label1  "RegimeCode"
#property indicator_type1   DRAW_HISTOGRAM
#property indicator_color1  clrMagenta
#property indicator_width1  3

//--- Input parameters
input int InpADXPeriod = 14;           // ADX period for trend confirmation
input double InpADXThresholdStrong = 35.0;  // ADX threshold for strong trend
input double InpADXThresholdMild = 25.0;    // ADX threshold for mild trend
input double InpADXThresholdRange = 20.0;   // ADX threshold for ranging
input double InpHurstTrending = 0.55;       // Hurst threshold for trending
input double InpATRVolatileThreshold = 85.0; // ATR percentile for volatile
input double InpATRRangeTightThreshold = 30.0; // ATR percentile for tight range
input double InpATRRangeWideThreshold = 70.0;  // ATR percentile for wide range

//--- Indicator buffer
double BufferRegimeCode[];  // Buffer 0: Regime classification code

//--- Custom indicator handles
int handleAdaptiveATR = INVALID_HANDLE;
int handleHurstExponent = INVALID_HANDLE;
int handleADX = INVALID_HANDLE;

//--- Regime state constants
#define REGIME_RANGING_WIDE    -2   // ADX < 20 AND ATR pct 30-70
#define REGIME_RANGING_TIGHT   -1   // ADX < 20 AND ATR pct < 30
#define REGIME_TRENDING_MILD    1   // ADX 25-35
#define REGIME_TRENDING_STRONG  2   // ADX > 35 AND H > 0.55
#define REGIME_VOLATILE         3   // ATR pct > 85 regardless of ADX

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize buffer for output
   SetIndexBuffer(0, BufferRegimeCode, INDICATOR_DATA);

   // Load custom indicators via iCustom
   handleAdaptiveATR = iCustom(NULL, 0, "AdaptiveATR");
   if(handleAdaptiveATR == INVALID_HANDLE)
   {
      Print("Error: Failed to load AdaptiveATR indicator");
      return INIT_FAILED;
   }

   handleHurstExponent = iCustom(NULL, 0, "HurstExponent");
   if(handleHurstExponent == INVALID_HANDLE)
   {
      Print("Error: Failed to load HurstExponent indicator");
      return INIT_FAILED;
   }

   handleADX = iADX(_Symbol, PERIOD_CURRENT, InpADXPeriod);
   if(handleADX == INVALID_HANDLE)
   {
      Print("Error: Failed to create ADX handle");
      return INIT_FAILED;
   }

   // Set plot properties
   PlotIndexSetString(0, PLOT_LABEL, "RegimeCode");
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0.0);

   IndicatorSetString(INDICATOR_SHORTNAME, "RegimeClassifier");

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
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
   // Need enough bars for calculations
   if(rates_total < 100)
      return(0);

   int start = 0;
   if(prev_calculated > 0)
      start = prev_calculated - 1;

   // Copy all indicator buffers before the loop (index 0 = most recent bar)
   double atrPercentileBuf[];
   double hurstBuf[];
   double adxBuf[];
   bool buffersReady = (CopyBuffer(handleAdaptiveATR,   1, 0, rates_total, atrPercentileBuf) > 0 &&
                        CopyBuffer(handleHurstExponent, 0, 0, rates_total, hurstBuf)         > 0 &&
                        CopyBuffer(handleADX,           0, 0, rates_total, adxBuf)           > 0);
   if(!buffersReady) return(prev_calculated);

   // Calculate for new bars
   for(int i = start; i < rates_total; i++)
   {
      // reverse index: buf[0]=newest, buf[rates_total-1-i]=bar i
      int pos = rates_total - 1 - i;

      // Step 1: Get percentile rank from AdaptiveATR (Buffer 1)
      double atrPercentile = (pos < ArraySize(atrPercentileBuf)) ? atrPercentileBuf[pos] : 50.0;

      // Step 2: Get Hurst value from HurstExponent (Buffer 0)
      double hurstValue = (pos < ArraySize(hurstBuf)) ? hurstBuf[pos] : 0.5;

      // Step 3: Get ADX value for trend confirmation
      double adx = (pos < ArraySize(adxBuf)) ? adxBuf[pos] : 0.0;

      // Step 4: Classify regime based on ADX, ATR percentile, and Hurst
      int regimeCode = ClassifyRegime(adx, atrPercentile, hurstValue);

      // Step 5: Output to buffer
      BufferRegimeCode[i] = (double)regimeCode;
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Classify regime based on multiple indicators                     |
//+------------------------------------------------------------------+
int ClassifyRegime(double adx, double atrPercentile, double hurstValue)
{
   int regime = REGIME_TRENDING_MILD; // Default

   // Priority 1: Check for volatile regime (overrides everything)
   if(atrPercentile > InpATRVolatileThreshold)
   {
      regime = REGIME_VOLATILE;
      return regime;
   }

   // Priority 2: Check ADX levels for trend/range classification
   if(adx > InpADXThresholdStrong)
   {
      // Strong trend
      if(hurstValue > InpHurstTrending)
         regime = REGIME_TRENDING_STRONG;
      else
         regime = REGIME_TRENDING_MILD;
   }
   else if(adx >= InpADXThresholdMild && adx <= InpADXThresholdStrong)
   {
      // Mild trend
      regime = REGIME_TRENDING_MILD;
   }
   else if(adx < InpADXThresholdRange)
   {
      // Ranging regime - check ATR percentile for tight vs wide
      if(atrPercentile < InpATRRangeTightThreshold)
      {
         regime = REGIME_RANGING_TIGHT;
      }
      else if(atrPercentile <= InpATRRangeWideThreshold)
      {
         regime = REGIME_RANGING_WIDE;
      }
      else
      {
         // High volatility but low ADX = transition zone
         regime = REGIME_VOLATILE;
      }
   }

   return regime;
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Release indicator handles
   if(handleAdaptiveATR != INVALID_HANDLE)
      IndicatorRelease(handleAdaptiveATR);

   if(handleHurstExponent != INVALID_HANDLE)
      IndicatorRelease(handleHurstExponent);

   if(handleADX != INVALID_HANDLE)
      IndicatorRelease(handleADX);
}

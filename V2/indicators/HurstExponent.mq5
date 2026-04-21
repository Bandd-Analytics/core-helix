//+------------------------------------------------------------------+
//|                                                HurstExponent.mq5 |
//|                    MT5 POC - Hurst Exponent via R/S Analysis |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2
#property indicator_label1  "HurstValue"
#property indicator_label2  "HurstSignal"
#property indicator_type1   DRAW_LINE
#property indicator_type2   DRAW_HISTOGRAM
#property indicator_color1  clrDodgerBlue
#property indicator_color2  clrPurple
#property indicator_width1  2
#property indicator_width2  2

//--- Input parameters
input int InpWindow = 100;          // R/S analysis window (100 bars)
input int InpSubdivisions = 5;      // Number of subdivision levels for R/S
input double InpTrendingThreshold = 0.55;   // H > 0.55 = trending
input double InpMeanRevThreshold = 0.45;    // H < 0.45 = mean-reverting

//--- Indicator buffers
double BufferHurstValue[];        // Buffer 0: Raw Hurst exponent
double BufferHurstSignal[];       // Buffer 1: Discretized signal (-1, 0, 1)

//--- Hurst signal constants
#define HURST_MEANREVERT -1
#define HURST_RANDOM     0
#define HURST_TRENDING   1

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize buffers for output
   SetIndexBuffer(0, BufferHurstValue, INDICATOR_DATA);
   SetIndexBuffer(1, BufferHurstSignal, INDICATOR_DATA);

   // Set plot properties
   PlotIndexSetString(0, PLOT_LABEL, "HurstValue");
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetString(1, PLOT_LABEL, "HurstSignal");
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, 0.0);

   IndicatorSetString(INDICATOR_SHORTNAME, "HurstExponent(" +
                      IntegerToString(InpWindow) + "," +
                      IntegerToString(InpSubdivisions) + ")");

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
   // Need enough bars for analysis
   if(rates_total < InpWindow)
      return(0);

   int start = 0;
   if(prev_calculated > 0)
      start = prev_calculated - 1;

   // Calculate for new bars (update every 10 bars to reduce overhead)
   for(int i = start; i < rates_total; i++)
   {
      if(i < InpWindow - 1)
      {
         BufferHurstValue[i] = 0.5; // Default to 0.5 (random walk)
         BufferHurstSignal[i] = HURST_RANDOM;
         continue;
      }

      // Calculate Hurst exponent for current window
      double hurstValue = CalculateHurst(close, i, InpWindow, InpSubdivisions);

      BufferHurstValue[i] = hurstValue;

      // Discretize Hurst value into signal
      int signal = HURST_RANDOM;
      if(hurstValue > InpTrendingThreshold)
         signal = HURST_TRENDING;
      else if(hurstValue < InpMeanRevThreshold)
         signal = HURST_MEANREVERT;

      BufferHurstSignal[i] = (double)signal;
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Calculate Hurst Exponent via R/S Analysis                        |
//|                                                                   |
//| Algorithm:                                                        |
//| 1. Divide window into subdivisions                                |
//| 2. For each subdivision, calculate rescaled range (R/S)           |
//| 3. For multiple scales, fit log(R/S) = H*log(n) + intercept      |
//| 4. Return slope H from log-log regression                         |
//+------------------------------------------------------------------+
double CalculateHurst(const double &close[], int barIndex, int windowSize, int subdivisions)
{
   if(barIndex < windowSize - 1) return 0.5;

   // Collect closing prices for the window
   double window[];
   ArrayResize(window, windowSize);

   for(int i = 0; i < windowSize; i++)
   {
      window[i] = close[barIndex - (windowSize - 1 - i)];
   }

   // Calculate log-scale values for R/S at different subdivisions
   double logScales[];
   double logRS[];
   ArrayResize(logScales, subdivisions);
   ArrayResize(logRS, subdivisions);

   // Test different scales (from smaller to larger subdivisions)
   for(int scale = 1; scale <= subdivisions; scale++)
   {
      int n = windowSize / scale;
      if(n < 2) break;

      // Calculate mean R/S for this scale
      double rs = CalculateRSForScale(window, windowSize, n);

      logScales[scale - 1] = MathLog((double)n);
      logRS[scale - 1] = MathLog(rs);
   }

   // Perform linear regression: log(R/S) = H * log(n) + intercept
   double hurst = LinearRegression(logScales, logRS, subdivisions);

   // Clamp to reasonable range [0.0, 1.0]
   if(hurst < 0.0) hurst = 0.0;
   if(hurst > 1.0) hurst = 1.0;

   return hurst;
}

//+------------------------------------------------------------------+
//| Calculate R/S (Rescaled Range) for a given scale                |
//+------------------------------------------------------------------+
double CalculateRSForScale(const double &window[], int windowSize, int scaleSize)
{
   int numChunks = windowSize / scaleSize;
   if(numChunks < 1) return 1.0;

   double totalRS = 0.0;

   // Process each chunk
   for(int chunk = 0; chunk < numChunks; chunk++)
   {
      int startIdx = chunk * scaleSize;
      int endIdx = startIdx + scaleSize;

      // Calculate mean of chunk
      double chunkMean = 0.0;
      for(int i = startIdx; i < endIdx && i < windowSize; i++)
      {
         chunkMean += window[i];
      }
      chunkMean /= scaleSize;

      // Calculate cumulative mean-adjusted values
      double maxRange = -1e10;
      double minRange = 1e10;
      double cumulativeSum = 0.0;

      for(int i = startIdx; i < endIdx && i < windowSize; i++)
      {
         cumulativeSum += (window[i] - chunkMean);
         if(cumulativeSum > maxRange) maxRange = cumulativeSum;
         if(cumulativeSum < minRange) minRange = cumulativeSum;
      }

      // Calculate range
      double range = maxRange - minRange;

      // Calculate standard deviation of chunk
      double stdDev = 0.0;
      for(int i = startIdx; i < endIdx && i < windowSize; i++)
      {
         double diff = window[i] - chunkMean;
         stdDev += diff * diff;
      }
      stdDev = MathSqrt(stdDev / scaleSize);

      // Avoid division by zero
      if(stdDev < 1e-10) stdDev = 1e-10;

      // Calculate rescaled range (R/S)
      totalRS += range / stdDev;
   }

   // Average R/S across all chunks
   double avgRS = totalRS / numChunks;

   return avgRS;
}

//+------------------------------------------------------------------+
//| Linear Regression: fit log(R/S) = H*log(n) + intercept          |
//+------------------------------------------------------------------+
double LinearRegression(const double &x[], const double &y[], int count)
{
   if(count < 2) return 0.5;

   double sumX = 0.0;
   double sumY = 0.0;
   double sumXY = 0.0;
   double sumX2 = 0.0;

   int validCount = 0;

   for(int i = 0; i < count; i++)
   {
      if(x[i] > 0 && y[i] > -1e10)
      {
         sumX += x[i];
         sumY += y[i];
         sumXY += x[i] * y[i];
         sumX2 += x[i] * x[i];
         validCount++;
      }
   }

   if(validCount < 2) return 0.5;

   double meanX = sumX / validCount;
   double meanY = sumY / validCount;

   double numerator = sumXY - validCount * meanX * meanY;
   double denominator = sumX2 - validCount * meanX * meanX;

   if(MathAbs(denominator) < 1e-10) return 0.5;

   double slope = numerator / denominator;

   return slope;
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Clean up arrays if needed
}

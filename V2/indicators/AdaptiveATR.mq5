//+------------------------------------------------------------------+
//|                                                     AdaptiveATR.mq5 |
//|                                   MT5 POC - Adaptive Volatility ATR |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 3
#property indicator_plots   1
#property indicator_label1  "AdaptiveATR"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrBlueViolet
#property indicator_width1  2

//--- Input parameters
input int InpATRPeriodMin = 7;      // Minimum ATR period (fast)
input int InpATRPeriodMax = 28;     // Maximum ATR period (stable)
input int InpLookbackWindow = 100;  // 100-bar reference window for percentile rank
input int InpATRBasePeriod = 14;    // Base ATR period for comparison (neutral point)

//--- Indicator buffers
double BufferATR[];           // Buffer 0: Current ATR value using adaptive period
double BufferPercentile[];    // Buffer 1: Percentile rank of current ATR (0-100)
double BufferPeriod[];        // Buffer 2: Current period in use (7-28)

//--- Utility arrays for ATR calculation
double ATR14Values[];         // Store ATR(14) values for percentile calculation (100-bar window)
int ATRWindowPos = 0;         // Current position in circular buffer
int ValidBarsInWindow = 0;    // Count of valid bars in window

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize buffers for output
   SetIndexBuffer(0, BufferATR, INDICATOR_DATA);
   SetIndexBuffer(1, BufferPercentile, INDICATOR_DATA);
   SetIndexBuffer(2, BufferPeriod, INDICATOR_DATA);

   // Reserve array for 100-bar ATR(14) rolling window
   ArrayResize(ATR14Values, InpLookbackWindow);
   ArrayInitialize(ATR14Values, 0.0);
   ATRWindowPos = 0;
   ValidBarsInWindow = 0;

   // Set plot properties
   PlotIndexSetString(0, PLOT_LABEL, "AdaptiveATR");
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0.0);

   IndicatorSetString(INDICATOR_SHORTNAME, "AdaptiveATR(" + IntegerToString(InpATRBasePeriod) + ")");

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
   // Need enough bars for ATR base period + lookback window
   if(rates_total < InpATRBasePeriod + InpLookbackWindow)
      return(0);

   int start = prev_calculated - 1;
   if(start < InpATRBasePeriod + InpLookbackWindow - 1)
      start = InpATRBasePeriod + InpLookbackWindow - 1;

   // Calculate for new bars
   for(int i = start; i < rates_total; i++)
   {
      // Step 1: Calculate ATR(14) for current bar using arrays
      double atr14 = CalcATR(high, low, close, i, InpATRBasePeriod);

      if(atr14 <= 0) continue; // Skip if ATR calculation failed

      // Step 2: Add current ATR(14) to rolling window (circular buffer)
      if(ATR14Values[ATRWindowPos] == 0.0 && ValidBarsInWindow < InpLookbackWindow)
         ValidBarsInWindow++; // Count new valid entries up to window size

      ATR14Values[ATRWindowPos] = atr14;
      ATRWindowPos = (ATRWindowPos + 1) % InpLookbackWindow;

      // Step 3: Calculate percentile rank of current ATR(14) in window
      double percentile = CalculatePercentileRank(atr14);

      // Step 4: Determine adaptive period based on percentile
      int adaptivePeriod = DetermineAdaptivePeriod(percentile);

      // Step 5: Calculate final ATR using adaptive period
      double adaptiveATR = CalcATR(high, low, close, i, adaptivePeriod);

      // Step 6: Output to buffers
      BufferATR[i] = adaptiveATR;
      BufferPercentile[i] = percentile;
      BufferPeriod[i] = (double)adaptivePeriod;
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Calculate simple ATR from price arrays (SMA of True Range)       |
//+------------------------------------------------------------------+
double CalcATR(const double &high[], const double &low[], const double &close[], int bar, int period)
{
   if(bar < period) return 0.0;
   double sum = 0.0;
   for(int k = bar - period + 1; k <= bar; k++)
   {
      double tr = high[k] - low[k];
      if(k > 0)
      {
         tr = MathMax(tr, MathAbs(high[k] - close[k-1]));
         tr = MathMax(tr, MathAbs(low[k]  - close[k-1]));
      }
      sum += tr;
   }
   return sum / period;
}

//+------------------------------------------------------------------+
//| Calculate percentile rank of given value in rolling window        |
//+------------------------------------------------------------------+
double CalculatePercentileRank(double value)
{
   if(InpLookbackWindow < 1) return 50.0;

   int count_below = 0;
   int count_equal = 0;

   for(int i = 0; i < InpLookbackWindow; i++)
   {
      if(ATR14Values[i] > 0) // Only count valid values
      {
         if(ATR14Values[i] < value)
            count_below++;
         else if(MathAbs(ATR14Values[i] - value) < 1e-6)
            count_equal++;
      }
   }

   // Percentile rank = (count_below + 0.5 * count_equal) / total * 100
   double percentile = ((double)count_below + 0.5 * count_equal) / InpLookbackWindow * 100.0;

   // Clamp to valid range
   if(percentile < 0) percentile = 0;
   if(percentile > 100) percentile = 100;

   return percentile;
}

//+------------------------------------------------------------------+
//| Determine adaptive ATR period based on percentile rank           |
//+------------------------------------------------------------------+
int DetermineAdaptivePeriod(double percentile)
{
   int period;

   if(percentile > 80.0)
   {
      // High volatility (top 20%): use fast period
      period = InpATRPeriodMin;
   }
   else if(percentile < 20.0)
   {
      // Low volatility (bottom 20%): use stable period
      period = InpATRPeriodMax;
   }
   else
   {
      // Linear interpolation for 20-80 percentile range
      // percentile 20 → period 28
      // percentile 80 → period 7
      double t = (percentile - 20.0) / 60.0; // 0 to 1
      period = InpATRPeriodMax - (int)(t * (InpATRPeriodMax - InpATRPeriodMin) + 0.5);
   }

   // Clamp to valid range
   if(period < InpATRPeriodMin) period = InpATRPeriodMin;
   if(period > InpATRPeriodMax) period = InpATRPeriodMax;

   return period;
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Clean up arrays if needed
}

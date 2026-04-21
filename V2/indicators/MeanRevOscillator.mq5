//+------------------------------------------------------------------+
//|                                            MeanRevOscillator.mq5 |
//|                 MT5 POC - Z-Score Mean Reversion with Half-Life |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 4
#property indicator_plots   4
#property indicator_label1  "ZScore"
#property indicator_label2  "UpperThreshold"
#property indicator_label3  "LowerThreshold"
#property indicator_label4  "HalfLife"
#property indicator_type1   DRAW_LINE
#property indicator_type2   DRAW_LINE
#property indicator_type3   DRAW_LINE
#property indicator_type4   DRAW_LINE
#property indicator_color1  clrDodgerBlue
#property indicator_color2  clrRed
#property indicator_color3  clrGreen
#property indicator_color4  clrOrange
#property indicator_width1  2
#property indicator_width2  1
#property indicator_width3  1
#property indicator_width4  1
#property indicator_style2  STYLE_DOT
#property indicator_style3  STYLE_DOT

//--- Input parameters
input int InpPeriod = 48;           // Z-score lookback period (48 for AUDNZD, 30 for EURGBP)
input int InpHalfLifePeriod = 100;  // Period for half-life OLS regression
input double InpUpperThreshold = 2.0; // Upper z-score threshold line
input double InpLowerThreshold = -2.0; // Lower z-score threshold line

//--- Indicator buffers
double BufferZScore[];            // Buffer 0: Z-score value
double BufferUpperThreshold[];    // Buffer 1: Upper threshold line
double BufferLowerThreshold[];    // Buffer 2: Lower threshold line
double BufferHalfLife[];          // Buffer 3: Computed half-life in bars

//--- Utility arrays
double PriceChanges[];            // Store price changes for half-life OLS
double SimpleMovingAverage[];     // Store SMA values
double StandardDeviation[];       // Store StdDev values

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize buffers for output
   SetIndexBuffer(0, BufferZScore, INDICATOR_DATA);
   SetIndexBuffer(1, BufferUpperThreshold, INDICATOR_DATA);
   SetIndexBuffer(2, BufferLowerThreshold, INDICATOR_DATA);
   SetIndexBuffer(3, BufferHalfLife, INDICATOR_DATA);

   // Reserve utility arrays
   ArrayResize(PriceChanges, InpHalfLifePeriod);
   ArrayResize(SimpleMovingAverage, 0);
   ArrayResize(StandardDeviation, 0);

   // Set plot properties
   PlotIndexSetString(0, PLOT_LABEL, "ZScore");
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetString(1, PLOT_LABEL, "UpperThreshold");
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetString(2, PLOT_LABEL, "LowerThreshold");
   PlotIndexSetDouble(2, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetString(3, PLOT_LABEL, "HalfLife");
   PlotIndexSetDouble(3, PLOT_EMPTY_VALUE, 0.0);

   IndicatorSetString(INDICATOR_SHORTNAME, "MeanRevOscillator(" +
                      IntegerToString(InpPeriod) + ")");

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
   if(rates_total < InpPeriod + InpHalfLifePeriod)
      return(0);

   int start = 0;
   if(prev_calculated > 0)
      start = prev_calculated - 1;

   // Calculate for new bars
   for(int i = start; i < rates_total; i++)
   {
      if(i < InpPeriod - 1)
      {
         BufferZScore[i] = 0.0;
         BufferUpperThreshold[i] = InpUpperThreshold;
         BufferLowerThreshold[i] = InpLowerThreshold;
         BufferHalfLife[i] = 0.0;
         continue;
      }

      // Step 1: Calculate SMA and StdDev for z-score
      double sma = CalcSMA(close, i, InpPeriod);
      double stdDev = CalculateStdDev(close, i, InpPeriod, sma);

      // Step 2: Calculate Z-score
      double zScore = 0.0;
      if(stdDev > 0)
         zScore = (close[i] - sma) / stdDev;

      BufferZScore[i] = zScore;

      // Step 3: Output threshold lines
      BufferUpperThreshold[i] = InpUpperThreshold;
      BufferLowerThreshold[i] = InpLowerThreshold;

      // Step 4: Calculate half-life using OLS regression (every 10 bars to reduce overhead)
      double halfLife = 0.0;
      if(i > InpHalfLifePeriod && i % 10 == 0)
      {
         // Collect price changes for OLS
         for(int j = 0; j < InpHalfLifePeriod && i - j >= 1; j++)
         {
            PriceChanges[j] = close[i - j] - close[i - j - 1];
         }

         // Calculate half-life from OLS regression
         halfLife = CalculateHalfLife(close, i);
      }
      else if(i > 0 && BufferHalfLife[i-1] > 0)
      {
         halfLife = BufferHalfLife[i-1]; // Carry forward previous value
      }

      BufferHalfLife[i] = halfLife;
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Calculate SMA from close array                                   |
//+------------------------------------------------------------------+
double CalcSMA(const double &close[], int bar, int period)
{
   if(bar < period - 1) return 0.0;
   double sum = 0.0;
   for(int k = bar - period + 1; k <= bar; k++)
      sum += close[k];
   return sum / period;
}

//+------------------------------------------------------------------+
//| Calculate Standard Deviation                                     |
//+------------------------------------------------------------------+
double CalculateStdDev(const double &close[], int barIndex, int period, double sma)
{
   if(barIndex < period - 1) return 0.0;

   double sumSquaredDiff = 0.0;

   for(int i = 0; i < period; i++)
   {
      int idx = barIndex - i;
      if(idx < 0) break;

      double diff = close[idx] - sma;
      sumSquaredDiff += diff * diff;
   }

   double variance = sumSquaredDiff / period;
   double stdDev = MathSqrt(variance);

   return stdDev;
}

//+------------------------------------------------------------------+
//| Calculate Half-Life via OLS Regression                           |
//| Fits: dP(t) = lambda * P(t-1) + error                           |
//| Half-Life = -ln(2) / lambda                                      |
//+------------------------------------------------------------------+
double CalculateHalfLife(const double &close[], int barIndex)
{
   if(barIndex < InpHalfLifePeriod + 1) return 0.0;

   int n = InpHalfLifePeriod;
   double sumX = 0.0;
   double sumY = 0.0;
   double sumXY = 0.0;
   double sumX2 = 0.0;

   // Collect price changes and lagged prices for OLS
   for(int i = 0; i < n && barIndex - i - 1 >= 0; i++)
   {
      double priceChange = close[barIndex - i] - close[barIndex - i - 1];  // dP(t)
      double laggedPrice = close[barIndex - i - 1];                        // P(t-1)

      sumX += laggedPrice;
      sumY += priceChange;
      sumXY += laggedPrice * priceChange;
      sumX2 += laggedPrice * laggedPrice;
   }

   // Calculate OLS slope (lambda)
   double meanX = sumX / n;
   double meanY = sumY / n;

   double numerator = sumXY - n * meanX * meanY;
   double denominator = sumX2 - n * meanX * meanX;

   if(MathAbs(denominator) < 1e-10) return 0.0;

   double lambda = numerator / denominator;

   // Calculate half-life: -ln(2) / lambda
   if(lambda >= 0) return 0.0; // Mean-reversion requires negative lambda

   double halfLife = -MathLog(2.0) / lambda;

   // Clamp to reasonable range (0.5 to 500 bars)
   if(halfLife < 0.5) halfLife = 0.5;
   if(halfLife > 500) halfLife = 500;

   return halfLife;
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Clean up arrays if needed
}

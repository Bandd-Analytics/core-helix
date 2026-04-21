//+------------------------------------------------------------------+
//|                                               VolatilityRegime.mq5 |
//|                           MT5 POC - Volatility Regime Classification |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 1
#property indicator_plots   1
#property indicator_label1  "VolatilityRegime"
#property indicator_type1   DRAW_HISTOGRAM
#property indicator_color1  clrDodgerBlue
#property indicator_width1  2

//--- Input parameters
input int InpATRPeriod = 14;        // ATR period for volatility calculation
input int InpLookbackWindow = 252;  // 252 H4 bars ≈ 1 year lookback

//--- Indicator buffer
double BufferRegimeState[];    // Buffer 0: Regime state code (0, 1, or 2)

//--- Utility arrays
double ATRWindow[];           // Store ATR(14) values for percentile calculation
int WindowPos = 0;            // Current position in circular buffer
int ValidBarsInWindow = 0;    // Count of valid bars in window

//--- Regime state constants
#define REGIME_LOW      0     // Below 20th percentile - skip trading
#define REGIME_NORMAL   1     // 20-80th percentile - full position sizing
#define REGIME_HIGH     2     // Above 80th percentile - reduce size by 50%

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize buffer for output
   SetIndexBuffer(0, BufferRegimeState, INDICATOR_DATA);

   // Reserve array for 252-bar ATR lookback window
   ArrayResize(ATRWindow, InpLookbackWindow);
   ArrayInitialize(ATRWindow, 0.0);
   WindowPos = 0;
   ValidBarsInWindow = 0;

   // Set plot properties
   PlotIndexSetString(0, PLOT_LABEL, "VolatilityRegime");
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0.0);

   IndicatorSetString(INDICATOR_SHORTNAME, "VolatilityRegime(" +
                      IntegerToString(InpATRPeriod) + "," +
                      IntegerToString(InpLookbackWindow) + ")");

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
   // Need enough bars for ATR period + lookback window
   if(rates_total < InpATRPeriod + InpLookbackWindow)
      return(0);

   int start = prev_calculated - 1;
   if(start < InpATRPeriod + InpLookbackWindow - 1)
      start = InpATRPeriod + InpLookbackWindow - 1;

   // Calculate for new bars
   for(int i = start; i < rates_total; i++)
   {
      // Step 1: Calculate ATR(14) for current bar
      double atr = CalcATR(high, low, close, i, InpATRPeriod);

      if(atr <= 0) continue; // Skip if ATR calculation failed

      // Step 2: Add current ATR to rolling window (circular buffer)
      if(ATRWindow[WindowPos] == 0.0 && ValidBarsInWindow < InpLookbackWindow)
         ValidBarsInWindow++; // Count new valid entries up to window size

      ATRWindow[WindowPos] = atr;
      WindowPos = (WindowPos + 1) % InpLookbackWindow;

      // Step 3: Calculate percentile rank of current ATR in window
      double percentile = CalculatePercentileRank(atr);

      // Step 4: Determine regime state based on percentile
      int regimeState = DetermineRegimeState(percentile);

      // Step 5: Output to buffer
      BufferRegimeState[i] = (double)regimeState;
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
//| Calculate percentile rank of given ATR value in window            |
//+------------------------------------------------------------------+
double CalculatePercentileRank(double value)
{
   if(ValidBarsInWindow < 1) return 50.0;

   int count_below = 0;
   int count_equal = 0;

   for(int i = 0; i < InpLookbackWindow; i++)
   {
      if(ATRWindow[i] > 0) // Only count valid values
      {
         if(ATRWindow[i] < value)
            count_below++;
         else if(MathAbs(ATRWindow[i] - value) < 1e-6)
            count_equal++;
      }
   }

   // Percentile rank = (count_below + 0.5 * count_equal) / valid_count * 100
   double percentile = ((double)count_below + 0.5 * count_equal) / ValidBarsInWindow * 100.0;

   // Clamp to valid range
   if(percentile < 0) percentile = 0;
   if(percentile > 100) percentile = 100;

   return percentile;
}

//+------------------------------------------------------------------+
//| Determine regime state based on ATR percentile rank              |
//+------------------------------------------------------------------+
int DetermineRegimeState(double percentile)
{
   int regime;

   if(percentile < 20.0)
   {
      // Low volatility: skip trading
      regime = REGIME_LOW;
   }
   else if(percentile > 80.0)
   {
      // High volatility: reduce position size by 50%
      regime = REGIME_HIGH;
   }
   else
   {
      // Normal volatility: full position sizing
      regime = REGIME_NORMAL;
   }

   return regime;
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Clean up arrays if needed
}

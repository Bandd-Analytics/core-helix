//+------------------------------------------------------------------+
//|                                                   DonchianADX.mq5 |
//|                      MT5 POC - Donchian Breakout with ADX Filter |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 5
#property indicator_plots   5
#property indicator_label1  "UpperChannel"
#property indicator_label2  "LowerChannel"
#property indicator_label3  "Signal"
#property indicator_label4  "ExitUpper"
#property indicator_label5  "ExitLower"
#property indicator_type1   DRAW_LINE
#property indicator_type2   DRAW_LINE
#property indicator_type3   DRAW_HISTOGRAM
#property indicator_type4   DRAW_LINE
#property indicator_type5   DRAW_LINE
#property indicator_color1  clrDodgerBlue
#property indicator_color2  clrDodgerBlue
#property indicator_color3  clrRed
#property indicator_color4  clrSilver
#property indicator_color5  clrSilver
#property indicator_width1  2
#property indicator_width2  2
#property indicator_width3  2
#property indicator_width4  1
#property indicator_width5  1
#property indicator_style4  STYLE_DOT
#property indicator_style5  STYLE_DOT

//--- Input parameters
input int InpEntryPeriod = 20;     // Entry Donchian period (highest/lowest)
input int InpExitPeriod = 10;      // Exit Donchian period (highest/lowest)
input int InpADXPeriod = 14;       // ADX period for trend confirmation
input double InpADXThreshold = 25.0; // ADX threshold for signal validation

//--- Indicator buffers
double BufferUpperChannel[];   // Buffer 0: 20-period Donchian high
double BufferLowerChannel[];   // Buffer 1: 20-period Donchian low
double BufferSignal[];         // Buffer 2: Signal (1=long, -1=short, 0=none)
double BufferExitUpper[];      // Buffer 3: 10-period exit high
double BufferExitLower[];      // Buffer 4: 10-period exit low

//--- Internal tracking for signal generation
bool PreviousPriceAboveUpper[];  // Track if previous bar was above upper channel
bool PreviousPriceBelowLower[];  // Track if previous bar was below lower channel

//--- Signal constants
#define SIGNAL_NONE   0
#define SIGNAL_LONG   1
#define SIGNAL_SHORT -1

//--- Indicator handle
int m_adxHandle = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize buffers for output
   SetIndexBuffer(0, BufferUpperChannel, INDICATOR_DATA);
   SetIndexBuffer(1, BufferLowerChannel, INDICATOR_DATA);
   SetIndexBuffer(2, BufferSignal, INDICATOR_DATA);
   SetIndexBuffer(3, BufferExitUpper, INDICATOR_DATA);
   SetIndexBuffer(4, BufferExitLower, INDICATOR_DATA);

   // Reserve arrays for tracking state
   ArrayResize(PreviousPriceAboveUpper, 0);
   ArrayResize(PreviousPriceBelowLower, 0);

   // Set plot properties
   PlotIndexSetString(0, PLOT_LABEL, "UpperChannel");
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetString(1, PLOT_LABEL, "LowerChannel");
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetString(2, PLOT_LABEL, "Signal");
   PlotIndexSetDouble(2, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetString(3, PLOT_LABEL, "ExitUpper");
   PlotIndexSetDouble(3, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetString(4, PLOT_LABEL, "ExitLower");
   PlotIndexSetDouble(4, PLOT_EMPTY_VALUE, 0.0);

   IndicatorSetString(INDICATOR_SHORTNAME, "DonchianADX(" +
                      IntegerToString(InpEntryPeriod) + "," +
                      IntegerToString(InpExitPeriod) + "," +
                      IntegerToString(InpADXPeriod) + ")");

   m_adxHandle = iADX(_Symbol, PERIOD_CURRENT, InpADXPeriod);
   if(m_adxHandle == INVALID_HANDLE) return(INIT_FAILED);

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
   if(rates_total < InpEntryPeriod + 1)
      return(0);

   int start = 0;
   if(prev_calculated > 0)
      start = prev_calculated - 1;

   // Copy ADX values for all bars (CopyBuffer index 0 = most recent bar)
   double adxBuf[];
   if(CopyBuffer(m_adxHandle, 0, 0, rates_total, adxBuf) <= 0)
      return(prev_calculated);

   // Calculate for new bars
   for(int i = start; i < rates_total; i++)
   {
      // Step 1: Calculate Donchian entry channel (20-period)
      double upperChannel = CalculateDonchianHigh(high, i, InpEntryPeriod);
      double lowerChannel = CalculateDonchianLow(low, i, InpEntryPeriod);

      BufferUpperChannel[i] = upperChannel;
      BufferLowerChannel[i] = lowerChannel;

      // Step 2: Calculate exit channels (10-period)
      double exitUpper = CalculateDonchianHigh(high, i, InpExitPeriod);
      double exitLower = CalculateDonchianLow(low, i, InpExitPeriod);

      BufferExitUpper[i] = exitUpper;
      BufferExitLower[i] = exitLower;

      // Step 3: Get ADX value for confirmation (reverse index: buf[0]=newest)
      double adx = adxBuf[rates_total - 1 - i];

      // Step 4: Check for breakout signal on close (not intrabar)
      // Signal fires only when price crosses channel boundary on close
      int signal = SIGNAL_NONE;

      if(adx >= InpADXThreshold)
      {
         if(i > 0)
         {
            bool priceAboveUpper = (close[i] > upperChannel);
            bool priceBelowLower = (close[i] < lowerChannel);
            bool prevAboveUpper = (close[i-1] > upperChannel);
            bool prevBelowLower = (close[i-1] < lowerChannel);

            // Long signal: price closes above upper channel (and wasn't before)
            if(priceAboveUpper && !prevAboveUpper)
            {
               signal = SIGNAL_LONG;
            }
            // Short signal: price closes below lower channel (and wasn't before)
            else if(priceBelowLower && !prevBelowLower)
            {
               signal = SIGNAL_SHORT;
            }
         }
      }

      // Step 5: Output signal to buffer
      BufferSignal[i] = (double)signal;
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Calculate Donchian High (highest high over period)               |
//+------------------------------------------------------------------+
double CalculateDonchianHigh(const double &high[], int barIndex, int period)
{
   if(barIndex < period - 1) return 0.0;

   double maxHigh = high[barIndex];

   for(int i = 1; i < period; i++)
   {
      int idx = barIndex - i;
      if(idx < 0) break;
      if(high[idx] > maxHigh)
         maxHigh = high[idx];
   }

   return maxHigh;
}

//+------------------------------------------------------------------+
//| Calculate Donchian Low (lowest low over period)                  |
//+------------------------------------------------------------------+
double CalculateDonchianLow(const double &low[], int barIndex, int period)
{
   if(barIndex < period - 1) return 0.0;

   double minLow = low[barIndex];

   for(int i = 1; i < period; i++)
   {
      int idx = barIndex - i;
      if(idx < 0) break;
      if(low[idx] < minLow)
         minLow = low[idx];
   }

   return minLow;
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(m_adxHandle != INVALID_HANDLE)
      IndicatorRelease(m_adxHandle);
}

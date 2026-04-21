//+------------------------------------------------------------------+
//|                                                 SessionFilter.mq5 |
//|                    MT5 POC - Trading Session and News Event Filter |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2
#property indicator_label1  "SessionActive"
#property indicator_label2  "OverlapActive"
#property indicator_type1   DRAW_HISTOGRAM
#property indicator_type2   DRAW_HISTOGRAM
#property indicator_color1  clrLimeGreen
#property indicator_color2  clrGoldenrod
#property indicator_width1  1
#property indicator_width2  1

//--- Input parameters
input int InpLondonOpen = 7;      // London session open (GMT)
input int InpLondonClose = 16;    // London session close (GMT)
input int InpNewYorkOpen = 13;    // New York session open (GMT)
input int InpNewYorkClose = 22;   // New York session close (GMT)
input int InpTokyoOpen = 0;       // Tokyo session open (GMT)
input int InpTokyoClose = 9;      // Tokyo session close (GMT)
input int InpSydneyOpen = 22;     // Sydney session open (GMT)
input int InpSydneyClose = 7;     // Sydney session close (GMT, wraps around)
input int InpNewsBlackoutMinutes = 15; // Minutes before/after major news

//--- Indicator buffers
double BufferSessionActive[];  // Buffer 0: Any session active (1/0)
double BufferOverlapActive[];  // Buffer 1: Session overlap active (1/0)

//--- Session state constants
#define SESSION_LONDON   1
#define SESSION_NEWYORK  2
#define SESSION_TOKYO    4
#define SESSION_SYDNEY   8

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize buffers for output
   SetIndexBuffer(0, BufferSessionActive, INDICATOR_DATA);
   SetIndexBuffer(1, BufferOverlapActive, INDICATOR_DATA);

   // Set plot properties
   PlotIndexSetString(0, PLOT_LABEL, "SessionActive");
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetString(1, PLOT_LABEL, "OverlapActive");
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, 0.0);

   IndicatorSetString(INDICATOR_SHORTNAME, "SessionFilter");

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
   int start = 0;
   if(prev_calculated > 0)
      start = prev_calculated - 1;

   // Calculate for all bars
   for(int i = start; i < rates_total; i++)
   {
      // Get current GMT time
      datetime barTime = time[i];
      int hourGMT = Hour(barTime);
      int minuteGMT = Minute(barTime);
      double timeDecimal = hourGMT + minuteGMT / 60.0;

      // Step 1: Determine which sessions are active
      int activeSessions = 0;

      if(IsSessionActive(timeDecimal, InpLondonOpen, InpLondonClose, false))
         activeSessions |= SESSION_LONDON;

      if(IsSessionActive(timeDecimal, InpNewYorkOpen, InpNewYorkClose, false))
         activeSessions |= SESSION_NEWYORK;

      if(IsSessionActive(timeDecimal, InpTokyoOpen, InpTokyoClose, false))
         activeSessions |= SESSION_TOKYO;

      if(IsSessionActive(timeDecimal, InpSydneyOpen, InpSydneyClose, true))
         activeSessions |= SESSION_SYDNEY;

      // Step 2: Determine if any session is active
      int sessionActive = (activeSessions != 0) ? 1 : 0;

      // Step 3: Determine if overlapping sessions exist
      int overlapActive = DetectSessionOverlap(activeSessions);

      // Step 4: Apply news event blackout (if implemented with external data source)
      // For now, this is a placeholder - news events would be managed by the EA
      int newsBlackout = 0;
      // newsBlackout = CheckNewsBlackout(barTime);

      // Step 5: Output to buffers
      BufferSessionActive[i] = (double)sessionActive;
      BufferOverlapActive[i] = (double)overlapActive;
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Check if current time falls within a session                     |
//+------------------------------------------------------------------+
bool IsSessionActive(double timeDecimal, int sessionOpen, int sessionClose, bool wrapsAround)
{
   if(!wrapsAround)
   {
      // Normal session (doesn't wrap midnight): e.g., London 07:00-16:00
      return (timeDecimal >= sessionOpen && timeDecimal < sessionClose);
   }
   else
   {
      // Wrapping session: e.g., Sydney 22:00-07:00
      return (timeDecimal >= sessionOpen || timeDecimal < sessionClose);
   }
}

//+------------------------------------------------------------------+
//| Detect if multiple sessions are overlapping                      |
//+------------------------------------------------------------------+
int DetectSessionOverlap(int activeSessions)
{
   // Count number of active sessions
   int sessionCount = 0;

   if(activeSessions & SESSION_LONDON)   sessionCount++;
   if(activeSessions & SESSION_NEWYORK)  sessionCount++;
   if(activeSessions & SESSION_TOKYO)    sessionCount++;
   if(activeSessions & SESSION_SYDNEY)   sessionCount++;

   // Return 1 if 2 or more sessions overlap, 0 otherwise
   return (sessionCount >= 2) ? 1 : 0;
}

//+------------------------------------------------------------------+
//| Check if current time falls in news event blackout period        |
//| Note: This is a placeholder for future implementation with       |
//| external news event timestamps array                             |
//+------------------------------------------------------------------+
bool CheckNewsBlackout(datetime barTime)
{
   // This would read from a news event timestamp array
   // For now, return false (no blackout)
   // Example implementation would iterate through known news event times
   // and check if barTime is within BlackoutMinutes of any event
   return false;
}

//+------------------------------------------------------------------+
//| Hour extraction helper (for GMT time)                            |
//+------------------------------------------------------------------+
int Hour(datetime dt)
{
   return (int)(dt / 3600) % 24;
}

//+------------------------------------------------------------------+
//| Minute extraction helper                                         |
//+------------------------------------------------------------------+
int Minute(datetime dt)
{
   return (int)(dt / 60) % 60;
}

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Clean up if needed
}

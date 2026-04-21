//+------------------------------------------------------------------+
//|                                                 CTrendSignal.mqh |
//|                   MT5 POC - Trend Following Signal Generator |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CTREND_SIGNAL_H
#define CTREND_SIGNAL_H

#include "CSignalManager.mqh"

//--- Trend signal class
class CTrendSignal : public CSignalManager
{
private:
   int       ema50Handle;
   int       sma100Handle;
   int       rsiHandle;
   int       diHandle;
   double    lastDonchianSignal;
   int       barsHeld;

public:
   // Constructor & Destructor
   CTrendSignal();
   ~CTrendSignal();

   // Initialization
   virtual bool  Init(SSymbolConfig &symbolConfig);
   virtual void  Deinit();

   // Signal generation
   virtual bool  GenerateSignal(SSignalEntry &signal);

private:
   // Signal scoring helpers
   int       ScoreDonchianBreakout(int donchianSignal);
   int       ScoreADXStrength(double adx);
   int       ScoreDIAlignment(int barIndex);
   int       ScoreMAAlignment(double ema50, double sma100, int direction);

   // Entry validation
   bool      ValidateADXThreshold(double adx);
   bool      ValidateSessionFilter(int barIndex);
   bool      ValidateTrendDirection(double ema50, double sma100, int direction);

   // Exit conditions
   bool      CheckDonchianExit(int barIndex, int direction);
   bool      CheckTimeExit();

   // Helper methods
   double    GetEMA50(int barIndex);
   double    GetSMA100(int barIndex);
   double    GetRSI(int barIndex);
   double    GetPlusDI(int barIndex);
   double    GetMinusDI(int barIndex);
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CTrendSignal::CTrendSignal() : ema50Handle(INVALID_HANDLE),
                               sma100Handle(INVALID_HANDLE),
                               rsiHandle(INVALID_HANDLE),
                               diHandle(INVALID_HANDLE),
                               lastDonchianSignal(0), barsHeld(0)
{
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CTrendSignal::~CTrendSignal()
{
   Deinit();
}

//+------------------------------------------------------------------+
//| Initialize trend signal generator                               |
//+------------------------------------------------------------------+
bool CTrendSignal::Init(SSymbolConfig &symbolConfig)
{
   if(!CSignalManager::Init(symbolConfig))
      return false;

   // Load trend-following indicators on H4 timeframe
   ema50Handle = iMA(NULL, PERIOD_H4, 50, 0, MODE_EMA, PRICE_CLOSE);
   sma100Handle = iMA(NULL, PERIOD_H4, 100, 0, MODE_SMA, PRICE_CLOSE);
   rsiHandle = iRSI(NULL, config.primaryTimeframe, 14, PRICE_CLOSE);
   diHandle = iADX(NULL, config.primaryTimeframe, 14);

   if(ema50Handle == INVALID_HANDLE || sma100Handle == INVALID_HANDLE ||
      rsiHandle == INVALID_HANDLE || diHandle == INVALID_HANDLE)
   {
      Print("Error: Failed to load trend indicators for ", config.symbol);
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Deinitialize signal generator                                   |
//+------------------------------------------------------------------+
void CTrendSignal::Deinit()
{
   if(ema50Handle != INVALID_HANDLE)
      IndicatorRelease(ema50Handle);
   if(sma100Handle != INVALID_HANDLE)
      IndicatorRelease(sma100Handle);
   if(rsiHandle != INVALID_HANDLE)
      IndicatorRelease(rsiHandle);
   if(diHandle != INVALID_HANDLE)
      IndicatorRelease(diHandle);

   CSignalManager::Deinit();
}

//+------------------------------------------------------------------+
//| Generate trend following signal                                 |
//+------------------------------------------------------------------+
bool CTrendSignal::GenerateSignal(SSignalEntry &signal)
{
   if(!isInitialized)
      return false;

   int barIndex = 0;  // Current bar
   double close = iClose(config.symbol, config.primaryTimeframe, barIndex);
   double atr = GetAdaptiveATR(barIndex);
   double adx = GetADX(barIndex);
   double ema50 = GetEMA50(barIndex);
   double sma100 = GetSMA100(barIndex);
   int donchianSignal = GetDonchianSignal(barIndex);
   int regimeCode = GetRegimeCode(barIndex);

   // Initialize signal
   signal.signalType = SIGNAL_NONE;
   signal.signalScore = 0;
   signal.signalTime = TimeCurrent();
   signal.regimeCode = regimeCode;

   // Step 1: Check for invalid conditions
   if(atr <= 0)
      return false;

   // Step 2: Validate ADX threshold
   if(!ValidateADXThreshold(adx))
      return false;

   if(!ValidateSessionFilter(barIndex))
      return false;

   // Step 3: Check Donchian breakout signal
   if(donchianSignal == SIGNAL_NONE)
      return false;

   // Step 4: Validate MA alignment confirms direction
   if(!ValidateTrendDirection(ema50, sma100, donchianSignal))
      return false;

   // Step 5: Calculate composite signal score (0-100)
   int totalScore = 0;

   totalScore += ScoreDonchianBreakout(donchianSignal);      // 0-40 points
   totalScore += ScoreADXStrength(adx);                      // 0-20 points
   totalScore += ScoreDIAlignment(barIndex);                 // 0-20 points
   totalScore += ScoreMAAlignment(ema50, sma100, donchianSignal); // 0-20 points

   signal.signalScore = (double)totalScore;

   // Check threshold
   if(totalScore < SIGNAL_THRESHOLD)
      return false;

   // Step 6: Set entry parameters
   signal.signalType = donchianSignal;
   signal.entryPrice = close;
   signal.stopLossPips = atr * config.atrStopMultiplier;
   signal.takeProfitPips = atr * 2.5;  // 2.5R for trend trades

   signal.signalReason = "Donchian Breakout ADX=" + DoubleToString(adx, 1) +
                        " DI-Align Score=" + IntegerToString(ScoreDIAlignment(barIndex)) +
                        " Score=" + IntegerToString(totalScore);

   lastDonchianSignal = donchianSignal;
   barsHeld = 0;

   return true;
}

//+------------------------------------------------------------------+
//| Score Donchian breakout signal (0-40 points)                   |
//+------------------------------------------------------------------+
int CTrendSignal::ScoreDonchianBreakout(int donchianSignal)
{
   // Donchian signal is binary: long (+1) or short (-1)
   // Strong confirmation = 40 points
   return (donchianSignal != SIGNAL_NONE) ? 40 : 0;
}

//+------------------------------------------------------------------+
//| Score ADX strength (0-20 points)                               |
//+------------------------------------------------------------------+
int CTrendSignal::ScoreADXStrength(double adx)
{
   // ADX scale: 20 = threshold, 40+ = very strong
   if(adx < 20) return 0;
   if(adx >= 40) return 20;
   if(adx >= 35) return 18;
   if(adx >= 30) return 15;

   // Linear scaling 20-30
   return (int)((adx - 20) / 10 * 15);
}

//+------------------------------------------------------------------+
//| Score DI alignment (0-20 points)                               |
//+------------------------------------------------------------------+
int CTrendSignal::ScoreDIAlignment(int barIndex)
{
   double plusDI = GetPlusDI(barIndex);
   double minusDI = GetMinusDI(barIndex);

   // Strong alignment when one DI significantly above the other
   double diff = MathAbs(plusDI - minusDI);

   if(diff > 25) return 20;
   if(diff > 20) return 15;
   if(diff > 15) return 10;
   if(diff > 10) return 5;

   return 0;
}

//+------------------------------------------------------------------+
//| Score MA alignment (0-20 points)                               |
//+------------------------------------------------------------------+
int CTrendSignal::ScoreMAAlignment(double ema50, double sma100, int direction)
{
   if(direction == SIGNAL_LONG)
   {
      // Long: EMA50 should be above SMA100
      if(ema50 > sma100)
      {
         double ratio = ema50 / sma100;
         if(ratio > 1.005) return 20;
         if(ratio > 1.003) return 15;
         if(ratio > 1.001) return 10;
         return 5;
      }
   }
   else if(direction == SIGNAL_SHORT)
   {
      // Short: EMA50 should be below SMA100
      if(ema50 < sma100)
      {
         double ratio = sma100 / ema50;
         if(ratio > 1.005) return 20;
         if(ratio > 1.003) return 15;
         if(ratio > 1.001) return 10;
         return 5;
      }
   }

   return 0;
}

//+------------------------------------------------------------------+
//| Validate ADX threshold for trend confirmation                   |
//+------------------------------------------------------------------+
bool CTrendSignal::ValidateADXThreshold(double adx)
{
   if(config.minADXForEntry <= 0)
      return true;

   return (adx >= config.minADXForEntry);
}

//+------------------------------------------------------------------+
//| Validate session filter                                         |
//+------------------------------------------------------------------+
bool CTrendSignal::ValidateSessionFilter(int barIndex)
{
   if(!config.respectSessionFilter)
      return true;

   // Get session filter from indicator
   int sessionActive = (int)GetIndicatorBuffer(2, 0, barIndex);

   return (sessionActive == 1);
}

//+------------------------------------------------------------------+
//| Validate trend direction matches MA alignment                   |
//+------------------------------------------------------------------+
bool CTrendSignal::ValidateTrendDirection(double ema50, double sma100, int direction)
{
   if(direction == SIGNAL_LONG)
      return (ema50 > sma100);
   else if(direction == SIGNAL_SHORT)
      return (ema50 < sma100);

   return false;
}

//+------------------------------------------------------------------+
//| Check Donchian exit condition                                   |
//+------------------------------------------------------------------+
bool CTrendSignal::CheckDonchianExit(int barIndex, int direction)
{
   // Would check 10-period exit channel
   // Placeholder for actual implementation
   return false;
}

//+------------------------------------------------------------------+
//| Check time-based exit                                           |
//+------------------------------------------------------------------+
bool CTrendSignal::CheckTimeExit()
{
   barsHeld++;
   int maxHold = 48;  // 48 bars for trending trades

   return (barsHeld > maxHold);
}

//+------------------------------------------------------------------+
//| Get EMA50 on H4 timeframe                                       |
//+------------------------------------------------------------------+
double CTrendSignal::GetEMA50(int barIndex)
{
   double buffer[];
   if(CopyBuffer(ema50Handle, 0, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get SMA100 on H4 timeframe                                      |
//+------------------------------------------------------------------+
double CTrendSignal::GetSMA100(int barIndex)
{
   double buffer[];
   if(CopyBuffer(sma100Handle, 0, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get RSI value                                                   |
//+------------------------------------------------------------------+
double CTrendSignal::GetRSI(int barIndex)
{
   double buffer[];
   if(CopyBuffer(rsiHandle, 0, barIndex, 1, buffer) <= 0)
      return 50.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get +DI from ADX indicator                                      |
//+------------------------------------------------------------------+
double CTrendSignal::GetPlusDI(int barIndex)
{
   double buffer[];
   if(CopyBuffer(diHandle, 1, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get -DI from ADX indicator                                      |
//+------------------------------------------------------------------+
double CTrendSignal::GetMinusDI(int barIndex)
{
   double buffer[];
   if(CopyBuffer(diHandle, 2, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

#endif

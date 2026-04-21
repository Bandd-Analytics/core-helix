//+------------------------------------------------------------------+
//|                                                CMeanRevSignal.mqh |
//|                  MT5 POC - Mean Reversion Signal Generator |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CMEANREV_SIGNAL_H
#define CMEANREV_SIGNAL_H

#include "CSignalManager.mqh"

//--- Mean reversion signal class
class CMeanRevSignal : public CSignalManager
{
private:
   int       rsiHandle;
   int       bbandHandle;
   double    lastZScore;
   int       barsHeld;

public:
   // Constructor & Destructor
   CMeanRevSignal();
   ~CMeanRevSignal();

   // Initialization
   virtual bool  Init(SSymbolConfig &symbolConfig);
   virtual void  Deinit();

   // Signal generation
   virtual bool  GenerateSignal(SSignalEntry &signal);

private:
   // Signal scoring helpers
   int       ScoreZScoreMagnitude(double zScore);
   int       ScoreRSIConfirmation(double zScore, int barIndex);
   int       ScoreBollingerBandTouch(int barIndex);
   int       ScoreHalfLifeValidity(double halfLife);

   // Entry validation
   bool      ValidateRangeBreakout(double currentPrice);
   bool      ValidateADXRegiming(double adx);
   bool      ValidateSessionFilter(int barIndex);

   // Exit conditions
   bool      CheckZScoreExit(double zScore);
   bool      CheckTimeExit();

   // Helper methods
   double    GetRSI(int barIndex);
   double    GetBBandUpper(int barIndex);
   double    GetBBandLower(int barIndex);
   double    GetBBandMiddle(int barIndex);
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CMeanRevSignal::CMeanRevSignal() : rsiHandle(INVALID_HANDLE),
                                   bbandHandle(INVALID_HANDLE),
                                   lastZScore(0.0), barsHeld(0)
{
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CMeanRevSignal::~CMeanRevSignal()
{
   Deinit();
}

//+------------------------------------------------------------------+
//| Initialize mean reversion signal generator                      |
//+------------------------------------------------------------------+
bool CMeanRevSignal::Init(SSymbolConfig &symbolConfig)
{
   if(!CSignalManager::Init(symbolConfig))
      return false;

   // Load RSI and Bollinger Bands
   rsiHandle = iRSI(NULL, config.primaryTimeframe, 14, PRICE_CLOSE);
   bbandHandle = iBands(NULL, config.primaryTimeframe, config.zScorePeriod, 0, 2.0, PRICE_CLOSE);

   if(rsiHandle == INVALID_HANDLE || bbandHandle == INVALID_HANDLE)
   {
      Print("Error: Failed to load RSI or Bollinger Bands for ", config.symbol);
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Deinitialize signal generator                                   |
//+------------------------------------------------------------------+
void CMeanRevSignal::Deinit()
{
   if(rsiHandle != INVALID_HANDLE)
      IndicatorRelease(rsiHandle);
   if(bbandHandle != INVALID_HANDLE)
      IndicatorRelease(bbandHandle);

   CSignalManager::Deinit();
}

//+------------------------------------------------------------------+
//| Generate mean reversion signal                                  |
//+------------------------------------------------------------------+
bool CMeanRevSignal::GenerateSignal(SSignalEntry &signal)
{
   if(!isInitialized)
      return false;

   int barIndex = 0;  // Current bar
   double close = iClose(config.symbol, config.primaryTimeframe, barIndex);
   double atr = GetAdaptiveATR(barIndex);
   double zScore = GetZScore(barIndex);
   double halfLife = GetHalfLife(barIndex);
   double adx = GetADX(barIndex);
   int regimeCode = GetRegimeCode(barIndex);

   // Initialize signal
   signal.signalType = SIGNAL_NONE;
   signal.signalScore = 0;
   signal.signalTime = TimeCurrent();
   signal.regimeCode = regimeCode;

   // Step 1: Check for invalid conditions
   if(atr <= 0 || halfLife > 100)
      return false;  // Skip if ATR invalid or half-life too long

   // Step 2: Validate regime conditions
   if(!ValidateADXRegiming(adx))
      return false;  // ADX too high for mean reversion

   if(!ValidateSessionFilter(barIndex))
      return false;  // Outside tradeable session

   if(!ValidateRangeBreakout(close))
      return false;  // Outside range boundaries

   // Step 3: Check z-score magnitude for entry
   if(MathAbs(zScore) < config.zScoreEntryThreshold)
      return false;  // Z-score not extreme enough

   // Step 4: Calculate composite signal score (0-100)
   int totalScore = 0;

   totalScore += ScoreZScoreMagnitude(zScore);      // 0-40 points
   totalScore += ScoreRSIConfirmation(zScore, barIndex); // 0-30 points
   totalScore += ScoreBollingerBandTouch(barIndex); // 0-15 points
   totalScore += ScoreHalfLifeValidity(halfLife);   // 0-15 points

   signal.signalScore = (double)totalScore;

   // Check threshold
   if(totalScore < SIGNAL_THRESHOLD)
      return false;  // Signal score below 70 threshold

   // Step 5: Determine direction and calculate targets
   if(zScore > 0)
   {
      // Short signal (price too high)
      signal.signalType = SIGNAL_SHORT;
      signal.entryPrice = close;
      signal.stopLossPips = atr * config.atrStopMultiplier;
      signal.takeProfitPips = atr * 2.0;  // Conservative for mean reversion
   }
   else
   {
      // Long signal (price too low)
      signal.signalType = SIGNAL_LONG;
      signal.entryPrice = close;
      signal.stopLossPips = atr * config.atrStopMultiplier;
      signal.takeProfitPips = atr * 2.0;
   }

   signal.signalReason = "Z-Score=" + DoubleToString(zScore, 2) +
                        " HalfLife=" + DoubleToString(halfLife, 1) +
                        " Score=" + IntegerToString(totalScore);

   lastZScore = zScore;
   barsHeld = 0;

   return true;
}

//+------------------------------------------------------------------+
//| Score z-score magnitude contribution (0-40 points)              |
//+------------------------------------------------------------------+
int CMeanRevSignal::ScoreZScoreMagnitude(double zScore)
{
   double absZ = MathAbs(zScore);

   // Scale: 0 at z=1.5, 40 at z=2.5+
   if(absZ < 1.5) return 0;
   if(absZ > 2.5) return 40;

   // Linear scaling between 1.5 and 2.5
   return (int)((absZ - 1.5) / 1.0 * 40.0);
}

//+------------------------------------------------------------------+
//| Score RSI confirmation (0-30 points)                            |
//+------------------------------------------------------------------+
int CMeanRevSignal::ScoreRSIConfirmation(double zScore, int barIndex)
{
   double rsi = GetRSI(barIndex);

   if(zScore > 0)
   {
      // Short signal: RSI should be in 50-60 zone (overbought)
      if(rsi > 50 && rsi < 60) return 15;
      if(rsi >= 60) return 30;
   }
   else
   {
      // Long signal: RSI should be in 40-50 zone (oversold)
      if(rsi > 40 && rsi < 50) return 15;
      if(rsi <= 40) return 30;
   }

   return 0;
}

//+------------------------------------------------------------------+
//| Score Bollinger Band touch confirmation (0-15 points)          |
//+------------------------------------------------------------------+
int CMeanRevSignal::ScoreBollingerBandTouch(int barIndex)
{
   double close = iClose(config.symbol, config.primaryTimeframe, barIndex);
   double upper = GetBBandUpper(barIndex);
   double lower = GetBBandLower(barIndex);

   // Check if price is at band extremes
   if(close >= upper * 0.99) return 15;  // Near upper band
   if(close <= lower * 1.01) return 15;  // Near lower band

   return 0;
}

//+------------------------------------------------------------------+
//| Score half-life validity (0-15 points)                         |
//+------------------------------------------------------------------+
int CMeanRevSignal::ScoreHalfLifeValidity(double halfLife)
{
   // Optimal half-life: 30-80 bars
   if(halfLife > 30 && halfLife < 80) return 15;
   if(halfLife >= 20 && halfLife <= 100) return 10;

   return 0;
}

//+------------------------------------------------------------------+
//| Validate range breakout filter                                  |
//+------------------------------------------------------------------+
bool CMeanRevSignal::ValidateRangeBreakout(double currentPrice)
{
   if(config.rangeUpperBound <= 0 || config.rangeLowerBound <= 0)
      return true;  // No range boundaries set

   // Check if price is within range (not at breakout risk)
   return (currentPrice > config.rangeLowerBound && currentPrice < config.rangeUpperBound);
}

//+------------------------------------------------------------------+
//| Validate ADX for ranging confirmation                           |
//+------------------------------------------------------------------+
bool CMeanRevSignal::ValidateADXRegiming(double adx)
{
   if(config.maxADXForMeanRev <= 0)
      return true;

   return (adx < config.maxADXForMeanRev);
}

//+------------------------------------------------------------------+
//| Validate session filter                                         |
//+------------------------------------------------------------------+
bool CMeanRevSignal::ValidateSessionFilter(int barIndex)
{
   if(!config.respectSessionFilter)
      return true;

   // Get session filter from indicator
   int sessionActive = (int)GetIndicatorBuffer(2, 0, barIndex);

   return (sessionActive == 1);
}

//+------------------------------------------------------------------+
//| Check z-score exit condition                                    |
//+------------------------------------------------------------------+
bool CMeanRevSignal::CheckZScoreExit(double zScore)
{
   // Exit when z-score crosses 0 or becomes less extreme
   return (MathAbs(zScore) < config.zScoreExitThreshold);
}

//+------------------------------------------------------------------+
//| Check time-based exit                                           |
//+------------------------------------------------------------------+
bool CMeanRevSignal::CheckTimeExit()
{
   barsHeld++;
   int maxHold = config.maxHoldBarsZScore;

   return (barsHeld > maxHold);
}

//+------------------------------------------------------------------+
//| Get RSI value                                                   |
//+------------------------------------------------------------------+
double CMeanRevSignal::GetRSI(int barIndex)
{
   double buffer[];
   if(CopyBuffer(rsiHandle, 0, barIndex, 1, buffer) <= 0)
      return 50.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get Bollinger Band upper band                                   |
//+------------------------------------------------------------------+
double CMeanRevSignal::GetBBandUpper(int barIndex)
{
   double buffer[];
   if(CopyBuffer(bbandHandle, 1, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get Bollinger Band lower band                                   |
//+------------------------------------------------------------------+
double CMeanRevSignal::GetBBandLower(int barIndex)
{
   double buffer[];
   if(CopyBuffer(bbandHandle, 2, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get Bollinger Band middle (SMA)                                 |
//+------------------------------------------------------------------+
double CMeanRevSignal::GetBBandMiddle(int barIndex)
{
   double buffer[];
   if(CopyBuffer(bbandHandle, 0, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

#endif

//+------------------------------------------------------------------+
//|                                                CHybridSignal.mqh |
//|           MT5 POC - Adaptive Hybrid Trend + Mean Reversion |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CHYBRID_SIGNAL_H
#define CHYBRID_SIGNAL_H

#include "CSignalManager.mqh"

//--- Hybrid signal strategy class
class CHybridSignal : public CSignalManager
{
private:
   int       ema20Handle;
   int       ema200Handle;
   int       rsiHandle;
   int       bbandHandle;
   int       chandelerHandle;
   int       regimeState;        // Current regime: trending or ranging
   double    lastSignalScore;

public:
   // Constructor & Destructor
   CHybridSignal();
   ~CHybridSignal();

   // Initialization
   virtual bool  Init(SSymbolConfig &symbolConfig);
   virtual void  Deinit();

   // Signal generation
   virtual bool  GenerateSignal(SSignalEntry &signal);

private:
   // Regime detection
   int       DetermineRegime(double adx);

   // Trending mode signal scoring
   int       ScoreTrendingMode(double adx, int barIndex, int direction);
   int       ScorePullback(double close, double ema20);
   int       ScoreRSIPullback(double rsi, int direction);
   int       ScoreMA200Alignment(double close, double ema200, int direction);

   // Ranging mode signal scoring
   int       ScoreRangingMode(double zScore, int barIndex);
   int       ScoreRSIRanging(double rsi, int direction);
   int       ScoreBollingerBandRanging(double close, int barIndex);

   // Entry validation
   bool      ValidateTrendDirectionH4(int direction);
   bool      ValidateRegimeSwitch(int oldRegime, int newRegime);

   // Helper methods
   double    GetEMA20(int barIndex);
   double    GetEMA200(int barIndex);
   double    GetRSI(int barIndex);
   double    GetZScore(int barIndex);
   double    GetBBandUpper(int barIndex);
   double    GetBBandLower(int barIndex);
   double    GetClose(int barIndex);
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CHybridSignal::CHybridSignal() : ema20Handle(INVALID_HANDLE),
                                 ema200Handle(INVALID_HANDLE),
                                 rsiHandle(INVALID_HANDLE),
                                 bbandHandle(INVALID_HANDLE),
                                 chandelerHandle(INVALID_HANDLE),
                                 regimeState(0), lastSignalScore(0)
{
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CHybridSignal::~CHybridSignal()
{
   Deinit();
}

//+------------------------------------------------------------------+
//| Initialize hybrid signal generator                              |
//+------------------------------------------------------------------+
bool CHybridSignal::Init(SSymbolConfig &symbolConfig)
{
   if(!CSignalManager::Init(symbolConfig))
      return false;

   // Load H1 indicators for trend analysis
   ema20Handle = iMA(NULL, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   rsiHandle = iRSI(NULL, PERIOD_H1, 14, PRICE_CLOSE);
   bbandHandle = iBands(NULL, PERIOD_H1, 48, 0, 2.0, PRICE_CLOSE);

   // Load D1 indicators for macro confirmation
   ema200Handle = iMA(NULL, PERIOD_D1, 200, 0, MODE_SMA, PRICE_CLOSE);

   if(ema20Handle == INVALID_HANDLE || rsiHandle == INVALID_HANDLE ||
      bbandHandle == INVALID_HANDLE || ema200Handle == INVALID_HANDLE)
   {
      Print("Error: Failed to load hybrid indicators for ", config.symbol);
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Deinitialize signal generator                                   |
//+------------------------------------------------------------------+
void CHybridSignal::Deinit()
{
   if(ema20Handle != INVALID_HANDLE)
      IndicatorRelease(ema20Handle);
   if(ema200Handle != INVALID_HANDLE)
      IndicatorRelease(ema200Handle);
   if(rsiHandle != INVALID_HANDLE)
      IndicatorRelease(rsiHandle);
   if(bbandHandle != INVALID_HANDLE)
      IndicatorRelease(bbandHandle);

   CSignalManager::Deinit();
}

//+------------------------------------------------------------------+
//| Generate hybrid trend + mean-reversion signal                  |
//+------------------------------------------------------------------+
bool CHybridSignal::GenerateSignal(SSignalEntry &signal)
{
   if(!isInitialized)
      return false;

   int barIndex = 0;
   double close = GetClose(barIndex);
   double atr = GetAdaptiveATR(barIndex);
   double adx = GetADX(barIndex);
   double zScore = GetZScore(barIndex);
   double ema20 = GetEMA20(barIndex);
   double ema200 = GetEMA200(barIndex);
   double rsi = GetRSI(barIndex);
   int regimeCode = GetRegimeCode(barIndex);

   // Initialize signal
   signal.signalType = SIGNAL_NONE;
   signal.signalScore = 0;
   signal.signalTime = TimeCurrent();
   signal.regimeCode = regimeCode;

   // Step 1: Check for invalid conditions
   if(atr <= 0)
      return false;

   // Step 2: Determine current regime
   int newRegime = DetermineRegime(adx);

   if(newRegime != regimeState)
   {
      if(!ValidateRegimeSwitch(regimeState, newRegime))
         return false;  // Regime switch not yet confirmed
   }

   regimeState = newRegime;

   // Step 3: Generate signal based on regime
   int totalScore = 0;
   int direction = SIGNAL_NONE;

   if(regimeState == 1)
   {
      // TRENDING MODE: H4 ADX > 25
      // Wait for pullback to 20 EMA, enter on close in trend direction

      // Detect trend direction from D1 200 SMA
      if(!ValidateTrendDirectionH4(direction))
      {
         // Determine primary trend direction
         if(close > ema200)
            direction = SIGNAL_LONG;
         else
            direction = SIGNAL_SHORT;
      }

      totalScore = ScoreTrendingMode(adx, barIndex, direction);

      if(totalScore >= SIGNAL_THRESHOLD)
      {
         signal.signalType = direction;
         signal.stopLossPips = atr * config.atrStopMultiplier;  // 1.5x ATR
         signal.takeProfitPips = atr * 2.5;
         signal.signalReason = "Trending: Pullback to EMA20, Score=" + IntegerToString(totalScore);
      }
   }
   else if(regimeState == 0)
   {
      // RANGING MODE: H4 ADX < 20
      // Z-score entries at +/-1.8 with RSI confirmation

      if(MathAbs(zScore) < 1.8)
         return false;  // Z-score not extreme enough

      totalScore = ScoreRangingMode(zScore, barIndex);

      if(totalScore >= SIGNAL_THRESHOLD)
      {
         direction = (zScore > 0) ? SIGNAL_SHORT : SIGNAL_LONG;
         signal.signalType = direction;
         signal.stopLossPips = atr * 2.5;  // 2.5x ATR for ranging
         signal.takeProfitPips = atr * 1.5;
         signal.signalReason = "Ranging: Z-Score=" + DoubleToString(zScore, 2) +
                              " Score=" + IntegerToString(totalScore);
      }
   }

   signal.signalScore = (double)totalScore;
   signal.entryPrice = close;

   return (signal.signalType != SIGNAL_NONE && signal.signalScore >= SIGNAL_THRESHOLD);
}

//+------------------------------------------------------------------+
//| Determine if in trending or ranging regime                      |
//+------------------------------------------------------------------+
int CHybridSignal::DetermineRegime(double adx)
{
   // 1 = Trending (ADX > 25)
   // 0 = Ranging (ADX < 20)
   return (adx > 25) ? 1 : 0;
}

//+------------------------------------------------------------------+
//| Score trending mode signal (0-100)                              |
//+------------------------------------------------------------------+
int CHybridSignal::ScoreTrendingMode(double adx, int barIndex, int direction)
{
   int totalScore = 0;
   double close = GetClose(barIndex);
   double ema20 = GetEMA20(barIndex);
   double rsi = GetRSI(barIndex);

   // Check for pullback to 20 EMA
   totalScore += ScorePullback(close, ema20);        // 0-35 points

   // RSI in pullback zone (40-50)
   totalScore += ScoreRSIPullback(rsi, direction);   // 0-30 points

   // D1 200 SMA confirms direction
   totalScore += ScoreMA200Alignment(close, GetEMA200(barIndex), direction); // 0-20 points

   // ADX strength
   if(adx > 35) totalScore += 15;
   else if(adx > 25) totalScore += 10;

   return totalScore;
}

//+------------------------------------------------------------------+
//| Score pullback to EMA20 (0-35 points)                          |
//+------------------------------------------------------------------+
int CHybridSignal::ScorePullback(double close, double ema20)
{
   double pullbackPercent = MathAbs(close - ema20) / ema20 * 100;

   // Optimal pullback: 0.5-1.5% from EMA20
   if(pullbackPercent > 0.5 && pullbackPercent < 1.5) return 35;
   if(pullbackPercent > 0.3 && pullbackPercent < 2.0) return 25;
   if(pullbackPercent > 0.1 && pullbackPercent < 3.0) return 15;

   return 0;
}

//+------------------------------------------------------------------+
//| Score RSI pullback confirmation (0-30 points)                   |
//+------------------------------------------------------------------+
int CHybridSignal::ScoreRSIPullback(double rsi, int direction)
{
   if(direction == SIGNAL_LONG)
   {
      // Long pullback: RSI in 40-50 zone
      if(rsi > 40 && rsi < 50) return 30;
      if(rsi > 35 && rsi < 55) return 20;
      if(rsi > 30 && rsi < 60) return 10;
   }
   else if(direction == SIGNAL_SHORT)
   {
      // Short pullback: RSI in 50-60 zone
      if(rsi > 50 && rsi < 60) return 30;
      if(rsi > 45 && rsi < 65) return 20;
      if(rsi > 40 && rsi < 70) return 10;
   }

   return 0;
}

//+------------------------------------------------------------------+
//| Score D1 200 SMA alignment (0-20 points)                        |
//+------------------------------------------------------------------+
int CHybridSignal::ScoreMA200Alignment(double close, double ema200, int direction)
{
   if(direction == SIGNAL_LONG && close > ema200) return 20;
   if(direction == SIGNAL_SHORT && close < ema200) return 20;

   return 0;
}

//+------------------------------------------------------------------+
//| Score ranging mode signal (0-100)                               |
//+------------------------------------------------------------------+
int CHybridSignal::ScoreRangingMode(double zScore, int barIndex)
{
   int totalScore = 0;
   double rsi = GetRSI(barIndex);
   int direction = (zScore > 0) ? SIGNAL_SHORT : SIGNAL_LONG;

   // Z-score magnitude (0-40)
   double absZ = MathAbs(zScore);
   if(absZ > 2.0) totalScore += 40;
   else if(absZ > 1.8) totalScore += 30;
   else if(absZ > 1.5) totalScore += 20;

   // RSI confirmation (0-30)
   totalScore += ScoreRSIRanging(rsi, direction);

   // Bollinger Band touch (0-15)
   totalScore += ScoreBollingerBandRanging(GetClose(barIndex), barIndex);

   // Half-life validity (0-15)
   if(GetHalfLife(barIndex) > 20 && GetHalfLife(barIndex) < 80)
      totalScore += 15;

   return totalScore;
}

//+------------------------------------------------------------------+
//| Score RSI for ranging mode (0-30 points)                        |
//+------------------------------------------------------------------+
int CHybridSignal::ScoreRSIRanging(double rsi, int direction)
{
   if(direction == SIGNAL_SHORT)
   {
      // Short: RSI > 50
      if(rsi > 60) return 30;
      if(rsi > 55) return 20;
      if(rsi > 50) return 10;
   }
   else
   {
      // Long: RSI < 50
      if(rsi < 40) return 30;
      if(rsi < 45) return 20;
      if(rsi < 50) return 10;
   }

   return 0;
}

//+------------------------------------------------------------------+
//| Score Bollinger Band touch for ranging (0-15 points)           |
//+------------------------------------------------------------------+
int CHybridSignal::ScoreBollingerBandRanging(double close, int barIndex)
{
   double upper = GetBBandUpper(barIndex);
   double lower = GetBBandLower(barIndex);

   if(close >= upper * 0.99) return 15;
   if(close <= lower * 1.01) return 15;

   return 0;
}

//+------------------------------------------------------------------+
//| Validate trend direction on H4                                  |
//+------------------------------------------------------------------+
bool CHybridSignal::ValidateTrendDirectionH4(int direction)
{
   double adx = GetADX(0);  // Use current bar (0)
   return (adx > 25);
}

//+------------------------------------------------------------------+
//| Validate regime transition                                      |
//+------------------------------------------------------------------+
bool CHybridSignal::ValidateRegimeSwitch(int oldRegime, int newRegime)
{
   // Require at least 5 bars in new regime for confirmation
   // Placeholder - would need state tracking
   return true;
}

//+------------------------------------------------------------------+
//| Get EMA20 on H1 timeframe                                       |
//+------------------------------------------------------------------+
double CHybridSignal::GetEMA20(int barIndex)
{
   double buffer[];
   if(CopyBuffer(ema20Handle, 0, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get EMA200 on D1 timeframe                                      |
//+------------------------------------------------------------------+
double CHybridSignal::GetEMA200(int barIndex)
{
   double buffer[];
   if(CopyBuffer(ema200Handle, 0, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get RSI on H1 timeframe                                         |
//+------------------------------------------------------------------+
double CHybridSignal::GetRSI(int barIndex)
{
   double buffer[];
   if(CopyBuffer(rsiHandle, 0, barIndex, 1, buffer) <= 0)
      return 50.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get Z-Score value                                               |
//+------------------------------------------------------------------+
double CHybridSignal::GetZScore(int barIndex)
{
   return CSignalManager::GetZScore(barIndex);
}

//+------------------------------------------------------------------+
//| Get Bollinger Band upper                                        |
//+------------------------------------------------------------------+
double CHybridSignal::GetBBandUpper(int barIndex)
{
   double buffer[];
   if(CopyBuffer(bbandHandle, 1, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get Bollinger Band lower                                        |
//+------------------------------------------------------------------+
double CHybridSignal::GetBBandLower(int barIndex)
{
   double buffer[];
   if(CopyBuffer(bbandHandle, 2, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Get current close price                                         |
//+------------------------------------------------------------------+
double CHybridSignal::GetClose(int barIndex)
{
   return iClose(config.symbol, config.primaryTimeframe, barIndex);
}

#endif

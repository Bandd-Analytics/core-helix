//+------------------------------------------------------------------+
//|                                               CPositionSizer.mqh |
//|              MT5 POC - Position Sizing with ATR and Kelly Limits |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CPOSITION_SIZER_H
#define CPOSITION_SIZER_H

#include "CRiskManager.mqh"

//--- Position sizing configuration
struct SPositionSizingConfig
{
   double  drawdownMultiplier05;   // 0-5% DD: 1.0x (full risk)
   double  drawdownMultiplier10;   // 5-10% DD: 0.75x
   double  drawdownMultiplier15;   // 10-15% DD: 0.5x
   // >15% DD: 0x (halt)
};

//--- Position sizer class
class CPositionSizer : public CRiskManager
{
private:
   SPositionSizingConfig sizingConfig;
   double  lastKellySize[5];       // Rolling Kelly calculation for 5 pairs
   int     tradesInKellyWindow;    // Trades counted in 50-trade Kelly window

public:
   // Constructor & Destructor
   CPositionSizer();
   ~CPositionSizer();

   // Initialization
   bool      InitSizer(double initialEquity, SRiskLimits &inpLimits);

   // Position sizing with constraints
   double    CalculateSizeATR(SSymbolConfig &config, double atr,
                             double slMultiplier, double volatilityRegime);
   double    CalculateSizeWithKelly(double baseSize, double winRate,
                                   double avgWin, double avgLoss);
   double    ApplyDrawdownMultiplier(double size);
   double    ApplyVolatilityRegimeMultiplier(double size, int volatilityRegime);

   // Kelly tracking
   void      RecordTradeForKelly(bool isWin, double profitLoss);
   double    GetCurrentKellySize();

private:
   double    GetDrawdownMultiplier();
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CPositionSizer::CPositionSizer()
{
   // Initialize drawdown multipliers
   sizingConfig.drawdownMultiplier05 = 1.0;
   sizingConfig.drawdownMultiplier10 = 0.75;
   sizingConfig.drawdownMultiplier15 = 0.5;

   ArrayInitialize(lastKellySize, 0.0);
   tradesInKellyWindow = 0;
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CPositionSizer::~CPositionSizer()
{
}

//+------------------------------------------------------------------+
//| Initialize position sizer                                       |
//+------------------------------------------------------------------+
bool CPositionSizer::InitSizer(double initialEquity, SRiskLimits &inpLimits)
{
   return Init(initialEquity, inpLimits);
}

//+------------------------------------------------------------------+
//| Calculate size using ATR-based position sizing                 |
//+------------------------------------------------------------------+
double CPositionSizer::CalculateSizeATR(SSymbolConfig &config, double atr,
                                        double slMultiplier, double volatilityRegime)
{
   if(atr <= 0 || slMultiplier <= 0)
      return 0;

   // Base calculation: Risk per trade / (SL in pips * pip value)
   double stopLossPips = atr * slMultiplier;
   double baseSize = CalculateMaxLotSize(stopLossPips, config.pipValue);

   // Apply volatility regime multiplier
   double adjustedSize = ApplyVolatilityRegimeMultiplier(baseSize, (int)volatilityRegime);

   // Apply drawdown multiplier
   adjustedSize = ApplyDrawdownMultiplier(adjustedSize);

   // Round to nearest 0.01 lots
   adjustedSize = MathFloor(adjustedSize * 100) / 100;

   return adjustedSize;
}

//+------------------------------------------------------------------+
//| Calculate size with Kelly constraint applied                   |
//+------------------------------------------------------------------+
double CPositionSizer::CalculateSizeWithKelly(double baseSize, double winRate,
                                              double avgWin, double avgLoss)
{
   if(baseSize <= 0) return 0;

   double kellySize = CalculateKellySize(winRate, avgWin, avgLoss);

   // Apply Kelly as an upper bound cap on base size
   if(kellySize > 0 && kellySize < baseSize)
      return kellySize;

   return baseSize;
}

//+------------------------------------------------------------------+
//| Apply drawdown-based multiplier to position size                |
//+------------------------------------------------------------------+
double CPositionSizer::ApplyDrawdownMultiplier(double size)
{
   if(size <= 0) return 0;

   double ddPercent = GetDrawdownPercent();

   if(ddPercent > 15.0)
      return 0;  // Halt trading
   else if(ddPercent > 10.0)
      return size * sizingConfig.drawdownMultiplier15;  // 0.5x
   else if(ddPercent > 5.0)
      return size * sizingConfig.drawdownMultiplier10;  // 0.75x
   else
      return size * sizingConfig.drawdownMultiplier05;  // 1.0x
}

//+------------------------------------------------------------------+
//| Apply volatility regime multiplier                              |
//+------------------------------------------------------------------+
double CPositionSizer::ApplyVolatilityRegimeMultiplier(double size, int volatilityRegime)
{
   if(size <= 0) return 0;

   // Volatility regime codes:
   // 0 = Below 20th percentile (skip trading)
   // 1 = Normal (full position sizing)
   // 2 = Above 80th percentile (reduce size by 50%)

   switch(volatilityRegime)
   {
      case 0:
         return 0;  // Skip trading in low volatility
      case 2:
         return size * 0.5;  // Reduce by 50% in high volatility
      case 1:
      default:
         return size;  // Full sizing in normal volatility
   }
}

//+------------------------------------------------------------------+
//| Record trade for Kelly calculation (rolling 50-trade window)    |
//+------------------------------------------------------------------+
void CPositionSizer::RecordTradeForKelly(bool isWin, double profitLoss)
{
   // Log trade to parent class
   LogTrade(isWin, profitLoss);

   // Track in 50-trade Kelly window
   tradesInKellyWindow++;
   if(tradesInKellyWindow > 50)
      tradesInKellyWindow = 50;  // Cap at 50 trades
}

//+------------------------------------------------------------------+
//| Get current Kelly size based on recent trade history           |
//+------------------------------------------------------------------+
double CPositionSizer::GetCurrentKellySize()
{
   if(tradesInKellyWindow < 10)
      return 0;  // Need minimum 10 trades for Kelly

   SAccountState state = GetAccountState();

   double winRate = (double)state.winningTrades / state.totalTrades;
   double avgWin = (state.winningTrades > 0) ? state.largestWin / state.winningTrades : 0;
   double avgLoss = (state.losingTrades > 0) ? state.largestLoss / state.losingTrades : 1;

   return CalculateKellySize(winRate, avgWin, avgLoss);
}

//+------------------------------------------------------------------+
//| Get drawdown-based multiplier                                   |
//+------------------------------------------------------------------+
double CPositionSizer::GetDrawdownMultiplier()
{
   double ddPercent = GetDrawdownPercent();

   if(ddPercent > 15.0)
      return 0;
   else if(ddPercent > 10.0)
      return sizingConfig.drawdownMultiplier15;
   else if(ddPercent > 5.0)
      return sizingConfig.drawdownMultiplier10;
   else
      return sizingConfig.drawdownMultiplier05;
}

#endif

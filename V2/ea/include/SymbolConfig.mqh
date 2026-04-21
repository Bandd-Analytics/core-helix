//+------------------------------------------------------------------+
//|                                                  SymbolConfig.mqh |
//|                              MT5 POC - Symbol Configuration Header |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef SYMBOL_CONFIG_H
#define SYMBOL_CONFIG_H

//--- Strategy type enumeration
enum ENUM_STRATEGY_TYPE
{
   STRATEGY_MEAN_REVERSION = 0,   // Z-score oscillator based
   STRATEGY_TREND_FOLLOWING = 1,  // Donchian breakout based
   STRATEGY_HYBRID = 2             // EUR/USD: trend + mean-reversion adaptive
};

//--- Session enumeration
enum ENUM_SESSION_TYPE
{
   SESSION_LONDON = 0,
   SESSION_NEW_YORK = 1,
   SESSION_TOKYO = 2,
   SESSION_SYDNEY = 3,
   SESSION_ALL = 4
};

//--- Symbol configuration structure
struct SSymbolConfig
{
   string          symbol;                    // e.g., "EURUSD"
   int             index;                     // Portfolio index (0-4)
   ENUM_STRATEGY_TYPE strategyType;           // Strategy classification

   // Timeframes
   ENUM_TIMEFRAMES primaryTimeframe;          // Primary analysis timeframe
   ENUM_TIMEFRAMES secTimeframe;              // Secondary regime filter
   ENUM_TIMEFRAMES tertiaryTimeframe;         // Tertiary macro filter

   // Mean Reversion Parameters (if applicable)
   int             zScorePeriod;              // Z-score lookback (48 for AUDNZD, 30 for EURGBP)
   double          zScoreEntryThreshold;      // Entry z-score magnitude (±2.0)
   double          zScoreExitThreshold;       // Exit z-score magnitude (±0.5)
   int             maxHoldBarsZScore;         // Maximum hold time for mean reversion trades

   // Trend Following Parameters (if applicable)
   int             donchianEntryPeriod;       // Donchian entry period (20)
   int             donchianExitPeriod;        // Donchian exit period (10)
   double          adxThreshold;              // ADX threshold for trend confirmation (25)
   double          atrStopMultiplier;         // ATR multiplier for stop loss (2.0-2.5x)
   double          atrExitMultiplier;         // ATR multiplier for exit (3.0x for Chandelier)

   // Common Risk Parameters
   double          riskPerTrade;              // Risk per trade as % of equity (1%)
   double          maxStopLossPips;           // Maximum stop loss in pips
   double          partialCloseTarget;        // Target for partial close (1.5R)
   double          partialClosePercent;       // Percentage to close at target (50%)

   // Session and Filter Parameters
   ENUM_SESSION_TYPE preferredSession;        // Preferred trading session
   bool            respectSessionFilter;      // Whether to enforce session filter
   double          minADXForEntry;            // Minimum ADX for entry validation
   double          maxADXForMeanRev;          // Maximum ADX for mean reversion (ranging confirmation)

   // Pip value and contract specifications
   double          pipValue;                  // Value per pip per lot (for position sizing)
   double          spreadTypical;             // Typical spread in pips (IC Markets)
   double          commissionPerLot;          // Commission per lot per side ($3.50)
   int             pointsPerPip;              // Points per pip (typically 10 for 5-digit brokers)

   // Range boundaries (mean reversion pairs only)
   double          rangeUpperBound;           // Upper boundary for range break
   double          rangeLowerBound;           // Lower boundary for range break

   // Correlation properties
   bool            isHighCorrelation;         // Whether this pair is highly correlated with another
   int             correlationPairIndex;      // Index of correlated pair (if applicable)
   double          correlationThreshold;      // Threshold for correlation gating (0.75)
};

//--- Initialize symbol configuration for EURUSD (Hybrid Strategy)
inline SSymbolConfig InitEURUSD()
{
   SSymbolConfig config;
   config.symbol = "EURUSD";
   config.index = 0;
   config.strategyType = STRATEGY_HYBRID;

   config.primaryTimeframe = PERIOD_H1;
   config.secTimeframe = PERIOD_H4;
   config.tertiaryTimeframe = PERIOD_D1;

   config.zScorePeriod = 48;
   config.zScoreEntryThreshold = 1.8;
   config.zScoreExitThreshold = 0.0;
   config.maxHoldBarsZScore = 48;

   config.donchianEntryPeriod = 20;
   config.donchianExitPeriod = 10;
   config.adxThreshold = 25.0;
   config.atrStopMultiplier = 1.5;
   config.atrExitMultiplier = 3.0;

   config.riskPerTrade = 0.01;  // 1%
   config.maxStopLossPips = 100.0;
   config.partialCloseTarget = 1.5;
   config.partialClosePercent = 0.50;

   config.preferredSession = SESSION_ALL;
   config.respectSessionFilter = false;
   config.minADXForEntry = 0.0;
   config.maxADXForMeanRev = 20.0;

   config.pipValue = 0.10;
   config.spreadTypical = 0.02;
   config.commissionPerLot = 3.50;
   config.pointsPerPip = 10;

   config.rangeUpperBound = 0.0;
   config.rangeLowerBound = 0.0;

   config.isHighCorrelation = false;
   config.correlationPairIndex = -1;
   config.correlationThreshold = 0.75;

   return config;
}

//--- Initialize symbol configuration for USDJPY (Trend Following)
inline SSymbolConfig InitUSDJPY()
{
   SSymbolConfig config;
   config.symbol = "USDJPY";
   config.index = 1;
   config.strategyType = STRATEGY_TREND_FOLLOWING;

   config.primaryTimeframe = PERIOD_H4;
   config.secTimeframe = PERIOD_D1;
   config.tertiaryTimeframe = PERIOD_D1;

   config.zScorePeriod = 0;  // Not used
   config.zScoreEntryThreshold = 0.0;
   config.zScoreExitThreshold = 0.0;
   config.maxHoldBarsZScore = 0;

   config.donchianEntryPeriod = 20;
   config.donchianExitPeriod = 10;
   config.adxThreshold = 25.0;
   config.atrStopMultiplier = 2.0;
   config.atrExitMultiplier = 3.0;

   config.riskPerTrade = 0.01;  // 1%
   config.maxStopLossPips = 153.0;
   config.partialCloseTarget = 2.0;
   config.partialClosePercent = 0.33;

   config.preferredSession = SESSION_TOKYO;
   config.respectSessionFilter = true;
   config.minADXForEntry = 25.0;
   config.maxADXForMeanRev = 0.0;

   config.pipValue = 0.065;
   config.spreadTypical = 0.13;
   config.commissionPerLot = 3.50;
   config.pointsPerPip = 100;

   config.rangeUpperBound = 0.0;
   config.rangeLowerBound = 0.0;

   config.isHighCorrelation = false;
   config.correlationPairIndex = -1;
   config.correlationThreshold = 0.75;

   return config;
}

//--- Initialize symbol configuration for AUDNZD (Mean Reversion)
inline SSymbolConfig InitAUDNZD()
{
   SSymbolConfig config;
   config.symbol = "AUDNZD";
   config.index = 2;
   config.strategyType = STRATEGY_MEAN_REVERSION;

   config.primaryTimeframe = PERIOD_H1;
   config.secTimeframe = PERIOD_H4;
   config.tertiaryTimeframe = PERIOD_D1;

   config.zScorePeriod = 48;
   config.zScoreEntryThreshold = 2.0;
   config.zScoreExitThreshold = 0.5;
   config.maxHoldBarsZScore = 72;

   config.donchianEntryPeriod = 0;  // Not used
   config.donchianExitPeriod = 0;
   config.adxThreshold = 0.0;
   config.atrStopMultiplier = 2.0;
   config.atrExitMultiplier = 0.0;

   config.riskPerTrade = 0.01;  // 1%
   config.maxStopLossPips = 172.0;
   config.partialCloseTarget = 1.5;
   config.partialClosePercent = 0.50;

   config.preferredSession = SESSION_TOKYO;
   config.respectSessionFilter = true;
   config.minADXForEntry = 0.0;
   config.maxADXForMeanRev = 25.0;

   config.pipValue = 0.058;
   config.spreadTypical = 0.72;
   config.commissionPerLot = 3.50;
   config.pointsPerPip = 10000;

   config.rangeUpperBound = 1.2200;
   config.rangeLowerBound = 1.0800;

   config.isHighCorrelation = true;
   config.correlationPairIndex = 3;
   config.correlationThreshold = 0.75;

   return config;
}

//--- Initialize symbol configuration for EURGBP (Mean Reversion)
inline SSymbolConfig InitEURGBP()
{
   SSymbolConfig config;
   config.symbol = "EURGBP";
   config.index = 3;
   config.strategyType = STRATEGY_MEAN_REVERSION;

   config.primaryTimeframe = PERIOD_H4;
   config.secTimeframe = PERIOD_D1;
   config.tertiaryTimeframe = PERIOD_D1;

   config.zScorePeriod = 30;
   config.zScoreEntryThreshold = 2.0;
   config.zScoreExitThreshold = 0.3;
   config.maxHoldBarsZScore = 48;

   config.donchianEntryPeriod = 0;  // Not used
   config.donchianExitPeriod = 0;
   config.adxThreshold = 0.0;
   config.atrStopMultiplier = 2.5;
   config.atrExitMultiplier = 0.0;

   config.riskPerTrade = 0.01;  // 1%
   config.maxStopLossPips = 79.0;
   config.partialCloseTarget = 1.5;
   config.partialClosePercent = 0.50;

   config.preferredSession = SESSION_LONDON;
   config.respectSessionFilter = true;
   config.minADXForEntry = 0.0;
   config.maxADXForMeanRev = 25.0;

   config.pipValue = 0.127;
   config.spreadTypical = 0.27;
   config.commissionPerLot = 3.50;
   config.pointsPerPip = 10000;

   config.rangeUpperBound = 0.8850;
   config.rangeLowerBound = 0.8250;

   config.isHighCorrelation = true;
   config.correlationPairIndex = 0;  // Correlated with EURUSD
   config.correlationThreshold = 0.75;

   return config;
}

//--- Initialize symbol configuration for GBPJPY (Trend Following)
inline SSymbolConfig InitGBPJPY()
{
   SSymbolConfig config;
   config.symbol = "GBPJPY";
   config.index = 4;
   config.strategyType = STRATEGY_TREND_FOLLOWING;

   config.primaryTimeframe = PERIOD_H4;
   config.secTimeframe = PERIOD_D1;
   config.tertiaryTimeframe = PERIOD_D1;

   config.zScorePeriod = 0;  // Not used
   config.zScoreEntryThreshold = 0.0;
   config.zScoreExitThreshold = 0.0;
   config.maxHoldBarsZScore = 0;

   config.donchianEntryPeriod = 20;
   config.donchianExitPeriod = 10;
   config.adxThreshold = 25.0;
   config.atrStopMultiplier = 2.5;
   config.atrExitMultiplier = 3.0;

   config.riskPerTrade = 0.01;  // 1%
   config.maxStopLossPips = 153.0;
   config.partialCloseTarget = 2.0;
   config.partialClosePercent = 0.25;

   config.preferredSession = SESSION_LONDON;
   config.respectSessionFilter = true;
   config.minADXForEntry = 25.0;
   config.maxADXForMeanRev = 0.0;

   config.pipValue = 0.065;
   config.spreadTypical = 0.82;
   config.commissionPerLot = 3.50;
   config.pointsPerPip = 100;

   config.rangeUpperBound = 0.0;
   config.rangeLowerBound = 0.0;

   config.isHighCorrelation = true;
   config.correlationPairIndex = 1;  // Correlated with USDJPY
   config.correlationThreshold = 0.75;

   return config;
}


//--- Signal entry structure (defined here so all classes can use it without circular includes)
struct SSignalEntry
{
   int       signalType;
   double    signalScore;
   double    entryPrice;
   double    stopLossPips;
   double    takeProfitPips;
   int       regimeCode;
   string    signalReason;
   datetime  signalTime;
};

#endif

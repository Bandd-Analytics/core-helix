//+------------------------------------------------------------------+
//|                                                  MultiPairEA.mq5 |
//|                   MT5 POC - Multi-Pair EA Orchestrator |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "include/SymbolConfig.mqh"
#include "include/CCircuitBreaker.mqh"
#include "include/CMeanRevSignal.mqh"
#include "include/CTrendSignal.mqh"
#include "include/CHybridSignal.mqh"
#include "include/CScalingManager.mqh"
#include "include/CLogger.mqh"

//--- Input parameters
input double InpInitialEquity = 1000.0;           // Initial account equity
input double InpRiskPerTrade = 0.01;              // Risk per trade (1%)
input double InpMaxDailyLoss = 0.03;              // Daily loss limit (3%)
input double InpMaxWeeklyLoss = 0.06;             // Weekly loss limit (6%)
input double InpMaxDrawdown = 0.15;               // Maximum drawdown (15%)
input double InpKelleFraction = 0.25;             // Kelly fraction multiplier (0.25x)
input double InpSignalThreshold = 70;             // Minimum signal score (0-100)
input int    InpTimerIntervalSeconds = 1;        // Timer interval (1 second)

//--- Global EA state
CCircuitBreaker riskManager;
CScalingManager scalingManager;
CLogger         logger;
CMeanRevSignal  meanRevSignal[2];  // AUDNZD, EURGBP
CTrendSignal    trendSignal[2];    // USDJPY, GBPJPY
CHybridSignal   hybridSignal;      // EURUSD

SSymbolConfig   pairConfigs[5];
string          symbols[5] = {"EURUSD", "USDJPY", "AUDNZD", "EURGBP", "GBPJPY"};
bool            eaInitialized = false;
datetime        lastBarTime[5];
int             magicBaseNumber = 100000;

//+------------------------------------------------------------------+
//| Expert initialization function                                  |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("========== MultiPairEA Starting ==========");

   // Step 1: Initialize risk manager
   SRiskLimits limits;
   limits.riskPerTrade = InpRiskPerTrade;
   limits.maxDailyLoss = InpMaxDailyLoss;
   limits.maxWeeklyLoss = InpMaxWeeklyLoss;
   limits.maxDrawdown = InpMaxDrawdown;
   limits.kelleFraction = InpKelleFraction;
   limits.maxLeverage = 1.0 / 100.0;  // 1:100

   if(!riskManager.InitCircuitBreaker(InpInitialEquity, limits))
   {
      Print("Error: Failed to initialize Risk Manager");
      return INIT_FAILED;
   }

   // Step 2: Initialize logger
   if(!logger.Init("MarketMind_Journal"))
   {
      Print("Warning: Failed to initialize logger");
   }

   // Step 3: Initialize symbol configurations
   pairConfigs[0] = InitEURUSD();
   pairConfigs[1] = InitUSDJPY();
   pairConfigs[2] = InitAUDNZD();
   pairConfigs[3] = InitEURGBP();
   pairConfigs[4] = InitGBPJPY();

   // Step 4: Initialize signal generators
   // Mean Reversion signals (AUDNZD, EURGBP)
   if(!meanRevSignal[0].Init(pairConfigs[2]))
   {
      Print("Error: Failed to initialize AUDNZD signal generator");
      return INIT_FAILED;
   }

   if(!meanRevSignal[1].Init(pairConfigs[3]))
   {
      Print("Error: Failed to initialize EURGBP signal generator");
      return INIT_FAILED;
   }

   // Trend Following signals (USDJPY, GBPJPY)
   if(!trendSignal[0].Init(pairConfigs[1]))
   {
      Print("Error: Failed to initialize USDJPY signal generator");
      return INIT_FAILED;
   }

   if(!trendSignal[1].Init(pairConfigs[4]))
   {
      Print("Error: Failed to initialize GBPJPY signal generator");
      return INIT_FAILED;
   }

   // Hybrid signal (EURUSD)
   if(!hybridSignal.Init(pairConfigs[0]))
   {
      Print("Error: Failed to initialize EURUSD signal generator");
      return INIT_FAILED;
   }

   // Step 5: Initialize position scaling
   if(!scalingManager.InitScaling())
   {
      Print("Error: Failed to initialize scaling manager");
      return INIT_FAILED;
   }

   // Step 6: Set timer interval
   EventSetTimer(InpTimerIntervalSeconds);

   eaInitialized = true;
   Print("========== MultiPairEA Initialized Successfully ==========");

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();

   // Release signal generators
   meanRevSignal[0].Deinit();
   meanRevSignal[1].Deinit();
   trendSignal[0].Deinit();
   trendSignal[1].Deinit();
   hybridSignal.Deinit();

   logger.Close();

   Print("========== MultiPairEA Deinitialized ==========");
}

//+------------------------------------------------------------------+
//| Expert timer function                                           |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(!eaInitialized)
      return;

   // Step 1: Update account state
   double currentEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   riskManager.UpdateAccountState(currentEquity);

   // Step 2: Check circuit breaker
   if(!riskManager.CheckAllLimits())
   {
      Print("CIRCUIT BREAKER ACTIVE - Trading halted");
      return;
   }

   // Step 3: Refresh position status
   scalingManager.RefreshPositionStatus();

   // Step 4: Process each pair on new bar (H1 or H4 based on pair)
   ProcessPair(0, meanRevSignal[0], pairConfigs[0]);  // AUDNZD
   ProcessPair(1, meanRevSignal[1], pairConfigs[1]);  // EURGBP
   ProcessPair(2, trendSignal[0], pairConfigs[2]);    // USDJPY
   ProcessPair(3, trendSignal[1], pairConfigs[3]);    // GBPJPY
   ProcessPairHybrid(4);                              // EURUSD

   // Step 5: Check scaling conditions on all positions
   for(int i = 0; i < scalingManager.GetOpenPositionCount(); i++)
   {
      SOpenPosition pos;
      if(scalingManager.GetPosition(i, pos))
         scalingManager.CheckScalingConditions(pos.ticket);
   }
}

//+------------------------------------------------------------------+
//| Process a single pair for signal generation and entry           |
//+------------------------------------------------------------------+
template<typename T>
void ProcessPair(int pairIndex, T &signalGenerator, SSymbolConfig &config)
{
   // Check for new bar on primary timeframe
   ENUM_TIMEFRAMES tf = config.primaryTimeframe;
   datetime barTime = iTime(config.symbol, tf, 0);

   if(barTime == lastBarTime[pairIndex])
      return;  // Not a new bar yet

   lastBarTime[pairIndex] = barTime;

   // Generate signal
   SSignalEntry signal;
   if(!signalGenerator.GenerateSignal(signal))
      return;  // No signal generated

   // Check signal score threshold
   if(signal.signalScore < InpSignalThreshold)
      return;

   // Check if already have position for this pair
   if(riskManager.HasOpenPosition(config.symbol))
      return;  // Only one position per pair

   // Check circuit breaker again before entry
   if(!riskManager.CheckAllLimits())
      return;

   // Check position count limit
   if(!riskManager.CheckPositionCount(riskManager.GetOpenPositionCount()))
      return;

   // Calculate position size
   double atr = 0.0;
   int atrHandle = iATR(config.symbol, tf, 14);
   if(atrHandle != INVALID_HANDLE)
   {
      double atrBuf[];
      ArraySetAsSeries(atrBuf, true);
      if(CopyBuffer(atrHandle, 0, 0, 1, atrBuf) > 0) atr = atrBuf[0];
      IndicatorRelease(atrHandle);
   }
   double volatilityRegime = iCustom(config.symbol, tf, "VolatilityRegime", 14, 252, 0);
   double lotSize = riskManager.CalculateSizeATR(config, atr,
                                                 signal.stopLossPips / atr,
                                                 volatilityRegime);

   if(lotSize <= 0)
      return;

   // Submit entry order
   SEntryRequest entryReq;
   entryReq.symbol = config.symbol;
   entryReq.direction = (signal.signalType == SIGNAL_LONG) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   entryReq.volume = lotSize;
   entryReq.entryPrice = signal.entryPrice;
   entryReq.stopLossPips = signal.stopLossPips;
   entryReq.takeProfitPips = signal.takeProfitPips;
   entryReq.comment = signal.signalReason;
   entryReq.magicNumber = magicBaseNumber + pairIndex * 100;

   ulong ticket = 0;
   if(riskManager.SubmitEntryWithRetry(entryReq, ticket))
   {
      // Log the trade
      STradeLogEntry logEntry;
      logEntry.entryTime = TimeCurrent();
      logEntry.symbol = config.symbol;
      logEntry.direction = signal.signalType;
      logEntry.lotSize = lotSize;
      logEntry.entryPrice = signal.entryPrice;
      logEntry.stopLoss = signal.entryPrice - (signal.stopLossPips * _Point);
      logEntry.takeProfit = signal.entryPrice + (signal.takeProfitPips * _Point);
      logEntry.signalScore = signal.signalScore;
      logEntry.regimeCode = signal.regimeCode;
      logEntry.comment = signal.signalReason;

      logger.LogTrade(logEntry);
      Print("Entry submitted: ", config.symbol, " Ticket: ", ticket);
   }
}

//+------------------------------------------------------------------+
//| Process EUR/USD hybrid signal (overload for hybrid)             |
//+------------------------------------------------------------------+
void ProcessPairHybrid(int pairIndex)
{
   // Implementation for hybrid signal processing
   // Similar to ProcessPair but with different signal generator
}

//+------------------------------------------------------------------+
//| On tick handler (real-time updates)                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Update trailing stops and check exits on every tick
   if(!eaInitialized)
      return;

   // Could add real-time exit checks here if needed
}

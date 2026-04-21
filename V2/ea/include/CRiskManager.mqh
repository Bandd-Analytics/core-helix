//+------------------------------------------------------------------+
//|                                                 CRiskManager.mqh |
//|                    MT5 POC - Risk Management Framework Header |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CRISK_MANAGER_H
#define CRISK_MANAGER_H

#include "SymbolConfig.mqh"

//--- Risk limits structure
struct SRiskLimits
{
   double  riskPerTrade;          // Per-trade risk as % of equity (1%)
   double  maxDailyLoss;          // Daily loss limit as % of equity (3%)
   double  maxWeeklyLoss;         // Weekly loss limit as % of equity (6%)
   double  maxDrawdown;           // Maximum drawdown as % of equity (15%)
   double  maxAggregateRisk;       // Maximum aggregate portfolio risk (3%)
   double  kelleFraction;          // Kelly fraction multiplier (0.25x)
   double  maxLeverage;            // Self-imposed max leverage (1:100)
};

//--- Account state tracking
struct SAccountState
{
   double  initialEquity;
   double  currentEquity;
   double  highWaterMark;          // Peak equity for drawdown calculation
   double  todayOpenEquity;        // Equity at start of trading day
   datetime lastWeekStart;
   double  weekStartEquity;

   double  realizedPnL;            // Realized P&L from closed trades
   int     totalTrades;            // Total number of trades executed
   int     winningTrades;
   int     losingTrades;
   double  largestWin;
   double  largestLoss;
};

//--- Risk Manager class
class CRiskManager
{
protected:
   SRiskLimits    limits;
   SAccountState  accountState;
   bool           isInitialized;
   bool           circuitBreakerActive;

public:
   // Constructor & Destructor
   CRiskManager();
   ~CRiskManager();

   // Initialization
   bool      Init(double initialEquity, SRiskLimits &riskLimits);
   void      Reset();

   // Account state tracking
   void      UpdateAccountState(double currentEquity);
   void      LogTrade(bool isWin, double profitLoss);
   void      UpdateDailyReset();
   void      UpdateWeeklyReset();

   // Risk calculations
   double    CalculateMaxLotSize(double stopLossPips, double pipValue);
   double    CalculateKellySize(double winRate, double avgWin, double avgLoss);
   double    GetCurrentEquity() { return accountState.currentEquity; }
   double    GetHighWaterMark() { return accountState.highWaterMark; }

   // Constraint checks
   bool      CheckDailyLossLimit();
   bool      CheckWeeklyLossLimit();
   bool      CheckDrawdownLimit();
   bool      IsCircuitBreakerActive() { return circuitBreakerActive; }
   void      ActivateCircuitBreaker() { circuitBreakerActive = true; }
   void      DeactivateCircuitBreaker() { circuitBreakerActive = false; }

   // Accessors
   SAccountState GetAccountState() { return accountState; }
   SRiskLimits   GetLimits() { return limits; }
   double    GetDailyLossPercent();
   double    GetWeeklyLossPercent();
   double    GetDrawdownPercent();

private:
   double    GetDayOpenEquity();
   double    GetWeekStartEquity();
   bool      IsNewDay();
   bool      IsNewWeek();
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CRiskManager::CRiskManager() : isInitialized(false), circuitBreakerActive(false)
{
   ZeroMemory(accountState);
   ZeroMemory(limits);
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CRiskManager::~CRiskManager()
{
}

//+------------------------------------------------------------------+
//| Initialize risk manager with equity and limits                  |
//+------------------------------------------------------------------+
bool CRiskManager::Init(double initialEquity, SRiskLimits &riskLimits)
{
   if(initialEquity <= 0)
   {
      Print("Error: Invalid initial equity");
      return false;
   }

   accountState.initialEquity = initialEquity;
   accountState.currentEquity = initialEquity;
   accountState.highWaterMark = initialEquity;
   accountState.todayOpenEquity = initialEquity;
   accountState.weekStartEquity = initialEquity;
   accountState.lastWeekStart = TimeCurrent();

   accountState.realizedPnL = 0;
   accountState.totalTrades = 0;
   accountState.winningTrades = 0;
   accountState.losingTrades = 0;
   accountState.largestWin = 0;
   accountState.largestLoss = 0;

   limits = riskLimits;
   isInitialized = true;
   circuitBreakerActive = false;

   return true;
}

//+------------------------------------------------------------------+
//| Reset account state                                             |
//+------------------------------------------------------------------+
void CRiskManager::Reset()
{
   Init(accountState.initialEquity, limits);
}

//+------------------------------------------------------------------+
//| Update account state with current equity                        |
//+------------------------------------------------------------------+
void CRiskManager::UpdateAccountState(double currentEquity)
{
   if(!isInitialized) return;

   accountState.currentEquity = currentEquity;

   // Update high water mark for drawdown calculation
   if(currentEquity > accountState.highWaterMark)
      accountState.highWaterMark = currentEquity;

   // Check for daily/weekly resets
   if(IsNewDay())
      UpdateDailyReset();

   if(IsNewWeek())
      UpdateWeeklyReset();
}

//+------------------------------------------------------------------+
//| Log a closed trade                                              |
//+------------------------------------------------------------------+
void CRiskManager::LogTrade(bool isWin, double profitLoss)
{
   if(!isInitialized) return;

   accountState.totalTrades++;
   accountState.realizedPnL += profitLoss;

   if(isWin)
   {
      accountState.winningTrades++;
      if(profitLoss > accountState.largestWin)
         accountState.largestWin = profitLoss;
   }
   else
   {
      accountState.losingTrades++;
      if(profitLoss < accountState.largestLoss)
         accountState.largestLoss = profitLoss;
   }
}

//+------------------------------------------------------------------+
//| Handle daily reset (new trading day)                           |
//+------------------------------------------------------------------+
void CRiskManager::UpdateDailyReset()
{
   accountState.todayOpenEquity = accountState.currentEquity;
}

//+------------------------------------------------------------------+
//| Handle weekly reset (new trading week)                         |
//+------------------------------------------------------------------+
void CRiskManager::UpdateWeeklyReset()
{
   accountState.weekStartEquity = accountState.currentEquity;
   accountState.lastWeekStart = TimeCurrent();
}

//+------------------------------------------------------------------+
//| Calculate maximum lot size based on risk parameters             |
//+------------------------------------------------------------------+
double CRiskManager::CalculateMaxLotSize(double stopLossPips, double pipValue)
{
   if(!isInitialized || stopLossPips <= 0 || pipValue <= 0)
      return 0;

   // Risk amount per trade: 1% of current equity
   double riskAmount = accountState.currentEquity * limits.riskPerTrade;

   // Lot size = Risk Amount / (Stop Loss Pips * Pip Value)
   double lotSize = riskAmount / (stopLossPips * pipValue);

   // Round down to nearest 0.01
   lotSize = MathFloor(lotSize * 100) / 100;

   return lotSize;
}

//+------------------------------------------------------------------+
//| Calculate Kelly sizing for position                            |
//+------------------------------------------------------------------+
double CRiskManager::CalculateKellySize(double winRate, double avgWin, double avgLoss)
{
   if(avgLoss == 0) return 0;

   // Kelly: f* = (p*b - q) / b, where:
   //   p = win rate, q = 1-p
   //   b = win/loss ratio (avgWin / |avgLoss|)

   double p = winRate;
   double q = 1.0 - p;
   double b = (avgLoss != 0) ? avgWin / MathAbs(avgLoss) : 1.0;

   double kellySize = (p * b - q) / b;

   // Apply Kelly fraction (0.25x)
   kellySize = kellySize * limits.kelleFraction;

   if(kellySize < 0) kellySize = 0;

   return kellySize;
}

//+------------------------------------------------------------------+
//| Check daily loss limit                                          |
//+------------------------------------------------------------------+
bool CRiskManager::CheckDailyLossLimit()
{
   if(!isInitialized) return true;

   double dailyLoss = accountState.todayOpenEquity - accountState.currentEquity;
   double dailyLossPercent = (dailyLoss / accountState.initialEquity) * 100;

   return dailyLossPercent < (limits.maxDailyLoss * 100);
}

//+------------------------------------------------------------------+
//| Check weekly loss limit                                         |
//+------------------------------------------------------------------+
bool CRiskManager::CheckWeeklyLossLimit()
{
   if(!isInitialized) return true;

   double weeklyLoss = accountState.weekStartEquity - accountState.currentEquity;
   double weeklyLossPercent = (weeklyLoss / accountState.initialEquity) * 100;

   return weeklyLossPercent < (limits.maxWeeklyLoss * 100);
}

//+------------------------------------------------------------------+
//| Check maximum drawdown limit                                    |
//+------------------------------------------------------------------+
bool CRiskManager::CheckDrawdownLimit()
{
   if(!isInitialized) return true;

   double drawdown = accountState.highWaterMark - accountState.currentEquity;
   double drawdownPercent = (drawdown / accountState.initialEquity) * 100;

   return drawdownPercent < (limits.maxDrawdown * 100);
}

//+------------------------------------------------------------------+
//| Get daily loss as percentage                                    |
//+------------------------------------------------------------------+
double CRiskManager::GetDailyLossPercent()
{
   if(!isInitialized) return 0;

   double dailyLoss = accountState.todayOpenEquity - accountState.currentEquity;
   double dailyLossPercent = (dailyLoss / accountState.initialEquity) * 100;

   return dailyLossPercent;
}

//+------------------------------------------------------------------+
//| Get weekly loss as percentage                                   |
//+------------------------------------------------------------------+
double CRiskManager::GetWeeklyLossPercent()
{
   if(!isInitialized) return 0;

   double weeklyLoss = accountState.weekStartEquity - accountState.currentEquity;
   double weeklyLossPercent = (weeklyLoss / accountState.initialEquity) * 100;

   return weeklyLossPercent;
}

//+------------------------------------------------------------------+
//| Get drawdown as percentage                                      |
//+------------------------------------------------------------------+
double CRiskManager::GetDrawdownPercent()
{
   if(!isInitialized) return 0;

   double drawdown = accountState.highWaterMark - accountState.currentEquity;
   double drawdownPercent = (drawdown / accountState.initialEquity) * 100;

   return drawdownPercent;
}

//+------------------------------------------------------------------+
//| Check if new trading day                                        |
//+------------------------------------------------------------------+
bool CRiskManager::IsNewDay()
{
   datetime now = TimeCurrent();
   datetime lastReset = accountState.lastWeekStart;

   // Compare day component: divide by 86400 (seconds per day) and compare
   return ((int)(now / 86400) != (int)(lastReset / 86400));
}

//+------------------------------------------------------------------+
//| Check if new trading week (Monday)                             |
//+------------------------------------------------------------------+
bool CRiskManager::IsNewWeek()
{
   datetime now = TimeCurrent();
   datetime lastReset = accountState.lastWeekStart;

   // Get day of week: 0=Sunday, 1=Monday, ..., 6=Saturday
   // Use TimeHour/TimeMinute and calculate or use a 7-day window
   int daysDiff = ((int)(now / 86400) - (int)(lastReset / 86400)) / 7;

   // If we've crossed at least one Sunday/Monday boundary, it's a new week
   return (daysDiff > 0);
}

#endif

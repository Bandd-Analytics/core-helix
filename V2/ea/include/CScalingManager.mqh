//+------------------------------------------------------------------+
//|                                              CScalingManager.mqh |
//|                  MT5 POC - Position Scaling and Partial Closes |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CSCALING_MANAGER_H
#define CSCALING_MANAGER_H

#include "CExitManager.mqh"

//--- Scaling structure
struct SScalingLevel
{
   double    profitTarget;       // Profit level in R multiples (e.g., 2.0R)
   double    closePercent;       // Percentage to close (e.g., 0.33 = 33%)
};

//--- Scaling manager class
class CScalingManager : public CExitManager
{
private:
   SScalingLevel scalingLevels[5];
   int           levelCount;

public:
   // Constructor & Destructor
   CScalingManager();
   ~CScalingManager();

   // Initialization
   bool      InitScaling();
   bool      AddScalingLevel(double profitTargetR, double closePercent);

   // Scaling operations
   bool      CheckScalingConditions(ulong ticket);
   bool      ExecutePartialClose(ulong ticket, double profitTargetR);
   bool      ScaleInOnProfitTiers(ulong ticket);

private:
   double    GetPositionProfit(ulong ticket, double riskAmount);
   double    GetRMultiple(ulong ticket);
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CScalingManager::CScalingManager() : levelCount(0)
{
   isInitialized = false;
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CScalingManager::~CScalingManager()
{
}

//+------------------------------------------------------------------+
//| Initialize scaling manager with default levels                  |
//+------------------------------------------------------------------+
bool CScalingManager::InitScaling()
{
   if(!CExitManager::InitExit())
      return false;

   // Define default scaling levels for trending trades (Donchian)
   // Example: close 33% at 2R, 33% at 3R, trail remaining 34%
   AddScalingLevel(2.0, 0.33);  // Close 33% at 2R profit
   AddScalingLevel(3.0, 0.33);  // Close 33% at 3R profit
   // Remaining position trails with Chandelier stop

   isInitialized = true;
   return true;
}

//+------------------------------------------------------------------+
//| Add a scaling level to the manager                              |
//+------------------------------------------------------------------+
bool CScalingManager::AddScalingLevel(double profitTargetR, double closePercent)
{
   if(levelCount >= 5) return false;
   if(closePercent < 0 || closePercent > 1.0) return false;

   scalingLevels[levelCount].profitTarget = profitTargetR;
   scalingLevels[levelCount].closePercent = closePercent;
   levelCount++;

   return true;
}

//+------------------------------------------------------------------+
//| Check all scaling conditions for a position                     |
//+------------------------------------------------------------------+
bool CScalingManager::CheckScalingConditions(ulong ticket)
{
   if(!isInitialized)
      return false;

   if(!PositionSelectByTicket(ticket))
      return false;

   double rMultiple = GetRMultiple(ticket);

   // Check each scaling level
   for(int i = 0; i < levelCount; i++)
   {
      if(rMultiple >= scalingLevels[i].profitTarget)
      {
         // Execute partial close at this level
         if(ExecutePartialClose(ticket, scalingLevels[i].profitTarget))
            return true;
      }
   }

   return false;
}

//+------------------------------------------------------------------+
//| Execute partial close at profit target                          |
//+------------------------------------------------------------------+
bool CScalingManager::ExecutePartialClose(ulong ticket, double profitTargetR)
{
   if(!PositionSelectByTicket(ticket))
      return false;

   double volume = PositionGetDouble(POSITION_VOLUME);
   double currentProfit = PositionGetDouble(POSITION_PROFIT);

   // Find which scaling level this is
   int levelIndex = -1;
   for(int i = 0; i < levelCount; i++)
   {
      if(MathAbs(scalingLevels[i].profitTarget - profitTargetR) < 0.01)
      {
         levelIndex = i;
         break;
      }
   }

   if(levelIndex < 0) return false;

   // Calculate volume to close
   double volumeToClose = volume * scalingLevels[levelIndex].closePercent;
   volumeToClose = MathFloor(volumeToClose * 100) / 100;  // Round to nearest 0.01

   if(volumeToClose <= 0) return false;

   // Close partial position
   trade.PositionClosePartial(ticket, volumeToClose);

   if(trade.ResultRetcode() == 10009)  // TRADE_RETCODE_DONE
   {
      Print("Partial close executed - Ticket: ", ticket, " Volume: ", volumeToClose,
            " at ", profitTargetR, "R profit");
      return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| Scale in on profit tiers (add to winning position)             |
//+------------------------------------------------------------------+
bool CScalingManager::ScaleInOnProfitTiers(ulong ticket)
{
   // Placeholder for scale-in logic
   // Would add to position after certain profit levels
   return false;
}

//+------------------------------------------------------------------+
//| Calculate current R-multiple for position                       |
//+------------------------------------------------------------------+
double CScalingManager::GetRMultiple(ulong ticket)
{
   if(!PositionSelectByTicket(ticket))
      return 0.0;

   double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl = PositionGetDouble(POSITION_SL);
   double profit = PositionGetDouble(POSITION_PROFIT);
   double volume = PositionGetDouble(POSITION_VOLUME);

   // Calculate initial risk in pips
   double riskPips = MathAbs(openPrice - sl) / _Point;
   if(riskPips <= 0) return 0.0;

   // Get pip value
   string symbol = PositionGetString(POSITION_SYMBOL);
   double pipValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);

   // Profit in R: actual profit / (risk in pips * pip value per lot * volume)
   double rMultiple = profit / (riskPips * pipValue * volume);

   return rMultiple;
}

//+------------------------------------------------------------------+
//| Get position profit amount                                      |
//+------------------------------------------------------------------+
double CScalingManager::GetPositionProfit(ulong ticket, double riskAmount)
{
   if(!PositionSelectByTicket(ticket))
      return 0.0;

   return PositionGetDouble(POSITION_PROFIT);
}

#endif

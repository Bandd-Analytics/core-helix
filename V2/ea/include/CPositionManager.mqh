//+------------------------------------------------------------------+
//|                                              CPositionManager.mqh |
//|                  MT5 POC - Position Tracking and Management |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CPOSITION_MANAGER_H
#define CPOSITION_MANAGER_H

#include <Trade/Trade.mqh>
#include "CPositionSizer.mqh"

//--- Open position tracking structure
struct SOpenPosition
{
   ulong     ticket;
   string    symbol;
   int       type;              // OP_BUY or OP_SELL
   double    volume;
   double    openPrice;
   double    stopLoss;
   double    takeProfit;
   double    profitLoss;        // Current P&L
   datetime  openTime;
   datetime  lastUpdateTime;
   double    initialRisk;       // Risk amount at entry
   string    comment;
};

//--- Position manager class
class CPositionManager : public CPositionSizer
{
protected:
   SOpenPosition positions[100];  // Max 100 open positions
   int           positionCount;
   CTrade        trade;          // Trading class

public:
   // Constructor & Destructor
   CPositionManager();
   ~CPositionManager();

   // Initialization
   bool      Init();
   void      Deinit();

   // Position tracking
   void      UpdateAllPositions();
   int       GetOpenPositionCount() { return positionCount; }
   int       GetPositionCountForSymbol(string symbol);
   bool      GetPosition(int index, SOpenPosition &outPos);
   bool      GetPositionByTicket(ulong ticket, SOpenPosition &outPos);

   // Position queries
   double    GetTotalOpenRisk();
   double    GetSymbolExposure(string symbol);
   bool      HasOpenPosition(string symbol);
   int       CountPositionsByDirection(string symbol, int direction);

   // Position lifecycle
   bool      RegisterPosition(ulong ticket, SSignalEntry &signal);
   void      UnregisterPosition(ulong ticket);
   void      RefreshPositionStatus();

private:
   void      SyncWithBroker();
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CPositionManager::CPositionManager() : positionCount(0)
{
   isInitialized = false;
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CPositionManager::~CPositionManager()
{
   Deinit();
}

//+------------------------------------------------------------------+
//| Initialize position manager                                     |
//+------------------------------------------------------------------+
bool CPositionManager::Init()
{
   positionCount = 0;
   isInitialized = true;
   SyncWithBroker();
   return true;
}

//+------------------------------------------------------------------+
//| Deinitialize position manager                                   |
//+------------------------------------------------------------------+
void CPositionManager::Deinit()
{
   isInitialized = false;
}

//+------------------------------------------------------------------+
//| Update all open positions with current market data              |
//+------------------------------------------------------------------+
void CPositionManager::UpdateAllPositions()
{
   if(!isInitialized)
      return;

   for(int i = 0; i < positionCount; i++)
   {
      if(positions[i].ticket <= 0)
         continue;

      // Update P&L for each position
      if(PositionSelectByTicket(positions[i].ticket))
      {
         positions[i].profitLoss = PositionGetDouble(POSITION_PROFIT);
         positions[i].lastUpdateTime = TimeCurrent();
      }
   }
}

//+------------------------------------------------------------------+
//| Count open positions for a specific symbol                      |
//+------------------------------------------------------------------+
int CPositionManager::GetPositionCountForSymbol(string symbol)
{
   int count = 0;
   for(int i = 0; i < positionCount; i++)
   {
      if(positions[i].symbol == symbol)
         count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| Get position by index                                           |
//+------------------------------------------------------------------+
bool CPositionManager::GetPosition(int index, SOpenPosition &outPos)
{
   if(index >= 0 && index < positionCount)
   {
      outPos = positions[index];
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Get position by ticket number                                   |
//+------------------------------------------------------------------+
bool CPositionManager::GetPositionByTicket(ulong ticket, SOpenPosition &outPos)
{
   for(int i = 0; i < positionCount; i++)
   {
      if(positions[i].ticket == ticket)
      {
         outPos = positions[i];
         return true;
      }
   }
   return false;  // Return false if position not found
}

//+------------------------------------------------------------------+
//| Get total open risk across all positions                        |
//+------------------------------------------------------------------+
double CPositionManager::GetTotalOpenRisk()
{
   double totalRisk = 0;
   for(int i = 0; i < positionCount; i++)
   {
      totalRisk += positions[i].initialRisk;
   }
   return totalRisk;
}

//+------------------------------------------------------------------+
//| Get total symbol exposure                                       |
//+------------------------------------------------------------------+
double CPositionManager::GetSymbolExposure(string symbol)
{
   double exposure = 0;
   for(int i = 0; i < positionCount; i++)
   {
      if(positions[i].symbol == symbol)
         exposure += positions[i].volume;
   }
   return exposure;
}

//+------------------------------------------------------------------+
//| Check if position exists for symbol                             |
//+------------------------------------------------------------------+
bool CPositionManager::HasOpenPosition(string symbol)
{
   return (GetPositionCountForSymbol(symbol) > 0);
}

//+------------------------------------------------------------------+
//| Count positions by direction                                    |
//+------------------------------------------------------------------+
int CPositionManager::CountPositionsByDirection(string symbol, int direction)
{
   int count = 0;
   for(int i = 0; i < positionCount; i++)
   {
      if(positions[i].symbol == symbol && positions[i].type == direction)
         count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| Register a new position                                         |
//+------------------------------------------------------------------+
bool CPositionManager::RegisterPosition(ulong ticket, SSignalEntry &signal)
{
   if(positionCount >= 100)
      return false;

   positions[positionCount].ticket = ticket;
   positions[positionCount].symbol = Symbol();
   positions[positionCount].type = signal.signalType;
   positions[positionCount].openPrice = signal.entryPrice;
   positions[positionCount].stopLoss = signal.entryPrice - (signal.stopLossPips * _Point);
   positions[positionCount].takeProfit = signal.entryPrice + (signal.takeProfitPips * _Point);
   positions[positionCount].openTime = TimeCurrent();
   positions[positionCount].comment = signal.signalReason;

   positionCount++;
   return true;
}

//+------------------------------------------------------------------+
//| Unregister a closed position                                    |
//+------------------------------------------------------------------+
void CPositionManager::UnregisterPosition(ulong ticket)
{
   for(int i = 0; i < positionCount; i++)
   {
      if(positions[i].ticket == ticket)
      {
         // Shift remaining positions down
         for(int j = i; j < positionCount - 1; j++)
         {
            positions[j] = positions[j + 1];
         }
         positionCount--;
         break;
      }
   }
}

//+------------------------------------------------------------------+
//| Refresh position status from broker                             |
//+------------------------------------------------------------------+
void CPositionManager::RefreshPositionStatus()
{
   SyncWithBroker();
   UpdateAllPositions();
}

//+------------------------------------------------------------------+
//| Sync position list with broker                                  |
//+------------------------------------------------------------------+
void CPositionManager::SyncWithBroker()
{
   // Clear current list
   positionCount = 0;

   // Iterate through all open positions on broker
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) > 0)
      {
         if(positionCount < 100)
         {
            ulong ticket = PositionGetTicket(i);
            positions[positionCount].ticket = ticket;
            positions[positionCount].symbol = PositionGetString(POSITION_SYMBOL);
            positions[positionCount].type = (int)PositionGetInteger(POSITION_TYPE);
            positions[positionCount].volume = PositionGetDouble(POSITION_VOLUME);
            positions[positionCount].openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
            positions[positionCount].stopLoss = PositionGetDouble(POSITION_SL);
            positions[positionCount].takeProfit = PositionGetDouble(POSITION_TP);
            positions[positionCount].profitLoss = PositionGetDouble(POSITION_PROFIT);
            positions[positionCount].openTime = (datetime)PositionGetInteger(POSITION_TIME);
            positions[positionCount].lastUpdateTime = TimeCurrent();
            positions[positionCount].comment = PositionGetString(POSITION_COMMENT);

            positionCount++;
         }
      }
   }
}

#endif

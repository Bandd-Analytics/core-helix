//+------------------------------------------------------------------+
//|                                                 CExitManager.mqh |
//|                  MT5 POC - Exit Management and Stop/Target Logic |
//|                  v2.1: BEC partial close + trailing remainder    |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "2.10"

#ifndef CEXIT_MANAGER_H
#define CEXIT_MANAGER_H

#include "CEntryManager.mqh"

//--- Exit condition structure
struct SExitCondition
{
   bool   hitStopLoss;
   bool   hitTakeProfit;
   bool   timeExit;
   bool   trailingStop;
   bool   partialClose;     // Half position closed at intermediate target
   bool   manualClose;
   string reason;
};

//--- Per-position partial close state (parallel to barsHeld[])
//    Tracks whether the first 50% has been closed and trails the rest.
struct SPartialCloseState
{
   bool   partialClosed;    // True once the 50% close has been executed
   double trailingHigh;     // Best bid seen after partial close (for longs)
   double trailingLow;      // Best ask seen after partial close (for shorts)
   double trailATRMult;     // ATR multiplier for trailing the remainder
};

//--- Exit manager class
class CExitManager : public CEntryManager
{
private:
   int               maxHoldBars[5];
   int               barsHeld[100];
   double            trailingStopATR;
   SPartialCloseState partialState[100];  // Parallel to barsHeld[]

public:
   CExitManager();
   ~CExitManager();

   bool   InitExit(double trailingATRMult = 3.0);

   bool   CheckExitConditions(ulong ticket, SExitCondition &exitCond);
   bool   ClosePosition(ulong ticket, string reason);
   bool   UpdateTrailingStop(ulong ticket, double atr);
   bool   UpdateTakeProfit(ulong ticket, double newTP);

   // Partial close — call after CheckExitConditions() flags partialClose
   // Closes 50% of position and activates trailing stop for the remainder.
   // posType: "SWING", "SCALP", or "MOMENTUM" — used to pick trail multiplier.
   bool   ExecutePartialClose(ulong ticket, int posIdx, double atr,
                               const string posType);

   // Trail the remaining half after partial close has fired
   bool   UpdatePartialTrail(ulong ticket, int posIdx, double atr);

   // Register a new position so partial state is reset
   void   RegisterPartialState(int posIdx, double trailMult = 1.5);

private:
   bool   IsStopLossHit(ulong ticket);
   bool   IsTakeProfitHit(ulong ticket);
   bool   IsTimeExitTriggered(ulong ticket);
   bool   IsPartialCloseTriggered(ulong ticket, int posIdx);
   bool   IsPartialTrailHit(ulong ticket, int posIdx);
   void   IncreaseBarCounter(ulong ticket);
   int    FindPositionIndex(ulong ticket);
};

//+------------------------------------------------------------------+
CExitManager::CExitManager() : trailingStopATR(3.0)
{
   isInitialized = false;
   ArrayInitialize(barsHeld, 0);

   for(int i = 0; i < 100; i++)
   {
      partialState[i].partialClosed = false;
      partialState[i].trailingHigh  = 0.0;
      partialState[i].trailingLow   = DBL_MAX;
      partialState[i].trailATRMult  = 1.5;
   }
}

//+------------------------------------------------------------------+
CExitManager::~CExitManager() {}

//+------------------------------------------------------------------+
bool CExitManager::InitExit(double trailingATRMult)
{
   if(!CEntryManager::InitEntry()) return false;
   trailingStopATR = trailingATRMult;
   isInitialized   = true;
   return true;
}

//+------------------------------------------------------------------+
//| Reset partial close state when a new position is opened          |
//+------------------------------------------------------------------+
void CExitManager::RegisterPartialState(int posIdx, double trailMult)
{
   if(posIdx < 0 || posIdx >= 100) return;
   partialState[posIdx].partialClosed = false;
   partialState[posIdx].trailingHigh  = 0.0;
   partialState[posIdx].trailingLow   = DBL_MAX;
   partialState[posIdx].trailATRMult  = trailMult;
   barsHeld[posIdx] = 0;
}

//+------------------------------------------------------------------+
//| Check all exit conditions for a position                         |
//+------------------------------------------------------------------+
bool CExitManager::CheckExitConditions(ulong ticket, SExitCondition &exitCond)
{
   if(!isInitialized) return false;

   ZeroMemory(exitCond);

   int posIdx = FindPositionIndex(ticket);

   exitCond.hitStopLoss  = IsStopLossHit(ticket);
   exitCond.hitTakeProfit = IsTakeProfitHit(ticket);
   exitCond.timeExit     = IsTimeExitTriggered(ticket);

   // Partial close check: only fires once, only if not already partially closed
   if(posIdx >= 0 && !partialState[posIdx].partialClosed)
      exitCond.partialClose = IsPartialCloseTriggered(ticket, posIdx);

   // Trailing stop on the remainder (post-partial-close only)
   if(posIdx >= 0 && partialState[posIdx].partialClosed)
      exitCond.trailingStop = IsPartialTrailHit(ticket, posIdx);

   IncreaseBarCounter(ticket);

   return (exitCond.hitStopLoss  || exitCond.hitTakeProfit ||
           exitCond.timeExit     || exitCond.partialClose  ||
           exitCond.trailingStop);
}

//+------------------------------------------------------------------+
//| Check if price has reached 50% of the full profit target         |
//|                                                                   |
//| This uses the MT5 TP as a proxy for the full target. When price  |
//| reaches (entry + 0.5 * (TP - entry)) we flag partial close.      |
//+------------------------------------------------------------------+
bool CExitManager::IsPartialCloseTriggered(ulong ticket, int posIdx)
{
   if(!PositionSelectByTicket(ticket)) return false;

   double tp        = PositionGetDouble(POSITION_TP);
   double entryPx   = PositionGetDouble(POSITION_PRICE_OPEN);
   double bid       = SymbolInfoDouble(PositionGetString(POSITION_SYMBOL), SYMBOL_BID);
   double ask       = SymbolInfoDouble(PositionGetString(POSITION_SYMBOL), SYMBOL_ASK);
   int    type      = (int)PositionGetInteger(POSITION_TYPE);

   if(tp <= 0 || entryPx <= 0) return false;

   double halfTarget = entryPx + 0.5 * (tp - entryPx);  // Midpoint between entry and TP

   if(type == POSITION_TYPE_BUY)
      return (bid >= halfTarget);
   else
      return (ask <= halfTarget);
}

//+------------------------------------------------------------------+
//| Execute 50% close and arm the trailing stop for the remainder    |
//+------------------------------------------------------------------+
bool CExitManager::ExecutePartialClose(ulong ticket, int posIdx,
                                        double atr, const string posType)
{
   if(!PositionSelectByTicket(ticket)) return false;
   if(posIdx < 0 || posIdx >= 100)    return false;

   string _sym = PositionGetString(POSITION_SYMBOL);
   double lots = PositionGetDouble(POSITION_VOLUME);
   double volStep = SymbolInfoDouble(_sym, SYMBOL_VOLUME_STEP);
   if(volStep <= 0) volStep = 0.01;
   double halfLots = MathFloor(lots * 0.5 / volStep) * volStep;
   if(halfLots <= 0) return false;

   // Close 50% of the position
   bool ok = trade.PositionClosePartial(ticket, halfLots);
   if(!ok)
   {
      Print("CExitManager: Partial close failed for ticket ", ticket,
            " retcode=", trade.ResultRetcode());
      return false;
   }

   // Arm trailing state for the remaining half
   int    posType_int = (int)PositionGetInteger(POSITION_TYPE);
   double bid         = SymbolInfoDouble(PositionGetString(POSITION_SYMBOL), SYMBOL_BID);
   double ask         = SymbolInfoDouble(PositionGetString(POSITION_SYMBOL), SYMBOL_ASK);

   // Trail multiplier: tighter for scalps/momentum, wider for swings
   double trailMult = 1.5;
   if(StringFind(posType, "SWING") >= 0)    trailMult = 2.0;
   if(StringFind(posType, "SCALP") >= 0)    trailMult = 0.75;
   if(StringFind(posType, "MOMENTUM") >= 0) trailMult = 0.5;

   partialState[posIdx].partialClosed = true;
   partialState[posIdx].trailATRMult  = trailMult;
   partialState[posIdx].trailingHigh  = (posType_int == POSITION_TYPE_BUY)  ? bid : 0.0;
   partialState[posIdx].trailingLow   = (posType_int == POSITION_TYPE_SELL) ? ask : DBL_MAX;

   Print("CExitManager: Partial close executed on ", ticket,
         " halfLots=", DoubleToString(halfLots, 2),
         " trailing armed at mult=", DoubleToString(trailMult, 2));
   return true;
}

//+------------------------------------------------------------------+
//| Check if trailing stop for the remaining half has been hit       |
//+------------------------------------------------------------------+
bool CExitManager::IsPartialTrailHit(ulong ticket, int posIdx)
{
   if(!PositionSelectByTicket(ticket)) return false;
   if(posIdx < 0 || posIdx >= 100)    return false;
   if(!partialState[posIdx].partialClosed) return false;

   string sym  = PositionGetString(POSITION_SYMBOL);
   int    type = (int)PositionGetInteger(POSITION_TYPE);
   double atr  = 0.0;
   int    tmpH = iATR(sym, PERIOD_CURRENT, 14);
   if(tmpH != INVALID_HANDLE) { double b[1]; if(CopyBuffer(tmpH,0,0,1,b)>0) atr=b[0]; IndicatorRelease(tmpH); }
   double bid  = SymbolInfoDouble(sym, SYMBOL_BID);
   double ask  = SymbolInfoDouble(sym, SYMBOL_ASK);
   double mult = partialState[posIdx].trailATRMult;

   if(type == POSITION_TYPE_BUY)
   {
      // Update trailing high
      if(bid > partialState[posIdx].trailingHigh)
         partialState[posIdx].trailingHigh = bid;
      double trailSL = partialState[posIdx].trailingHigh - atr * mult * _Point;
      return (bid <= trailSL);
   }
   else
   {
      // Update trailing low
      if(ask < partialState[posIdx].trailingLow)
         partialState[posIdx].trailingLow = ask;
      double trailSL = partialState[posIdx].trailingLow + atr * mult * _Point;
      return (ask >= trailSL);
   }
}

//+------------------------------------------------------------------+
//| Update trailing stop for the remaining half (call each bar)      |
//+------------------------------------------------------------------+
bool CExitManager::UpdatePartialTrail(ulong ticket, int posIdx, double atr)
{
   if(!PositionSelectByTicket(ticket)) return false;
   if(posIdx < 0 || posIdx >= 100)    return false;
   if(!partialState[posIdx].partialClosed) return false;

   string sym  = PositionGetString(POSITION_SYMBOL);
   int    type = (int)PositionGetInteger(POSITION_TYPE);
   double bid  = SymbolInfoDouble(sym, SYMBOL_BID);
   double ask  = SymbolInfoDouble(sym, SYMBOL_ASK);
   double mult = partialState[posIdx].trailATRMult;

   // Update best price seen
   if(type == POSITION_TYPE_BUY && bid > partialState[posIdx].trailingHigh)
      partialState[posIdx].trailingHigh = bid;
   else if(type == POSITION_TYPE_SELL && ask < partialState[posIdx].trailingLow)
      partialState[posIdx].trailingLow = ask;

   // Push MT5 SL to the trail level (only tighten)
   double currentSL = PositionGetDouble(POSITION_SL);
   double newSL     = 0.0;

   if(type == POSITION_TYPE_BUY)
   {
      newSL = partialState[posIdx].trailingHigh - atr * mult * _Point;
      if(newSL > currentSL)
         trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP));
   }
   else
   {
      newSL = partialState[posIdx].trailingLow + atr * mult * _Point;
      if(newSL < currentSL || currentSL == 0)
         trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP));
   }

   return true;
}

//+------------------------------------------------------------------+
bool CExitManager::ClosePosition(ulong ticket, string reason)
{
   if(!PositionSelectByTicket(ticket)) return false;

   trade.PositionClose(ticket);

   if(trade.ResultRetcode() == 10009)
   {
      UnregisterPosition(ticket);
      return true;
   }

   Print("Error closing position ", ticket, " reason: ", reason);
   return false;
}

//+------------------------------------------------------------------+
bool CExitManager::UpdateTrailingStop(ulong ticket, double atr)
{
   if(!PositionSelectByTicket(ticket)) return false;

   int    type      = (int)PositionGetInteger(POSITION_TYPE);
   double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
   string sym       = PositionGetString(POSITION_SYMBOL);
   double bid       = SymbolInfoDouble(sym, SYMBOL_BID);
   double ask       = SymbolInfoDouble(sym, SYMBOL_ASK);
   double newSL     = 0;

   if(type == POSITION_TYPE_BUY)
   {
      newSL = bid - (atr * trailingStopATR * _Point);
      if(newSL > openPrice)
      {
         trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP));
         return true;
      }
   }
   else
   {
      newSL = ask + (atr * trailingStopATR * _Point);
      if(newSL < openPrice)
      {
         trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP));
         return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
bool CExitManager::UpdateTakeProfit(ulong ticket, double newTP)
{
   if(!PositionSelectByTicket(ticket)) return false;
   trade.PositionModify(ticket, PositionGetDouble(POSITION_SL), newTP);
   return (trade.ResultRetcode() == 10009);
}

//+------------------------------------------------------------------+
bool CExitManager::IsStopLossHit(ulong ticket)
{
   if(!PositionSelectByTicket(ticket)) return false;
   double sl  = PositionGetDouble(POSITION_SL);
   if(sl <= 0) return false;
   string sym = PositionGetString(POSITION_SYMBOL);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   int    type = (int)PositionGetInteger(POSITION_TYPE);
   return (type == POSITION_TYPE_BUY) ? (bid <= sl) : (ask >= sl);
}

//+------------------------------------------------------------------+
bool CExitManager::IsTakeProfitHit(ulong ticket)
{
   if(!PositionSelectByTicket(ticket)) return false;
   double tp  = PositionGetDouble(POSITION_TP);
   if(tp <= 0) return false;
   string sym = PositionGetString(POSITION_SYMBOL);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   int    type = (int)PositionGetInteger(POSITION_TYPE);
   return (type == POSITION_TYPE_BUY) ? (bid >= tp) : (ask <= tp);
}

//+------------------------------------------------------------------+
bool CExitManager::IsTimeExitTriggered(ulong ticket)
{
   for(int i = 0; i < GetOpenPositionCount(); i++)
   {
      SOpenPosition pos;
      if(GetPosition(i, pos) && pos.ticket == ticket)
         return (barsHeld[i] > 48);
   }
   return false;
}

//+------------------------------------------------------------------+
void CExitManager::IncreaseBarCounter(ulong ticket)
{
   for(int i = 0; i < GetOpenPositionCount(); i++)
   {
      SOpenPosition pos;
      if(GetPosition(i, pos) && pos.ticket == ticket)
      {
         barsHeld[i]++;
         break;
      }
   }
}

//+------------------------------------------------------------------+
int CExitManager::FindPositionIndex(ulong ticket)
{
   for(int i = 0; i < GetOpenPositionCount(); i++)
   {
      SOpenPosition pos;
      if(GetPosition(i, pos) && pos.ticket == ticket)
         return i;
   }
   return -1;
}

#endif

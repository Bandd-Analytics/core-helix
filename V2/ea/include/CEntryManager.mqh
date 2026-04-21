//+------------------------------------------------------------------+
//|                                                 CEntryManager.mqh |
//|                   MT5 POC - Order Entry Execution Manager |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CENTRY_MANAGER_H
#define CENTRY_MANAGER_H

#include "CPositionManager.mqh"

//--- Entry request structure
struct SEntryRequest
{
   string    symbol;
   int       direction;          // BUY or SELL
   double    volume;
   double    entryPrice;
   double    stopLossPips;
   double    takeProfitPips;
   string    comment;
   int       magicNumber;
};

//--- Entry manager class
class CEntryManager : public CPositionManager
{
private:
   int       maxRetries;
   int       retryDelayMs;
   double    slippagePips;

public:
   // Constructor & Destructor
   CEntryManager();
   ~CEntryManager();

   // Initialization
   bool      InitEntry(double slippagePips = 0.5, int maxRetries = 3);

   // Entry execution
   bool      SubmitEntry(SEntryRequest &request, ulong &resultTicket);
   bool      SubmitEntryWithRetry(SEntryRequest &request, ulong &resultTicket);

private:
   bool      ExecuteTrade(SEntryRequest &request, ulong &ticket);
   void      LogEntryError(int errorCode, SEntryRequest &request);
   bool      IsRetryableError(int errorCode);
   void      ApplySlippageToPrice(SEntryRequest &request);
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CEntryManager::CEntryManager() : maxRetries(3), retryDelayMs(500), slippagePips(0.5)
{
   isInitialized = false;
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CEntryManager::~CEntryManager()
{
}

//+------------------------------------------------------------------+
//| Initialize entry manager                                        |
//+------------------------------------------------------------------+
bool CEntryManager::InitEntry(double inpSlippagePips, int inpMaxRetries)
{
   if(!CPositionManager::Init())
      return false;

   slippagePips = inpSlippagePips;
   maxRetries = inpMaxRetries;

   // Set trading parameters
   trade.SetExpertMagicNumber(0);  // Will be set per entry

   isInitialized = true;
   return true;
}

//+------------------------------------------------------------------+
//| Submit entry order                                              |
//+------------------------------------------------------------------+
bool CEntryManager::SubmitEntry(SEntryRequest &request, ulong &resultTicket)
{
   if(!isInitialized)
      return false;

   return ExecuteTrade(request, resultTicket);
}

//+------------------------------------------------------------------+
//| Submit entry with automatic retry on failure                   |
//+------------------------------------------------------------------+
bool CEntryManager::SubmitEntryWithRetry(SEntryRequest &request, ulong &resultTicket)
{
   if(!isInitialized)
      return false;

   for(int attempt = 0; attempt < maxRetries; attempt++)
   {
      if(ExecuteTrade(request, resultTicket))
         return true;

      // Check if error is retryable
      int lastError = GetLastError();
      if(!IsRetryableError(lastError))
         return false;

      // Wait before retry
      Sleep(retryDelayMs);
   }

   return false;
}

//+------------------------------------------------------------------+
//| Execute trade order                                             |
//+------------------------------------------------------------------+
bool CEntryManager::ExecuteTrade(SEntryRequest &request, ulong &ticket)
{
   // Set magic number
   trade.SetExpertMagicNumber(request.magicNumber);

   // Calculate SL and TP
   double slPips = request.stopLossPips;
   double tpPips = request.takeProfitPips;
   double point = _Point;

   double sl = 0, tp = 0;

   if(request.direction == ORDER_TYPE_BUY)
   {
      sl = request.entryPrice - (slPips * point);
      tp = request.entryPrice + (tpPips * point);
   }
   else  // SELL
   {
      sl = request.entryPrice + (slPips * point);
      tp = request.entryPrice - (tpPips * point);
   }

   // Submit order
   if(request.direction == ORDER_TYPE_BUY)
   {
      if(trade.Buy(request.volume, request.symbol, request.entryPrice, sl, tp, request.comment))
      {
         ticket = trade.ResultOrder();
         return true;
      }
   }
   else
   {
      if(trade.Sell(request.volume, request.symbol, request.entryPrice, sl, tp, request.comment))
      {
         ticket = trade.ResultOrder();
         return true;
      }
   }

   LogEntryError(GetLastError(), request);
   return false;
}

//+------------------------------------------------------------------+
//| Log entry error                                                 |
//+------------------------------------------------------------------+
void CEntryManager::LogEntryError(int errorCode, SEntryRequest &request)
{
   Print("Entry Error for ", request.symbol, " - Error Code: ", errorCode,
         " - Retryable: ", IsRetryableError(errorCode) ? "Yes" : "No");
}

//+------------------------------------------------------------------+
//| Check if error code is retryable                                |
//+------------------------------------------------------------------+
bool CEntryManager::IsRetryableError(int errorCode)
{
   // Temporary errors that warrant retry
   // Common retryable error codes: timeout, network issues, price changes
   // Use conservative approach: retry for most non-permanent errors
   switch(errorCode)
   {
      case 0:  // Success - but should not retry on success
      case 10009:  // TRADE_RETCODE_DONE
         return false;
      case 128:   // Custom timeout code
      case 129:   // Custom network error code
         return true;
      default:
         // For now, don't retry on unhandled errors to avoid infinite loops
         return false;
   }
}

//+------------------------------------------------------------------+
//| Apply slippage adjustment to entry price                        |
//+------------------------------------------------------------------+
void CEntryManager::ApplySlippageToPrice(SEntryRequest &request)
{
   double point = _Point;

   if(request.direction == ORDER_TYPE_BUY)
      request.entryPrice += (slippagePips * point);
   else
      request.entryPrice -= (slippagePips * point);
}

#endif

//+------------------------------------------------------------------+
//|                                               CCircuitBreaker.mqh |
//|            MT5 POC - Multi-Layer Circuit Breaker System |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CCIRCUIT_BREAKER_H
#define CCIRCUIT_BREAKER_H

#include "CCorrelationMonitor.mqh"

//--- Circuit breaker state
struct SCircuitBreakerState
{
   bool     isDailyLimitHit;
   bool     isWeeklyLimitHit;
   bool     isDrawdownLimitHit;
   bool     isCircuitBreakerActive;
   datetime activationTime;
   int      hoursSinceActivation;
   bool     resumptionScheduled;
};

//--- Circuit breaker class
class CCircuitBreaker : public CCorrelationMonitor
{
private:
   SCircuitBreakerState cbState;
   int       CIRCUIT_BREAKER_HOURS;
   bool      isLoggingEnabled;

public:
   // Constructor & Destructor
   CCircuitBreaker();
   ~CCircuitBreaker();

   // Initialization
   bool      InitCircuitBreaker(double initialEquity, SRiskLimits &inpLimits);

   // Circuit breaker checks
   bool      CheckAllLimits();
   bool      IsDailyLimitBreached();
   bool      IsWeeklyLimitBreached();
   bool      IsDrawdownLimitBreached();
   bool      IsCircuitBreakerActive();

   // Circuit breaker control
   void      ActivateCircuitBreaker(string reason);
   void      DeactivateCircuitBreaker();
   void      CheckCircuitBreakerResumption();

   // State accessors
   SCircuitBreakerState GetCircuitBreakerState() { return cbState; }
   string    GetCircuitBreakerReason();

   // Logging
   void      SetLoggingEnabled(bool enabled) { isLoggingEnabled = enabled; }

private:
   int       CalculateHoursSinceActivation();
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CCircuitBreaker::CCircuitBreaker() : isLoggingEnabled(true), CIRCUIT_BREAKER_HOURS(48)
{
   ZeroMemory(cbState);
   cbState.isDailyLimitHit = false;
   cbState.isWeeklyLimitHit = false;
   cbState.isDrawdownLimitHit = false;
   cbState.isCircuitBreakerActive = false;
   cbState.activationTime = 0;
   cbState.hoursSinceActivation = 0;
   cbState.resumptionScheduled = false;
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CCircuitBreaker::~CCircuitBreaker()
{
}

//+------------------------------------------------------------------+
//| Initialize circuit breaker                                      |
//+------------------------------------------------------------------+
bool CCircuitBreaker::InitCircuitBreaker(double initialEquity, SRiskLimits &inpLimits)
{
   if(!InitMonitor(initialEquity, inpLimits))
      return false;

   ZeroMemory(cbState);
   cbState.isDailyLimitHit = false;
   cbState.isWeeklyLimitHit = false;
   cbState.isDrawdownLimitHit = false;
   cbState.isCircuitBreakerActive = false;

   return true;
}

//+------------------------------------------------------------------+
//| Check all risk limits (primary gating function)                 |
//+------------------------------------------------------------------+
bool CCircuitBreaker::CheckAllLimits()
{
   // First, check circuit breaker status
   if(IsCircuitBreakerActive())
   {
      CheckCircuitBreakerResumption();
      if(IsCircuitBreakerActive())
         return false;  // Circuit breaker still active
   }

   // Check individual limits
   cbState.isDailyLimitHit = !CheckDailyLossLimit();
   cbState.isWeeklyLimitHit = !CheckWeeklyLossLimit();
   cbState.isDrawdownLimitHit = !CheckDrawdownLimit();

   // If any limit breached, activate circuit breaker
   if(cbState.isDailyLimitHit || cbState.isWeeklyLimitHit || cbState.isDrawdownLimitHit)
   {
      ActivateCircuitBreaker(GetCircuitBreakerReason());
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Check if daily loss limit is breached                           |
//+------------------------------------------------------------------+
bool CCircuitBreaker::IsDailyLimitBreached()
{
   return !CheckDailyLossLimit();
}

//+------------------------------------------------------------------+
//| Check if weekly loss limit is breached                          |
//+------------------------------------------------------------------+
bool CCircuitBreaker::IsWeeklyLimitBreached()
{
   return !CheckWeeklyLossLimit();
}

//+------------------------------------------------------------------+
//| Check if drawdown limit is breached                             |
//+------------------------------------------------------------------+
bool CCircuitBreaker::IsDrawdownLimitBreached()
{
   return !CheckDrawdownLimit();
}

//+------------------------------------------------------------------+
//| Check if circuit breaker is currently active                    |
//+------------------------------------------------------------------+
bool CCircuitBreaker::IsCircuitBreakerActive()
{
   return cbState.isCircuitBreakerActive;
}

//+------------------------------------------------------------------+
//| Activate circuit breaker with reason logging                    |
//+------------------------------------------------------------------+
void CCircuitBreaker::ActivateCircuitBreaker(string reason)
{
   if(cbState.isCircuitBreakerActive)
      return;  // Already active

   cbState.isCircuitBreakerActive = true;
   cbState.activationTime = TimeCurrent();
   cbState.hoursSinceActivation = 0;
   cbState.resumptionScheduled = false;

   if(isLoggingEnabled)
   {
      Print("CIRCUIT BREAKER ACTIVATED at ", TimeToString(cbState.activationTime), " - Reason: ", reason);
      Print("Daily Loss: ", GetDailyLossPercent(), "% | ",
            "Weekly Loss: ", GetWeeklyLossPercent(), "% | ",
            "Drawdown: ", GetDrawdownPercent(), "%");
   }
}

//+------------------------------------------------------------------+
//| Deactivate circuit breaker                                      |
//+------------------------------------------------------------------+
void CCircuitBreaker::DeactivateCircuitBreaker()
{
   if(!cbState.isCircuitBreakerActive)
      return;

   cbState.isCircuitBreakerActive = false;
   cbState.activationTime = 0;
   cbState.hoursSinceActivation = 0;

   if(isLoggingEnabled)
   {
      Print("CIRCUIT BREAKER DEACTIVATED at ", TimeToString(TimeCurrent()));
      Print("Resume trading with 0.5% risk for first 10 trades");
   }
}

//+------------------------------------------------------------------+
//| Check if circuit breaker should be resumed                      |
//+------------------------------------------------------------------+
void CCircuitBreaker::CheckCircuitBreakerResumption()
{
   if(!cbState.isCircuitBreakerActive)
      return;

   int hoursSince = CalculateHoursSinceActivation();

   // After 48 hours, allow resumption
   if(hoursSince >= CIRCUIT_BREAKER_HOURS && !cbState.resumptionScheduled)
   {
      cbState.resumptionScheduled = true;

      if(isLoggingEnabled)
      {
         Print("Circuit breaker 48-hour cooldown complete. Resumption scheduled with reduced risk.");
      }

      // Check if we can safely resume (limits no longer breached)
      if(CheckDailyLossLimit() && CheckWeeklyLossLimit())
      {
         DeactivateCircuitBreaker();
      }
   }
}

//+------------------------------------------------------------------+
//| Get circuit breaker reason string                               |
//+------------------------------------------------------------------+
string CCircuitBreaker::GetCircuitBreakerReason()
{
   string reason = "";

   if(cbState.isDailyLimitHit)
      reason += "Daily loss limit hit (" + DoubleToString(GetDailyLossPercent(), 2) + "%) | ";

   if(cbState.isWeeklyLimitHit)
      reason += "Weekly loss limit hit (" + DoubleToString(GetWeeklyLossPercent(), 2) + "%) | ";

   if(cbState.isDrawdownLimitHit)
      reason += "Drawdown limit hit (" + DoubleToString(GetDrawdownPercent(), 2) + "%)";

   return reason;
}

//+------------------------------------------------------------------+
//| Calculate hours since circuit breaker activation                |
//+------------------------------------------------------------------+
int CCircuitBreaker::CalculateHoursSinceActivation()
{
   if(cbState.activationTime == 0)
      return 0;

   long secondsSince = TimeCurrent() - cbState.activationTime;
   return (int)(secondsSince / 3600);
}

#endif

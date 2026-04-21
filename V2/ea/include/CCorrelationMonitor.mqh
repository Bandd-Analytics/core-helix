//+------------------------------------------------------------------+
//|                                            CCorrelationMonitor.mqh |
//|              MT5 POC - Correlation Tracking and Portfolio Risk    |
//|              v2.1: Added StatArb cointegration Z-score +          |
//|                    per-currency net exposure tracking             |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "2.10"

#ifndef CCORRELATION_MONITOR_H
#define CCORRELATION_MONITOR_H

#include "CExitManager.mqh"

//--- Correlation matrix (5x5 flattened)
struct SCorrelationMatrix
{
   double   data[25];
   datetime lastUpdate;
};

//--- Portfolio risk tracker
struct SPortfolioRisk
{
   double totalRisk;
   double aggregateRiskLimit;
   int    positionCount;
   int    maxConcurrentPositions;
   double maxSingleCurrencyExposure;
};

//--- Cointegration spread state for mean-reversion pairs
//    Tracks log-price Z-score for AUDNZD (idx 0) and EURGBP (idx 1)
struct SCointegrationSpread
{
   double logPriceHistory[60];   // Rolling 60-bar log-price buffer
   int    bufferPos;             // Circular buffer position
   int    validBars;             // Bars populated so far
   double spreadMean;            // Rolling mean of log-price
   double spreadStdDev;          // Rolling std-dev of log-price
   double zScore;                // Current Z-score
};

//--- Currency exposure tracker
//    Currencies: 0=EUR 1=USD 2=GBP 3=JPY 4=AUD 5=NZD
//    Pair-to-currency exposure map (base=+1, quote=-1 per lot):
//      EURUSD[0]: +EUR, -USD
//      USDJPY[1]: +USD, -JPY
//      AUDNZD[2]: +AUD, -NZD
//      EURGBP[3]: +EUR, -GBP
//      GBPJPY[4]: +GBP, -JPY
struct SCurrencyExposure
{
   double netLots[6];   // Signed net lots: positive = long, negative = short
};

//+------------------------------------------------------------------+
class CCorrelationMonitor : public CExitManager
{
private:
   SCorrelationMatrix  correlationMatrix;
   SPortfolioRisk      portfolioRisk;
   double              dailyReturns[450];       // 5 pairs x 90 days, flattened
   int                 returnBarIndex;

   // Cointegration spread state for the 2 mean-reversion pairs
   SCointegrationSpread cointSpread[2];         // [0]=AUDNZD, [1]=EURGBP

   // Per-currency net lot exposure
   SCurrencyExposure   currencyExposure;

   // Pair→currency signed weights [pairIdx][currIdx] = +1 / -1 / 0
   static int          pairCurrencyMap[5][6];

public:
   CCorrelationMonitor();
   ~CCorrelationMonitor();

   bool     InitMonitor(double initialEquity, SRiskLimits &inpLimits);

   // Pearson correlation
   bool     UpdateCorrelationMatrix(string &pairSymbols[]);
   double   GetCorrelation(int pair1, int pair2);
   void     RecordDailyReturn(int pairIndex, double dailyReturn);

   // Portfolio risk
   bool     CheckAggregateRiskLimit(double proposedRisk);
   bool     CheckPositionCount(int currentPositions);
   bool     CheckHighCorrelationPairs(int pair1Index, int pair2Index);
   double   GetAdjustedRiskForCorrelation(double baseRisk, int pair1Index, int pair2Index);

   SPortfolioRisk GetPortfolioRisk()    { return portfolioRisk; }
   double   GetTotalPortfolioRisk()     { return portfolioRisk.totalRisk; }
   void     AddPositionRisk(double riskAmount);
   void     RemovePositionRisk(double riskAmount);
   void     ResetPortfolioRisk();

   // Cointegration Z-score (mean-reversion pairs only)
   void     UpdateSpreadZScore(int spreadIdx, double currentPrice);
   double   GetSpreadZScore(int spreadIdx);
   bool     IsSpreadExtreme(int spreadIdx, double threshold = 2.0);

   // Currency exposure
   void     UpdateCurrencyExposure(int pairIdx, double lots, int direction, bool isClose);
   double   GetCurrencyExposure(int currIdx);
   bool     CheckCurrencyExposureLimit(int pairIdx, double proposedLots, int direction);
   string   GetCurrencyExposureReport();

private:
   double   CalculateCorrelation(double &returns1[], double &returns2[], int count);
   double   CalculateMean(double &data[], int count);
   double   CalculateStdDev(double &data[], int count);
   void     RecalcSpreadStats(int spreadIdx);
};

// Static pair→currency map (base=+1, quote=-1, absent=0)
// Row  0=EURUSD: EUR+1 USD-1
// Row  1=USDJPY: USD+1 JPY-1
// Row  2=AUDNZD: AUD+1 NZD-1
// Row  3=EURGBP: EUR+1 GBP-1
// Row  4=GBPJPY: GBP+1 JPY-1
//       cols:  EUR  USD  GBP  JPY  AUD  NZD
static int CCorrelationMonitor::pairCurrencyMap[5][6] =
{
   {  1,  -1,   0,   0,   0,   0 },  // EURUSD
   {  0,   1,   0,  -1,   0,   0 },  // USDJPY
   {  0,   0,   0,   0,   1,  -1 },  // AUDNZD
   {  1,   0,  -1,   0,   0,   0 },  // EURGBP
   {  0,   0,   1,  -1,   0,   0 }   // GBPJPY
};

//+------------------------------------------------------------------+
CCorrelationMonitor::CCorrelationMonitor() : returnBarIndex(0)
{
   for(int i = 0; i < 5; i++)
      for(int j = 0; j < 5; j++)
         correlationMatrix.data[i*5 + j] = (i == j) ? 1.0 : 0.0;

   correlationMatrix.lastUpdate = 0;

   portfolioRisk.totalRisk                = 0;
   portfolioRisk.aggregateRiskLimit       = 0.03;
   portfolioRisk.positionCount            = 0;
   portfolioRisk.maxConcurrentPositions   = 5;
   portfolioRisk.maxSingleCurrencyExposure = 0.02;

   ArrayInitialize(dailyReturns, 0.0);

   // Initialise cointegration spread buffers
   for(int s = 0; s < 2; s++)
   {
      ArrayInitialize(cointSpread[s].logPriceHistory, 0.0);
      cointSpread[s].bufferPos  = 0;
      cointSpread[s].validBars  = 0;
      cointSpread[s].spreadMean = 0.0;
      cointSpread[s].spreadStdDev = 0.0;
      cointSpread[s].zScore     = 0.0;
   }

   // Initialise currency exposure
   ArrayInitialize(currencyExposure.netLots, 0.0);
}

//+------------------------------------------------------------------+
CCorrelationMonitor::~CCorrelationMonitor() {}

//+------------------------------------------------------------------+
bool CCorrelationMonitor::InitMonitor(double initialEquity, SRiskLimits &inpLimits)
{
   if(!InitSizer(initialEquity, inpLimits))       return false;
   if(!CPositionManager::Init())                  return false;
   if(!CEntryManager::InitEntry())                return false;
   if(!CExitManager::InitExit())                  return false;

   ResetPortfolioRisk();
   return true;
}

//+------------------------------------------------------------------+
//| Update Pearson correlation matrix from recorded daily returns    |
//+------------------------------------------------------------------+
bool CCorrelationMonitor::UpdateCorrelationMatrix(string &pairSymbols[])
{
   if(returnBarIndex < 30) return false;

   for(int i = 0; i < 5; i++)
   {
      for(int j = i + 1; j < 5; j++)
      {
         double returns1[90], returns2[90];
         for(int k = 0; k < 90; k++)
         {
            returns1[k] = dailyReturns[i*90 + k];
            returns2[k] = dailyReturns[j*90 + k];
         }
         double corr = CalculateCorrelation(returns1, returns2, 90);
         correlationMatrix.data[i*5 + j] = corr;
         correlationMatrix.data[j*5 + i] = corr;
      }
   }

   correlationMatrix.lastUpdate = TimeCurrent();
   return true;
}

//+------------------------------------------------------------------+
double CCorrelationMonitor::GetCorrelation(int pair1, int pair2)
{
   if(pair1 < 0 || pair1 >= 5 || pair2 < 0 || pair2 >= 5) return 0.0;
   return correlationMatrix.data[pair1*5 + pair2];
}

//+------------------------------------------------------------------+
void CCorrelationMonitor::RecordDailyReturn(int pairIndex, double dailyReturn)
{
   if(pairIndex < 0 || pairIndex >= 5) return;
   dailyReturns[pairIndex*90 + (returnBarIndex % 90)] = dailyReturn;
   if(pairIndex == 4) returnBarIndex++;
}

//+------------------------------------------------------------------+
bool CCorrelationMonitor::CheckAggregateRiskLimit(double proposedRisk)
{
   return (portfolioRisk.totalRisk + proposedRisk)
          <= (GetAccountState().initialEquity * portfolioRisk.aggregateRiskLimit);
}

//+------------------------------------------------------------------+
bool CCorrelationMonitor::CheckPositionCount(int currentPositions)
{
   return currentPositions < portfolioRisk.maxConcurrentPositions;
}

//+------------------------------------------------------------------+
bool CCorrelationMonitor::CheckHighCorrelationPairs(int pair1Index, int pair2Index)
{
   if(pair1Index < 0 || pair1Index >= 5 || pair2Index < 0 || pair2Index >= 5)
      return true;
   return MathAbs(GetCorrelation(pair1Index, pair2Index)) <= 0.75;
}

//+------------------------------------------------------------------+
double CCorrelationMonitor::GetAdjustedRiskForCorrelation(double baseRisk,
                                                           int pair1Index,
                                                           int pair2Index)
{
   if(pair1Index < 0 || pair1Index >= 5 || pair2Index < 0 || pair2Index >= 5)
      return baseRisk;
   double corr = MathAbs(GetCorrelation(pair1Index, pair2Index));
   if(corr > 0.75) return baseRisk / (1.0 + corr);
   return baseRisk;
}

//+------------------------------------------------------------------+
void CCorrelationMonitor::AddPositionRisk(double riskAmount)
{
   portfolioRisk.totalRisk += riskAmount;
   portfolioRisk.positionCount++;
}

//+------------------------------------------------------------------+
void CCorrelationMonitor::RemovePositionRisk(double riskAmount)
{
   portfolioRisk.totalRisk = MathMax(0.0, portfolioRisk.totalRisk - riskAmount);
   portfolioRisk.positionCount = MathMax(0, portfolioRisk.positionCount - 1);
}

//+------------------------------------------------------------------+
void CCorrelationMonitor::ResetPortfolioRisk()
{
   portfolioRisk.totalRisk     = 0;
   portfolioRisk.positionCount = 0;
}

// ═══════════════════════════════════════════════════════════════════
// COINTEGRATION SPREAD Z-SCORE
// spreadIdx: 0 = AUDNZD, 1 = EURGBP
// These are single cross-pair instruments so log(price) IS the
// cointegration spread — no hedge ratio needed.
// ═══════════════════════════════════════════════════════════════════

//+------------------------------------------------------------------+
//| Feed a new close price; updates rolling log-price Z-score        |
//+------------------------------------------------------------------+
void CCorrelationMonitor::UpdateSpreadZScore(int spreadIdx, double currentPrice)
{
   if(spreadIdx < 0 || spreadIdx > 1) return;
   if(currentPrice <= 0)              return;

   double logPrice = MathLog(currentPrice);

   cointSpread[spreadIdx].logPriceHistory[cointSpread[spreadIdx].bufferPos] = logPrice;
   cointSpread[spreadIdx].bufferPos = (cointSpread[spreadIdx].bufferPos + 1) % 60;
   if(cointSpread[spreadIdx].validBars < 60) cointSpread[spreadIdx].validBars++;

   if(cointSpread[spreadIdx].validBars >= 20)
      RecalcSpreadStats(spreadIdx);
}

//+------------------------------------------------------------------+
//| Recalculate mean, stddev, and Z-score from current buffer        |
//+------------------------------------------------------------------+
void CCorrelationMonitor::RecalcSpreadStats(int spreadIdx)
{
   int n = cointSpread[spreadIdx].validBars;

   double sum = 0.0;
   for(int i = 0; i < 60; i++)
      if(i < n) sum += cointSpread[spreadIdx].logPriceHistory[i];
   double mean = sum / n;

   double varSum = 0.0;
   for(int i = 0; i < 60; i++)
      if(i < n) varSum += MathPow(cointSpread[spreadIdx].logPriceHistory[i] - mean, 2);
   double stddev = (n > 1) ? MathSqrt(varSum / (n - 1)) : 0.0;

   cointSpread[spreadIdx].spreadMean   = mean;
   cointSpread[spreadIdx].spreadStdDev = stddev;

   int latestIdx = (cointSpread[spreadIdx].bufferPos - 1 + 60) % 60;
   double latestLogPrice = cointSpread[spreadIdx].logPriceHistory[latestIdx];

   cointSpread[spreadIdx].zScore = (stddev > 0) ? (latestLogPrice - mean) / stddev : 0.0;
}

//+------------------------------------------------------------------+
double CCorrelationMonitor::GetSpreadZScore(int spreadIdx)
{
   if(spreadIdx < 0 || spreadIdx > 1) return 0.0;
   return cointSpread[spreadIdx].zScore;
}

//+------------------------------------------------------------------+
//| Returns true when |Z| >= threshold — mean reversion entry zone   |
//+------------------------------------------------------------------+
bool CCorrelationMonitor::IsSpreadExtreme(int spreadIdx, double threshold)
{
   return MathAbs(GetSpreadZScore(spreadIdx)) >= threshold;
}

// ═══════════════════════════════════════════════════════════════════
// PER-CURRENCY NET EXPOSURE
// ═══════════════════════════════════════════════════════════════════

//+------------------------------------------------------------------+
//| Call on trade open (isClose=false) and close (isClose=true)      |
//| direction: +1 = long, -1 = short                                 |
//+------------------------------------------------------------------+
void CCorrelationMonitor::UpdateCurrencyExposure(int pairIdx, double lots,
                                                  int direction, bool isClose)
{
   if(pairIdx < 0 || pairIdx >= 5) return;

   double sign = isClose ? -1.0 : 1.0;  // Close reverses the exposure

   for(int c = 0; c < 6; c++)
   {
      double weight = (double)pairCurrencyMap[pairIdx][c];
      if(weight != 0)
         currencyExposure.netLots[c] += sign * direction * lots * weight;
   }
}

//+------------------------------------------------------------------+
//| Returns current net lot exposure for a currency (0-5 index)     |
//+------------------------------------------------------------------+
double CCorrelationMonitor::GetCurrencyExposure(int currIdx)
{
   if(currIdx < 0 || currIdx >= 6) return 0.0;
   return currencyExposure.netLots[currIdx];
}

//+------------------------------------------------------------------+
//| Returns false if adding this trade would push any currency       |
//| beyond maxSingleCurrencyExposure (as fraction of equity)        |
//+------------------------------------------------------------------+
bool CCorrelationMonitor::CheckCurrencyExposureLimit(int pairIdx, double proposedLots,
                                                       int direction)
{
   if(pairIdx < 0 || pairIdx >= 5) return true;

   double equity = GetAccountState().initialEquity;
   double limit  = portfolioRisk.maxSingleCurrencyExposure * equity;

   for(int c = 0; c < 6; c++)
   {
      double weight = (double)pairCurrencyMap[pairIdx][c];
      if(weight == 0) continue;

      double projected = MathAbs(currencyExposure.netLots[c]
                                  + direction * proposedLots * weight);
      if(projected > limit)
      {
         Print("CCorrelationMonitor: Currency exposure limit hit for currency index ", c,
               " projected=", DoubleToString(projected, 2),
               " limit=", DoubleToString(limit, 2));
         return false;
      }
   }
   return true;
}

//+------------------------------------------------------------------+
//| Returns a one-line string of net lots per currency for logging   |
//+------------------------------------------------------------------+
string CCorrelationMonitor::GetCurrencyExposureReport()
{
   string names[6] = {"EUR","USD","GBP","JPY","AUD","NZD"};
   string report = "NetLots: ";
   for(int c = 0; c < 6; c++)
   {
      if(MathAbs(currencyExposure.netLots[c]) > 0.001)
         report += names[c] + "=" + DoubleToString(currencyExposure.netLots[c], 2) + " ";
   }
   return report;
}

// ═══════════════════════════════════════════════════════════════════
// INTERNAL STATISTICS HELPERS
// ═══════════════════════════════════════════════════════════════════

double CCorrelationMonitor::CalculateCorrelation(double &returns1[], double &returns2[], int count)
{
   if(count < 2) return 0.0;

   double mean1 = CalculateMean(returns1, count);
   double mean2 = CalculateMean(returns2, count);

   double cov = 0.0, std1 = 0.0, std2 = 0.0;
   for(int i = 0; i < count; i++)
   {
      double d1 = returns1[i] - mean1;
      double d2 = returns2[i] - mean2;
      cov  += d1 * d2;
      std1 += d1 * d1;
      std2 += d2 * d2;
   }

   std1 = MathSqrt(std1 / count);
   std2 = MathSqrt(std2 / count);
   if(std1 == 0 || std2 == 0) return 0.0;

   return (cov / count) / (std1 * std2);
}

double CCorrelationMonitor::CalculateMean(double &data[], int count)
{
   if(count <= 0) return 0.0;
   double sum = 0.0;
   for(int i = 0; i < count; i++) sum += data[i];
   return sum / count;
}

double CCorrelationMonitor::CalculateStdDev(double &data[], int count)
{
   if(count < 2) return 0.0;
   double mean = CalculateMean(data, count);
   double sq   = 0.0;
   for(int i = 0; i < count; i++) sq += MathPow(data[i] - mean, 2);
   return MathSqrt(sq / count);
}

#endif

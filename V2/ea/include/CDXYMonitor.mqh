//+------------------------------------------------------------------+
//|                                                  CDXYMonitor.mqh |
//|            MT5 POC - USD Index Proxy + Intermarket Divergence    |
//|                                                                   |
//| Constructs a DXY proxy from 3 USD pairs in the portfolio:        |
//|   EURUSD (inverse), USDJPY (direct), GBPUSD (inverse)           |
//|                                                                   |
//| Used to detect when a USD pair is diverging from DXY direction:  |
//|   → EURUSD rising while DXY proxy also rising = divergence       |
//|   → Use as a confirmation filter before taking USD pair entries  |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CDXY_MONITOR_H
#define CDXY_MONITOR_H

//--- DXY bias constants
#define DXY_BIAS_BULLISH   1    // USD strengthening
#define DXY_BIAS_BEARISH  -1    // USD weakening
#define DXY_BIAS_NEUTRAL   0    // Unclear / conflicting

//--- Divergence constants
#define DXY_NO_DIVERGENCE       0
#define DXY_DIVERGENCE_BULLISH  1   // Pair bullish but DXY also bullish (fight)
#define DXY_DIVERGENCE_BEARISH -1   // Pair bearish but DXY also bearish (fight)

//--- State for one constituent pair
struct SDXYComponent
{
   string symbol;
   bool   inverseUSD;      // true = USD is quote (EURUSD, GBPUSD); false = USD is base (USDJPY)
   double returnHistory[20]; // Rolling 20-bar close returns
   int    bufferPos;
   int    validBars;
};

class CDXYMonitor
{
private:
   SDXYComponent components[3];    // EURUSD, USDJPY, GBPUSD
   double        dxyReturnHistory[20];
   int           dxyBufPos;
   int           dxyValidBars;

   double        dxyMA;            // Short-term mean of DXY proxy returns
   int           currentBias;
   double        divergenceThreshold; // Min return magnitude to flag divergence

public:
   CDXYMonitor();

   void   Init(double divThreshold = 0.0003);
   void   UpdateComponent(int compIdx, double currentClose, double prevClose);
   void   RecalcDXY();

   int    GetDXYBias()                           { return currentBias; }

   // Check if a proposed trade on a USD pair diverges from DXY direction.
   // pairIdx: 0=EURUSD, 1=USDJPY — only USD pairs are checked.
   // tradeDirection: +1=long, -1=short
   // Returns a DXY_DIVERGENCE_* constant.
   int    CheckDivergence(int pairIdx, int tradeDirection);

   // Returns true when DXY bias is clear AND the pair direction aligns.
   // Use as a bonus confirmation (not a hard block).
   bool   IsDXYAligned(int pairIdx, int tradeDirection);

   string GetStatusLine();

private:
   double CalcComponentReturn(int compIdx);
};

//+------------------------------------------------------------------+
CDXYMonitor::CDXYMonitor()
   : dxyBufPos(0), dxyValidBars(0), dxyMA(0.0),
     currentBias(DXY_BIAS_NEUTRAL), divergenceThreshold(0.0003)
{
   // EURUSD — USD is quote, so invert to get USD direction
   components[0].symbol     = "EURUSD";
   components[0].inverseUSD = true;
   components[0].bufferPos  = 0;
   components[0].validBars  = 0;
   ArrayInitialize(components[0].returnHistory, 0.0);

   // USDJPY — USD is base, direct
   components[1].symbol     = "USDJPY";
   components[1].inverseUSD = false;
   components[1].bufferPos  = 0;
   components[1].validBars  = 0;
   ArrayInitialize(components[1].returnHistory, 0.0);

   // GBPUSD — USD is quote, invert
   components[2].symbol     = "GBPUSD";
   components[2].inverseUSD = true;
   components[2].bufferPos  = 0;
   components[2].validBars  = 0;
   ArrayInitialize(components[2].returnHistory, 0.0);

   ArrayInitialize(dxyReturnHistory, 0.0);
}

//+------------------------------------------------------------------+
void CDXYMonitor::Init(double divThreshold)
{
   divergenceThreshold = divThreshold;
}

//+------------------------------------------------------------------+
//| Feed a new bar's close for one component.                        |
//| Call for all 3 components each bar, then call RecalcDXY().       |
//+------------------------------------------------------------------+
void CDXYMonitor::UpdateComponent(int compIdx, double currentClose, double prevClose)
{
   if(compIdx < 0 || compIdx >= 3) return;
   if(prevClose <= 0 || currentClose <= 0) return;

   SDXYComponent *c = &components[compIdx];

   double rawReturn = (currentClose - prevClose) / prevClose;

   // Invert return for pairs where USD is the quote currency
   double usdReturn = c->inverseUSD ? -rawReturn : rawReturn;

   c->returnHistory[c->bufferPos] = usdReturn;
   c->bufferPos = (c->bufferPos + 1) % 20;
   if(c->validBars < 20) c->validBars++;
}

//+------------------------------------------------------------------+
//| Recompute composite DXY proxy return and determine bias          |
//+------------------------------------------------------------------+
void CDXYMonitor::RecalcDXY()
{
   // Require all 3 components to have at least 5 bars
   for(int c = 0; c < 3; c++)
      if(components[c].validBars < 5) return;

   // Most-recent bar composite return = equal-weight average of 3 USD returns
   double r[3];
   for(int c = 0; c < 3; c++)
   {
      int latestIdx = (components[c].bufferPos - 1 + 20) % 20;
      r[c] = components[c].returnHistory[latestIdx];
   }
   double compositeReturn = (r[0] + r[1] + r[2]) / 3.0;

   // Store in DXY return history
   dxyReturnHistory[dxyBufPos] = compositeReturn;
   dxyBufPos = (dxyBufPos + 1) % 20;
   if(dxyValidBars < 20) dxyValidBars++;

   // Short-term mean of DXY proxy returns (5-bar)
   int lookback = MathMin(dxyValidBars, 5);
   double sum   = 0.0;
   for(int i = 0; i < lookback; i++)
   {
      int idx = (dxyBufPos - 1 - i + 20) % 20;
      sum += dxyReturnHistory[idx];
   }
   dxyMA = sum / lookback;

   // Classify bias
   if(dxyMA >  divergenceThreshold)       currentBias = DXY_BIAS_BULLISH;
   else if(dxyMA < -divergenceThreshold)  currentBias = DXY_BIAS_BEARISH;
   else                                   currentBias = DXY_BIAS_NEUTRAL;
}

//+------------------------------------------------------------------+
//| Detect divergence between the proposed trade and DXY direction   |
//|                                                                   |
//| Only meaningful for USD-denominated pairs (idx 0 = EURUSD,       |
//| idx 1 = USDJPY). Non-USD pairs return DXY_NO_DIVERGENCE.         |
//|                                                                   |
//| Example:                                                          |
//|   DXY = BULLISH (USD rising)                                      |
//|   Trade = LONG EURUSD (buy EUR, sell USD)                        |
//|   → Fighting the DXY → DXY_DIVERGENCE_BULLISH                    |
//+------------------------------------------------------------------+
int CDXYMonitor::CheckDivergence(int pairIdx, int tradeDirection)
{
   if(currentBias == DXY_BIAS_NEUTRAL) return DXY_NO_DIVERGENCE;

   // Only check EURUSD (pairIdx 0) and USDJPY (pairIdx 1)
   if(pairIdx != 0 && pairIdx != 1) return DXY_NO_DIVERGENCE;

   bool usdIsBase = (pairIdx == 1);  // USDJPY: long = long USD

   // Determine what the trade implies for USD
   // EURUSD long = short USD; USDJPY long = long USD
   int impliedUSDDirection = usdIsBase ? tradeDirection : -tradeDirection;

   if(impliedUSDDirection == 1 && currentBias == DXY_BIAS_BEARISH)
      return DXY_DIVERGENCE_BEARISH;  // Going long USD while DXY says USD weak

   if(impliedUSDDirection == -1 && currentBias == DXY_BIAS_BULLISH)
      return DXY_DIVERGENCE_BULLISH;  // Going short USD while DXY says USD strong

   return DXY_NO_DIVERGENCE;
}

//+------------------------------------------------------------------+
//| Returns true when DXY aligns with the proposed trade direction   |
//+------------------------------------------------------------------+
bool CDXYMonitor::IsDXYAligned(int pairIdx, int tradeDirection)
{
   return CheckDivergence(pairIdx, tradeDirection) == DXY_NO_DIVERGENCE
          && currentBias != DXY_BIAS_NEUTRAL;
}

//+------------------------------------------------------------------+
string CDXYMonitor::GetStatusLine()
{
   string bias;
   if(currentBias == DXY_BIAS_BULLISH)       bias = "BULLISH";
   else if(currentBias == DXY_BIAS_BEARISH)  bias = "BEARISH";
   else                                       bias = "NEUTRAL";

   return "DXY Proxy: " + bias
          + " | MA=" + DoubleToString(dxyMA * 10000.0, 2) + "pp";
}

#endif

//+------------------------------------------------------------------+
//|                                               CSignalManager.mqh |
//|                 MT5 POC - Signal Generation Base Class |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "1.00"

#ifndef CSIGNAL_MANAGER_H
#define CSIGNAL_MANAGER_H

#include "SymbolConfig.mqh"

//--- Signal constants
#define SIGNAL_NONE     0
#define SIGNAL_LONG     1
#define SIGNAL_SHORT   -1
#define SIGNAL_THRESHOLD 70  // 70/100 required for entry

//--- Signal manager base class
class CSignalManager
{
protected:
   SSymbolConfig  config;
   bool          isInitialized;
   int           indicatorHandles[7];  // Handles for 7 custom indicators

public:
   // Constructor & Destructor
   CSignalManager();
   ~CSignalManager();

   // Initialization
   virtual bool  Init(SSymbolConfig &symbolConfig);
   virtual void  Deinit();

   // Signal generation (must be overridden)
   virtual bool  GenerateSignal(SSignalEntry &signal) = 0;

   // Helper methods
   bool          LoadIndicators();
   void          ReleaseIndicators();
   double        GetIndicatorBuffer(int handleIndex, int bufferIndex, int barIndex);
   int           GetPrimaryTimeframe();
   string        GetSymbol() { return config.symbol; }

protected:
   // Indicator loading helpers
   int           LoadAdaptiveATR();
   int           LoadVolatilityRegime();
   int           LoadSessionFilter();
   int           LoadDonchianADX();
   int           LoadMeanRevOscillator();
   int           LoadHurstExponent();
   int           LoadRegimeClassifier();

   // Data retrieval helpers
   double        GetAdaptiveATR(int barIndex);
   double        GetATRPercentile(int barIndex);
   int           GetVolatilityRegime(int barIndex);
   int           GetRegimeCode(int barIndex);
   double        GetZScore(int barIndex);
   double        GetHalfLife(int barIndex);
   int           GetDonchianSignal(int barIndex);
   double        GetADX(int barIndex);
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CSignalManager::CSignalManager() : isInitialized(false)
{
   ArrayInitialize(indicatorHandles, INVALID_HANDLE);
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CSignalManager::~CSignalManager()
{
   Deinit();
}

//+------------------------------------------------------------------+
//| Initialize signal manager                                       |
//+------------------------------------------------------------------+
bool CSignalManager::Init(SSymbolConfig &symbolConfig)
{
   config = symbolConfig;

   if(!LoadIndicators())
   {
      Print("Error: Failed to load indicators for ", config.symbol);
      return false;
   }

   isInitialized = true;
   return true;
}

//+------------------------------------------------------------------+
//| Deinitialize signal manager                                     |
//+------------------------------------------------------------------+
void CSignalManager::Deinit()
{
   ReleaseIndicators();
   isInitialized = false;
}

//+------------------------------------------------------------------+
//| Load all required indicators                                    |
//+------------------------------------------------------------------+
bool CSignalManager::LoadIndicators()
{
   indicatorHandles[0] = LoadAdaptiveATR();
   indicatorHandles[1] = LoadVolatilityRegime();
   indicatorHandles[2] = LoadSessionFilter();
   indicatorHandles[3] = LoadDonchianADX();
   indicatorHandles[4] = LoadMeanRevOscillator();
   indicatorHandles[5] = LoadHurstExponent();
   indicatorHandles[6] = LoadRegimeClassifier();

   // All indicators should be loaded successfully
   for(int i = 0; i < 7; i++)
   {
      if(indicatorHandles[i] == INVALID_HANDLE)
      {
         Print("Error: Failed to load indicator ", i);
         return false;
      }
   }

   return true;
}

//+------------------------------------------------------------------+
//| Release all indicator handles                                   |
//+------------------------------------------------------------------+
void CSignalManager::ReleaseIndicators()
{
   for(int i = 0; i < 7; i++)
   {
      if(indicatorHandles[i] != INVALID_HANDLE)
      {
         IndicatorRelease(indicatorHandles[i]);
         indicatorHandles[i] = INVALID_HANDLE;
      }
   }
}

//+------------------------------------------------------------------+
//| Get value from indicator buffer                                 |
//+------------------------------------------------------------------+
double CSignalManager::GetIndicatorBuffer(int handleIndex, int bufferIndex, int barIndex)
{
   if(handleIndex < 0 || handleIndex >= 7 || indicatorHandles[handleIndex] == INVALID_HANDLE)
      return 0.0;

   double buffer[];
   if(CopyBuffer(indicatorHandles[handleIndex], bufferIndex, barIndex, 1, buffer) <= 0)
      return 0.0;

   return buffer[0];
}

//+------------------------------------------------------------------+
//| Load AdaptiveATR indicator                                      |
//+------------------------------------------------------------------+
int CSignalManager::LoadAdaptiveATR()
{
   return iCustom(NULL, 0, "AdaptiveATR");
}

//+------------------------------------------------------------------+
//| Load VolatilityRegime indicator                                 |
//+------------------------------------------------------------------+
int CSignalManager::LoadVolatilityRegime()
{
   return iCustom(NULL, 0, "VolatilityRegime");
}

//+------------------------------------------------------------------+
//| Load SessionFilter indicator                                    |
//+------------------------------------------------------------------+
int CSignalManager::LoadSessionFilter()
{
   return iCustom(NULL, 0, "SessionFilter");
}

//+------------------------------------------------------------------+
//| Load DonchianADX indicator                                      |
//+------------------------------------------------------------------+
int CSignalManager::LoadDonchianADX()
{
   return iCustom(NULL, 0, "DonchianADX", 20, 10, 14);
}

//+------------------------------------------------------------------+
//| Load MeanRevOscillator indicator                                |
//+------------------------------------------------------------------+
int CSignalManager::LoadMeanRevOscillator()
{
   return iCustom(NULL, 0, "MeanRevOscillator", config.zScorePeriod);
}

//+------------------------------------------------------------------+
//| Load HurstExponent indicator                                    |
//+------------------------------------------------------------------+
int CSignalManager::LoadHurstExponent()
{
   return iCustom(NULL, 0, "HurstExponent");
}

//+------------------------------------------------------------------+
//| Load RegimeClassifier indicator                                 |
//+------------------------------------------------------------------+
int CSignalManager::LoadRegimeClassifier()
{
   return iCustom(NULL, 0, "RegimeClassifier");
}

//+------------------------------------------------------------------+
//| Get AdaptiveATR value                                           |
//+------------------------------------------------------------------+
double CSignalManager::GetAdaptiveATR(int barIndex)
{
   return GetIndicatorBuffer(0, 0, barIndex);
}

//+------------------------------------------------------------------+
//| Get ATR percentile rank                                         |
//+------------------------------------------------------------------+
double CSignalManager::GetATRPercentile(int barIndex)
{
   return GetIndicatorBuffer(0, 1, barIndex);
}

//+------------------------------------------------------------------+
//| Get volatility regime                                           |
//+------------------------------------------------------------------+
int CSignalManager::GetVolatilityRegime(int barIndex)
{
   return (int)GetIndicatorBuffer(1, 0, barIndex);
}

//+------------------------------------------------------------------+
//| Get unified regime code                                         |
//+------------------------------------------------------------------+
int CSignalManager::GetRegimeCode(int barIndex)
{
   return (int)GetIndicatorBuffer(6, 0, barIndex);
}

//+------------------------------------------------------------------+
//| Get Z-score value                                               |
//+------------------------------------------------------------------+
double CSignalManager::GetZScore(int barIndex)
{
   return GetIndicatorBuffer(4, 0, barIndex);
}

//+------------------------------------------------------------------+
//| Get half-life value                                             |
//+------------------------------------------------------------------+
double CSignalManager::GetHalfLife(int barIndex)
{
   return GetIndicatorBuffer(4, 3, barIndex);
}

//+------------------------------------------------------------------+
//| Get Donchian signal                                             |
//+------------------------------------------------------------------+
int CSignalManager::GetDonchianSignal(int barIndex)
{
   return (int)GetIndicatorBuffer(3, 2, barIndex);
}

//+------------------------------------------------------------------+
//| Get ADX value                                                   |
//+------------------------------------------------------------------+
double CSignalManager::GetADX(int barIndex)
{
   int handle = iADX(config.symbol, config.primaryTimeframe, 14);
   if(handle == INVALID_HANDLE) return 0.0;
   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(handle, 0, barIndex, 1, buf) <= 0) { IndicatorRelease(handle); return 0.0; }
   IndicatorRelease(handle);
   return buf[0];
}

//+------------------------------------------------------------------+
//| Get primary timeframe                                           |
//+------------------------------------------------------------------+
int CSignalManager::GetPrimaryTimeframe()
{
   return config.primaryTimeframe;
}

#endif

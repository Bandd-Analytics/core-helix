//+------------------------------------------------------------------+
//|  SM_BPCT.mq4                                                      |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator (MQ4 idiomatic / D-20)|
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md |
//|                                                                   |
//|  D-17 Built ⚠ Low confidence — implementation per Verified Updates|
//|  2026-04-27 mini-HUD interpretation (NOT pressure-tracker; see    |
//|  Pitfall 10). // [INFER] on every guessed branch.                 |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_BPCT.ex4 (mini-HUD)"
#property version   "1.00"
#property indicator_chart_window
#property strict

// [INFER] (D-17) — Verified Updates 2026-04-27 mini-HUD; not pressure-tracker.

extern int    InpCornerOfChart        = 1;     // 0=LL 1=UR 2=LR 3=UL — VERIFIED RIGHT_TOP=1
extern bool   InpShowPrice            = true;
extern bool   InpShowXtraDetails      = true;
extern bool   InpShowSmallerSize      = true;
extern bool   InpShowTradePips        = true;
extern int    InpShiftUpDn            = 0;
extern int    InpAdjustSideToSide     = 0;
extern color  InpLabelColor           = clrWhite;
extern color  InpSpreadColor          = clrGold;
extern color  InpPriceUpColor         = clrLime;
extern color  InpPriceDnColor         = clrCrimson;
extern color  InpPriceAtExtremeColor  = clrDarkGreen;
extern double InpDistanceFromExtreme  = 12.0;  // VERIFIED
extern bool   InpHODLODAlert          = false;
extern double InpPipsToHODLODForAlert = 5.0;   // VERIFIED

string ObjectPrefix = "smBPCT_";
double g_pip = 0.0;
datetime g_last_alert_ts = 0;

//+------------------------------------------------------------------+
int init()
  {
   int digits = (int)MarketInfo(_Symbol, MODE_DIGITS);
   g_pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;
   IndicatorShortName("SM_BPCT (mini-HUD)");
   CreateLabels();
   Recompute();
   EventSetTimer(1);
   return(0);
  }

//+------------------------------------------------------------------+
int deinit()
  {
   CleanupObjects();
   EventKillTimer();
   return(0);
  }

//+------------------------------------------------------------------+
int start()
  {
   return(0);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
  }

//+------------------------------------------------------------------+
void CreateLabels()
  {
   string rows[5] = {"price", "spread", "hod", "lod", "alert"};
   for(int i = 0; i < 5; i++)
     {
      string name = ObjectPrefix + rows[i];
      if(ObjectFind(name) < 0)
         ObjectCreate(name, OBJ_LABEL, 0, 0, 0);

      ObjectSet(name, OBJPROP_CORNER,    InpCornerOfChart);
      ObjectSet(name, OBJPROP_XDISTANCE, 8 + InpAdjustSideToSide);
      ObjectSet(name, OBJPROP_YDISTANCE, 20 + InpShiftUpDn + i * 16);
      ObjectSetText(name, "", InpShowSmallerSize ? 9 : 11, "Arial", InpLabelColor);
     }
  }

//+------------------------------------------------------------------+
void Recompute()
  {
   double bid = MarketInfo(_Symbol, MODE_BID);
   double ask = MarketInfo(_Symbol, MODE_ASK);
   if(bid <= 0.0 || ask <= 0.0 || g_pip <= 0.0)
      return;

   double hod = iHigh(_Symbol, PERIOD_D1, 0);
   double lod = iLow (_Symbol, PERIOD_D1, 0);
   double spread_pips = (ask - bid) / g_pip;
   double hod_dist    = (hod - bid) / g_pip;
   double lod_dist    = (bid - lod) / g_pip;

   color price_color = InpLabelColor;
   if(InpShowPrice)
     {
      // [INFER] At-extreme color
      if(hod_dist < InpDistanceFromExtreme || lod_dist < InpDistanceFromExtreme)
         price_color = InpPriceAtExtremeColor;
      else
         price_color = (bid >= (hod + lod) / 2.0) ? InpPriceUpColor : InpPriceDnColor;
     }

   if(InpShowPrice)
      SetLabel("price",
               _Symbol + "  " + DoubleToStr(bid, (int)MarketInfo(_Symbol, MODE_DIGITS)),
               price_color);

   if(InpShowXtraDetails)
      SetLabel("spread",
               "Spread: " + DoubleToStr(spread_pips, 1) + " pips",
               InpSpreadColor);

   if(InpShowTradePips)
     {
      SetLabel("hod",
               "HOD: " + DoubleToStr(hod, (int)MarketInfo(_Symbol, MODE_DIGITS))
                       + " (-" + DoubleToStr(hod_dist, 1) + " pips)",
               InpLabelColor);
      SetLabel("lod",
               "LOD: " + DoubleToStr(lod, (int)MarketInfo(_Symbol, MODE_DIGITS))
                       + " (+" + DoubleToStr(lod_dist, 1) + " pips)",
               InpLabelColor);
     }

   string alert_text = "";
   color  alert_color = InpLabelColor;
   if(InpHODLODAlert)
     {
      if(hod_dist < InpPipsToHODLODForAlert)
        {
         alert_text = "NEAR HOD";
         alert_color = InpPriceAtExtremeColor;
         FireAlertOnce("SM_BPCT: " + _Symbol + " near HOD");
        }
      else if(lod_dist < InpPipsToHODLODForAlert)
        {
         alert_text = "NEAR LOD";
         alert_color = InpPriceAtExtremeColor;
         FireAlertOnce("SM_BPCT: " + _Symbol + " near LOD");
        }
     }
   SetLabel("alert", alert_text, alert_color);
  }

//+------------------------------------------------------------------+
void SetLabel(string suffix, string text, color c)
  {
   string name = ObjectPrefix + suffix;
   ObjectSetText(name, text, InpShowSmallerSize ? 9 : 11, "Arial", c);
  }

//+------------------------------------------------------------------+
void FireAlertOnce(string msg)
  {
   datetime now = TimeCurrent();
   if(now - g_last_alert_ts < 60)
      return;
   g_last_alert_ts = now;
   Alert(msg);
  }

//+------------------------------------------------------------------+
void CleanupObjects()
  {
   for(int i = ObjectsTotal() - 1; i >= 0; i--)
     {
      string n = ObjectName(i);
      if(StringFind(n, ObjectPrefix) == 0)
         ObjectDelete(n);
     }
  }

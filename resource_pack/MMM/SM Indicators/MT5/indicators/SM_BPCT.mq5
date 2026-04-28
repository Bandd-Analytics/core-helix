//+------------------------------------------------------------------+
//|  SM_BPCT.mq5                                                      |
//|  Phase 12 Plan 02 — Tier 1 atomic indicator                       |
//|  Spec: resource_pack/MMM/SM Indicators/docs/indicators/SM_BPCT.md |
//|                                                                   |
//|  D-17 Built ⚠ Low confidence — implementation per Verified Updates|
//|  2026-04-27 mini-HUD interpretation, NOT spec body's pressure-    |
//|  tracker hypothesis (Pitfall 10). Every guessed branch carries    |
//|  // [INFER] (D-17).                                                |
//|                                                                   |
//|  Mini-HUD: corner-positioned OBJ_LABEL displaying real-time price |
//|  + spread + HOD/LOD distance + proximity alert.                    |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics — Phase 12 reconstruction of !SM_BPCT.ex4 (mini-HUD per Verified Updates)"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

// [INFER] (D-17 Low confidence) — implementation per Verified Updates
// 2026-04-27 mini-HUD interpretation, NOT spec body's pressure-tracker
// hypothesis (see SM_BPCT.md Pitfall 10).

//--- Spec Section 3 — Verified Updates 2026-04-27 (16 inputs verbatim)
input ENUM_BASE_CORNER InpCornerOfChart        = CORNER_RIGHT_UPPER; // VERIFIED RIGHT_TOP
input bool             InpShowPrice            = true;
input bool             InpShowXtraDetails      = true;
input bool             InpShowSmallerSize      = true;
input bool             InpShowTradePips        = true;
input int              InpShiftUpDn            = 0;        // pixel offset
input int              InpAdjustSideToSide     = 0;
input color            InpLabelColor           = clrWhite;
input color            InpSpreadColor          = clrGold;
input color            InpPriceUpColor         = clrLime;
input color            InpPriceDnColor         = clrCrimson;
input color            InpPriceAtExtremeColor  = clrDarkGreen; // C'0,100,0' equivalent
input double           InpDistanceFromExtreme  = 12.0;     // VERIFIED pip threshold
input bool             InpHODLODAlert          = false;
input double           InpPipsToHODLODForAlert = 5.0;      // VERIFIED

const string InpObjectPrefix = "smBPCT_";

//--- Module state
double g_pip = 0.0;
datetime g_last_alert_ts = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   // [INFER] JPY/3-digit detection — pip math (Pitfall: pip math).
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   g_pip = (digits == 3 || digits == 5) ? 10.0 * _Point : _Point;

   IndicatorSetString(INDICATOR_SHORTNAME, "SM_BPCT (mini-HUD)");

   CreateLabels();
   Recompute();
   EventSetTimer(1);  // [INFER] 1-second refresh for live HUD
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   CleanupObjects();
   EventKillTimer();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Recompute();
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tv[],
                const long &v[], const int &sp[])
  {
   // [INFER] No per-bar buffer work — HUD updates on timer.
   return(rates_total);
  }

//+------------------------------------------------------------------+
void CreateLabels()
  {
   // [INFER] One stacked label per HUD row. Y offsets [INFER].
   string rows[] = {"price", "spread", "hod", "lod", "alert"};
   for(int i = 0; i < ArraySize(rows); i++)
     {
      string name = InpObjectPrefix + rows[i];
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);

      ObjectSetInteger(0, name, OBJPROP_CORNER,    InpCornerOfChart);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 8 + InpAdjustSideToSide);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE,
                       20 + InpShiftUpDn + i * 16);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE,
                       InpShowSmallerSize ? 9 : 11);
      ObjectSetString (0, name, OBJPROP_FONT, "Arial");
      ObjectSetInteger(0, name, OBJPROP_ANCHOR,
                       (InpCornerOfChart == CORNER_RIGHT_UPPER ||
                        InpCornerOfChart == CORNER_RIGHT_LOWER)
                          ? ANCHOR_RIGHT_UPPER : ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN,    true);
     }
  }

//+------------------------------------------------------------------+
void Recompute()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(bid <= 0.0 || ask <= 0.0 || g_pip <= 0.0)
      return;

   // [INFER] HOD/LOD = current Daily bar high/low.
   double hod = iHigh(_Symbol, PERIOD_D1, 0);
   double lod = iLow (_Symbol, PERIOD_D1, 0);
   double spread_pips = (ask - bid) / g_pip;
   double hod_dist    = (hod - bid) / g_pip;
   double lod_dist    = (bid - lod) / g_pip;

   // [INFER] At-extreme color when distance < InpDistanceFromExtreme.
   color price_color = InpLabelColor;
   if(InpShowPrice)
     {
      if(hod_dist < InpDistanceFromExtreme || lod_dist < InpDistanceFromExtreme)
         price_color = InpPriceAtExtremeColor;
      else
         price_color = (bid >= (hod + lod) / 2.0) ? InpPriceUpColor : InpPriceDnColor;
     }

   if(InpShowPrice)
      SetLabel("price",
               StringFormat("%s  %.5f", _Symbol, bid),
               price_color);

   if(InpShowXtraDetails)
      SetLabel("spread",
               StringFormat("Spread: %.1f pips", spread_pips),
               InpSpreadColor);

   if(InpShowTradePips)
     {
      SetLabel("hod",
               StringFormat("HOD: %.5f (-%.1f pips)", hod, hod_dist),
               InpLabelColor);
      SetLabel("lod",
               StringFormat("LOD: %.5f (+%.1f pips)", lod, lod_dist),
               InpLabelColor);
     }

   // [INFER] Alert when within InpPipsToHODLODForAlert of either extreme.
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
   string name = InpObjectPrefix + suffix;
   ObjectSetString (0, name, OBJPROP_TEXT,  text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
  }

//+------------------------------------------------------------------+
void FireAlertOnce(string msg)
  {
   // [INFER] Suppress duplicate alerts within the same minute.
   datetime now = TimeCurrent();
   if(now - g_last_alert_ts < 60)
      return;
   g_last_alert_ts = now;
   Alert(msg);
  }

//+------------------------------------------------------------------+
void CleanupObjects()
  {
   for(int i = ObjectsTotal(0, 0, -1) - 1; i >= 0; i--)
     {
      string n = ObjectName(0, i, 0, -1);
      if(StringFind(n, InpObjectPrefix) == 0)
         ObjectDelete(0, n);
     }
  }

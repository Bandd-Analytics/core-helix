//+------------------------------------------------------------------+
//|  ADR_Levels.mq5                                                   |
//|  Phase 8.4 INFRA-04 — D-18, D-19, D-16                            |
//|                                                                   |
//|  Draws three horizontal lines anchored to today's PERIOD_D1 open: |
//|     ADR-high  =  today_open + ADR / 2                              |
//|     ADR-mid   =  today_open                                        |
//|     ADR-low   =  today_open - ADR / 2                              |
//|                                                                   |
//|  ADR = mean of (Daily High - Daily Low) over InpLookbackDays bars  |
//|  via iHigh/iLow on PERIOD_D1 — works on any chart timeframe (D-16).|
//|                                                                   |
//|  Recompute trigger:                                               |
//|    OnInit + EventSetTimer(60s) -> OnTimer                         |
//|    OnCalculate detects PERIOD_D1 bar change                       |
//+------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0   // We draw via ObjectCreate, not buffers

input int InpLookbackDays = 20;
input color InpHighColor  = clrDeepSkyBlue;
input color InpLowColor   = clrOrangeRed;
input color InpMidColor   = clrSilver;

const string InpObjectPrefix = "ADR_LVL_";


int OnInit()
{
    Recompute();
    EventSetTimer(60);
    return(INIT_SUCCEEDED);
}


void OnDeinit(const int reason)
{
    CleanupObjects();
    EventKillTimer();
}


void OnTimer()
{
    Recompute();
}


int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[],
                const double &open[], const double &high[], const double &low[],
                const double &close[], const long &tv[], const long &v[], const int &sp[])
{
    static datetime last_d1_bar = 0;
    datetime cur_d1 = iTime(_Symbol, PERIOD_D1, 0);
    if(cur_d1 != last_d1_bar)
    {
        Recompute();
        last_d1_bar = cur_d1;
    }
    return(rates_total);
}


void Recompute()
{
    // ADR = mean of (Daily High - Daily Low) over InpLookbackDays bars.
    // Always reads PERIOD_D1 regardless of current chart period (D-16).
    double sum = 0.0;
    for(int i = 1; i <= InpLookbackDays; i++)
    {
        sum += iHigh(_Symbol, PERIOD_D1, i) - iLow(_Symbol, PERIOD_D1, i);
    }
    double adr = sum / InpLookbackDays;

    double today_open = iOpen(_Symbol, PERIOD_D1, 0);
    double hi  = today_open + adr / 2.0;
    double lo  = today_open - adr / 2.0;
    double mid = today_open;

    DrawHLine(InpObjectPrefix + "high", hi, InpHighColor);
    DrawHLine(InpObjectPrefix + "low",  lo, InpLowColor);
    DrawHLine(InpObjectPrefix + "mid",  mid, InpMidColor);
}


void DrawHLine(string name, double price, color c)
{
    if(ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
    ObjectSetDouble(0, name, OBJPROP_PRICE, price);
    ObjectSetInteger(0, name, OBJPROP_COLOR, c);
    ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
    ObjectSetInteger(0, name, OBJPROP_BACK, true);
}


void CleanupObjects()
{
    for(int i = ObjectsTotal(0) - 1; i >= 0; i--)
    {
        string n = ObjectName(0, i);
        if(StringFind(n, InpObjectPrefix) == 0) ObjectDelete(0, n);
    }
}

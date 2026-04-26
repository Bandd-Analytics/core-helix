//+------------------------------------------------------------------+
//|  BandD_TradeReplay.mq5                                             |
//|  Phase 8.4 INFRA-04 — D-15, D-16, D-17                              |
//|                                                                    |
//|  Renders backtest trades onto any chart timeframe (M15/H1/H4/D1).  |
//|  Reads CSV at InpCsvPath with columns:                              |
//|    entry_ts, exit_ts, entry_px, exit_px, sl, tp,                    |
//|    direction, strategy, pair, timeframe                             |
//|                                                                    |
//|  D-16 invariant: every coordinate is (datetime, price), so MT5     |
//|  positions objects on whatever chart period is shown — no          |
//|  hardcoded PERIOD_xx in the rendering path.                         |
//|                                                                    |
//|  RESEARCH Pitfall 5: InpObjectPrefix = "BandD_TR_" enables          |
//|  orphan-free OnDeinit cleanup on timeframe switch.                  |
//+------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

input string InpCsvPath    = "trades_latest.csv";   // D-17 — configurable
input color  InpLongColor  = clrLimeGreen;
input color  InpShortColor = clrTomato;
input color  InpSlColor    = clrDarkRed;
input color  InpTpColor    = clrDarkGreen;

const string InpObjectPrefix = "BandD_TR_";


int OnInit()
{
    LoadAndRenderTrades();
    return(INIT_SUCCEEDED);
}


void OnDeinit(const int reason)
{
    // D-16 / Pitfall 5 — orphan-free on timeframe switch
    int total = ObjectsTotal(0);
    for(int i = total - 1; i >= 0; i--)
    {
        string name = ObjectName(0, i);
        if(StringFind(name, InpObjectPrefix) == 0)
            ObjectDelete(0, name);
    }
}


int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
    // Renders happen in OnInit via LoadAndRenderTrades — no per-bar work.
    // _Period reference here is intentional documentation that this indicator
    // is timeframe-agnostic by design (D-16): no PERIOD_xx pinning, all
    // objects are time-anchored via iTime / chart-id 0.
    return(rates_total);
}


void LoadAndRenderTrades()
{
    int handle = FileOpen(InpCsvPath, FILE_READ | FILE_CSV | FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        Print("BandD_TradeReplay: CSV open fail at ", InpCsvPath,
              " (err=", GetLastError(), ")");
        return;
    }

    // Skip 10-column header row (D-17 column convention)
    for(int h = 0; h < 10; h++)
    {
        string _hdr = FileReadString(handle);
    }
    if(!FileIsLineEnding(handle)) FileReadString(handle);

    int n = 0;
    while(!FileIsEnding(handle))
    {
        datetime entry_ts = FileReadDatetime(handle);
        datetime exit_ts  = FileReadDatetime(handle);
        double   entry_px = FileReadNumber(handle);
        double   exit_px  = FileReadNumber(handle);
        double   sl       = FileReadNumber(handle);
        double   tp       = FileReadNumber(handle);
        string   dir      = FileReadString(handle);
        string   strat    = FileReadString(handle);
        string   pair     = FileReadString(handle);
        string   tf       = FileReadString(handle);

        // Filter to current chart's symbol; uses _Symbol so the indicator is
        // timeframe-agnostic (works on M15/H1/H4/D1 because all coords are
        // (datetime, price) — see D-16).
        if(pair != _Symbol) continue;

        RenderOne(n, entry_ts, exit_ts, entry_px, exit_px, sl, tp, dir);
        n++;
    }
    FileClose(handle);
    Print("BandD_TradeReplay: rendered ", n, " trades for ", _Symbol,
          " on period=", EnumToString((ENUM_TIMEFRAMES)_Period));
}


void RenderOne(int idx, datetime e_ts, datetime x_ts, double e_px, double x_px,
               double sl, double tp, string direction)
{
    bool is_long = (direction == "LONG");
    color side = is_long ? InpLongColor : InpShortColor;

    // Entry arrow — auto-anchors at chart's current period using iTime, no
    // PERIOD_xx hardcoding (D-16). chart-id 0 == current chart.
    string n_entry = InpObjectPrefix + IntegerToString(idx) + "_entry";
    ObjectCreate(0, n_entry, OBJ_ARROW_BUY, 0, e_ts, e_px);
    ObjectSetInteger(0, n_entry, OBJPROP_COLOR, side);

    string n_exit = InpObjectPrefix + IntegerToString(idx) + "_exit";
    ObjectCreate(0, n_exit, OBJ_ARROW_SELL, 0, x_ts, x_px);
    ObjectSetInteger(0, n_exit, OBJPROP_COLOR, side);

    // Connecting trendline
    string n_line = InpObjectPrefix + IntegerToString(idx) + "_line";
    ObjectCreate(0, n_line, OBJ_TREND, 0, e_ts, e_px, x_ts, x_px);
    ObjectSetInteger(0, n_line, OBJPROP_COLOR, side);
    ObjectSetInteger(0, n_line, OBJPROP_RAY_RIGHT, false);

    // SL rectangle (entry_ts, sl) -> (exit_ts, entry_px)
    string n_sl = InpObjectPrefix + IntegerToString(idx) + "_sl";
    ObjectCreate(0, n_sl, OBJ_RECTANGLE, 0, e_ts, sl, x_ts, e_px);
    ObjectSetInteger(0, n_sl, OBJPROP_COLOR, InpSlColor);
    ObjectSetInteger(0, n_sl, OBJPROP_FILL, true);
    ObjectSetInteger(0, n_sl, OBJPROP_BACK, true);

    // TP rectangle (entry_ts, entry_px) -> (exit_ts, tp)
    string n_tp = InpObjectPrefix + IntegerToString(idx) + "_tp";
    ObjectCreate(0, n_tp, OBJ_RECTANGLE, 0, e_ts, e_px, x_ts, tp);
    ObjectSetInteger(0, n_tp, OBJPROP_COLOR, InpTpColor);
    ObjectSetInteger(0, n_tp, OBJPROP_FILL, true);
    ObjectSetInteger(0, n_tp, OBJPROP_BACK, true);

    // R-multiple text label at exit
    double risk = MathAbs(e_px - sl);
    double r_mult = (is_long ? (x_px - e_px) : (e_px - x_px)) / (risk > 0 ? risk : 1e-9);
    string n_txt = InpObjectPrefix + IntegerToString(idx) + "_r";
    ObjectCreate(0, n_txt, OBJ_TEXT, 0, x_ts, x_px);
    ObjectSetString (0, n_txt, OBJPROP_TEXT, StringFormat("%.1fR", r_mult));
    ObjectSetInteger(0, n_txt, OBJPROP_COLOR, side);
    ObjectSetInteger(0, n_txt, OBJPROP_FONTSIZE, 9);
    ObjectSetInteger(0, n_txt, OBJPROP_ANCHOR, ANCHOR_LEFT);
}

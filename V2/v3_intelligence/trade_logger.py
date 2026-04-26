"""
Trade Logger — persistent SQLite journal for trades and strategy decisions.

Two tables:
  trades       — every executed trade with full market context at entry
  decision_log — append-only record of every parameter change and its outcome
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).parent.parent / "data" / "marketmind.db"


class TradeLogger:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS trades (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    logged_at       TEXT NOT NULL,
                    symbol          TEXT NOT NULL,
                    strategy_type   TEXT NOT NULL,
                    entry_date      TEXT NOT NULL,
                    exit_date       TEXT,
                    entry_price     REAL NOT NULL,
                    exit_price      REAL,
                    pnl_pct         REAL,
                    bars_held       INTEGER,
                    session         TEXT,
                    exit_reason     TEXT,
                    size            REAL,
                    -- market context at entry (for RAG embedding)
                    daily_z         REAL,
                    h1_z            REAL,
                    h1_atr          REAL,
                    vol_percentile  REAL,
                    hour_utc        INTEGER,
                    -- outcome classification
                    won             INTEGER,
                    notes           TEXT
                );

                CREATE TABLE IF NOT EXISTS decision_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    logged_at   TEXT NOT NULL,
                    parameter   TEXT NOT NULL,
                    from_value  TEXT,
                    to_value    TEXT,
                    rationale   TEXT NOT NULL,
                    result      TEXT,
                    verdict     TEXT,
                    session_id  TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
                CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_type);
                CREATE INDEX IF NOT EXISTS idx_trades_entry_date ON trades(entry_date);
            """)

            # Phase 8.4 INFRA-03 / D-12 / RESEARCH open Q2 — params_json holds JSON
            # snapshot of active strategy params at trade-entry time (z-thresholds,
            # ATR multipliers, etc.). Idempotent via try/except OperationalError on
            # 'duplicate column name' (SQLite < 3.35 lacks IF NOT EXISTS for ALTER
            # TABLE ADD COLUMN). Nullable for legacy rows.
            try:
                conn.execute("ALTER TABLE trades ADD COLUMN params_json TEXT")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise  # genuine schema error — surface it
                # column already exists (idempotent)

    def log_trade(self, trade: dict):
        """Record a completed trade with full market context."""
        pnl = trade.get("pnl_pct")
        row = {
            "logged_at":      datetime.utcnow().isoformat(),
            "symbol":         trade["symbol"],
            "strategy_type":  trade["type"],
            "entry_date":     str(trade["entry_date"]),
            "exit_date":      str(trade.get("exit_date", "")),
            "entry_price":    trade["entry_price"],
            "exit_price":     trade.get("exit_price"),
            "pnl_pct":        pnl,
            "bars_held":      trade.get("bars_held"),
            "session":        trade.get("session"),
            "exit_reason":    trade.get("exit_reason"),
            "size":           trade.get("size", 1.0),
            "daily_z":        trade.get("daily_z"),
            "h1_z":           trade.get("h1_z"),
            "h1_atr":         trade.get("h1_atr"),
            "vol_percentile": trade.get("vol_percentile"),
            "hour_utc":       trade.get("hour_utc"),
            "won":            int(pnl > 0) if pnl is not None else None,
            "notes":          trade.get("notes"),
            "params_json":    trade.get("params_json"),
        }
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO trades (
                    logged_at, symbol, strategy_type, entry_date, exit_date,
                    entry_price, exit_price, pnl_pct, bars_held, session,
                    exit_reason, size, daily_z, h1_z, h1_atr, vol_percentile,
                    hour_utc, won, notes, params_json
                ) VALUES (
                    :logged_at, :symbol, :strategy_type, :entry_date, :exit_date,
                    :entry_price, :exit_price, :pnl_pct, :bars_held, :session,
                    :exit_reason, :size, :daily_z, :h1_z, :h1_atr, :vol_percentile,
                    :hour_utc, :won, :notes, :params_json
                )
            """, row)

    def log_decision(
        self,
        parameter: str,
        from_value,
        to_value,
        rationale: str,
        result: Optional[str] = None,
        verdict: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Append a strategy parameter change to the decision log."""
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO decision_log (
                    logged_at, parameter, from_value, to_value,
                    rationale, result, verdict, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                parameter,
                str(from_value) if from_value is not None else None,
                str(to_value) if to_value is not None else None,
                rationale,
                result,
                verdict,
                session_id,
            ))

    def log_trades_bulk(self, trades_df):
        """Bulk-load trades from a backtest results DataFrame."""
        for _, row in trades_df.iterrows():
            self.log_trade(row.to_dict())

    def get_stats(self, symbol: Optional[str] = None, strategy_type: Optional[str] = None) -> dict:
        """Return summary stats, optionally filtered by symbol or strategy."""
        filters = ["pnl_pct IS NOT NULL"]
        params = []
        if symbol:
            filters.append("symbol = ?")
            params.append(symbol)
        if strategy_type:
            filters.append("strategy_type = ?")
            params.append(strategy_type)
        where = "WHERE " + " AND ".join(filters)

        with self._connect() as conn:
            row = conn.execute(f"""
                SELECT
                    COUNT(*)                          AS total,
                    SUM(won)                          AS wins,
                    AVG(pnl_pct)                      AS avg_pnl,
                    SUM(pnl_pct)                      AS total_pnl,
                    AVG(bars_held)                    AS avg_bars
                FROM trades {where}
            """, params).fetchone()
            if not row or row["total"] == 0:
                return {}
            total = row["total"]
            wins  = row["wins"] or 0
            return {
                "total_trades": total,
                "win_rate":     wins / total,
                "avg_pnl_pct":  row["avg_pnl"],
                "total_pnl_pct": row["total_pnl"],
                "avg_bars_held": row["avg_bars"],
            }

    def get_recent_decisions(self, n: int = 20) -> list:
        """Return the last n strategy parameter changes."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM decision_log ORDER BY id DESC LIMIT ?", (n,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_similar_trades(self, symbol: str, strategy_type: str, session: str, n: int = 20) -> list:
        """Retrieve recent similar trades for RAG context (lightweight SQL version)."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT pnl_pct, won, daily_z, h1_z, vol_percentile, bars_held
                FROM trades
                WHERE symbol = ? AND strategy_type = ? AND session = ?
                  AND pnl_pct IS NOT NULL
                ORDER BY id DESC LIMIT ?
            """, (symbol, strategy_type, session, n)).fetchall()
            return [dict(r) for r in rows]

    def print_summary(self):
        """Print a full performance summary to stdout."""
        with self._connect() as conn:
            symbols = [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM trades").fetchall()]

        print("\n" + "="*70)
        print("TRADE JOURNAL SUMMARY")
        print("="*70)
        for sym in symbols:
            s = self.get_stats(symbol=sym)
            if s:
                print(f"{sym:8} | Trades: {s['total_trades']:4} | "
                      f"Win%: {s['win_rate']*100:5.1f}% | "
                      f"P&L: {s['total_pnl_pct']*100:7.2f}%")

        overall = self.get_stats()
        if overall:
            print("-"*70)
            print(f"{'TOTAL':8} | Trades: {overall['total_trades']:4} | "
                  f"Win%: {overall['win_rate']*100:5.1f}% | "
                  f"P&L: {overall['total_pnl_pct']*100:7.2f}%")
        print("="*70)

        decisions = self.get_recent_decisions(5)
        if decisions:
            print("\nLAST 5 DECISIONS:")
            for d in decisions:
                verdict = f"[{d['verdict']}]" if d['verdict'] else ""
                print(f"  {d['logged_at'][:10]} | {d['parameter']:30} "
                      f"{d['from_value']} → {d['to_value']} {verdict}")
                print(f"    WHY: {d['rationale']}")
                if d['result']:
                    print(f"    RESULT: {d['result']}")

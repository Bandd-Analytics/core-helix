"""V2/scripts/pull_live_trades.py — hourly live trade puller (MT5 -> TradeLogger).

Cross-platform contract:
  Windows / Wine'd Python with MetaTrader5 importable:
      python -m scripts.pull_live_trades --account live --since today
      → calls MetaTrader5.history_deals_get(), pairs deals into trades,
        log_trade_if_new() into V2/data/marketmind.db.

  Linux without MetaTrader5 (the package is Windows-only):
      python -m scripts.pull_live_trades --source inbox --since today
      → reads V2/data/live/inbox/*.json and ingests; intended for
        rsync / git / Dropbox handoff from a Windows host that ran the
        same script in --source mt5 mode and wrote --emit-json.

  Auto:
      python -m scripts.pull_live_trades --since today
      → tries MT5 if importable, falls back to inbox.

Idempotency:
  TradeLogger.log_trade_if_new uses the partial UNIQUE INDEX on
  broker_position_id added in trade_logger._init_db. Re-running the puller
  hourly is safe: trades from prior runs are skipped, only new closes land.

Hourly schedule snippets are at the bottom of this file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from v3_intelligence.trade_logger import TradeLogger


# ─────────────────────────────────────────────────────────────────────────────
# Detect MetaTrader5 availability (Windows / Wine'd Python only)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import MetaTrader5 as mt5  # type: ignore[import-not-found]
    _MT5_AVAILABLE = True
except ModuleNotFoundError:
    mt5 = None  # type: ignore[assignment]
    _MT5_AVAILABLE = False


_REPO_DATA = Path(__file__).resolve().parents[1] / "data"
DEFAULT_INBOX = _REPO_DATA / "live" / "inbox"

_RECOGNIZED_PREFIXES = ("DAILY_SWING", "H1_SCALP", "M15_SCALP", "H1_MOMENTUM")
_RECOGNIZED_TAGS = {f"{p}_{d}" for p in _RECOGNIZED_PREFIXES for d in ("LONG", "SHORT")}


def parse_strategy_from_comment(comment: str, deal_type: str) -> str:
    """Map an MT5 deal comment to a journal strategy_type.

    Recognized router tags ("H1_SCALP_LONG" etc.) round-trip verbatim. Anything
    else (empty, "MANUAL", "yolo") collapses to MANUAL_LONG / MANUAL_SHORT
    based on the closing-deal direction inferred from `deal_type`.
    """
    tag = (comment or "").strip().upper()
    if tag in _RECOGNIZED_TAGS:
        return tag
    return "MANUAL_LONG" if deal_type.lower() == "buy" else "MANUAL_SHORT"


def _parse_iso(ts: str) -> datetime:
    """Parse an ISO-8601 string to an aware UTC datetime.

    Tolerates trailing 'Z' (Pythons before 3.11 reject it in fromisoformat).
    """
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def pair_deals_to_trades(deals: Iterable[dict]) -> list[dict]:
    """Collapse (open, close) deal pairs sharing a position_id into trade rows.

    Positions with only one deal (still open) are silently dropped — they have
    no exit price yet and don't belong in the closed-trade journal.
    """
    by_position: dict[Any, list[dict]] = {}
    for d in deals:
        by_position.setdefault(d["position_id"], []).append(d)

    trades: list[dict] = []
    for position_id, group in by_position.items():
        if len(group) < 2:
            continue  # still open — skip
        group_sorted = sorted(group, key=lambda d: _parse_iso(d["time"]))
        opener, closer = group_sorted[0], group_sorted[-1]
        entry_dt = _parse_iso(opener["time"])
        exit_dt = _parse_iso(closer["time"])
        entry_price = float(opener["price"])
        exit_price = float(closer["price"])
        is_long = opener["type"].lower() == "buy"
        pnl_pct = ((exit_price - entry_price) / entry_price) if is_long \
            else ((entry_price - exit_price) / entry_price)
        strategy_type = parse_strategy_from_comment(
            opener.get("comment", "") or closer.get("comment", ""),
            deal_type=opener["type"],
        )
        trades.append({
            "broker_position_id": str(position_id),
            "symbol":         opener["symbol"],
            "type":           strategy_type,
            "entry_date":     entry_dt,
            "exit_date":      exit_dt,
            "entry_price":    entry_price,
            "exit_price":     exit_price,
            "pnl_pct":        pnl_pct,
            "size":           float(opener.get("volume", 0.0)),
            "exit_reason":    "live_close",
            "session":        None,
            "hour_utc":       entry_dt.hour,
            "notes":          f"live ingest; opener_ticket={opener.get('ticket')} "
                              f"closer_ticket={closer.get('ticket')}",
        })
    return trades


def load_inbox_deals(inbox_dir: Path) -> list[dict]:
    """Read all *.json files in inbox_dir and return their concatenated deal lists."""
    if not inbox_dir.exists() or not inbox_dir.is_dir():
        return []
    deals: list[dict] = []
    for path in sorted(inbox_dir.glob("*.json")):
        with path.open() as f:
            chunk = json.load(f)
        if isinstance(chunk, list):
            deals.extend(chunk)
        else:
            print(f"  WARN: {path} did not contain a JSON list; skipped",
                  file=sys.stderr)
    return deals


def parse_since(arg: str, logger: Optional[TradeLogger],
                now: Optional[datetime] = None) -> datetime:
    """Resolve --since to an aware UTC datetime.

    Accepts: 'today' (today 00:00 UTC), 'auto' (last journal entry_date or
    30d ago if empty), or any YYYY-MM-DD / ISO-8601 string.
    """
    now = now or datetime.now(timezone.utc)
    if arg == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if arg == "auto":
        last = None
        if logger is not None:
            with logger._connect() as conn:
                row = conn.execute(
                    "SELECT MAX(entry_date) FROM trades "
                    "WHERE broker_position_id IS NOT NULL"
                ).fetchone()
                last = row[0] if row else None
        if last:
            try:
                return _parse_iso(last)
            except ValueError:
                pass
        return now - timedelta(days=30)
    return _parse_iso(arg)


def ingest_deals(deals: list[dict], logger: TradeLogger) -> dict[str, int]:
    """End-to-end: pair deals, log_trade_if_new each. Return per-run summary."""
    inserted = 0
    skipped = 0
    for trade in pair_deals_to_trades(deals):
        if logger.log_trade_if_new(trade):
            inserted += 1
        else:
            skipped += 1
    return {"inserted": inserted, "skipped": skipped, "candidates": inserted + skipped}


def record_heartbeat(logger: TradeLogger, source: str, summary: dict) -> None:
    """Append a heartbeat row to decision_log so the journal records that the
    puller ran and what it found, even on no-op runs."""
    logger.log_decision(
        parameter="heartbeat:pull_live_trades",
        from_value=None,
        to_value=source,
        rationale=f"hourly puller ran via source={source}",
        result=json.dumps(summary, sort_keys=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# MT5 fetch path (Windows / Wine'd Python only)
# ─────────────────────────────────────────────────────────────────────────────


def _mt5_account_creds(account: str) -> tuple[int, str, str]:
    """Pull MT5 LIVE / DEMO creds from environment (.env loaded by caller)."""
    prefix = "MT5_LIVE" if account == "live" else "MT5_DEMO"
    login = os.environ.get(f"{prefix}_Trading_Account_Login")
    password = os.environ.get(f"{prefix}_Trading_Account_Login_Password")
    server = os.environ.get(f"{prefix}_Trading_Account_Server")
    if not (login and password and server):
        raise RuntimeError(
            f"Missing {prefix}_Trading_Account_* env vars; "
            "load them via python-dotenv from the repo root .env"
        )
    return int(login), password, server


def fetch_mt5_deals(account: str, since: datetime,
                    until: Optional[datetime] = None) -> list[dict]:
    """Fetch closed-position deals from MT5 in (since, until]. Windows-only.

    Returns a list of plain-dict deals in the format expected by
    pair_deals_to_trades. Each MT5 closed position emits two deals (open +
    close) sharing a position_id; we keep both and let the pairer collapse.
    """
    if not _MT5_AVAILABLE:
        raise RuntimeError(
            "MetaTrader5 package not importable — run on Windows or under Wine. "
            "On Linux use --source inbox with JSON drops in V2/data/live/inbox/."
        )
    until = until or datetime.now(timezone.utc)
    login, password, server = _mt5_account_creds(account)
    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize() failed: {mt5.last_error()}")
    try:
        if not mt5.login(login, password=password, server=server):
            raise RuntimeError(
                f"mt5.login() failed for account {login} on {server}: "
                f"{mt5.last_error()}"
            )
        raw = mt5.history_deals_get(since, until)
        if raw is None:
            return []
        out: list[dict] = []
        for d in raw:
            # MT5 deal types: 0=DEAL_TYPE_BUY, 1=DEAL_TYPE_SELL, others=balance/credit/etc.
            if d.type not in (0, 1):
                continue
            if not d.position_id:
                continue
            out.append({
                "ticket":      int(d.ticket),
                "position_id": int(d.position_id),
                "type":        "buy" if d.type == 0 else "sell",
                "symbol":      d.symbol,
                "volume":      float(d.volume),
                "price":       float(d.price),
                "time":        datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat(),
                "comment":     d.comment or "",
                "profit":      float(d.profit),
            })
        return out
    finally:
        mt5.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def _maybe_load_dotenv() -> None:
    """Try to load .env from repo root. Soft-fail if python-dotenv missing."""
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    repo_root = Path(__file__).resolve().parents[2]
    for candidate in (repo_root / ".env", _REPO_DATA.parent / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="pull_live_trades",
        description="Hourly live MT5 -> TradeLogger ingestion (Phase 09.1 follow-on)",
    )
    ap.add_argument("--source", choices=("auto", "mt5", "inbox"), default="auto",
                    help="Where to read deals from. 'auto' picks mt5 if importable, else inbox.")
    ap.add_argument("--account", choices=("live", "demo"), default="live",
                    help="Which env credentials to use when --source=mt5")
    ap.add_argument("--since", default="auto",
                    help="Lower bound: 'today', 'auto' (= last journal ts or 30d), or YYYY-MM-DD")
    ap.add_argument("--until", default=None,
                    help="Upper bound (default = now). YYYY-MM-DD or ISO-8601.")
    ap.add_argument("--inbox", default=str(DEFAULT_INBOX),
                    help=f"Inbox dir for --source=inbox (default {DEFAULT_INBOX})")
    ap.add_argument("--emit-json", default=None,
                    help="Optional path: when --source=mt5, also dump fetched deals as JSON "
                         "(for cross-host handoff to a Linux ingest box)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Pair and report, but do not write to TradeLogger")
    args = ap.parse_args(argv)

    _maybe_load_dotenv()
    logger = TradeLogger()

    source = args.source
    if source == "auto":
        source = "mt5" if _MT5_AVAILABLE else "inbox"

    since = parse_since(args.since, logger=logger)
    until = _parse_iso(args.until) if args.until else datetime.now(timezone.utc)

    if source == "mt5":
        deals = fetch_mt5_deals(args.account, since=since, until=until)
        if args.emit_json:
            Path(args.emit_json).parent.mkdir(parents=True, exist_ok=True)
            Path(args.emit_json).write_text(json.dumps(deals, indent=2))
            print(f"wrote {len(deals)} deals to {args.emit_json}")
    else:
        deals = load_inbox_deals(Path(args.inbox))

    print(f"source={source} since={since.isoformat()} until={until.isoformat()} "
          f"deals_fetched={len(deals)}")

    if args.dry_run:
        paired = pair_deals_to_trades(deals)
        print(f"DRY-RUN: would pair {len(deals)} deals -> {len(paired)} trades; "
              f"no DB writes")
        return 0

    summary = ingest_deals(deals, logger=logger)
    summary["source"] = source
    record_heartbeat(logger, source=source, summary=summary)
    print(f"inserted={summary['inserted']} skipped_dupes={summary['skipped']} "
          f"candidates={summary['candidates']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ─────────────────────────────────────────────────────────────────────────────
# Hourly schedule snippets — copy/paste, do not auto-install
# ─────────────────────────────────────────────────────────────────────────────
#
# Linux (cron, runs at minute 5 of every hour, 24/7):
#     5 * * * * cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2 && \
#       /home/user/.local/bin/python -m scripts.pull_live_trades \
#       --source auto --since auto >> /tmp/helix_pull_live.log 2>&1
#
# Windows (Task Scheduler — schtasks /Create from a CMD prompt):
#     schtasks /Create /SC HOURLY /TN "Helix\PullLiveTrades" /TR ^
#       "C:\Python312\python.exe -m scripts.pull_live_trades --source mt5 --since auto" ^
#       /SD 01/01/2026 /ST 00:05 ^
#       /F  /RL LIMITED ^
#       /RP <PASSWORD> ^
#       /RU <USER>
#     # Working directory must be set to the V2 dir; use the GUI to set Start In
#     # if you prefer not to wrap in a .bat. A wrapper .bat is more reliable:
#     #     @echo off
#     #     cd /d C:\path\to\helix\V2
#     #     C:\Python312\python.exe -m scripts.pull_live_trades --source mt5 --since auto
#
# Wine on Linux (if running MT5 + Windows Python under Wine):
#     5 * * * * cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2 && \
#       wine "C:/Python312/python.exe" -m scripts.pull_live_trades \
#       --source mt5 --since auto >> /tmp/helix_pull_live.log 2>&1

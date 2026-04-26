"""
Pair Configuration — per-symbol strategy overrides with tiered sizing.

Data-driven configuration updated 2026-04-20 after full evaluation matrix
(backtest_evaluate_all.py tested all 8 pairs × 4 strategies independently).

SWING strategy (730-day H1 window):
  USDJPY Sh 3.09 | GBPJPY Sh 1.93 | GBPAUD Sh 1.86 | GBPUSD Sh 1.05
  EURGBP Sh 0.45 (marginal but included)
  EURUSD Sh -0.20 | AUDNZD Sh -2.16 | GBPNZD Sh -0.34 — disabled for swing

M15 SCALP strategy (60-day M15 window, IC Markets Raw required):
  GBPNZD Sh 3.65 | EURUSD Sh 2.62 | GBPUSD Sh 2.60 | AUDNZD Sh 2.19
  EURGBP Sh 1.86 | GBPAUD Sh 1.08 | USDJPY Sh 0.93
  GBPJPY Sh -0.02 — disabled (structurally negative all thresholds tested)

H1 SCALP strategy (730-day H1 window):
  AUDNZD Sh 1.63 | EURGBP Sh 1.32 | GBPJPY Sh 0.85
  All other pairs negative — disabled

MOMENTUM strategy (730-day H1 window):
  EURGBP Sh 1.57 | GBPUSD Sh 1.00 | AUDNZD Sh 0.55
  All other pairs negative — disabled

Strategies are INDEPENDENT: each pair can run multiple strategies simultaneously
with no shared position state. Capital allocation is per-strategy.

swing_max_bars: 120 H1 bars = ~5 trading days
H1 ATR used for swing exits (not daily ATR).
"""
from dataclasses import dataclass


@dataclass
class PairConfig:
    symbol: str
    tier: int                        # 1=Elite, 2=Solid, 3=Weak

    # Position sizing multipliers
    swing_size_mult: float = 1.0
    scalp_size_mult: float = 1.0
    momentum_size_mult: float = 1.0

    # Z-score entry thresholds
    swing_z_threshold: float = 2.0
    scalp_z_threshold: float = 2.0
    momentum_z_threshold: float = 1.5
    momentum_daily_z_threshold: float = 1.5

    # ATR multipliers — H1 scale
    swing_target_atr: float = 4.0
    swing_stop_atr: float = 1.5
    scalp_target_atr: float = 2.0
    scalp_stop_atr: float = 0.75
    momentum_target_atr: float = 1.0
    momentum_stop_atr: float = 0.5

    # Max hold bars (H1 bars)
    swing_max_bars: int = 120        # ~5 trading days
    scalp_max_bars: int = 4          # ~4 hours
    momentum_max_bars: int = 2       # ~2 hours

    # Strategy participation flags
    allow_swing: bool = True
    allow_scalp: bool = False        # default OFF — only on validated pairs
    allow_momentum: bool = False     # default OFF — only on validated pairs

    # M15 intraday scalp layer
    allow_m15_scalp: bool = False
    m15_z_threshold: float = 2.0
    m15_target_atr: float = 2.5
    m15_stop_atr: float = 1.5
    m15_max_bars: int = 12           # 3 hours
    m15_size_mult: float = 0.7

    notes: str = ""


# ── Per-pair configurations ────────────────────────────────────────────────────
# Each strategy enabled/disabled based on evaluation matrix results.
# Strategies are independent — multiple can be active on the same pair.

PAIR_CONFIGS: dict[str, PairConfig] = {

    # ── USDJPY: Elite swing pair. M15 marginal but positive. ─────────────────
    "USDJPY": PairConfig(
        symbol="USDJPY", tier=1,
        swing_size_mult=1.0,
        allow_swing=True,
        allow_scalp=False,           # H1 scalp Sh -1.64 — strongly negative (4yr)
        allow_momentum=False,        # Momentum Sh -0.29 — negative (4yr)
        allow_m15_scalp=True,        # M15 Sh 0.93 — marginal positive
        m15_z_threshold=2.0,
        m15_size_mult=0.5,           # Reduced — marginal edge
        notes="Swing Sh 3.09 (best pair). M15 Sh 0.93 (marginal, 0.5x size). H1 scalp/momentum both negative. | 4yr corrected — 2026-04-25: scalp Sh=-1.64 win=41.1% n=654; momentum Sh=-0.29 win=47.9% n=1316",
    ),

    # ── GBPJPY: Elite swing. H1 scalp enabled per 4yr routing matrix. ───────────────
    "GBPJPY": PairConfig(
        symbol="GBPJPY", tier=1,
        swing_size_mult=1.0,
        allow_swing=True,
        allow_scalp=True,            # H1 scalp Sh 0.64 — enabled per 4yr routing matrix (user approved 2026-04-25)
        allow_momentum=False,        # Momentum Sh 0.44 — below threshold (4yr)
        allow_m15_scalp=False,       # M15 Sh -0.02 — all Z thresholds tested, structurally negative
        notes="Swing Sh 1.93. H1 scalp Sh 0.85 (borderline, disabled). M15 negative all thresholds. Swing-only. | 4yr corrected — 2026-04-25: scalp Sh=0.64 win=48.3% n=753; momentum Sh=0.44 win=46.7% n=1395",
    ),

    # ── GBPAUD: Strong swing. M15 positive. ──────────────────────────────────
    "GBPAUD": PairConfig(
        symbol="GBPAUD", tier=1,
        swing_size_mult=1.0,
        allow_swing=True,
        allow_scalp=False,           # H1 scalp Sh -0.61
        allow_momentum=False,        # Momentum Sh -0.11
        allow_m15_scalp=True,        # M15 Sh 1.08 — positive
        m15_z_threshold=2.0,
        m15_size_mult=0.6,
        notes="Swing Sh 1.86. M15 Sh 1.08 (positive, 0.6x size). H1 scalp/momentum negative.",
    ),

    # ── GBPUSD: THREE positive strategies. Best M15 among T1. ────────────────
    "GBPUSD": PairConfig(
        symbol="GBPUSD", tier=1,
        swing_size_mult=1.0,
        allow_swing=True,            # Swing Sh 1.05
        allow_scalp=False,           # H1 scalp Sh -0.15
        allow_momentum=True,         # Momentum Sh 1.00 — validated
        momentum_size_mult=0.4,      # Smaller — lower conviction than swing
        allow_m15_scalp=True,        # M15 Sh 2.60 — best M15 T1 pair
        m15_z_threshold=2.0,
        m15_size_mult=0.7,
        notes="Swing Sh 1.05 + Momentum Sh 1.00 + M15 Sh 2.60. Three independent strategies all positive.",
    ),

    # ── EURGBP: Four positive strategies. Multi-strategy pair. ───────────────
    "EURGBP": PairConfig(
        symbol="EURGBP", tier=2,
        swing_size_mult=0.8,
        allow_swing=True,            # Swing Sh 0.45 — marginal but positive
        allow_scalp=True,            # H1 scalp Sh 1.09 — validated (4yr)
        scalp_size_mult=0.5,
        allow_momentum=True,         # Momentum Sh 0.84 — validated (4yr)
        momentum_size_mult=0.4,
        allow_m15_scalp=True,        # M15 Sh 1.86 — best M15 strategy here
        m15_z_threshold=2.0,
        m15_size_mult=0.5,
        notes="Multi-strategy: Swing Sh 0.45, H1 Scalp Sh 1.32, Momentum Sh 1.57, M15 Sh 1.86. All positive. | 4yr corrected — 2026-04-25: scalp Sh=1.09 win=48.3% n=974; momentum Sh=0.84 win=49.7% n=1651",
    ),

    # ── GBPNZD: M15 still best. H1 scalp re-enabled per Phase 8.4 D-07 4yr re-eval. ──
    "GBPNZD": PairConfig(
        symbol="GBPNZD", tier=2,
        swing_size_mult=0.0,
        swing_z_threshold=99.0,
        allow_swing=False,           # Swing Sh -0.34 — disabled
        allow_scalp=True,            # H1 scalp Sh 0.66 (4yr PiT, 928 trades) — re-enabled per 08.4-03 D-07
        allow_momentum=False,        # Momentum Sh 0.42 (4yr PiT, 1880 trades) — below 0.5 threshold, kept disabled
        allow_m15_scalp=True,        # M15 Sh 3.65 — BEST M15 pair in portfolio
        m15_z_threshold=2.0,
        m15_size_mult=0.7,
        notes="08.4-03 4yr PiT re-eval (real GBPNZD H1 4yr from MT5 Path A): scalp Sh=0.66 n=928 wr=47.5% — CROSSED, allow_scalp flipped True. Momentum Sh=0.42 n=1880 wr=46.2% — below 0.5 threshold, stays disabled. M15 Sh 3.65 unchanged. Eval JSON: backtest/results/gbpnzd_4yr_eval_2026-04-26.json.",
    ),

    # ── EURUSD: Swing/H1/Momentum negative. M15 Sh 2.62 — re-enabled. ────────
    "EURUSD": PairConfig(
        symbol="EURUSD", tier=2,
        swing_size_mult=0.0,
        swing_z_threshold=99.0,
        allow_swing=False,           # Swing Sh -0.20 — disabled
        allow_scalp=False,           # H1 scalp Sh -0.24 — disabled (4yr)
        allow_momentum=False,        # Momentum Sh -0.04 — disabled (4yr)
        allow_m15_scalp=True,        # M15 Sh 2.62 — most liquid pair, tight raw spreads
        m15_z_threshold=2.0,
        m15_size_mult=0.7,
        notes="Swing/H1/Momentum disabled. M15 Sh 2.62 — liquid pair benefits most from raw account spreads. | 4yr corrected — 2026-04-25: scalp Sh=-0.24 win=41.9% n=880; momentum Sh=-0.04 win=46.2% n=1538",
    ),

    # ── AUDNZD: Swing negative. M15 Sh 2.19 + H1 scalp Sh 1.59 (4yr). ───────
    "AUDNZD": PairConfig(
        symbol="AUDNZD", tier=2,
        swing_size_mult=0.0,
        swing_z_threshold=99.0,
        allow_swing=False,           # Swing Sh -2.16 — structural drift
        allow_scalp=True,            # H1 scalp Sh 1.59 — validated positive (4yr)
        scalp_size_mult=0.5,
        allow_momentum=True,         # Momentum Sh 0.97 — validated positive (4yr)
        momentum_size_mult=0.3,      # Small size — low conviction
        allow_m15_scalp=True,        # M15 Sh 2.19 — positive
        m15_z_threshold=2.0,
        m15_size_mult=0.6,
        notes="Swing Sh -2.16 (structural drift). H1 Scalp Sh 1.63 + Momentum Sh 0.55 + M15 Sh 2.19. | 4yr corrected — 2026-04-25: scalp Sh=1.59 win=53.5% n=437; momentum Sh=0.97 win=50.2% n=1032",
    ),
}


# ── Accessor ───────────────────────────────────────────────────────────────────

_DEFAULT_CONFIG = PairConfig(symbol="DEFAULT", tier=2)


def get_pair_config(symbol: str) -> PairConfig:
    """Return config for a symbol, falling back to Tier 2 defaults."""
    return PAIR_CONFIGS.get(symbol, _DEFAULT_CONFIG)


def print_pair_summary():
    print("\n" + "="*120)
    print("PAIR CONFIGURATION SUMMARY — Data-driven (backtest_evaluate_all.py)")
    print("="*120)
    print(f"{'Symbol':8} {'Tier':5} {'Swing':6} {'H1Scalp':8} {'Momentum':9} {'M15':5} {'M15Sh':6} Notes")
    print("-"*120)
    sharpes = {
        'USDJPY': (3.09, -2.34, -1.61, 0.93),
        'GBPJPY': (1.93,  0.85,  0.21,-0.02),
        'GBPAUD': (1.86, -0.61, -0.11, 1.08),
        'GBPUSD': (1.05, -0.15,  1.00, 2.60),
        'EURGBP': (0.45,  1.32,  1.57, 1.86),
        'GBPNZD': (-0.34,-0.60, -1.23, 3.65),
        'EURUSD': (-0.20,-0.17, -1.03, 2.62),
        'AUDNZD': (-2.16, 1.63,  0.55, 2.19),
    }
    for sym, cfg in PAIR_CONFIGS.items():
        sh = sharpes.get(sym, (0,0,0,0))
        sw  = f"✓{sh[0]:+.2f}" if cfg.allow_swing else f"✗{sh[0]:+.2f}"
        sc  = f"✓{sh[1]:+.2f}" if cfg.allow_scalp else f"✗{sh[1]:+.2f}"
        mo  = f"✓{sh[2]:+.2f}" if cfg.allow_momentum else f"✗{sh[2]:+.2f}"
        m15 = f"✓{sh[3]:+.2f}" if cfg.allow_m15_scalp else f"✗{sh[3]:+.2f}"
        print(f"{sym:8} {'T'+str(cfg.tier):5} {sw:7} {sc:9} {mo:9} {m15:7}  {cfg.notes[:55]}")
    print("="*120)


if __name__ == "__main__":
    print_pair_summary()

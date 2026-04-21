"""
Pure-numpy signal filter implementations ported from vectorbt.pro concepts.
No dependency on the vbt package — these run standalone.

Available:
    rolling_hurst(close, window, lags) → H exponent series (0–1)
    rolling_ols_zscore(close, window)  → trend-adjusted Z-score
    sigdet_zscore(close, lag, influence, factor) → adaptive Z-score
"""

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view


# ─────────────────────────────────────────────────────────────────────────────
# Hurst Exponent  (variance-scaling method)
#
# H < 0.45 → mean-reverting regime    (good for our Z-score entries)
# H ~ 0.50 → random walk              (neutral)
# H > 0.55 → trending regime          (block mean-reversion entries)
#
# Method: for increasing aggregation lags, variance of log-returns scales as
#   Var(τ) ∝ τ^(2H)  →  H = slope / 2  from log-log OLS fit
# ─────────────────────────────────────────────────────────────────────────────

def _hurst_single(arr: np.ndarray, lags=(2, 4, 8, 16, 32)) -> float:
    """Compute Hurst exponent for a single price window (raw numpy array)."""
    log_ret = np.diff(np.log(arr))
    if len(log_ret) < 16:  # absolute minimum for any meaningful fit
        return np.nan

    vars_, valid_lags = [], []
    for lag in lags:
        n_chunks = len(log_ret) // lag
        if n_chunks < 4:
            continue
        chunks = log_ret[: n_chunks * lag].reshape(n_chunks, lag).sum(axis=1)
        v = chunks.var(ddof=0)
        if v > 0:
            vars_.append(v)
            valid_lags.append(lag)

    if len(valid_lags) < 3:
        return np.nan

    slope = np.polyfit(np.log(valid_lags), np.log(vars_), 1)[0]
    return float(slope / 2.0)


def rolling_hurst(close: pd.Series, window: int = 100,
                  lags: tuple = (2, 4, 8, 16, 32)) -> pd.Series:
    """
    Rolling Hurst exponent.

    Args:
        close:  Price series (daily, H1, or M15).
        window: Look-back bars.  Recommend 60 for daily, 100 for M15.
        lags:   Aggregation lags for variance scaling fit.

    Returns:
        pd.Series of H values (0–1).  NaN for the first `window` bars.
    """
    result = close.rolling(window).apply(
        lambda x: _hurst_single(x, lags=lags), raw=True
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# OLS Z-score  (trend-adjusted signal)
#
# Fits a linear regression y = a + b*t over the window (t = bar index).
# Z-score = (current_price - predicted_price) / std(residuals)
#
# This measures deviation from the TREND line, not from a flat rolling mean.
# More accurate for pairs that drift slowly (e.g. EURGBP).
# ─────────────────────────────────────────────────────────────────────────────

def rolling_ols_zscore(close: pd.Series, window: int = 20) -> pd.Series:
    """
    Rolling OLS regression Z-score (vectorised — no Python loop over bars).

    Args:
        close:  Price series.
        window: Regression window.

    Returns:
        pd.Series of Z-scores.  NaN for the first `window-1` bars.
    """
    arr = close.values.astype(float)
    n   = len(arr)

    if n < window:
        return pd.Series(np.nan, index=close.index)

    # Pre-compute fixed OLS weights for x = [0, 1, ..., window-1]
    x      = np.arange(window, dtype=float)
    x_mean = x.mean()
    Sxx    = ((x - x_mean) ** 2).sum()
    # slope weights: s_w[i] = (x[i] - x_mean) / Sxx
    s_w = (x - x_mean) / Sxx

    # sliding windows: shape (n - window + 1, window)
    wins      = sliding_window_view(arr, window)          # (M, W)
    y_means   = wins.mean(axis=1)                         # (M,)
    slopes    = (wins * s_w).sum(axis=1)                  # (M,)
    intercepts = y_means - slopes * x_mean                # (M,)

    # predicted values for each window: shape (M, W)
    pred      = slopes[:, None] * x[None, :] + intercepts[:, None]
    residuals = wins - pred                                # (M, W)
    stds      = residuals.std(axis=1, ddof=0)              # (M,)

    # Z-score at the last (current) bar of each window
    last_res  = residuals[:, -1]
    zs        = np.where(stds > 0, last_res / stds, 0.0)

    result    = np.full(n, np.nan)
    result[window - 1:] = zs
    return pd.Series(result, index=close.index)


# ─────────────────────────────────────────────────────────────────────────────
# SIGDET — Adaptive signal-detection Z-score
#
# Standard rolling Z-score is polluted by volatility spikes: one large candle
# inflates std for the next 20 bars, suppressing future signals.
# SIGDET updates its mean/std baseline with reduced weight (influence) when
# the current bar is flagged as a signal, so spikes don't warp the reference.
#
# Returns a Z-score series whose denominator adapts to filter out outliers.
# ─────────────────────────────────────────────────────────────────────────────

def sigdet_zscore(close: pd.Series, lag: int = 20,
                  factor: float = 2.0, influence: float = 0.5) -> pd.Series:
    """
    Adaptive Z-score with spike-resistant baseline.

    Args:
        close:     Price series.
        lag:       Rolling window for mean/std (mirrors our current 20-bar period).
        factor:    Threshold multiplier — bar is a 'signal' if |z| > factor.
        influence: Weight [0–1] for signal bars when updating baseline.
                   0 = ignore outliers entirely, 1 = same as standard rolling.

    Returns:
        pd.Series of adaptive Z-scores.
    """
    arr    = close.values.astype(float)
    n      = len(arr)

    filtered = arr.copy()
    avg      = np.full(n, np.nan)
    std      = np.full(n, np.nan)
    zscore   = np.full(n, np.nan)

    # Initialise baseline on first `lag` bars
    avg[lag - 1] = arr[:lag].mean()
    std[lag - 1] = arr[:lag].std(ddof=0)

    for i in range(lag, n):
        prev_avg = avg[i - 1]
        prev_std = std[i - 1]

        if not np.isnan(prev_std) and prev_std > 0:
            z = (arr[i] - prev_avg) / prev_std
            if abs(z) > factor:
                # Outlier bar: blend with previous filtered value
                filtered[i] = influence * arr[i] + (1 - influence) * filtered[i - 1]
            else:
                filtered[i] = arr[i]
        else:
            filtered[i] = arr[i]

        window_data = filtered[i - lag + 1: i + 1]
        avg[i] = window_data.mean()
        std[i] = window_data.std(ddof=0)

        if not np.isnan(std[i]) and std[i] > 0:
            zscore[i] = (arr[i] - avg[i]) / std[i]

    return pd.Series(zscore, index=close.index)

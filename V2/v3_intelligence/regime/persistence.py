"""JSON persistence for fitted HMMGARCHRegimeDetector instances (D-11).

Schema (schema_version = 1):

  schema_version : int (always 1 for this layout)
  pair           : str
  n_states       : int
  garch_params   : list of {mu, omega, alpha, beta} dicts
  transmat       : (n_states, n_states) nested float list
  startprob      : (n_states,) float list
  variance_ordering :
      state_labels             : ["TRENDING", "MEAN_REVERTING", "CRISIS"][:n_states]
      unconditional_variances  : list of floats (monotonically increasing — REGM-02)
  fit_metadata :
      fitted_at_utc      : ISO-8601 UTC timestamp
      data_window        : str (e.g. "4yr")
      data_path          : str (origin CSV path or "synthetic")
      n_bars             : int
      hmmlearn_converged : bool
      v1_parity_tested   : bool

JSON-only serialisation (no binary formats). numpy arrays are written via
`.tolist()` and read back via `np.asarray(..., dtype=np.float64)`; roundtrip
is exact for finite IEEE-754 doubles (well within the 1e-12 tolerance
asserted by tests).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import numpy as np

from .emissions import GARCHParams
from .hmm_garch import HMMGARCHRegimeDetector

SCHEMA_VERSION = 1
STATE_LABELS = ["TRENDING", "MEAN_REVERTING", "CRISIS"]

PathLike = Union[str, Path]


def save_detector(
    detector: HMMGARCHRegimeDetector,
    path: PathLike,
    *,
    pair: str,
    data_path: str,
    data_window: str = "4yr",
    n_bars: int = 0,
    hmmlearn_converged: bool = True,
    v1_parity_tested: bool = False,
) -> None:
    """Serialize a fitted detector to JSON at `path`.

    Parameters
    ----------
    detector:
        A fitted HMMGARCHRegimeDetector (raises RuntimeError if not).
    path:
        Output JSON path. Parent directory is created if missing.
    pair:
        Pair label (e.g. "USDJPY") embedded in the JSON for forensic context.
    data_path:
        Origin CSV path (or "synthetic" for tests). Stored in fit_metadata.
    data_window:
        Window label (e.g. "4yr"). Stored in fit_metadata. Defaults "4yr".
    n_bars:
        Number of bars used to fit. Stored in fit_metadata.
    hmmlearn_converged:
        Whether the GaussianHMM EM converged. Stored in fit_metadata.
    v1_parity_tested:
        Whether parity vs V1 has been validated. Stored in fit_metadata.

    Raises
    ------
    RuntimeError:
        If the detector has not been fit, or is missing transmat_/startprob_.
    """
    if not detector.is_fitted:
        raise RuntimeError(
            "save_detector: detector has not been fit; cannot persist."
        )
    if detector.transmat_ is None or detector.startprob_ is None:
        raise RuntimeError(
            "save_detector: detector is missing transmat_ or startprob_."
        )

    blob = {
        "schema_version": SCHEMA_VERSION,
        "pair": pair,
        "n_states": detector.n_states,
        "garch_params": [
            {"mu": p.mu, "omega": p.omega, "alpha": p.alpha, "beta": p.beta}
            for p in detector.garch_params
        ],
        "transmat":  np.asarray(detector.transmat_,  dtype=np.float64).tolist(),
        "startprob": np.asarray(detector.startprob_, dtype=np.float64).tolist(),
        "variance_ordering": {
            "state_labels": list(STATE_LABELS[: detector.n_states]),
            "unconditional_variances": [
                p.unconditional_variance for p in detector.garch_params
            ],
        },
        "fit_metadata": {
            "fitted_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "data_window":   data_window,
            "data_path":     data_path,
            "n_bars":        int(n_bars),
            "hmmlearn_converged": bool(hmmlearn_converged),
            "v1_parity_tested":   bool(v1_parity_tested),
        },
    }

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        json.dump(blob, f, indent=2)


def load_detector(path: PathLike) -> HMMGARCHRegimeDetector:
    """Reconstruct a fitted detector from a JSON file at `path`.

    Returns
    -------
    HMMGARCHRegimeDetector
        Detector with `is_fitted == True`; `garch_params`, `transmat_`,
        `startprob_` populated from the JSON. No re-fit; values are
        IEEE-754-roundtripped from disk.

    Raises
    ------
    FileNotFoundError:
        If `path` does not exist.
    KeyError:
        If the JSON is missing `schema_version`.
    ValueError:
        If `schema_version` is not the supported value (1).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Detector JSON not found: {p}")

    with p.open("r") as f:
        blob = json.load(f)

    if "schema_version" not in blob:
        raise KeyError(
            f"{p} missing required field 'schema_version'; cannot load."
        )
    if blob["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"{p} schema_version={blob['schema_version']} not supported "
            f"(expected {SCHEMA_VERSION})."
        )

    n_states = int(blob["n_states"])
    det = HMMGARCHRegimeDetector(n_states=n_states)
    det.garch_params = [
        GARCHParams(
            mu=float(p_["mu"]),
            omega=float(p_["omega"]),
            alpha=float(p_["alpha"]),
            beta=float(p_["beta"]),
        )
        for p_ in blob["garch_params"]
    ]
    det.transmat_ = np.asarray(blob["transmat"], dtype=np.float64)
    det.startprob_ = np.asarray(blob["startprob"], dtype=np.float64)
    det._fitted = True
    return det


__all__ = ["save_detector", "load_detector", "SCHEMA_VERSION", "STATE_LABELS"]

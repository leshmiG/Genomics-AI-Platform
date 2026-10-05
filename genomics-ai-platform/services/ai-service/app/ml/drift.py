"""Population Stability Index (PSI) drift monitoring against the training reference."""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_SAMPLES = 200
EPS = 1e-4


def psi(expected: list[float], actual: list[float]) -> float:
    e = np.clip(np.asarray(expected, dtype=float), EPS, None)
    a = np.clip(np.asarray(actual, dtype=float), EPS, None)
    e, a = e / e.sum(), a / a.sum()
    return float(np.sum((a - e) * np.log(a / e)))


def status(value: float) -> str:
    if value < 0.1:
        return "ok"
    if value < 0.25:
        return "warn"
    return "alert"


def drift_report(batch: pd.DataFrame, reference: dict) -> dict:
    n = len(batch)
    if n < MIN_SAMPLES:
        return {
            "n": n,
            "overall": "insufficient_data",
            "message": f"Need at least {MIN_SAMPLES} rows for stable PSI; got {n}.",
            "features": {},
        }
    feats: dict[str, dict] = {}
    for c, spec in reference["numeric"].items():
        edges = [-np.inf if e is None and i == 0 else (np.inf if e is None else e)
                 for i, e in enumerate(spec["edges"])]
        counts, _ = np.histogram(batch[c], bins=edges)
        v = psi(spec["props"], (counts / max(counts.sum(), 1)).tolist())
        feats[c] = {"psi": round(v, 4), "status": status(v)}
    for c, spec in reference["binary"].items():
        p1 = float(batch[c].mean())
        v = psi(spec["props"], [1 - p1, p1])
        feats[c] = {"psi": round(v, 4), "status": status(v)}
    for c, spec in reference["categorical"].items():
        cats = list(spec)
        vc = batch[c].value_counts(normalize=True)
        v = psi([spec[k] for k in cats], [float(vc.get(k, 0.0)) for k in cats])
        feats[c] = {"psi": round(v, 4), "status": status(v)}
    order = {"ok": 0, "warn": 1, "alert": 2}
    overall = max((f["status"] for f in feats.values()), key=order.get)
    return {"n": n, "overall": overall, "features": feats}

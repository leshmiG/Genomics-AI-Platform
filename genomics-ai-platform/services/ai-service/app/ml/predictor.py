"""Load the packaged model and serve predictions with model-agnostic explanations."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from .cohort import FEATURES


class ModelNotReady(RuntimeError):
    pass


class Predictor:
    def __init__(self, model_dir: str | Path):
        d = Path(model_dir)
        model_path, card_path = d / "model.joblib", d / "model_card.json"
        if not model_path.exists() or not card_path.exists():
            raise ModelNotReady(
                f"No model artifacts in {d}. Run: python -m app.ml.train --out {d}"
            )
        self.model = joblib.load(model_path)
        self.card = json.loads(card_path.read_text())
        self.reference = self.card["reference_values"]
        self.bands = self.card["risk_bands"]

    @property
    def version(self) -> str:
        return self.card["version"]

    def _band(self, p: float) -> str:
        if p >= self.bands["high"]:
            return "high"
        if p >= self.bands["moderate"]:
            return "moderate"
        return "low"

    def predict(self, record: dict) -> dict:
        row = pd.DataFrame([{k: record[k] for k in FEATURES}])
        p = float(self.model.predict_proba(row)[:, 1][0])

        # Occlusion explanation: how much does the risk change if this feature took its
        # reference value? Works for any model type.
        contributions = []
        for f in FEATURES:
            alt = row.copy()
            alt[f] = self.reference[f]
            delta = p - float(self.model.predict_proba(alt)[:, 1][0])
            contributions.append({"feature": f, "value": record[f], "effect": round(delta, 4)})
        contributions.sort(key=lambda c: abs(c["effect"]), reverse=True)

        return {
            "probability": round(p, 4),
            "risk_band": self._band(p),
            "model_version": self.version,
            "top_factors": contributions[:4],
            "note": "Calibrated on a synthetic cohort; demonstration only.",
        }

"""Train, evaluate and package the clopidogrel poor-response model.

Run:  python -m app.ml.train --out artifacts/models --n 6000 --seed 42

Why it is built this way (interview talking points):
  * Two candidates (logistic regression vs gradient boosting). We serve the simpler model
    unless the complex one wins by a meaningful margin (parsimony rule) because clinical
    users need transparency and the data is tabular and small.
  * Probabilities are calibrated (sigmoid / Platt) and we report Brier score + ECE, not just
    AUC. A risk score that is well-ranked but badly calibrated misleads clinicians.
  * Evaluation is repeated per group to surface performance gaps.
  * The model card stores the data hash, library versions and the reference distribution
    used later for drift monitoring (PSI).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .cohort import BINARY, CATEGORICAL, FEATURES, GROUP_COL, NUMERIC, PHENOTYPES, TARGET, make_cohort

PARSIMONY_MARGIN = 0.02  # complex model must beat simple one by this much CV AUC


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC),
            ("bin", "passthrough", BINARY),
            ("cat", OneHotEncoder(categories=[PHENOTYPES], handle_unknown="ignore"), CATEGORICAL),
        ]
    )


def _candidates() -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline(
            [("prep", _preprocessor()), ("clf", LogisticRegression(max_iter=1000, C=1.0))]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("prep", _preprocessor()),
                ("clf", HistGradientBoostingClassifier(max_depth=3, learning_rate=0.08, random_state=0)),
            ]
        ),
    }


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    ece = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            ece += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(ece)


def _reference_distribution(df: pd.DataFrame) -> dict:
    ref: dict = {"numeric": {}, "categorical": {}, "binary": {}}
    for c in NUMERIC:
        edges = np.unique(np.quantile(df[c], np.linspace(0, 1, 11)))
        edges[0], edges[-1] = -np.inf, np.inf
        counts, _ = np.histogram(df[c], bins=edges)
        ref["numeric"][c] = {
            "edges": [None if np.isinf(e) else float(e) for e in edges],
            "props": (counts / counts.sum()).tolist(),
            "median": float(df[c].median()),
        }
    for c in BINARY:
        ref["binary"][c] = {"props": [float(1 - df[c].mean()), float(df[c].mean())]}
    for c in CATEGORICAL:
        vc = df[c].value_counts(normalize=True)
        ref["categorical"][c] = {k: float(vc.get(k, 0.0)) for k in PHENOTYPES}
    return ref


def train(n: int = 6000, seed: int = 42, out_dir: str | Path = "artifacts/models") -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = make_cohort(n, seed)
    data_hash = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()

    train_df, test_df = train_test_split(df, test_size=0.25, random_state=seed, stratify=df[TARGET])
    X_tr, y_tr = train_df[FEATURES], train_df[TARGET].to_numpy()
    X_te, y_te = test_df[FEATURES], test_df[TARGET].to_numpy()

    cv = StratifiedKFold(5, shuffle=True, random_state=seed)
    cv_auc = {
        name: float(cross_val_score(pipe, X_tr, y_tr, cv=cv, scoring="roc_auc").mean())
        for name, pipe in _candidates().items()
    }
    chosen = "logistic_regression"
    if cv_auc["hist_gradient_boosting"] - cv_auc["logistic_regression"] > PARSIMONY_MARGIN:
        chosen = "hist_gradient_boosting"

    base = _candidates()[chosen]
    model = CalibratedClassifierCV(base, method="sigmoid", cv=5)
    model.fit(X_tr, y_tr)

    p_te = model.predict_proba(X_te)[:, 1]
    metrics = {
        "auc": float(roc_auc_score(y_te, p_te)),
        "brier": float(brier_score_loss(y_te, p_te)),
        "ece": expected_calibration_error(y_te, p_te),
        "base_rate_test": float(y_te.mean()),
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
    }
    subgroup = {}
    for g, part in test_df.assign(_p=p_te).groupby(GROUP_COL):
        entry = {
            "n": int(len(part)),
            "observed_rate": float(part[TARGET].mean()),
            "mean_predicted": float(part["_p"].mean()),
        }
        if part[TARGET].nunique() == 2:
            entry["auc"] = float(roc_auc_score(part[TARGET], part["_p"]))
        subgroup[str(g)] = entry

    ref = _reference_distribution(train_df)
    version = f"{datetime.now(UTC).strftime('%Y%m%d')}-{data_hash[:8]}"
    card = {
        "model_name": "clopidogrel_poor_response",
        "version": version,
        "algorithm": chosen,
        "candidate_cv_auc": cv_auc,
        "parsimony_margin": PARSIMONY_MARGIN,
        "features": FEATURES,
        "target": TARGET,
        "metrics": metrics,
        "subgroup_metrics": subgroup,
        "reference_distribution": ref,
        "reference_values": {
            **{c: ref["numeric"][c]["median"] for c in NUMERIC},
            **{c: 0 for c in BINARY},
            "cyp2c19_phenotype": "Normal Metabolizer",
        },
        "risk_bands": {"low": 0.0, "moderate": 0.25, "high": 0.45},
        "training": {
            "seed": seed,
            "data": "SYNTHETIC cohort (app/ml/cohort.py)",
            "data_sha256": data_hash,
            "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "intended_use": "Teaching/demo of an MLOps lifecycle. Not for clinical decisions.",
        "limitations": [
            "Trained on simulated data with invented effect sizes.",
            "Single gene phenotype; ignores CYP2C19 interacting drugs beyond PPI flag.",
            "No external validation; calibration is only valid for the simulated distribution.",
        ],
    }

    joblib.dump(model, out / "model.joblib")
    (out / "model_card.json").write_text(json.dumps(card, indent=2))
    return card


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/models")
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    c = train(args.n, args.seed, args.out)
    print(json.dumps({k: c[k] for k in ("version", "algorithm", "metrics", "candidate_cv_auc")}, indent=2))

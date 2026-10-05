import json

import numpy as np
import pandas as pd
import pytest

from app.ml.cohort import FEATURES, PHENOTYPES, make_cohort
from app.ml.drift import MIN_SAMPLES, drift_report, psi
from app.ml.predictor import ModelNotReady, Predictor
from app.ml.train import expected_calibration_error

BASE = {
    "age": 64, "bmi": 28, "egfr": 80, "ppi_use": 0, "diabetes": 0, "smoker": 0,
    "cyp2c19_phenotype": "Normal Metabolizer",
}


def test_cohort_is_reproducible_and_has_all_phenotypes():
    a, b = make_cohort(1500, 3), make_cohort(1500, 3)
    pd.testing.assert_frame_equal(a, b)
    assert set(a["cyp2c19_phenotype"]) <= set(PHENOTYPES)
    assert 0.1 < a["poor_response"].mean() < 0.6


def test_cohort_has_group_allele_structure():
    df = make_cohort(8000, 1)
    pm_rate = df.groupby("group")["cyp2c19_phenotype"].apply(lambda s: (s == "Poor Metabolizer").mean())
    assert pm_rate["B"] > pm_rate["A"]  # group B has higher *2/*3 frequency by construction


def test_model_card_contents(model_dir):
    card = json.loads((model_dir / "model_card.json").read_text())
    assert card["algorithm"] in {"logistic_regression", "hist_gradient_boosting"}
    assert 0.6 < card["metrics"]["auc"] < 0.9
    assert card["metrics"]["ece"] < 0.08, "calibration should be reasonable"
    assert set(card["subgroup_metrics"]) == {"A", "B", "C"}
    assert len(card["training"]["data_sha256"]) == 64


def test_prediction_direction_makes_clinical_sense(model_dir):
    p = Predictor(model_dir)
    normal = p.predict(BASE)["probability"]
    poor = p.predict({**BASE, "cyp2c19_phenotype": "Poor Metabolizer"})["probability"]
    ultra = p.predict({**BASE, "cyp2c19_phenotype": "Ultrarapid Metabolizer"})["probability"]
    assert poor > normal > ultra
    assert p.predict({**BASE, "ppi_use": 1})["probability"] > normal


def test_explanation_ranks_phenotype_first_for_poor_metabolizer(model_dir):
    out = Predictor(model_dir).predict({**BASE, "cyp2c19_phenotype": "Poor Metabolizer"})
    assert out["top_factors"][0]["feature"] == "cyp2c19_phenotype"
    assert out["top_factors"][0]["effect"] > 0
    assert out["risk_band"] in {"moderate", "high"}


def test_predictor_without_artifacts_raises(tmp_path):
    with pytest.raises(ModelNotReady):
        Predictor(tmp_path)


def test_ece_perfect_and_bad():
    y = np.array([0, 1] * 500)
    assert expected_calibration_error(y, np.full(1000, 0.5)) < 1e-9
    assert expected_calibration_error(y, np.where(y == 1, 0.05, 0.95)) > 0.8


def test_psi_identity_and_shift():
    assert psi([0.25] * 4, [0.25] * 4) == pytest.approx(0, abs=1e-9)
    assert psi([0.25] * 4, [0.7, 0.1, 0.1, 0.1]) > 0.25


def test_drift_report_detects_shift_and_stays_quiet_otherwise(model_dir):
    card = json.loads((model_dir / "model_card.json").read_text())
    ref = card["reference_distribution"]

    same = make_cohort(2000, seed=99)[FEATURES]
    assert drift_report(same, ref)["overall"] in {"ok", "warn"}
    assert drift_report(same, ref)["features"]["age"]["status"] == "ok"

    shifted = same.copy()
    shifted["age"] = shifted["age"] + 18
    shifted["cyp2c19_phenotype"] = "Poor Metabolizer"
    rep = drift_report(shifted, ref)
    assert rep["overall"] == "alert"
    assert rep["features"]["age"]["status"] == "alert"
    assert rep["features"]["cyp2c19_phenotype"]["status"] == "alert"


def test_drift_guard_for_small_batches(model_dir):
    card = json.loads((model_dir / "model_card.json").read_text())
    small = make_cohort(MIN_SAMPLES - 1, 5)[FEATURES]
    assert drift_report(small, card["reference_distribution"])["overall"] == "insufficient_data"

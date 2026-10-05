"""Synthetic cohort generator.

All data here is SIMULATED. No real patient data is used or implied, and the effect sizes are
invented for demonstration. Three abstract groups (A, B, C) have different allele
frequencies so we can demonstrate subgroup evaluation and population stratification; they do
not represent real populations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.genomics.pgx import call_from_diplotype

NUMERIC = ["age", "bmi", "egfr"]
BINARY = ["ppi_use", "diabetes", "smoker"]
CATEGORICAL = ["cyp2c19_phenotype"]
FEATURES = NUMERIC + BINARY + CATEGORICAL
TARGET = "poor_response"
GROUP_COL = "group"

PHENOTYPES = [
    "Ultrarapid Metabolizer",
    "Rapid Metabolizer",
    "Normal Metabolizer",
    "Intermediate Metabolizer",
    "Poor Metabolizer",
]

# Haplotype frequencies per synthetic group: *1 is the remainder.
_HAP_FREQ = {
    "A": {"*2": 0.15, "*3": 0.005, "*17": 0.21},
    "B": {"*2": 0.30, "*3": 0.05, "*17": 0.02},
    "C": {"*2": 0.12, "*3": 0.001, "*17": 0.10},
}
_GROUP_P = {"A": 0.5, "B": 0.3, "C": 0.2}

_PHENO_LOGIT = {
    "Ultrarapid Metabolizer": -0.6,
    "Rapid Metabolizer": -0.3,
    "Normal Metabolizer": 0.0,
    "Intermediate Metabolizer": 1.0,
    "Poor Metabolizer": 2.2,
}

_PHENO_CACHE: dict[str, str] = {}


def _phenotype_for(a1: str, a2: str) -> str:
    key = "/".join(sorted([a1, a2]))
    if key not in _PHENO_CACHE:
        _PHENO_CACHE[key] = call_from_diplotype("CYP2C19", key).phenotype
    return _PHENO_CACHE[key]


def make_cohort(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    groups = rng.choice(list(_GROUP_P), size=n, p=list(_GROUP_P.values()))

    pheno = np.empty(n, dtype=object)
    for g in _GROUP_P:
        idx = np.where(groups == g)[0]
        f = _HAP_FREQ[g]
        alleles = ["*1", "*2", "*3", "*17"]
        p = [1 - sum(f.values()), f["*2"], f["*3"], f["*17"]]
        h1 = rng.choice(alleles, size=len(idx), p=p)
        h2 = rng.choice(alleles, size=len(idx), p=p)
        pheno[idx] = [_phenotype_for(a, b) for a, b in zip(h1, h2, strict=True)]

    age = np.clip(rng.normal(64, 11, n), 30, 95).round(0)
    bmi = np.clip(rng.normal(28.5, 4.8, n), 16, 55).round(1)
    egfr = np.clip(rng.normal(82 - 0.35 * (age - 64), 18, n), 15, 130).round(0)
    ppi = rng.binomial(1, 0.28, n)
    diabetes = rng.binomial(1, np.clip(0.18 + 0.004 * (bmi - 28), 0.02, 0.6))
    smoker = rng.binomial(1, 0.2, n)

    logit = (
        -1.6
        + np.array([_PHENO_LOGIT[p] for p in pheno])
        + 0.5 * ppi
        + 0.4 * diabetes
        + 0.05 * (bmi - 27)
        + 0.01 * (age - 65)
        - 0.004 * (egfr - 80)
        - 0.2 * smoker
    )
    prob = 1 / (1 + np.exp(-logit))
    y = rng.binomial(1, prob)

    return pd.DataFrame(
        {
            "age": age,
            "bmi": bmi,
            "egfr": egfr,
            "ppi_use": ppi,
            "diabetes": diabetes,
            "smoker": smoker,
            "cyp2c19_phenotype": pheno,
            GROUP_COL: groups,
            TARGET: y,
        }
    )

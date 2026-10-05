"""Gene-drug guidance lookup (paraphrased, simplified, for demonstration only).

This is NOT a copy of any guideline. In production, load versioned CPIC/DPWG content from a
curated source, record the guideline version in every response, and have a clinical
pharmacist sign off on changes (see docs/SAFETY.md).
"""

from __future__ import annotations

from dataclasses import dataclass

GUIDELINE_SOURCE = "demo-table-v0 (paraphrased; verify against current CPIC/DPWG before clinical use)"

DISCLAIMER = (
    "Educational decision-support demo. Not a medical device. Any clinical action must be "
    "confirmed by a qualified clinician against current guidelines."
)


@dataclass(frozen=True)
class DrugGuidance:
    drug: str
    gene: str
    phenotype: str
    recommendation: str
    strength: str  # strong | moderate | optional | informational


# (drug, gene) -> phenotype -> (recommendation, strength)
_TABLE: dict[tuple[str, str], dict[str, tuple[str, str]]] = {
    ("clopidogrel", "CYP2C19"): {
        "Ultrarapid Metabolizer": (
            "Standard dosing; normal or increased active-metabolite formation expected.", "strong"),
        "Rapid Metabolizer": (
            "Standard dosing; normal or increased active-metabolite formation expected.", "strong"),
        "Normal Metabolizer": ("Standard dosing.", "strong"),
        "Intermediate Metabolizer": (
            "Reduced activation likely. Where an alternative antiplatelet is appropriate and not "
            "contraindicated (e.g. in ACS or PCI), consider it.",
            "moderate",
        ),
        "Poor Metabolizer": (
            "Markedly reduced activation. Avoid clopidogrel if a suitable alternative antiplatelet "
            "is available and not contraindicated.",
            "strong",
        ),
    },
    ("simvastatin", "SLCO1B1"): {
        "Normal Function": ("Standard dosing per label.", "strong"),
        "Decreased Function": (
            "Higher myopathy risk at higher doses. Consider a lower dose or an alternative statin; "
            "monitor for muscle symptoms.",
            "moderate",
        ),
        "Poor Function": (
            "Substantially higher myopathy risk. Prefer an alternative statin or a low dose with monitoring.",
            "strong",
        ),
    },
    ("azathioprine", "TPMT"): {
        "Normal Metabolizer": ("Standard starting dose with routine monitoring.", "strong"),
        "Intermediate Metabolizer": (
            "Consider a reduced starting dose with closer blood count monitoring.",
            "strong",
        ),
        "Poor Metabolizer": (
            "Severe myelosuppression risk. Use an alternative agent or a drastically reduced dose "
            "under specialist supervision.",
            "strong",
        ),
    },
    ("fluorouracil", "DPYD"): {
        "Normal Metabolizer": ("Standard dosing.", "strong"),
        "Intermediate Metabolizer": (
            "Increased toxicity risk. Reduce the starting dose per guideline and titrate by tolerance.",
            "strong",
        ),
        "Poor Metabolizer": (
            "Life-threatening toxicity risk. Avoid fluoropyrimidines; specialist advice required.",
            "strong",
        ),
    },
    ("warfarin", "CYP2C9"): {
        "Normal Metabolizer": (
            "Use a validated pharmacogenetic dosing algorithm; standard INR monitoring.", "optional"),
        "Intermediate Metabolizer": (
            "Lower dose requirement likely and slower time to stable INR; use a validated dosing algorithm.",
            "moderate",
        ),
        "Poor Metabolizer": (
            "Markedly lower dose requirement and higher bleeding risk; use a validated algorithm "
            "and monitor closely.",
            "moderate",
        ),
    },
}

DRUG_TO_GENE = {drug: gene for (drug, gene) in _TABLE}
SUPPORTED_DRUGS = sorted(DRUG_TO_GENE)


def lookup(drug: str, phenotype: str) -> DrugGuidance | None:
    drug = drug.lower().strip()
    gene = DRUG_TO_GENE.get(drug)
    if gene is None:
        return None
    entry = _TABLE[(drug, gene)].get(phenotype)
    if entry is None:
        return DrugGuidance(
            drug, gene, phenotype,
            "No automated recommendation for this phenotype/result; refer to a clinical pharmacist.",
            "informational",
        )
    return DrugGuidance(drug, gene, phenotype, entry[0], entry[1])

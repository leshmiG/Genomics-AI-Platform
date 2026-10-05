"""Pharmacogenomics (PGx) star-allele calling and phenotype translation.

EDUCATIONAL REFERENCE IMPLEMENTATION. The allele definitions and phenotype rules below are a
deliberately small subset written for demonstration and tests. Real clinical use requires the
current, versioned CPIC / PharmVar / PharmGKB tables, structural-variant handling (e.g. CYP2D6
copy number), a validated assay, and clinical governance. See docs/SAFETY.md.

Design points worth knowing for interviews:
  * Calling is deterministic and rule-based. Language models never compute clinical calls.
  * Unphased genotypes can be ambiguous (cis vs trans). We enumerate every haplotype pair that
    is consistent with the observed genotype and only report a phenotype if all agree.
  * A variant missing from the input is NOT assumed reference silently; we warn.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

# Function labels ordered from worst to best, used when an unrecognised haplotype carries
# several defining variants (we take the most severe, i.e. conservative, function).
FUNCTION_SEVERITY = {"no": 0, "decreased": 1, "normal": 2, "increased": 3}


@dataclass(frozen=True)
class Variant:
    rsid: str
    ref: str
    alt: str
    allele: str  # star allele that this variant defines when present alone


@dataclass(frozen=True)
class GeneDef:
    gene: str
    variants: tuple[Variant, ...]
    function: dict[str, str]  # allele -> function label
    activity: dict[str, float] = field(default_factory=dict)  # allele -> activity value
    # Known multi-variant haplotypes: frozenset of rsids -> allele name (e.g. TPMT *3A)
    cis_alleles: dict[frozenset, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Genotype:
    """Two haplotype calls: 0 = reference, 1 = alt, None = missing."""

    a1: int | None
    a2: int | None
    phased: bool = False

    @property
    def missing(self) -> bool:
        return self.a1 is None or self.a2 is None

    @property
    def alt_count(self) -> int:
        return sum(1 for a in (self.a1, self.a2) if a == 1)


@dataclass
class GeneCall:
    gene: str
    diplotype: str | None
    phenotype: str
    activity_score: float | None
    phase_ambiguous: bool
    candidate_diplotypes: list[str]
    warnings: list[str]

    def as_dict(self) -> dict:
        return self.__dict__.copy()


# --------------------------------------------------------------------------------------
# Gene definitions (subset). Verify against PharmVar/CPIC before any real use.
# --------------------------------------------------------------------------------------
GENES: dict[str, GeneDef] = {
    "CYP2C19": GeneDef(
        gene="CYP2C19",
        variants=(
            Variant("rs4244285", "G", "A", "*2"),
            Variant("rs4986893", "G", "A", "*3"),
            Variant("rs12248560", "C", "T", "*17"),
        ),
        function={"*1": "normal", "*2": "no", "*3": "no", "*17": "increased"},
    ),
    "CYP2C9": GeneDef(
        gene="CYP2C9",
        variants=(
            Variant("rs1799853", "C", "T", "*2"),
            Variant("rs1057910", "A", "C", "*3"),
        ),
        function={"*1": "normal", "*2": "decreased", "*3": "no"},
        activity={"*1": 1.0, "*2": 0.5, "*3": 0.0},
    ),
    "SLCO1B1": GeneDef(
        gene="SLCO1B1",
        variants=(Variant("rs4149056", "T", "C", "*5"),),
        function={"*1": "normal", "*5": "decreased"},
    ),
    "TPMT": GeneDef(
        gene="TPMT",
        variants=(
            Variant("rs1800462", "C", "G", "*2"),
            Variant("rs1800460", "C", "T", "*3B"),
            Variant("rs1142345", "T", "C", "*3C"),
        ),
        function={"*1": "normal", "*2": "no", "*3A": "no", "*3B": "no", "*3C": "no"},
        cis_alleles={frozenset({"rs1800460", "rs1142345"}): "*3A"},
    ),
    "DPYD": GeneDef(
        gene="DPYD",
        variants=(Variant("rs3918290", "C", "T", "*2A"),),
        function={"*1": "normal", "*2A": "no"},
        activity={"*1": 1.0, "*2A": 0.0},
    ),
}

ALL_TARGET_RSIDS = {v.rsid: v for g in GENES.values() for v in g.variants}


def _star_sort_key(allele: str) -> tuple:
    m = re.match(r"\*(\d+)(.*)", allele)
    return (int(m.group(1)), m.group(2)) if m else (10_000, allele)


def _hap_to_allele(gene: GeneDef, present: frozenset[str]) -> tuple[str, str, list[str]]:
    """Map the set of defining rsids on one haplotype to (allele_name, function, warnings)."""
    if not present:
        return "*1", gene.function["*1"], []
    if present in gene.cis_alleles:
        name = gene.cis_alleles[present]
        return name, gene.function[name], []
    by_rsid = {v.rsid: v for v in gene.variants}
    if len(present) == 1:
        name = by_rsid[next(iter(present))].allele
        return name, gene.function[name], []
    names = sorted((by_rsid[r].allele for r in present), key=_star_sort_key)
    worst = min((gene.function[n] for n in names), key=lambda f: FUNCTION_SEVERITY[f])
    label = "+".join(names) + "?"
    return label, worst, [f"Unrecognised haplotype combination {label}; most severe function used."]


def _allele_activity(gene: GeneDef, allele: str) -> float:
    """Activity value of an allele; unrecognised combined haplotypes use their lowest part."""
    if allele in gene.activity:
        return gene.activity[allele]
    parts = allele.rstrip("?").split("+")
    return min(gene.activity.get(p, 1.0) for p in parts)


def _enumerate_haplotype_pairs(rsids: list[str], counts: dict[str, int]):
    """All unordered haplotype pairs consistent with per-variant alt counts (0/1/2)."""
    subsets = [frozenset(c) for n in range(len(rsids) + 1) for c in itertools.combinations(rsids, n)]
    seen = set()
    for h1, h2 in itertools.product(subsets, repeat=2):
        if all((r in h1) + (r in h2) == counts[r] for r in rsids):
            key = frozenset([h1, h2]) if h1 != h2 else (h1,)
            if key not in seen:
                seen.add(key)
                yield h1, h2


def _phenotype(gene: GeneDef, functions: list[str], activity_total: float | None) -> str:
    g = gene.gene
    n_no = functions.count("no")
    n_dec = functions.count("decreased")
    n_inc = functions.count("increased")
    if g == "CYP2C19":
        if n_inc == 2:
            return "Ultrarapid Metabolizer"
        if n_inc == 1 and n_no == 0:
            return "Rapid Metabolizer"
        if n_no == 2:
            return "Poor Metabolizer"
        if n_no == 1:
            return "Intermediate Metabolizer"
        return "Normal Metabolizer"
    if g in ("CYP2C9", "DPYD"):
        assert activity_total is not None
        if activity_total >= 2.0:
            return "Normal Metabolizer"
        if activity_total >= 1.0:
            return "Intermediate Metabolizer"
        return "Poor Metabolizer"
    if g == "SLCO1B1":
        reduced = n_dec + n_no
        return ["Normal Function", "Decreased Function", "Poor Function"][min(reduced, 2)]
    if g == "TPMT":
        if n_no == 2:
            return "Poor Metabolizer"
        if n_no == 1:
            return "Intermediate Metabolizer"
        return "Normal Metabolizer"
    raise ValueError(f"No phenotype rule for {g}")


def call_gene(gene_name: str, genotypes: dict[str, Genotype]) -> GeneCall:
    """Call a diplotype and phenotype for one gene from per-rsid genotypes."""
    gene = GENES[gene_name]
    warnings: list[str] = []
    rsids = [v.rsid for v in gene.variants]

    missing = [r for r in rsids if r not in genotypes or genotypes[r].missing]
    for r in missing:
        warnings.append(f"{r} not assayed or no-call; assumed reference. Result may be a false negative.")

    counts = {r: (0 if r in missing else genotypes[r].alt_count) for r in rsids}
    het = [r for r in rsids if counts[r] == 1]

    # Phased shortcut: every het site is phased and there is more than one of them.
    candidates: list[tuple[frozenset, frozenset]]
    if len(het) >= 2 and all(genotypes[r].phased for r in het):
        h1 = frozenset(r for r in rsids if r not in missing and genotypes[r].a1 == 1)
        h2 = frozenset(r for r in rsids if r not in missing and genotypes[r].a2 == 1)
        candidates = [(h1, h2)]
    else:
        candidates = list(_enumerate_haplotype_pairs(rsids, counts))

    interpretations = []
    for h1, h2 in candidates:
        a1, f1, w1 = _hap_to_allele(gene, h1)
        a2, f2, w2 = _hap_to_allele(gene, h2)
        alleles = sorted([a1, a2], key=_star_sort_key)
        act = None
        if gene.activity:
            act = sum(_allele_activity(gene, a) for a in (a1, a2))
        interpretations.append(
            {
                "diplotype": "/".join(alleles),
                "phenotype": _phenotype(gene, [f1, f2], act),
                "activity": act,
                "warnings": w1 + w2,
            }
        )

    diplotypes = sorted({i["diplotype"] for i in interpretations})
    phenotypes = {i["phenotype"] for i in interpretations}
    phase_ambiguous = len(diplotypes) > 1

    if len(phenotypes) == 1:
        phenotype = phenotypes.pop()
        if phase_ambiguous:
            warnings.append(
                "Phase ambiguity: diplotype undetermined but all consistent interpretations "
                "give the same phenotype."
            )
        chosen = interpretations[0]
        diplotype = chosen["diplotype"] if not phase_ambiguous else None
        activity = chosen["activity"]
    else:
        phenotype = "Indeterminate"
        diplotype = None
        activity = None
        warnings.append(
            "Phase ambiguity changes the phenotype; phased data (long reads / trio / "
            "family) or targeted haplotype assay needed before any clinical use."
        )

    for i in interpretations:
        for w in i["warnings"]:
            if w not in warnings:
                warnings.append(w)

    return GeneCall(
        gene=gene_name,
        diplotype=diplotype,
        phenotype=phenotype,
        activity_score=activity,
        phase_ambiguous=phase_ambiguous,
        candidate_diplotypes=diplotypes,
        warnings=warnings,
    )


def call_all(genotypes: dict[str, Genotype]) -> dict[str, GeneCall]:
    return {name: call_gene(name, genotypes) for name in GENES}


def call_from_diplotype(gene_name: str, diplotype: str) -> GeneCall:
    """Translate a lab-reported diplotype string (e.g. '*1/*2') to a phenotype."""
    gene = GENES[gene_name]
    m = re.fullmatch(r"\s*(\*\w+)\s*/\s*(\*\w+)\s*", diplotype)
    if not m:
        raise ValueError(f"Diplotype must look like '*1/*2', got {diplotype!r}")
    a1, a2 = m.group(1), m.group(2)
    for a in (a1, a2):
        if a not in gene.function:
            raise ValueError(f"Allele {a} is not defined for {gene_name} in this reference table")
    funcs = [gene.function[a1], gene.function[a2]]
    act = sum(gene.activity[a] for a in (a1, a2)) if gene.activity else None
    alleles = sorted([a1, a2], key=_star_sort_key)
    return GeneCall(
        gene=gene_name,
        diplotype="/".join(alleles),
        phenotype=_phenotype(gene, funcs, act),
        activity_score=act,
        phase_ambiguous=False,
        candidate_diplotypes=["/".join(alleles)],
        warnings=[],
    )

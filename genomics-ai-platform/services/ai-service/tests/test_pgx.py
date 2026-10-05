import pytest

from app.genomics.guidance import lookup
from app.genomics.pgx import Genotype, call_from_diplotype, call_gene
from app.genomics.vcf import VcfError, parse_vcf, render_demo_vcf

HOM_REF = Genotype(0, 0)
HET = Genotype(0, 1)
HOM_ALT = Genotype(1, 1)


def test_cyp2c19_star1_star2_is_intermediate():
    call = call_gene("CYP2C19", {"rs4244285": HET})
    assert call.diplotype == "*1/*2"
    assert call.phenotype == "Intermediate Metabolizer"


def test_cyp2c19_homozygous_star2_is_poor():
    call = call_gene("CYP2C19", {"rs4244285": HOM_ALT})
    assert call.diplotype == "*2/*2"
    assert call.phenotype == "Poor Metabolizer"


def test_cyp2c19_star17_het_is_rapid_and_hom_is_ultrarapid():
    assert call_gene("CYP2C19", {"rs12248560": HET}).phenotype == "Rapid Metabolizer"
    assert call_gene("CYP2C19", {"rs12248560": HOM_ALT}).phenotype == "Ultrarapid Metabolizer"


def test_cyp2c19_star2_plus_star17_trans_is_intermediate_even_though_unphased():
    # cis and trans interpretations both give Intermediate -> phenotype is resolved
    call = call_gene("CYP2C19", {"rs4244285": HET, "rs12248560": HET})
    assert call.phenotype == "Intermediate Metabolizer"
    assert call.phase_ambiguous is True
    assert call.diplotype is None  # diplotype itself is undetermined


def test_cyp2c9_activity_scores():
    assert call_gene("CYP2C9", {}).activity_score == 2.0
    assert call_gene("CYP2C9", {"rs1799853": HET}).activity_score == 1.5
    poor = call_gene("CYP2C9", {"rs1057910": HOM_ALT})
    assert poor.activity_score == 0.0 and poor.phenotype == "Poor Metabolizer"


def test_dpyd_star2a_het_is_intermediate():
    call = call_gene("DPYD", {"rs3918290": HET})
    assert call.phenotype == "Intermediate Metabolizer"
    assert call.activity_score == 1.0


def test_slco1b1_function_levels():
    assert call_gene("SLCO1B1", {}).phenotype == "Normal Function"
    assert call_gene("SLCO1B1", {"rs4149056": HET}).phenotype == "Decreased Function"
    assert call_gene("SLCO1B1", {"rs4149056": HOM_ALT}).phenotype == "Poor Function"


def test_tpmt_unphased_double_het_is_indeterminate():
    """*3B + *3C het: cis => *3A/*1 (Intermediate), trans => *3B/*3C (Poor)."""
    call = call_gene("TPMT", {"rs1800460": HET, "rs1142345": HET})
    assert call.phenotype == "Indeterminate"
    assert call.phase_ambiguous is True
    assert set(call.candidate_diplotypes) == {"*1/*3A", "*3B/*3C"}


def test_tpmt_phased_cis_resolves_to_star3a():
    cis = {
        "rs1800460": Genotype(1, 0, phased=True),
        "rs1142345": Genotype(1, 0, phased=True),
    }
    call = call_gene("TPMT", cis)
    assert call.diplotype == "*1/*3A"
    assert call.phenotype == "Intermediate Metabolizer"


def test_tpmt_phased_trans_resolves_to_poor():
    trans = {
        "rs1800460": Genotype(1, 0, phased=True),
        "rs1142345": Genotype(0, 1, phased=True),
    }
    call = call_gene("TPMT", trans)
    assert call.diplotype == "*3B/*3C"
    assert call.phenotype == "Poor Metabolizer"


def test_tpmt_both_homozygous_is_star3a_homozygous():
    call = call_gene("TPMT", {"rs1800460": HOM_ALT, "rs1142345": HOM_ALT})
    assert call.diplotype == "*3A/*3A"
    assert call.phenotype == "Poor Metabolizer"


def test_missing_variant_triggers_warning_not_silent_reference():
    call = call_gene("CYP2C19", {"rs4244285": Genotype(None, None)})
    assert any("assumed reference" in w for w in call.warnings)


def test_call_from_diplotype_validates_input():
    assert call_from_diplotype("CYP2C19", "*2/*17").phenotype == "Intermediate Metabolizer"
    with pytest.raises(ValueError):
        call_from_diplotype("CYP2C19", "*2-*17")
    with pytest.raises(ValueError):
        call_from_diplotype("CYP2C19", "*1/*99")


def test_guidance_lookup():
    g = lookup("clopidogrel", "Poor Metabolizer")
    assert g and g.gene == "CYP2C19" and "Avoid" in g.recommendation
    assert lookup("unknown-drug", "Poor Metabolizer") is None
    assert "refer" in lookup("clopidogrel", "Indeterminate").recommendation.lower()


def test_vcf_parsing_end_to_end():
    text = render_demo_vcf(
        {
            "S1": {"rs4244285": "0/1", "rs3918290": "0/1"},
            "S2": {"rs4244285": "1/1"},
            "S3": {"rs1800460": "1|0", "rs1142345": "0|1"},
        }
    )
    res = parse_vcf(text.encode())
    assert set(res.samples) == {"S1", "S2", "S3"}
    assert res.samples["S1"]["rs4244285"].alt_count == 1
    assert res.samples["S3"]["rs1800460"].phased is True
    assert call_gene("CYP2C19", res.samples["S2"]).phenotype == "Poor Metabolizer"
    assert call_gene("TPMT", res.samples["S3"]).diplotype == "*3B/*3C"


def test_vcf_ref_alt_mismatch_is_skipped_with_warning():
    bad = (
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\n"
        "chr10\t1\trs4244285\tA\tG\t.\tPASS\t.\tGT\t0/1\n"
    )
    res = parse_vcf(bad.encode())
    assert res.samples["S1"] == {}
    assert any("differs from expected" in w for w in res.warnings)


def test_vcf_rejects_non_vcf():
    with pytest.raises(VcfError):
        parse_vcf(b"hello world\n")

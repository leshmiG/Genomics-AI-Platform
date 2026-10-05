"""Minimal streaming VCF reader for targeted PGx variants.

It reads only the lines whose ID column matches one of our target rsIDs, so a multi-GB VCF is
processed in constant memory. It does NOT replace a real toolchain (bcftools norm, VEP,
GATK). Production flow: normalise + annotate upstream (see pipelines/nextflow), then hand a
slim VCF to this reader.

Matching is by rsID, not coordinates, to avoid shipping genome-build-specific positions
that could silently be wrong. Real pipelines should also verify chrom:pos against the build.
"""

from __future__ import annotations

import gzip
import io
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .pgx import ALL_TARGET_RSIDS, Genotype


@dataclass
class VcfParseResult:
    samples: dict[str, dict[str, Genotype]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    records_seen: int = 0
    records_used: int = 0


class VcfError(ValueError):
    pass


def _open_text(source: str | Path | bytes | io.IOBase) -> Iterator[str]:
    if isinstance(source, bytes):
        raw = source
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        yield from raw.decode("utf-8", errors="replace").splitlines()
        return
    if isinstance(source, str | Path):
        path = Path(source)
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                yield line.rstrip("\n")
        return
    for line in source:  # file-like
        yield line.decode() if isinstance(line, bytes) else line.rstrip("\n")


def _parse_gt(gt: str) -> Genotype | None:
    gt = gt.split(":")[0]
    phased = "|" in gt
    parts = gt.replace("|", "/").split("/")
    if len(parts) != 2:  # haploid or malformed: not supported for autosomal PGx genes
        return None

    def conv(x: str) -> int | None:
        if x == ".":
            return None
        if x in ("0", "1"):
            return int(x)
        return -1  # other ALT index: handled by caller

    a1, a2 = conv(parts[0]), conv(parts[1])
    if -1 in (a1, a2):
        return None
    return Genotype(a1, a2, phased)


def parse_vcf(source: str | Path | bytes | io.IOBase, max_lines: int | None = None) -> VcfParseResult:
    """Parse target PGx variants. Raises VcfError if the header/columns are unusable."""
    result = VcfParseResult()
    sample_names: list[str] = []
    saw_fileformat = False

    for n, line in enumerate(_open_text(source), start=1):
        if max_lines is not None and n > max_lines:
            result.warnings.append(f"Stopped after {max_lines} lines (max_lines guard).")
            break
        if not line:
            continue
        if line.startswith("##"):
            saw_fileformat |= line.startswith("##fileformat=VCF")
            continue
        if line.startswith("#CHROM"):
            cols = line.lstrip("#").split("\t")
            if len(cols) < 10 or cols[:5] != ["CHROM", "POS", "ID", "REF", "ALT"]:
                raise VcfError("Header must contain CHROM POS ID REF ALT ... FORMAT and >=1 sample")
            sample_names = cols[9:]
            for s in sample_names:
                result.samples[s] = {}
            continue
        if not sample_names:
            raise VcfError("Data line found before #CHROM header")

        result.records_seen += 1
        fields = line.split("\t")
        if len(fields) < 9 + len(sample_names):
            result.warnings.append(f"Line {n}: too few columns, skipped")
            continue
        ids = fields[2].split(";")
        target = next((i for i in ids if i in ALL_TARGET_RSIDS), None)
        if target is None:
            continue

        expected = ALL_TARGET_RSIDS[target]
        ref, alt = fields[3], fields[4]
        if ref != expected.ref or alt != expected.alt:
            result.warnings.append(
                f"{target}: REF/ALT {ref}>{alt} differs from expected {expected.ref}>{expected.alt} "
                "(strand flip, multi-allelic or different build?). Record skipped."
            )
            continue

        fmt = fields[8].split(":")
        if "GT" not in fmt:
            result.warnings.append(f"{target}: no GT in FORMAT, skipped")
            continue
        gt_idx = fmt.index("GT")
        result.records_used += 1
        for s, cell in zip(sample_names, fields[9:], strict=False):
            parts = cell.split(":")
            if gt_idx >= len(parts):
                continue
            g = _parse_gt(parts[gt_idx])
            if g is None:
                result.warnings.append(f"{s}/{target}: unsupported or malformed GT '{parts[gt_idx]}'")
                continue
            result.samples[s][target] = g

    if not sample_names:
        raise VcfError("No #CHROM header found; not a VCF")
    if not saw_fileformat:
        result.warnings.append("Missing ##fileformat header line")
    return result


def render_demo_vcf(samples: dict[str, dict[str, str]]) -> str:
    """Build a small VCF text for tests/demos. samples: {name: {rsid: 'GT'}}; others 0/0."""
    names = list(samples)
    lines = [
        "##fileformat=VCFv4.2",
        "##source=genomics-ai-platform-demo",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t" + "\t".join(names),
    ]
    for i, (rsid, v) in enumerate(sorted(ALL_TARGET_RSIDS.items()), start=1):
        gts = [samples[s].get(rsid, "0/0") for s in names]
        lines.append(f"chrDemo\t{i * 1000}\t{rsid}\t{v.ref}\t{v.alt}\t.\tPASS\t.\tGT\t" + "\t".join(gts))
    return "\n".join(lines) + "\n"

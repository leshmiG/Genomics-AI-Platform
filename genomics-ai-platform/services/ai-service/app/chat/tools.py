"""Deterministic tools the chatbot can invoke. The LLM never computes a clinical call."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.genomics.guidance import SUPPORTED_DRUGS, lookup
from app.genomics.pgx import GENES, call_from_diplotype

_GENE_DIPLO = re.compile(
    r"\b(" + "|".join(GENES) + r")\b[^\n*]{0,30}(\*\w+)\s*/\s*(\*\w+)", re.I
)


@dataclass
class ToolResult:
    name: str
    summary: str
    data: dict


def run_pgx_lookup(message: str) -> list[ToolResult]:
    """If the message contains e.g. 'CYP2C19 *1/*2' translate it and attach drug guidance."""
    results: list[ToolResult] = []
    lowered = message.lower()
    mentioned_drugs = [d for d in SUPPORTED_DRUGS if d in lowered]
    for m in _GENE_DIPLO.finditer(message):
        gene = m.group(1).upper()
        diplotype = f"{m.group(2)}/{m.group(3)}"
        try:
            call = call_from_diplotype(gene, diplotype)
        except ValueError as exc:
            results.append(ToolResult("pgx_lookup", f"Could not interpret {gene} {diplotype}: {exc}", {}))
            continue
        lines = [f"{gene} {call.diplotype} translates to: {call.phenotype}."]
        if call.activity_score is not None:
            lines[0] = lines[0][:-1] + f" (activity score {call.activity_score})."
        guidance = []
        for drug in mentioned_drugs:
            g = lookup(drug, call.phenotype)
            if g and g.gene == gene:
                lines.append(f"For {drug}: {g.recommendation}")
                guidance.append(g.__dict__)
        results.append(
            ToolResult("pgx_lookup", " ".join(lines), {"call": call.as_dict(), "guidance": guidance})
        )
    return results

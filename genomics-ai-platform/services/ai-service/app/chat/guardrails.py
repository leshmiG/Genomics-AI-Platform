"""Input/output guardrails for the chatbot (defence in depth; not a substitute for Bedrock
Guardrails or a clinical safety review).

* PII redaction: emails, phone numbers, long digit strings (e.g. 9-digit national IDs) and MRNs
  are replaced before the text reaches logs, retrieval or an external LLM.
* Prompt-injection heuristics: obvious attempts to override instructions or exfiltrate prompts.
* Personal dosing requests: the bot is educational and must not tell a person what to do with
  their own medication.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("mrn", re.compile(r"\b(?:mrn|medical record(?: number)?)\s*[:#]?\s*[A-Za-z0-9-]{5,}\b", re.I)),
    ("phone", re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")),
    ("long_number", re.compile(r"\b\d{9,}\b")),
]

_INJECTION = [
    re.compile(p, re.I)
    for p in (
        r"ignore (?:all |any |the )?(?:previous|prior|above) (?:instructions|rules|prompts?)",
        r"disregard (?:your|the) (?:instructions|rules|guidelines|system prompt)",
        r"(?:reveal|show|print|repeat) (?:your|the) (?:system )?(?:prompt|instructions)",
        r"you are now (?:in )?(?:developer|dan|jailbreak|unrestricted)",
        r"pretend (?:that )?you (?:have no|are not bound)",
        r"override (?:your )?safety",
    )
]

_PERSONAL_DOSING = [
    re.compile(p, re.I)
    for p in (
        r"\bshould i (?:stop|start|take|increase|reduce|lower|skip|switch|change)\b",
        r"\b(?:my|me) (?:dose|dosage|medication|prescription|tablets?|pills?)\b"
        r".*\b(?:change|stop|increase|reduce|skip)\b",
        r"\b(?:can|may) i (?:stop|skip|double|halve)\b",
        r"\bwhat dose (?:should|do) i\b",
    )
]


@dataclass
class InputCheck:
    text: str  # redacted text
    redactions: list[str] = field(default_factory=list)
    injection: bool = False
    personal_dosing: bool = False


def redact_pii(text: str) -> tuple[str, list[str]]:
    found: list[str] = []
    for label, pat in _PII_PATTERNS:
        if pat.search(text):
            found.append(label)
            text = pat.sub(f"[{label.upper()}_REDACTED]", text)
    return text, found


def check_input(text: str) -> InputCheck:
    redacted, found = redact_pii(text)
    return InputCheck(
        text=redacted,
        redactions=found,
        injection=any(p.search(text) for p in _INJECTION),
        personal_dosing=any(p.search(text) for p in _PERSONAL_DOSING),
    )


REFUSAL_INJECTION = (
    "I can't follow instructions that try to change my rules or reveal my configuration. "
    "I can still answer questions about pharmacogenomics, genomic data formats and this platform."
)
REFUSAL_PERSONAL_DOSING = (
    "I can't advise on starting, stopping or changing your own medication. Please speak to your "
    "prescriber or pharmacist; do not change a prescribed medicine on the basis of a chatbot. "
    "I'm happy to explain general concepts, such as what a metabolizer phenotype means."
)
REFUSAL_NO_EVIDENCE = (
    "I don't have enough information in my knowledge base to answer that reliably, so I won't guess. "
    "Try rephrasing, or ask about pharmacogenomics, genomic file formats, data governance or ML safety."
)
DISCLAIMER = (
    "Educational information only, not medical advice. Clinical decisions need a qualified clinician "
    "and current guidelines."
)

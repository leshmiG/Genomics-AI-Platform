"""A small, dependency-free BM25 (Okapi) index for keyword search.

Dense vectors capture meaning; BM25 captures exact tokens such as gene names, rsIDs and
star alleles (CYP2C19, rs4244285, *17) which embeddings often blur. Hybrid retrieval gets
both.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[A-Za-z0-9*_]+")
_STOP = frozenset(
    (
        "a an and are as at be by for from has have in is it its of on or that the this to was were "
        "with what how do does did why which who whom when where i my me we our you your can could "
        "should would will about tell explain please give mean means"
    ).split()
)


_SUFFIXES = ("ations", "ation", "ings", "ing", "ies", "ied", "ed", "es", "ly", "s")


def stem(token: str) -> str:
    """Very light suffix stripping (dosed/dosing/doses -> dos). Skips gene names, rsIDs, alleles."""
    if len(token) <= 4 or any(ch.isdigit() or ch == "*" for ch in token):
        return token
    for suf in _SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 3:
            return token[: -len(suf)]
    return token


def tokenize(text: str) -> list[str]:
    out = []
    for m in _TOKEN.finditer(text):
        t = m.group(0).lower()
        if t not in _STOP:
            out.append(stem(t))
    return out


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tokens = [tokenize(d) for d in docs]
        self.doc_len = [len(t) for t in self.tokens]
        self.avg_len = (sum(self.doc_len) / len(docs)) if docs else 0.0
        self.tf = [Counter(t) for t in self.tokens]
        df: Counter = Counter()
        for t in self.tf:
            df.update(t.keys())
        n = len(docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    def coverage(self, query: str) -> list[float]:
        """IDF-weighted fraction of the query's content words found in each document.

        Words absent from the whole corpus get the maximum IDF, so a query made of unknown
        words (off-topic) scores near zero for every document. Unlike raw BM25, the result is
        bounded in [0, 1], which makes it usable as a fixed "is this answerable?" threshold.
        """
        q = list(dict.fromkeys(tokenize(query)))
        if not q:
            return [0.0] * len(self.tf)
        max_idf = max(self.idf.values(), default=1.0)
        weights = {w: self.idf.get(w, max_idf) for w in q}
        total = sum(weights.values())
        return [sum(wt for w, wt in weights.items() if w in tf) / total for tf in self.tf]

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            norm = self.k1 * (1 - self.b + self.b * self.doc_len[i] / (self.avg_len or 1.0))
            for w in q:
                f = tf.get(w, 0)
                if f:
                    s += self.idf.get(w, 0.0) * f * (self.k1 + 1) / (f + norm)
            out.append(s)
        return out

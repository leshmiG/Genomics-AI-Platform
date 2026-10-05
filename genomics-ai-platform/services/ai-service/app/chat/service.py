"""Chat orchestration: guardrails -> deterministic tools -> hybrid retrieval -> grounded answer."""

from __future__ import annotations

import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from app.core.config import Settings
from app.rag.retriever import HybridRetriever

from . import guardrails as gr
from .llm import LLM
from .tools import run_pgx_lookup

_CITE = re.compile(r"\[(\d+)\]")
_CLINICAL = re.compile(
    r"\b(drug|dose|dosing|dosage|clopidogrel|simvastatin|warfarin|azathioprine|fluorouracil|metaboli[sz]er|"
    r"therapy|medication|prescri)\w*", re.I)


@dataclass
class ChatResponse:
    answer: str
    grounded: bool
    citations: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    session_id: str = ""

    def as_dict(self) -> dict:
        return self.__dict__.copy()


class SessionStore:
    """Bounded in-memory sessions with TTL. For multiple replicas use Redis/DynamoDB instead."""

    def __init__(self, max_sessions: int = 1000, ttl_seconds: int = 1800, max_turns: int = 6):
        self._data: OrderedDict[str, tuple[float, list[tuple[str, str]]]] = OrderedDict()
        self.max_sessions, self.ttl, self.max_turns = max_sessions, ttl_seconds, max_turns

    def history(self, sid: str) -> list[tuple[str, str]]:
        self._evict()
        entry = self._data.get(sid)
        return list(entry[1]) if entry else []

    def append(self, sid: str, question: str, answer: str) -> None:
        _, turns = self._data.get(sid, (0.0, []))
        turns = (turns + [(question, answer)])[-self.max_turns:]
        self._data[sid] = (time.time(), turns)
        self._data.move_to_end(sid)
        self._evict()

    def _evict(self) -> None:
        now = time.time()
        for sid in [s for s, (t, _) in self._data.items() if now - t > self.ttl]:
            del self._data[sid]
        while len(self._data) > self.max_sessions:
            self._data.popitem(last=False)


class ChatService:
    def __init__(self, retriever: HybridRetriever, llm: LLM, settings: Settings):
        self.retriever, self.llm, self.settings = retriever, llm, settings
        self.sessions = SessionStore()

    def _grounded(self, hits) -> bool:
        if not hits:
            return False
        best_cov = max(h.coverage for h in hits)
        best_dense = max(h.dense_score for h in hits)
        return best_cov >= self.settings.rag_min_coverage or best_dense >= self.settings.rag_min_dense

    def answer(self, message: str, session_id: str = "default") -> ChatResponse:
        chk = gr.check_input(message)
        flags = [f"redacted:{r}" for r in chk.redactions]

        if chk.injection:
            return ChatResponse(gr.REFUSAL_INJECTION, False, flags=flags + ["prompt_injection"], session_id=session_id)
        if chk.personal_dosing:
            return ChatResponse(gr.REFUSAL_PERSONAL_DOSING, False, flags=flags + ["personal_dosing"],
                                session_id=session_id)

        # The retrieval query includes the last user turn so follow-ups ("and for TPMT?") work.
        history = self.sessions.history(session_id)
        retrieval_query = chk.text if not history else f"{history[-1][0]} {chk.text}"

        tool_results = run_pgx_lookup(chk.text)
        tool_notes = [t.summary for t in tool_results]

        hits = self.retriever.search(retrieval_query, self.settings.rag_top_k)
        # Rank with conversation context, but decide "is this answerable?" from the CURRENT
        # message alone. Otherwise an off-topic question could ride on the previous turn's
        # keywords and slip past the gate.
        gate_hits = self.retriever.search(chk.text, self.settings.rag_top_k) if history else hits
        grounded = self._grounded(gate_hits)

        if not grounded and not tool_results:
            return ChatResponse(gr.REFUSAL_NO_EVIDENCE, False, flags=flags + ["no_evidence"], session_id=session_id)

        used_hits = hits if grounded else []
        answer = self.llm.generate(chk.text, used_hits, tool_notes, history).strip()
        if not answer:
            return ChatResponse(gr.REFUSAL_NO_EVIDENCE, False, flags=flags + ["empty_generation"],
                                session_id=session_id)

        # Keep only citations the model actually referenced; if none, list the sources used.
        cited = sorted({int(n) for n in _CITE.findall(answer) if 0 < int(n) <= len(used_hits)})
        if used_hits and not cited:
            flags.append("no_inline_citations")
            cited = list(range(1, len(used_hits) + 1))
        citations = [
            {"ref": n, "source": used_hits[n - 1].chunk.source, "heading": used_hits[n - 1].chunk.heading,
             "chunk_id": used_hits[n - 1].chunk.id}
            for n in cited
        ]

        if _CLINICAL.search(chk.text) or _CLINICAL.search(answer) or tool_results:
            answer = f"{answer}\n\n{gr.DISCLAIMER}"

        self.sessions.append(session_id, chk.text, answer)
        return ChatResponse(
            answer=answer, grounded=bool(used_hits) or bool(tool_results), citations=citations,
            tools=[{"name": t.name, "summary": t.summary, "data": t.data} for t in tool_results],
            flags=flags, session_id=session_id,
        )

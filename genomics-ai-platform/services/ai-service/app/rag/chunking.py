"""Heading-aware chunking with overlap.

Splitting on markdown headings keeps each chunk about one idea and lets us store the heading
as metadata (used for citations). Long sections are split on paragraph/sentence boundaries
with a character overlap so facts at the boundary are not lost.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chunk:
    id: str
    source: str
    heading: str
    text: str

    def as_dict(self) -> dict:
        return {"id": self.id, "source": self.source, "heading": self.heading, "text": self.text}


_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_long(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sentences = _SENT_SPLIT.split(text)
    chunks, cur = [], ""
    for s in sentences:
        if cur and len(cur) + len(s) + 1 > max_chars:
            chunks.append(cur.strip())
            tail = cur[-overlap:] if overlap else ""
            # start next chunk at a word boundary inside the overlap window
            tail = tail[tail.find(" ") + 1:] if " " in tail else tail
            cur = tail + " " + s
        else:
            cur = f"{cur} {s}".strip()
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def chunk_markdown(text: str, source: str, max_chars: int = 900, overlap: int = 150) -> list[Chunk]:
    sections: list[tuple[str, list[str]]] = []
    title = Path(source).stem.replace("_", " ")
    heading, buf = title, []
    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            if "".join(buf).strip():
                sections.append((heading, buf))
            heading, buf = m.group(2).strip(), []
        else:
            buf.append(line)
    if "".join(buf).strip():
        sections.append((heading, buf))

    out: list[Chunk] = []
    for heading, lines in sections:
        body = re.sub(r"\n{2,}", "\n\n", "\n".join(lines).strip())
        for i, piece in enumerate(_split_long(body, max_chars, overlap)):
            if len(piece) < 40:
                continue
            out.append(Chunk(id=f"{Path(source).stem}#{len(out)}", source=Path(source).name,
                             heading=heading, text=f"{heading}. {piece}" if i == 0 else piece))
    return out


def load_directory(path: str | Path, max_chars: int = 900, overlap: int = 150) -> list[Chunk]:
    chunks: list[Chunk] = []
    for f in sorted(Path(path).glob("*.md")):
        chunks.extend(chunk_markdown(f.read_text(encoding="utf-8"), f.name, max_chars, overlap))
    return chunks

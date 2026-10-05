"""Request/response models. Validation here is the first line of defence against bad input."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.genomics.pgx import GENES
from app.ml.cohort import PHENOTYPES

GeneName = Literal[tuple(GENES)]  # type: ignore[valid-type]
Phenotype = Literal[tuple(PHENOTYPES)]  # type: ignore[valid-type]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiplotypeRequest(Strict):
    gene: GeneName
    diplotype: str = Field(pattern=r"^\s*\*\w+\s*/\s*\*\w+\s*$", max_length=32)
    drugs: list[str] = Field(default_factory=list, max_length=10)


class PredictRequest(Strict):
    age: float = Field(ge=18, le=110)
    bmi: float = Field(ge=10, le=70)
    egfr: float = Field(ge=5, le=200)
    ppi_use: Literal[0, 1]
    diabetes: Literal[0, 1]
    smoker: Literal[0, 1]
    cyp2c19_phenotype: Phenotype


class DriftRequest(Strict):
    rows: list[PredictRequest] = Field(min_length=1, max_length=5000)


class SearchRequest(Strict):
    query: str = Field(min_length=2, max_length=500)
    k: int = Field(default=4, ge=1, le=10)


class ChatRequest(Strict):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(default="default", pattern=r"^[A-Za-z0-9_-]{1,64}$")

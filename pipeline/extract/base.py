from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from schema.models import Chunk


@dataclass
class RawCompany:
    surface: str           # as it appears in text
    canonical_id: str = ""  # filled by resolver


@dataclass
class RawRelation:
    source_surface: str
    target_surface: str
    relation_type: str
    what_flows: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    confidence: float = 1.0
    evidence: str = ""
    source_chunk_ids: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    companies: list[RawCompany]
    relations: list[RawRelation]


@runtime_checkable
class Extractor(Protocol):
    def extract(self, chunks: list[Chunk]) -> ExtractionResult:
        ...

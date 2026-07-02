from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Company:
    canonical_id: str          # e.g. "NVIDIA"
    display_name: str
    aliases: list[str] = field(default_factory=list)
    mention_count: int = 0
    ticker: Optional[str] = None


@dataclass
class RelationEdge:
    source: str                  # canonical_id
    target: str                  # canonical_id
    relation_type: str           # from RelationTypes
    date: str                    # YYYYMMDD week key
    what_flows: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_family: Optional[str] = None
    mention_count: int = 1
    confidence: float = 1.0
    evidence: str = ""
    source_chunk_ids: list[str] = field(default_factory=list)
    # Pass-2 fields
    contract_scale_norm: Optional[float] = None
    weight: Optional[float] = None


@dataclass
class Chunk:
    chunk_id: str        # e.g. "20251019#市场表现"
    week: str            # YYYYMMDD
    section_title: str
    text: str

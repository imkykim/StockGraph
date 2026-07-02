"""
Edge building:
- Apply entity resolver to raw relations
- Fold CUSTOMER_OF → SUPPLIES (swap source/target)
- Build RelationEdge objects ready for merge
"""
from __future__ import annotations
import math
from typing import Optional

from schema.models import RelationEdge
from schema.relation_types import RelationTypes, SYMMETRIC_RELATIONS, FOLD_TO_SUPPLIES
from pipeline.extract.base import ExtractionResult, RawRelation
from pipeline.standardize.entity_resolver import EntityResolver

# Unit family mapping for weight normalization
UNIT_FAMILY: dict[str, str] = {
    "GW": "power", "MW": "power", "TW": "power",
    "WPM": "throughput", "万WPM": "throughput", "KWPM": "throughput",
    "亿USD": "money", "亿RMB": "money", "M USD": "money", "B USD": "money",
    "M": "volume", "K": "volume", "万": "volume",
}

_BASE_WEIGHT = 0.1


def _fold_direction(rel: RawRelation) -> RawRelation:
    """CUSTOMER_OF(A,B) → SUPPLIES(B,A). Mutates a copy."""
    if rel.relation_type in FOLD_TO_SUPPLIES:
        return RawRelation(
            source_surface=rel.target_surface,
            target_surface=rel.source_surface,
            relation_type=RelationTypes.SUPPLIES,
            what_flows=rel.what_flows,
            quantity=rel.quantity,
            unit=rel.unit,
            confidence=rel.confidence,
            evidence=rel.evidence,
            source_chunk_ids=list(rel.source_chunk_ids),
        )
    return rel


def build_edges(
    result: ExtractionResult,
    resolver: EntityResolver,
) -> list[RelationEdge]:
    """Convert ExtractionResult → list of RelationEdge (pre-merge, pre-weight)."""
    edges: list[RelationEdge] = []

    for raw in result.relations:
        raw = _fold_direction(raw)

        src = resolver.resolve(raw.source_surface)
        tgt = resolver.resolve(raw.target_surface)

        unit = raw.unit
        unit_family = UNIT_FAMILY.get(unit, "other") if unit else None

        edges.append(RelationEdge(
            source=src,
            target=tgt,
            relation_type=raw.relation_type,
            date="",          # filled by caller who knows the chunk's week
            what_flows=raw.what_flows,
            quantity=raw.quantity,
            unit=unit,
            unit_family=unit_family,
            mention_count=1,
            confidence=raw.confidence,
            evidence=raw.evidence,
            source_chunk_ids=list(raw.source_chunk_ids),
        ))
    return edges


def build_edges_from_chunks(
    result: ExtractionResult,
    chunk_week_map: dict[str, str],
    resolver: EntityResolver,
) -> list[RelationEdge]:
    """Build edges AND fill date from chunk_id → week mapping."""
    edges: list[RelationEdge] = []
    for raw in result.relations:
        raw = _fold_direction(raw)
        src = resolver.resolve(raw.source_surface)
        tgt = resolver.resolve(raw.target_surface)

        # Determine week from first source_chunk_id
        week = ""
        for cid in raw.source_chunk_ids:
            if cid in chunk_week_map:
                week = chunk_week_map[cid]
                break

        unit = raw.unit
        unit_family = UNIT_FAMILY.get(unit, "other") if unit else None

        edges.append(RelationEdge(
            source=src,
            target=tgt,
            relation_type=raw.relation_type,
            date=week,
            what_flows=raw.what_flows,
            quantity=raw.quantity,
            unit=unit,
            unit_family=unit_family,
            mention_count=1,
            confidence=raw.confidence,
            evidence=raw.evidence,
            source_chunk_ids=list(raw.source_chunk_ids),
        ))
    return edges

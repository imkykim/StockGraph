"""
Merge edges and compute 2-pass weights.

Pass 1 (local): collect raw quantity/unit, set mention_count.
Pass 2 (global): log1p + min-max normalize within each unit_family,
                 then compute final weight.
"""
from __future__ import annotations
import math
from collections import defaultdict
from typing import Optional

from schema.models import RelationEdge
from schema.relation_types import SYMMETRIC_RELATIONS

_BASE = 0.1


def _edge_key(edge: RelationEdge):
    """Merge key: asymmetric or frozenset-based for symmetric relations."""
    if edge.relation_type in SYMMETRIC_RELATIONS:
        return (frozenset({edge.source, edge.target}), edge.relation_type, edge.date)
    return (edge.source, edge.target, edge.relation_type, edge.date)


def merge_edges(edges: list[RelationEdge]) -> list[RelationEdge]:
    """
    Merge edges that share the same key.
    - mention_count sums
    - source_chunk_ids union
    - confidence takes max
    - quantity/unit kept from first non-None
    """
    buckets: dict = {}

    for edge in edges:
        key = _edge_key(edge)
        if key not in buckets:
            buckets[key] = edge
            # ensure list is mutable
            buckets[key].source_chunk_ids = list(edge.source_chunk_ids)
        else:
            existing = buckets[key]
            existing.mention_count += edge.mention_count
            existing.source_chunk_ids = list(
                set(existing.source_chunk_ids) | set(edge.source_chunk_ids)
            )
            existing.confidence = max(existing.confidence, edge.confidence)
            if existing.quantity is None and edge.quantity is not None:
                existing.quantity = edge.quantity
                existing.unit = edge.unit
                existing.unit_family = edge.unit_family
            if existing.what_flows is None and edge.what_flows is not None:
                existing.what_flows = edge.what_flows

    return list(buckets.values())


def suppress_co_mention(edges: list[RelationEdge]) -> list[RelationEdge]:
    """
    Remove CO_MENTION edges for pairs that already have a typed edge.
    Must be called AFTER merge.
    """
    typed_pairs: set[frozenset] = set()
    for e in edges:
        if e.relation_type != "CO_MENTION":
            typed_pairs.add(frozenset({e.source, e.target}))

    return [
        e for e in edges
        if not (e.relation_type == "CO_MENTION"
                and frozenset({e.source, e.target}) in typed_pairs)
    ]


def compute_weights(edges: list[RelationEdge]) -> list[RelationEdge]:
    """
    2-pass weight:
    Pass 1: log1p(quantity) per unit_family bucket.
    Pass 2: min-max normalize within family → contract_scale_norm.
    Final: weight = (mention_count / mc_max) * max(contract_scale_norm, BASE).
    """
    # Collect log-scaled quantities per family
    family_vals: dict[str, list[float]] = defaultdict(list)
    for e in edges:
        if e.quantity is not None and e.unit_family:
            family_vals[e.unit_family].append(math.log1p(e.quantity))

    family_min: dict[str, float] = {}
    family_max: dict[str, float] = {}
    for fam, vals in family_vals.items():
        family_min[fam] = min(vals)
        family_max[fam] = max(vals)

    mc_max = max((e.mention_count for e in edges), default=1)

    for e in edges:
        if e.quantity is not None and e.unit_family and e.unit_family in family_min:
            lo = family_min[e.unit_family]
            hi = family_max[e.unit_family]
            log_val = math.log1p(e.quantity)
            norm = (log_val - lo) / (hi - lo) if hi > lo else 1.0
            e.contract_scale_norm = round(norm, 4)
        else:
            e.contract_scale_norm = None

        csn = e.contract_scale_norm if e.contract_scale_norm is not None else 0.0
        mc_ratio = e.mention_count / mc_max
        e.weight = round(mc_ratio * max(csn, _BASE), 4)

    return edges

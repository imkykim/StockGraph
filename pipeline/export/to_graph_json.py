"""Export nodes and edges to graph.json."""
from __future__ import annotations
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from schema.models import RelationEdge, Company
from pipeline.standardize.node_classifier import classify


def build_node_list(
    edges: list[RelationEdge],
    extra_companies: Optional[list[Company]] = None,
) -> list[dict]:
    """
    Derive node list from edges.
    mention_count = number of edges the node participates in.
    """
    mention_counts: dict[str, int] = defaultdict(int)
    for e in edges:
        mention_counts[e.source] += e.mention_count
        mention_counts[e.target] += e.mention_count

    # Add extra companies that may have 0 edges
    if extra_companies:
        for c in extra_companies:
            if c.canonical_id not in mention_counts:
                mention_counts[c.canonical_id] = c.mention_count

    nodes = []
    for canonical_id, mc in sorted(mention_counts.items()):
        nodes.append({
            "id": canonical_id,
            "label": canonical_id,
            "mention_count": mc,
            "type": classify(canonical_id),
        })
    return nodes


def edges_to_dicts(edges: list[RelationEdge]) -> list[dict]:
    out = []
    for e in edges:
        out.append({
            "source": e.source,
            "target": e.target,
            "relation_type": e.relation_type,
            "date": e.date,
            "what_flows": e.what_flows,
            "quantity": e.quantity,
            "unit": e.unit,
            "unit_family": e.unit_family,
            "mention_count": e.mention_count,
            "confidence": e.confidence,
            "weight": e.weight,
            "contract_scale_norm": e.contract_scale_norm,
            "evidence": e.evidence,
            "source_chunk_ids": e.source_chunk_ids,
        })
    return out


def export_graph(
    edges: list[RelationEdge],
    output_path: str,
    extra_companies: Optional[list[Company]] = None,
) -> None:
    nodes = build_node_list(edges, extra_companies)
    edge_dicts = edges_to_dicts(edges)
    graph = {"nodes": nodes, "edges": edge_dicts}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    print(f"Exported {len(nodes)} nodes, {len(edge_dicts)} edges → {output_path}")

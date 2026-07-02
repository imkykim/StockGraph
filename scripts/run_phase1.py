#!/usr/bin/env python3
"""
ChainGraph Phase 1 end-to-end pipeline.

Usage:
  python scripts/run_phase1.py --input data/examples/Tech周报_讨论.docx \\
                                --weeks 5 --extractor seed
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.ingest.docx_adapter import load_chunks
from pipeline.standardize.entity_resolver import EntityResolver
from pipeline.graph.edge_builder import build_edges_from_chunks
from pipeline.graph.merge import merge_edges, suppress_co_mention, compute_weights
from pipeline.export.to_graph_json import export_graph


def get_extractor(name: str):
    if name == "seed":
        from pipeline.extract.seed_extractor import SeedExtractor
        return SeedExtractor()
    elif name == "llm":
        from pipeline.extract.llm_extractor import LLMExtractor
        return LLMExtractor()
    else:
        print(f"Unknown extractor '{name}'. Use 'seed' or 'llm'.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="ChainGraph Phase 1 pipeline")
    parser.add_argument("--input", required=True, help="Path to docx file")
    parser.add_argument("--weeks", type=int, default=5, help="Number of weeks to process")
    parser.add_argument("--extractor", default="seed", choices=["seed", "llm"])
    parser.add_argument("--output", default="data/output/graph.json")
    args = parser.parse_args()

    print(f"[1/5] Loading chunks from {args.input} (top {args.weeks} weeks)...")
    chunks = load_chunks(args.input, weeks=args.weeks)
    print(f"      {len(chunks)} chunks, {len(set(c.week for c in chunks))} weeks")

    chunk_week_map = {c.chunk_id: c.week for c in chunks}

    print(f"[2/5] Extracting with '{args.extractor}' extractor...")
    extractor = get_extractor(args.extractor)
    result = extractor.extract(chunks)
    print(f"      {len(result.companies)} company surfaces, {len(result.relations)} raw relations")

    print("[3/5] Resolving entities...")
    resolver = EntityResolver()
    edges = build_edges_from_chunks(result, chunk_week_map, resolver)
    if resolver.merge_candidates:
        print(f"      Unresolved (new nodes): {sorted(resolver.merge_candidates)}")

    print("[4/5] Merging edges + computing weights...")
    edges = merge_edges(edges)
    edges = suppress_co_mention(edges)
    edges = compute_weights(edges)
    print(f"      {len(edges)} edges after merge/suppress")

    print(f"[5/5] Exporting to {args.output}...")
    export_graph(edges, args.output)
    print("Done.")


if __name__ == "__main__":
    main()

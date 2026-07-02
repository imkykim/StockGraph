#!/usr/bin/env python3
"""
ChainGraph Phase 1 Definition of Done verification.
Checks graph.json against all DoD criteria.
"""
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GRAPH_PATH = "data/output/graph.json"

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"


def load_graph(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    msg = f"{status} {label}"
    if detail:
        msg += f"\n       {detail}"
    print(msg)
    return condition


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else GRAPH_PATH
    if not Path(path).exists():
        print(f"{FAIL} graph.json not found at {path}")
        print("  Run: python scripts/run_phase1.py --input data/examples/Tech周报_讨论.docx --extractor seed")
        sys.exit(1)

    g = load_graph(path)
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    node_ids = {n["id"] for n in nodes}
    failures = 0

    # ── 1. Basic structure ─────────────────────────────────────────────────
    print("\n── Basic Structure ──")
    ok = check("graph.json has nodes and edges",
               len(nodes) > 0 and len(edges) > 0,
               f"{len(nodes)} nodes, {len(edges)} edges")
    failures += not ok

    required_fields = {"source", "target", "relation_type", "date", "weight"}
    bad = [e for e in edges if not required_fields.issubset(e.keys())
           or e.get("weight") is None]
    ok = check("All edges have source/target/relation_type/date/weight filled",
               len(bad) == 0,
               f"{len(bad)} edges missing fields" if bad else "")
    failures += not ok

    # ── 2. DoD minimum relations ────────────────────────────────────────────
    print("\n── DoD Minimum Relations ──")

    def find_edge(src, tgt, rel, **kwargs):
        for e in edges:
            if e["source"] == src and e["target"] == tgt and e["relation_type"] == rel:
                match = True
                for k, v in kwargs.items():
                    if k == "quantity" and v is not None:
                        if e.get("quantity") is None or abs(e["quantity"] - v) > 1:
                            match = False
                    elif k == "unit" and v is not None:
                        if e.get("unit") != v:
                            match = False
                if match:
                    return e
        return None

    dod_checks = [
        ("Innolight → NVIDIA [SUPPLIES, 광모듈]",
         find_edge("Innolight", "NVIDIA", "SUPPLIES")),
        ("Source Photonics → Google [SUPPLIES, 광모듈]",
         find_edge("Source Photonics", "Google", "SUPPLIES")),
        ("OpenAI → Broadcom [CONTRACTS_WITH, 10 GW]",
         find_edge("OpenAI", "Broadcom", "CONTRACTS_WITH", quantity=10.0, unit="GW")),
        ("OpenAI → AMD [CONTRACTS_WITH, 6 GW]",
         find_edge("OpenAI", "AMD", "CONTRACTS_WITH", quantity=6.0, unit="GW")),
        ("OpenAI → Samsung [CONTRACTS_WITH, 900000 WPM DRAM]",
         find_edge("OpenAI", "Samsung", "CONTRACTS_WITH", quantity=900000.0, unit="WPM")),
        ("OpenAI → SK Hynix [CONTRACTS_WITH, DRAM]",
         find_edge("OpenAI", "SK Hynix", "CONTRACTS_WITH")),
        ("SK Hynix → NVIDIA [SUPPLIES, HBM]",
         find_edge("SK Hynix", "NVIDIA", "SUPPLIES")),
        ("TSMC → NVIDIA [SUPPLIES, CoWoS/foundry]",
         find_edge("TSMC", "NVIDIA", "SUPPLIES")),
        ("Foxconn → NVIDIA [SUPPLIES, AI server/rack]",
         find_edge("Foxconn", "NVIDIA", "SUPPLIES")),
    ]

    for label, result in dod_checks:
        ok = check(label, result is not None,
                   f"evidence: {result.get('evidence', '')[:80]}" if result else "NOT FOUND")
        failures += not ok

    # ── 3. Entity merging ───────────────────────────────────────────────────
    print("\n── Entity Merging (alias → single canonical node) ──")

    # Check that non-canonical alias surfaces do NOT appear as separate nodes
    alias_groups = [
        ("旭창/Innolight → canonical=Innolight", ["旭창", "旭创"]),
        ("海力士/Hynix → canonical=SK Hynix", ["海力士", "Hynix"]),
        ("OAI/OpenAI → canonical=OpenAI", ["OAI", "Altman"]),
        ("AVGO/Broadcom → canonical=Broadcom", ["AVGO"]),
        ("TSM/TSMC → canonical=TSMC", ["TSM", "台积電", "台积电"]),
        ("三星/Samsung → canonical=Samsung", ["三星"]),
    ]

    for label, bad_aliases in alias_groups:
        leaked = [a for a in bad_aliases if a in node_ids]
        ok = check(f"No alias nodes for {label}",
                   len(leaked) == 0,
                   f"Leaked aliases: {leaked}" if leaked else "")
        failures += not ok

    # ── 4. No CUSTOMER_OF edges ─────────────────────────────────────────────
    print("\n── Edge Type Constraints ──")

    customer_of = [e for e in edges if e["relation_type"] == "CUSTOMER_OF"]
    ok = check("CUSTOMER_OF count = 0 (all folded to SUPPLIES)",
               len(customer_of) == 0,
               f"Found {len(customer_of)} CUSTOMER_OF edges" if customer_of else "")
    failures += not ok

    # ── 5. Weight range [0, 1] ──────────────────────────────────────────────
    print("\n── Weight Validity ──")

    bad_weights = [e for e in edges if e.get("weight") is None
                   or not (0 <= e["weight"] <= 1)]
    ok = check("All weight ∈ [0, 1]",
               len(bad_weights) == 0,
               f"Bad weights: {[(e['source'], e['target'], e['weight']) for e in bad_weights]}"
               if bad_weights else "")
    failures += not ok

    # ── 6. CO_MENTION suppression ───────────────────────────────────────────
    print("\n── CO_MENTION Suppression ──")

    typed_pairs: set = set()
    for e in edges:
        if e["relation_type"] != "CO_MENTION":
            typed_pairs.add((e["source"], e["target"]))
            typed_pairs.add((e["target"], e["source"]))

    co_mention_violations = [
        e for e in edges
        if e["relation_type"] == "CO_MENTION"
        and (e["source"], e["target"]) in typed_pairs
    ]
    ok = check("No CO_MENTION on pairs that have typed edges",
               len(co_mention_violations) == 0,
               f"Violations: {[(e['source'], e['target']) for e in co_mention_violations]}"
               if co_mention_violations else "")
    failures += not ok

    # ── Summary ─────────────────────────────────────────────────────────────
    print(f"\n{'='*50}")
    total = len(dod_checks) + 9
    if failures == 0:
        print(f"\033[92mAll checks passed!\033[0m ({total - failures}/{total})")
    else:
        print(f"\033[91m{failures} check(s) FAILED\033[0m ({total - failures}/{total} passed)")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()

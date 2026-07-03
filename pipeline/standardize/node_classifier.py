"""
Node type classifier — deterministic, keyword-based.

The LLM extractor over-extracts: it emits sector/product terms (存储, 光, DRAM),
regions (中国区), and institutions (美国政府) as if they were companies. Rather
than dropping them (which loses context like "AI 挤占存储 needs"), we tag each
node with a `node_type` so the viz can color/filter them apart from real firms.

Matching is EXACT on the canonical id (default COMPANY). This is intentional:
real company names often contain a sector char (e.g. 长光辰芯 contains 光, 长飞),
so substring matching would misclassify them. Only a bare "光" is a SECTOR.
"""
from __future__ import annotations

COMPANY = "COMPANY"
SECTOR = "SECTOR"
REGION = "REGION"
INSTITUTION = "INSTITUTION"

# Industry / product / technology segments — not corporate actors.
SECTOR_TERMS: set[str] = {
    "光", "存储", "存储器", "内存",
    "DRAM", "HBM", "NAND", "NOR", "SSD",
    "CoWoS", "先进封装", "封装", "先进制程", "晶圆", "Wafer",
    "光模块", "光通信", "光芯片", "光源", "硅光",
    "AI", "算力", "云", "云计算", "服务器", "AI服务器",
    "CSP", "芯片", "半导体", "PCB", "铜连接", "液冷",
    "电池", "储能", "机器人", "人形机器人", "自动驾驶",
}

# Geographies — not corporate actors.
REGION_TERMS: set[str] = {
    "中国", "中国区", "中国大陆", "大陆", "美国", "韩国", "日本",
    "台湾", "欧洲", "东南亚", "印度", "全球", "海外",
}

# Governments / public bodies — not corporate actors.
INSTITUTION_TERMS: set[str] = {
    "美国政府", "政府", "中国政府", "商务部", "美国商务部",
    "白宫", "国会", "监管机构", "海关",
}


def classify(canonical_id: str) -> str:
    """Return the node type for a canonical id. Defaults to COMPANY."""
    cid = canonical_id.strip()
    if cid in INSTITUTION_TERMS:
        return INSTITUTION
    if cid in REGION_TERMS:
        return REGION
    if cid in SECTOR_TERMS:
        return SECTOR
    return COMPANY

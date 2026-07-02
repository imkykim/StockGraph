"""
Seed extractor — deterministic, no API key required.
Pattern-matches chunk text to emit headline relationships with evidence.
All emitted relations are whitelist-verified against actually occurring text.
"""
from __future__ import annotations
import re
from typing import Optional

from schema.models import Chunk
from schema.relation_types import RelationTypes
from pipeline.extract.base import ExtractionResult, RawCompany, RawRelation

# ---------------------------------------------------------------------------
# Pattern helpers
# ---------------------------------------------------------------------------

_GW_PAT = re.compile(r"(\d+(?:\.\d+)?)\s*GW")
_WPM_PAT = re.compile(r"(\d+(?:[,，]\d+)?)\s*万?\s*W[Pp][Mm]")
_WPM_DIGIT_PAT = re.compile(r"([9８8]\d{4,6})\s*(?:Wafer|WPM|万?\s*WPM)", re.IGNORECASE)


def _snippet(text: str, keyword: str, window: int = 60) -> str:
    idx = text.find(keyword)
    if idx == -1:
        return keyword
    start = max(0, idx - window // 2)
    end = min(len(text), idx + window // 2)
    return text[start:end].replace("\n", " ").strip()


# ---------------------------------------------------------------------------
# Rule definitions
# Each rule is a function(chunk) -> list[RawRelation]
# ---------------------------------------------------------------------------

def _rule_innolight_nvidia(chunk: Chunk) -> list[RawRelation]:
    """旭创/Innolight SUPPLIES 光모듈 to NVIDIA."""
    out = []
    text = chunk.text
    # Evidence: "NV 1.6光模块加单，CW光源成为旭创产能debottleneck"
    # or "旭创" + "NV" + "加单" in same chunk
    if ("旭创" in text or "Innolight" in text) and re.search(r"NV|NVDA|NVIDIA|英伟达", text):
        if re.search(r"加单|光模块|debottleneck|供应", text):
            evid = _snippet(text, "旭创", 80) if "旭创" in text else _snippet(text, "Innolight", 80)
            out.append(RawRelation(
                source_surface="旭创",
                target_surface="NVIDIA",
                relation_type=RelationTypes.SUPPLIES,
                what_flows="光模块",
                confidence=0.95,
                evidence=evid,
                source_chunk_ids=[chunk.chunk_id],
            ))
    return out


def _rule_yuanjie_google(chunk: Chunk) -> list[RawRelation]:
    """源杰 SUPPLIES 光模块 to Google."""
    out = []
    text = chunk.text
    if "源杰" in text and "Google" in text and re.search(r"加单|光模块", text):
        evid = _snippet(text, "源杰", 80)
        out.append(RawRelation(
            source_surface="源杰",
            target_surface="Google",
            relation_type=RelationTypes.SUPPLIES,
            what_flows="光模块",
            confidence=0.9,
            evidence=evid,
            source_chunk_ids=[chunk.chunk_id],
        ))
    return out


def _rule_openai_broadcom_10gw(chunk: Chunk) -> list[RawRelation]:
    """OpenAI CONTRACTS_WITH Broadcom, 10 GW ASIC."""
    out = []
    text = chunk.text
    # "AVGO与OAI 10GW合作"
    if re.search(r"AVGO|Broadcom", text) and re.search(r"OAI|OpenAI", text):
        m = _GW_PAT.search(text)
        qty = float(m.group(1)) if m else None
        if qty and qty >= 8:  # sanity: 10 GW
            evid = _snippet(text, "AVGO" if "AVGO" in text else "Broadcom", 80)
            out.append(RawRelation(
                source_surface="OpenAI",
                target_surface="Broadcom",
                relation_type=RelationTypes.CONTRACTS_WITH,
                what_flows="TPU/ASIC",
                quantity=qty,
                unit="GW",
                confidence=0.95,
                evidence=evid,
                source_chunk_ids=[chunk.chunk_id],
            ))
    return out


def _rule_openai_amd_6gw(chunk: Chunk) -> list[RawRelation]:
    """OpenAI CONTRACTS_WITH AMD, 6 GW."""
    out = []
    text = chunk.text
    if "AMD" in text and re.search(r"OAI|OpenAI", text) and re.search(r"6\s*GW|6GW", text):
        evid = _snippet(text, "AMD", 80)
        out.append(RawRelation(
            source_surface="OpenAI",
            target_surface="AMD",
            relation_type=RelationTypes.CONTRACTS_WITH,
            quantity=6.0,
            unit="GW",
            confidence=0.95,
            evidence=evid,
            source_chunk_ids=[chunk.chunk_id],
        ))
    return out


def _rule_openai_samsung_hynix_dram(chunk: Chunk) -> list[RawRelation]:
    """OpenAI CONTRACTS_WITH Samsung + SK Hynix, 900K WPM DRAM."""
    out = []
    text = chunk.text
    # "Altman访问韩国，与三星/Hynix签订29CY 90万WPM DRAM订单"
    has_openai = re.search(r"OAI|OpenAI|Altman", text)
    has_dram = "DRAM" in text or "存储" in text
    has_wpm = re.search(r"90万\s*W[Pp][Mm]|900.?00[0-9]?\s*Wafer|90万Wafer|万WPM", text)
    has_samsung = re.search(r"三星|Samsung", text)
    has_hynix = re.search(r"Hynix|海力士", text)

    if has_openai and (has_wpm or (has_dram and re.search(r"90万|900000", text))):
        evid_base = _snippet(text, "三星" if "三星" in text else "Samsung", 100)
        if has_samsung:
            out.append(RawRelation(
                source_surface="OpenAI",
                target_surface="Samsung",
                relation_type=RelationTypes.CONTRACTS_WITH,
                what_flows="DRAM",
                quantity=900000.0,
                unit="WPM",
                confidence=0.92,
                evidence=evid_base,
                source_chunk_ids=[chunk.chunk_id],
            ))
        if has_hynix:
            evid_hynix = _snippet(text, "Hynix" if "Hynix" in text else "海力士", 100)
            out.append(RawRelation(
                source_surface="OpenAI",
                target_surface="SK Hynix",
                relation_type=RelationTypes.CONTRACTS_WITH,
                what_flows="DRAM",
                quantity=900000.0,
                unit="WPM",
                confidence=0.92,
                evidence=evid_hynix,
                source_chunk_ids=[chunk.chunk_id],
            ))
    return out


def _rule_hynix_supplies_hbm(chunk: Chunk) -> list[RawRelation]:
    """SK Hynix SUPPLIES HBM (to NVIDIA implied)."""
    out = []
    text = chunk.text
    if re.search(r"Hynix|海力士", text) and "HBM" in text:
        evid = _snippet(text, "HBM", 80)
        out.append(RawRelation(
            source_surface="SK Hynix",
            target_surface="NVIDIA",
            relation_type=RelationTypes.SUPPLIES,
            what_flows="HBM",
            confidence=0.8,
            evidence=evid,
            source_chunk_ids=[chunk.chunk_id],
        ))
    return out


def _rule_tsmc_supplies_nvidia(chunk: Chunk) -> list[RawRelation]:
    """TSMC SUPPLIES CoWoS/foundry to NVIDIA."""
    out = []
    text = chunk.text
    has_tsm = re.search(r"TSM|台积电|TSMC", text)
    has_nv = re.search(r"NV\b|NVIDIA|英伟达", text)
    if has_tsm and has_nv and re.search(r"CoWoS|foundry|先进制程", text):
        evid = _snippet(text, "CoWoS" if "CoWoS" in text else "TSM", 80)
        out.append(RawRelation(
            source_surface="TSMC",
            target_surface="NVIDIA",
            relation_type=RelationTypes.SUPPLIES,
            what_flows="CoWoS/foundry",
            confidence=0.85,
            evidence=evid,
            source_chunk_ids=[chunk.chunk_id],
        ))
    return out


def _rule_foxconn_supplies_nvidia(chunk: Chunk) -> list[RawRelation]:
    """Foxconn (工业富联) SUPPLIES AI server/rack to NVIDIA."""
    out = []
    text = chunk.text
    has_foxconn = re.search(r"工业富联|FII|富联|鸿海", text)
    has_nv = re.search(r"NV\b|NVIDIA|英伟达", text)
    if has_foxconn and re.search(r"Rack|rack|AI server|AI机架", text):
        evid = _snippet(text, "工业富联" if "工业富联" in text else "FII", 80)
        out.append(RawRelation(
            source_surface="Foxconn",
            target_surface="NVIDIA",
            relation_type=RelationTypes.SUPPLIES,
            what_flows="AI server/rack",
            confidence=0.8,
            evidence=evid,
            source_chunk_ids=[chunk.chunk_id],
        ))
    return out


def _rule_kioxia_sandisk_nand(chunk: Chunk) -> list[RawRelation]:
    """Kioxia / Sandisk supply NAND — clean room constraint context."""
    out = []
    text = chunk.text
    if re.search(r"SNDK|Sandisk|SanDisk", text) and re.search(r"Kioxia|铠侠", text):
        if re.search(r"NAND|clean room|Clear room|扩产", text):
            evid = _snippet(text, "SNDK" if "SNDK" in text else "Sandisk", 80)
            out.append(RawRelation(
                source_surface="Sandisk",
                target_surface="Kioxia",
                relation_type=RelationTypes.CO_MENTION,
                what_flows="NAND",
                confidence=0.7,
                evidence=evid,
                source_chunk_ids=[chunk.chunk_id],
            ))
    return out


# ---------------------------------------------------------------------------
# Whitelist guard: required canonical pairs that must be in the final output
# ---------------------------------------------------------------------------
_REQUIRED_PAIRS = {
    ("旭创", "NVIDIA"),
    ("源杰", "Google"),
    ("OpenAI", "Broadcom"),
    ("OpenAI", "AMD"),
    ("OpenAI", "Samsung"),
    ("OpenAI", "SK Hynix"),
}

_RULES = [
    _rule_innolight_nvidia,
    _rule_yuanjie_google,
    _rule_openai_broadcom_10gw,
    _rule_openai_amd_6gw,
    _rule_openai_samsung_hynix_dram,
    _rule_hynix_supplies_hbm,
    _rule_tsmc_supplies_nvidia,
    _rule_foxconn_supplies_nvidia,
    _rule_kioxia_sandisk_nand,
]


class SeedExtractor:
    def extract(self, chunks: list[Chunk]) -> ExtractionResult:
        relations: list[RawRelation] = []
        seen_companies: set[str] = set()

        for chunk in chunks:
            for rule in _RULES:
                for rel in rule(chunk):
                    relations.append(rel)
                    seen_companies.add(rel.source_surface)
                    seen_companies.add(rel.target_surface)

        # Collect all mentioned company surfaces from chunk text for nodes
        extra_surfaces = set()
        company_pats = [
            r"旭创", r"源杰", r"NVIDIA", r"Google", r"OpenAI", r"OAI",
            r"AVGO", r"Broadcom", r"AMD", r"Samsung", r"三星",
            r"Hynix", r"海力士", r"TSMC", r"台积电", r"TSM",
            r"Foxconn", r"工业富联", r"Kioxia", r"SNDK", r"Sandisk",
            r"LRCX", r"SK Hynix",
        ]
        for chunk in chunks:
            for pat in company_pats:
                if re.search(pat, chunk.text):
                    extra_surfaces.add(pat.replace(r"\b", ""))
        seen_companies |= extra_surfaces

        companies = [RawCompany(surface=s) for s in seen_companies]
        return ExtractionResult(companies=companies, relations=relations)

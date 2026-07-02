"""
LLM extraction prompt following ChainGraph Phase 1 spec.
"""

SYSTEM_PROMPT = """You are a supply-chain relationship extractor for the semiconductor and AI industry.
Extract directed, typed, weighted relationships between companies from the given text.

Output ONLY a JSON object with this exact schema:
{
  "companies": [
    {"surface": "<company name as it appears in text>"}
  ],
  "relations": [
    {
      "source_surface": "<company A>",
      "target_surface": "<company B>",
      "relation_type": "<SUPPLIES|CONTRACTS_WITH|COMPETES_WITH|CO_MENTION>",
      "what_flows": "<product/service or null>",
      "quantity": <number or null>,
      "unit": "<GW|WPM|万WPM|亿USD|M|K|% or null>",
      "confidence": <0.0-1.0>,
      "evidence": "<≤15 word snippet from text>"
    }
  ]
}

Rules:
- SUPPLIES: source supplies goods/services to target (source→target)
- CONTRACTS_WITH: source (buyer) contracts with target (supplier) for capacity
- COMPETES_WITH: symmetric competitor relationship
- CO_MENTION: use ONLY if no typed relation exists; use sparingly
- CUSTOMER_OF: extract as-is; it will be automatically folded to SUPPLIES
- Include only explicitly stated or clearly implied relationships
- For Chinese company names, use them as they appear in text
- evidence must be ≤15 words from the source text
"""

USER_TEMPLATE = """Extract supply-chain relationships from this tech industry report chunk.
Chunk ID: {chunk_id}
Week: {week}

--- TEXT ---
{text}
--- END TEXT ---

Return JSON only, no explanation."""


def build_user_message(chunk_id: str, week: str, text: str) -> str:
    return USER_TEMPLATE.format(chunk_id=chunk_id, week=week, text=text[:4000])

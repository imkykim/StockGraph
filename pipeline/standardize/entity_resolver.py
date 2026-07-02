from __future__ import annotations
import re
import unicodedata
from typing import Optional

from pipeline.standardize.alias_dict import ALIAS_MAP

# Legal suffix patterns to strip before matching (Latin and CJK)
_LATIN_SUFFIX = re.compile(
    r"\s*(Inc\.?|Ltd\.?|LLC\.?|Corp\.?|Co\.?|Limited|Corporation|"
    r"Technologies|Technology|Systems|Holdings?|Group)\s*$",
    re.IGNORECASE,
)
_CJK_SUFFIX = re.compile(r"[\s　]*(株式会社|有限公司|股份有限公司|集団|集团|グループ)\s*$")

_CJK_RANGE = re.compile(r"[一-鿿぀-ヿ가-힯]")


def norm_surface(surface: str) -> str:
    """
    Normalize a company surface form for alias lookup:
    1. NFKC (full-width → half-width, ligatures)
    2. Strip legal suffixes
    3. Lowercase only Latin characters; CJK stays as-is
    4. Strip surrounding whitespace
    """
    s = unicodedata.normalize("NFKC", surface.strip())
    s = _CJK_SUFFIX.sub("", s)
    s = _LATIN_SUFFIX.sub("", s)
    s = s.strip()
    # Lowercase only if string contains no CJK
    if not _CJK_RANGE.search(s):
        s = s.lower()
    return s


class EntityResolver:
    """
    Two-stage resolver:
      Stage 1: alias dict (O(1) after norm_surface)
      Stage 2: [Phase 2 placeholder] embedding-based fuzzy match
    Unresolved surfaces become new nodes with merge_candidate=True.
    """

    def __init__(self, node_store: Optional[dict[str, dict]] = None):
        # node_store: canonical_id → node metadata (loaded from prev graph.json for idempotency)
        self._node_store: dict[str, dict] = node_store or {}
        self._merge_candidates: set[str] = set()

    def resolve(self, surface: str) -> str:
        """Return canonical_id for a surface form."""
        normed = norm_surface(surface)

        # Stage 1: exact alias lookup (normed)
        if normed in ALIAS_MAP:
            return ALIAS_MAP[normed]

        # Also try original surface (handles CJK already normalized)
        if surface in ALIAS_MAP:
            return ALIAS_MAP[surface]

        # Stage 2: [Phase 2] embedding candidate — placeholder
        # For now, unknown surface → treat as its own canonical id
        canonical = surface.strip()
        self._merge_candidates.add(canonical)
        return canonical

    @property
    def merge_candidates(self) -> set[str]:
        return set(self._merge_candidates)

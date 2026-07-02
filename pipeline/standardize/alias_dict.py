"""
Alias dictionary: surface form → canonical_id.
CJK strings are matched as-is; Latin strings are lowercased before lookup.
"""

# Format: canonical_id → list of known surface aliases
# norm_surface() is applied before lookup (see entity_resolver.py)
ALIAS_MAP: dict[str, str] = {}

_CANONICAL_TO_ALIASES: dict[str, list[str]] = {
    "NVIDIA": [
        "NVIDIA", "NV", "NVDA", "英伟达", "老黄",
        "Nvidia", "nvidia",
    ],
    "Google": [
        "Google", "GOOG", "Alphabet", "google",
    ],
    "OpenAI": [
        "OpenAI", "OAI", "Altman", "openai",
        "Sam Altman",
    ],
    "Broadcom": [
        "Broadcom", "AVGO", "avgo", "broadcom",
    ],
    "AMD": [
        "AMD", "amd", "Advanced Micro Devices",
    ],
    "Samsung": [
        "Samsung", "三星", "samsung",
        "Samsung Electronics",
    ],
    "SK Hynix": [
        "SK Hynix", "Hynix", "海力士", "SK하이닉스",
        "sk hynix", "hynix",
    ],
    "TSMC": [
        "TSMC", "TSM", "台积电", "台積電", "tsmc", "tsm",
    ],
    "Innolight": [
        "Innolight", "旭创", "旭創",
    ],
    "Source Photonics": [
        "源杰", "Source Photonics", "source photonics",
        "Eoptolink",
    ],
    "Foxconn": [
        "Foxconn", "工业富联", "FII", "鸿海", "富联",
        "foxconn", "fii",
        "Foxconn Industrial Internet",
    ],
    "Kioxia": [
        "Kioxia", "铠侠", "kioxia",
    ],
    "Sandisk": [
        "Sandisk", "SanDisk", "SNDK", "WDC", "sandisk", "sndk",
    ],
    "Lam Research": [
        "Lam Research", "LRCX", "lrcx", "lam research",
    ],
    "ASML": [
        "ASML", "asml",
    ],
    "Micron": [
        "Micron", "MU", "mu", "micron",
    ],
    "MediaTek": [
        "MediaTek", "MTK", "联发科", "mtk", "mediatek",
    ],
    "Apple": [
        "Apple", "AAPL", "苹果", "apple", "aapl",
    ],
    "Microsoft": [
        "Microsoft", "MSFT", "微软", "microsoft",
    ],
    "Meta": [
        "Meta", "Facebook", "meta", "facebook",
    ],
    "Amazon": [
        "Amazon", "AWS", "amazon", "aws",
    ],
    "Texas Instruments": [
        "Texas Instruments", "TXN", "TI", "txn", "ti",
    ],
    "Arista Networks": [
        "Arista Networks", "ANET", "Arista", "anet", "arista",
    ],
    "Oracle": [
        "Oracle", "ORCL", "oracle", "orcl",
    ],
}

# Build flat lookup: normalized surface → canonical_id
for canonical, aliases in _CANONICAL_TO_ALIASES.items():
    for alias in aliases:
        ALIAS_MAP[alias] = canonical

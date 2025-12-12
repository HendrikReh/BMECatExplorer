"""Shared search constants for facets and filtering."""

# ECLASS segment names (first 2 digits)
ECLASS_SEGMENTS: dict[str, str] = {
    "21": "Fasteners, fixing",
    "22": "Machine tools",
    "23": "Industrial automation",
    "24": "Plastics machinery",
    "25": "Process engineering",
    "26": "Energy technology",
    "27": "Electrical engineering",
    "28": "Construction",
    "29": "HVAC",
    "30": "Packaging",
    "31": "Vehicles",
    "32": "Electronics",
    "33": "Information technology",
    "34": "Office, furniture",
    "35": "Food, agriculture",
    "36": "Medical, laboratory",
    "37": "Safety, security",
    "38": "Services",
    "39": "Mining, raw materials",
}

# Order unit labels
ORDER_UNIT_LABELS: dict[str, str] = {
    "C62": "Piece",
    "MTR": "Meter",
    "PK": "Pack",
    "SET": "Set",
    "PR": "Pair",
    "RO": "Roll",
    "CT": "Carton",
    "CL": "Coil",
    "BG": "Bag",
    "RD": "Rod",
}

# Price band definitions
PRICE_BANDS: list[dict[str, int | float | str | None]] = [
    {"key": "0-10", "label": "€0 - €10", "from": 0, "to": 10},
    {"key": "10-50", "label": "€10 - €50", "from": 10, "to": 50},
    {"key": "50-200", "label": "€50 - €200", "from": 50, "to": 200},
    {"key": "200-1000", "label": "€200 - €1,000", "from": 200, "to": 1000},
    {"key": "1000+", "label": "€1,000+", "from": 1000, "to": None},
]


def build_price_band_aggs() -> dict:
    """Build price band range aggregation on normalized unit price."""
    ranges = []
    for band in PRICE_BANDS:
        r = {"key": band["key"]}
        if band["from"] is not None:
            r["from"] = band["from"]
        if band["to"] is not None:
            r["to"] = band["to"]
        ranges.append(r)
    return {"range": {"field": "price_unit_amount", "ranges": ranges}}

"""ECLASS code-to-name mapping utilities."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.config import settings


@lru_cache(maxsize=1)
def load_eclass_names(path: str | None = None) -> dict[str, str]:
    """Load ECLASS names mapping from JSON file.

    Args:
        path: Path to JSON file with {"<code>": "<name>"} entries.

    Returns:
        Dictionary mapping ECLASS codes to human-readable names.
    """
    if not path:
        return {}

    file_path = Path(path)
    if not file_path.exists():
        return {}

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()}
    except Exception:
        # Fail soft if mapping is malformed
        return {}


ECLASS_NAMES = load_eclass_names(settings.eclass_names_path)


def get_eclass_name(code: str | None) -> str | None:
    """Resolve ECLASS name with a safe fallback."""
    if not code:
        return None
    return ECLASS_NAMES.get(code) or f"ECLASS {code}"

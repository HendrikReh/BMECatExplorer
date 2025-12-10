"""Text preparation for embedding generation."""

import html
import re


def clean_html(text: str) -> str:
    """Clean HTML entities and normalize whitespace."""
    if not text:
        return ""

    # Decode HTML entities (&amp; -> &, &lt; -> <, etc.)
    text = html.unescape(text)

    # Remove any remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def prepare_embedding_text(
    description_short: str | None,
    description_long: str | None,
    manufacturer_name: str | None,
    eclass_id: str | None,
    max_length: int = 8000,
) -> str:
    """
    Combine product text fields for embedding generation.

    Optimized for OpenAI text-embedding-3-small which has 8191 token limit.
    German text averages ~1.3 tokens per word, so we limit to ~8000 chars.
    """
    parts = []

    if description_short:
        parts.append(clean_html(description_short))

    if description_long:
        desc = clean_html(description_long)
        # Limit long description to avoid token overflow
        if len(desc) > 2000:
            desc = desc[:2000] + "..."
        parts.append(desc)

    if manufacturer_name:
        parts.append(f"Hersteller: {manufacturer_name}")

    if eclass_id:
        parts.append(f"ECLASS: {eclass_id}")

    text = ". ".join(parts)

    # Final length check
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text


def prepare_embedding_text_from_dict(product: dict, max_length: int = 8000) -> str:
    """Convenience wrapper for dict-based product data."""
    return prepare_embedding_text(
        description_short=product.get("description_short"),
        description_long=product.get("description_long"),
        manufacturer_name=product.get("manufacturer_name"),
        eclass_id=product.get("eclass_id"),
        max_length=max_length,
    )

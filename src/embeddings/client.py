"""OpenAI embedding client with batching and rate limiting."""

import time
from collections.abc import Iterator

from openai import OpenAI, RateLimitError

from src.config import settings

# Module-level cached client instance
_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Get OpenAI client with configured API key.

    Returns a cached client instance for efficiency.

    Returns:
        Configured OpenAI client instance.

    Raises:
        ValueError: If OPENAI_API_KEY is not set.
    """
    global _client
    if _client is not None:
        return _client
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required for embedding generation. "
            "Set it in .env or as an environment variable."
        )
    _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed_single(text: str) -> list[float]:
    """Generate embedding for a single text.

    Args:
        text: Text to embed.

    Returns:
        Embedding vector (1536 dimensions by default).
    """
    client = get_client()
    response = client.embeddings.create(
        input=text,
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
    )
    return response.data[0].embedding


def embed_batch(texts: list[str], max_retries: int = 3) -> list[list[float]]:
    """Generate embeddings for a batch of texts with retry logic.

    Handles rate limiting with exponential backoff.

    Args:
        texts: List of texts to embed.
        max_retries: Maximum retry attempts on rate limit errors.

    Returns:
        List of embedding vectors in the same order as input texts.

    Raises:
        RateLimitError: If rate limit is exceeded after all retries.
    """
    if not texts:
        return []

    client = get_client()
    retry_delay = 1.0

    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                input=texts,
                model=settings.openai_embedding_model,
                dimensions=settings.openai_embedding_dimensions,
            )
            return [item.embedding for item in response.data]
        except RateLimitError:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise

    return []  # Should not reach here


def embed_texts(
    texts: list[str],
    batch_size: int | None = None,
    show_progress: bool = False,
) -> list[list[float]]:
    """Generate embeddings for a list of texts in batches.

    Splits large text lists into batches and processes them sequentially.

    Args:
        texts: List of texts to embed.
        batch_size: Number of texts per API call. Defaults to
            settings.embedding_batch_size.
        show_progress: If True, print progress to stderr.

    Returns:
        List of embedding vectors in the same order as input texts.
    """
    if batch_size is None:
        batch_size = settings.embedding_batch_size

    embeddings: list[list[float]] = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i : i + batch_size]
        batch_embeddings = embed_batch(batch)
        embeddings.extend(batch_embeddings)

        if show_progress:
            import sys

            print(
                f"Embedded {min(i + batch_size, total):,}/{total:,} texts...",
                file=sys.stderr,
            )

    return embeddings


def embed_texts_iter(
    texts: Iterator[str],
    batch_size: int | None = None,
) -> Iterator[list[float]]:
    """Generate embeddings lazily from an iterator.

    Useful for streaming large datasets without loading all texts into memory.
    Processes texts in batches internally while yielding one embedding at a time.

    Args:
        texts: Iterator of texts to embed.
        batch_size: Number of texts per API call. Defaults to
            settings.embedding_batch_size.

    Yields:
        Embedding vectors one at a time, in the same order as input texts.
    """
    if batch_size is None:
        batch_size = settings.embedding_batch_size

    batch: list[str] = []

    for text in texts:
        batch.append(text)

        if len(batch) >= batch_size:
            embeddings = embed_batch(batch)
            for emb in embeddings:
                yield emb
            batch = []

    # Final batch
    if batch:
        embeddings = embed_batch(batch)
        for emb in embeddings:
            yield emb

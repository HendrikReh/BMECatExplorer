"""OpenSearch client setup."""

from opensearchpy import OpenSearch

from src.config import settings
from src.search.mapping import INDEX_SETTINGS

client = OpenSearch(
    hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
    http_compress=True,
    use_ssl=settings.opensearch_use_ssl,
    verify_certs=settings.opensearch_verify_certs,
)


def create_index(delete_existing: bool = False) -> None:
    """Create the products index with mapping."""
    index_name = settings.opensearch_index

    if client.indices.exists(index=index_name):
        if delete_existing:
            client.indices.delete(index=index_name)
        else:
            print(
                f"Index '{index_name}' already exists. "
                "Use delete_existing=True to recreate."
            )
            return

    client.indices.create(index=index_name, body=INDEX_SETTINGS)
    print(f"Created index '{index_name}'")


def delete_index() -> None:
    """Delete the products index."""
    index_name = settings.opensearch_index
    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)
        print(f"Deleted index '{index_name}'")

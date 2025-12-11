"""Index products from PostgreSQL to OpenSearch with embeddings."""

import sys

from opensearchpy.helpers import bulk
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.config import settings
from src.db.database import sync_engine
from src.db.models import Product
from src.eclass.names import get_eclass_name
from src.search.client import client, create_index

BATCH_SIZE = 1000


def product_to_doc(
    product: Product,
    catalog_id: str | None = None,
    source_file: str | None = None,
    embedding: list[float] | None = None,
    embedding_text: str | None = None,
) -> dict:
    """Convert a Product model to an OpenSearch document."""
    doc = {
        "_index": settings.opensearch_index,
        "_id": product.supplier_aid,
        "supplier_aid": product.supplier_aid,
        "ean": product.ean,
        "manufacturer_aid": product.manufacturer_aid,
        "manufacturer_name": product.manufacturer_name,
        "description_short": product.description_short,
        "description_long": product.description_long,
        "delivery_time": product.delivery_time,
        "order_unit": product.order_unit,
        "price_quantity": product.price_quantity,
        "quantity_min": product.quantity_min,
        "eclass_id": product.eclass_id,
        "eclass_name": get_eclass_name(product.eclass_id),
        "eclass_system": product.eclass_system,
    }

    # Catalog/provenance fields
    if catalog_id:
        doc["catalog_id"] = catalog_id
    if source_file:
        doc["source_file"] = source_file
        doc["source_uri"] = f"bmecat://{catalog_id or 'default'}/{product.supplier_aid}"

    # Add first price (primary price for search/filtering)
    if product.prices:
        price = product.prices[0]
        doc["price_amount"] = float(price.amount) if price.amount else None
        doc["price_currency"] = price.currency
        doc["price_type"] = price.price_type

    # Add first image
    if product.media:
        doc["image"] = product.media[0].source

    # Add embedding if provided
    if embedding:
        doc["embedding"] = embedding
    if embedding_text:
        doc["embedding_text"] = embedding_text

    return doc


def index_all(
    recreate_index: bool = True,
    catalog_id: str | None = None,
    source_file: str | None = None,
    generate_embeddings: bool = False,
) -> int:
    """
    Index all products from PostgreSQL to OpenSearch.

    Args:
        recreate_index: Delete and recreate the index before indexing
        catalog_id: Optional catalog identifier for multi-catalog support
        source_file: Optional source file name for provenance
        generate_embeddings: Generate OpenAI embeddings (requires OPENAI_API_KEY)

    Returns the number of documents indexed.
    """
    if recreate_index:
        create_index(delete_existing=True)

    # Lazy import to avoid requiring OpenAI when not generating embeddings
    if generate_embeddings:
        from src.embeddings.client import embed_batch
        from src.embeddings.text_prep import prepare_embedding_text

        print("Embedding generation enabled.", file=sys.stderr)
    else:
        embed_batch = None
        prepare_embedding_text = None

    count = 0

    with Session(sync_engine) as session:
        offset = 0
        while True:
            stmt = (
                select(Product)
                .options(selectinload(Product.prices), selectinload(Product.media))
                .order_by(Product.id)
                .offset(offset)
                .limit(BATCH_SIZE)
            )
            products = session.scalars(stmt).all()

            if not products:
                break

            # Generate embeddings for batch if enabled
            embeddings: list[list[float] | None] = [None] * len(products)
            embedding_texts: list[str | None] = [None] * len(products)

            if generate_embeddings and embed_batch and prepare_embedding_text:
                # Prepare texts for embedding
                texts = []
                for p in products:
                    text = prepare_embedding_text(
                        description_short=p.description_short,
                        description_long=p.description_long,
                        manufacturer_name=p.manufacturer_name,
                        eclass_id=p.eclass_id,
                    )
                    texts.append(text)
                    embedding_texts[products.index(p)] = text

                # Generate embeddings in batch
                try:
                    embeddings = embed_batch(texts)
                    print(f"  Generated {len(embeddings)} embeddings", file=sys.stderr)
                except Exception as e:
                    print(
                        f"  Warning: Embedding generation failed: {e}", file=sys.stderr
                    )
                    embeddings = [None] * len(products)

            # Convert to documents
            docs = [
                product_to_doc(
                    p,
                    catalog_id=catalog_id,
                    source_file=source_file,
                    embedding=embeddings[i] if i < len(embeddings) else None,
                    embedding_text=(
                        embedding_texts[i] if i < len(embedding_texts) else None
                    ),
                )
                for i, p in enumerate(products)
            ]

            success, errors = bulk(client, docs, raise_on_error=False)
            count += success
            if errors:
                print(f"  Errors in batch: {len(errors)}", file=sys.stderr)
                # Print first error for debugging
                if errors:
                    print(f"  First error: {errors[0]}", file=sys.stderr)
            offset += BATCH_SIZE

            print(f"Indexed {count:,} documents...", file=sys.stderr)

    # Refresh index to make documents searchable
    client.indices.refresh(index=settings.opensearch_index)

    return count


def index_catalog(
    catalog_id: str,
    source_file: str | None = None,
    generate_embeddings: bool = False,
) -> int:
    """
    Index products with catalog namespace (does not recreate index).

    Use this for adding a new catalog to an existing index.
    """
    return index_all(
        recreate_index=False,
        catalog_id=catalog_id,
        source_file=source_file,
        generate_embeddings=generate_embeddings,
    )


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Index products to OpenSearch")
    parser.add_argument(
        "--catalog-id",
        help="Catalog identifier for multi-catalog support",
    )
    parser.add_argument(
        "--source-file",
        help="Source file name for provenance tracking",
    )
    parser.add_argument(
        "--embeddings",
        action="store_true",
        help="Generate OpenAI embeddings (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--no-recreate",
        action="store_true",
        help="Don't recreate the index (append to existing)",
    )

    args = parser.parse_args()

    print("Starting indexing...", file=sys.stderr)
    if args.catalog_id:
        print(f"  Catalog: {args.catalog_id}", file=sys.stderr)
    if args.source_file:
        print(f"  Source: {args.source_file}", file=sys.stderr)
    if args.embeddings:
        print("  Embeddings: enabled", file=sys.stderr)

    count = index_all(
        recreate_index=not args.no_recreate,
        catalog_id=args.catalog_id,
        source_file=args.source_file,
        generate_embeddings=args.embeddings,
    )

    print(f"Done. Indexed {count:,} products.", file=sys.stderr)


if __name__ == "__main__":
    main()

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
    effective_catalog_id = catalog_id or product.catalog_id or "default"
    effective_source_file = source_file or product.source_file
    doc_id = f"{effective_catalog_id}:{product.supplier_aid}"

    doc = {
        "_index": settings.opensearch_index,
        "_id": doc_id,
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
        "catalog_id": effective_catalog_id,
    }

    # Catalog/provenance fields
    if effective_source_file:
        doc["source_file"] = effective_source_file
    doc["source_uri"] = f"bmecat://{effective_catalog_id}/{product.supplier_aid}"

    # Prices: index full list and keep a primary scalar for filtering.
    if product.prices:
        prices_payload: list[dict] = []
        for p in product.prices:
            prices_payload.append(
                {
                    "price_type": p.price_type,
                    "amount": float(p.amount) if p.amount is not None else None,
                    "currency": p.currency,
                    "tax": float(p.tax) if p.tax is not None else None,
                }
            )
        doc["prices"] = prices_payload

        primary_price = next(
            (p for p in product.prices if p.amount is not None), product.prices[0]
        )
        doc["price_amount"] = (
            float(primary_price.amount)
            if primary_price.amount is not None
            else None
        )
        doc["price_currency"] = primary_price.currency
        doc["price_type"] = primary_price.price_type

        # Normalized unit price: amount / price_quantity (BMECat prices often apply
        # to a bundle quantity, e.g. 100 units).
        qty = product.price_quantity
        if primary_price.amount is not None and qty:
            try:
                if qty > 0:
                    doc["price_unit_amount"] = float(primary_price.amount) / qty
            except Exception:
                doc["price_unit_amount"] = None

    # Media: index full list and keep a first image for UI convenience.
    if product.media:
        media_payload: list[dict] = []
        for m in product.media:
            media_payload.append(
                {
                    "source": m.source,
                    "type": m.type,
                    "description": m.description,
                    "purpose": m.purpose,
                }
            )
        doc["media"] = media_payload
        doc["image"] = media_payload[0].get("source")

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
        last_id = 0
        while True:
            stmt = (
                select(Product)
                .options(selectinload(Product.prices), selectinload(Product.media))
                .where(Product.id > last_id)
                .order_by(Product.id)
                .limit(BATCH_SIZE)
            )
            products = session.scalars(stmt).all()

            if not products:
                break
            last_id = products[-1].id

            # Generate embeddings for batch if enabled
            embeddings: list[list[float] | None] = [None] * len(products)
            embedding_texts: list[str | None] = [None] * len(products)

            if generate_embeddings and embed_batch and prepare_embedding_text:
                # Prepare texts for embedding
                texts = []
                for i, p in enumerate(products):
                    text = prepare_embedding_text(
                        description_short=p.description_short,
                        description_long=p.description_long,
                        manufacturer_name=p.manufacturer_name,
                        eclass_id=p.eclass_id,
                    )
                    texts.append(text)
                    embedding_texts[i] = text

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

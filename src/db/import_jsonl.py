"""Import JSONL product data into PostgreSQL."""

import json
import sys
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.db.database import init_db_sync, sync_engine
from src.db.models import Product, ProductMedia, ProductPrice

BATCH_SIZE = 1000


def parse_product(
    data: dict,
    catalog_id: str = "default",
    source_file: str | None = None,
) -> tuple[Product, list[ProductPrice], list[ProductMedia]]:
    """Parse a JSON record into SQLAlchemy model instances."""
    # Extract article_status if present
    article_status = data.get("article_status", {})

    product = Product(
        catalog_id=data.get("catalog_id") or catalog_id,
        supplier_aid=data["supplier_aid"],
        ean=data.get("ean"),
        manufacturer_aid=data.get("manufacturer_aid"),
        manufacturer_name=data.get("manufacturer_name"),
        description_short=data.get("description_short"),
        description_long=data.get("description_long"),
        delivery_time=data.get("delivery_time"),
        order_unit=data.get("order_unit"),
        price_quantity=data.get("price_quantity"),
        quantity_min=data.get("quantity_min"),
        quantity_interval=data.get("quantity_interval"),
        eclass_id=data.get("eclass_id"),
        eclass_system=data.get("eclass_system"),
        daily_price=data.get("daily_price"),
        mode=data.get("mode"),
        article_status_text=article_status.get("text"),
        article_status_type=article_status.get("type"),
        source_file=data.get("source_file") or source_file,
    )

    prices = []
    for p in data.get("prices", []):
        price = ProductPrice(
            price_type=p.get("price_type"),
            amount=Decimal(str(p["amount"])) if p.get("amount") is not None else None,
            currency=p.get("currency"),
            tax=Decimal(str(p["tax"])) if p.get("tax") is not None else None,
        )
        prices.append(price)

    media_items = []
    for m in data.get("media", []):
        media = ProductMedia(
            source=m.get("source"),
            type=m.get("type"),
            description=m.get("description"),
            purpose=m.get("purpose"),
        )
        media_items.append(media)

    # Handle legacy "image" field (single image as string)
    if "image" in data and not media_items:
        media_items.append(ProductMedia(source=data["image"]))

    return product, prices, media_items


def import_jsonl(
    file_path: str,
    catalog_id: str = "default",
    source_file: str | None = None,
    replace_catalog: bool = False,
) -> int:
    """
    Import JSONL file into PostgreSQL.

    Returns the number of records imported.
    """
    init_db_sync()

    count = 0
    batch: list[Product] = []

    with Session(sync_engine) as session:
        if replace_catalog:
            session.execute(
                delete(Product).where(Product.catalog_id == catalog_id)
            )
            session.commit()

        with open(file_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                data = json.loads(line)
                product, prices, media_items = parse_product(
                    data, catalog_id=catalog_id, source_file=source_file
                )

                # Attach related objects
                product.prices = prices
                product.media = media_items

                batch.append(product)
                count += 1

                if len(batch) >= BATCH_SIZE:
                    session.add_all(batch)
                    session.commit()
                    batch = []
                    print(f"Imported {count:,} records...", file=sys.stderr)

            # Final batch
            if batch:
                session.add_all(batch)
                session.commit()

    return count


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Import JSONL product data")
    parser.add_argument("file", help="Path to products.jsonl")
    parser.add_argument(
        "--catalog-id",
        default="default",
        help="Catalog namespace to assign to imported products",
    )
    parser.add_argument(
        "--source-file",
        help="Original BMECat XML filename for provenance",
    )
    parser.add_argument(
        "--replace-catalog",
        action="store_true",
        help=(
            "Delete existing products for the target catalog_id before importing. "
            "Useful for rerunning imports without duplicate errors."
        ),
    )

    args = parser.parse_args()

    file_path = args.file
    print(f"Importing {file_path}...", file=sys.stderr)

    count = import_jsonl(
        file_path,
        catalog_id=args.catalog_id,
        source_file=args.source_file,
        replace_catalog=args.replace_catalog,
    )
    print(f"Done. Imported {count:,} products.", file=sys.stderr)


if __name__ == "__main__":
    main()

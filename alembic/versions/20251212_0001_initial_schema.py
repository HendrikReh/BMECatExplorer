"""Initial schema with multi-catalog support.

Revision ID: 20251212_0001
Revises:
Create Date: 2025-12-12
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20251212_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "catalog_id",
            sa.String(length=100),
            nullable=False,
            server_default="default",
        ),
        sa.Column("supplier_aid", sa.String(length=50), nullable=False),
        sa.Column("ean", sa.String(length=20), nullable=True),
        sa.Column("manufacturer_aid", sa.String(length=50), nullable=True),
        sa.Column("manufacturer_name", sa.String(length=255), nullable=True),
        sa.Column("description_short", sa.Text(), nullable=True),
        sa.Column("description_long", sa.Text(), nullable=True),
        sa.Column("delivery_time", sa.Integer(), nullable=True),
        sa.Column("order_unit", sa.String(length=10), nullable=True),
        sa.Column("price_quantity", sa.Integer(), nullable=True),
        sa.Column("quantity_min", sa.Integer(), nullable=True),
        sa.Column("quantity_interval", sa.Integer(), nullable=True),
        sa.Column("eclass_id", sa.String(length=20), nullable=True),
        sa.Column("eclass_system", sa.String(length=50), nullable=True),
        sa.Column("daily_price", sa.Boolean(), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=True),
        sa.Column("article_status_text", sa.String(length=50), nullable=True),
        sa.Column("article_status_type", sa.String(length=20), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "catalog_id", "supplier_aid", name="uq_products_catalog_supplier_aid"
        ),
    )

    op.create_index("ix_products_catalog_id", "products", ["catalog_id"])
    op.create_index("ix_products_ean", "products", ["ean"])
    op.create_index(
        "ix_products_manufacturer_name", "products", ["manufacturer_name"]
    )
    op.create_index("ix_products_eclass_id", "products", ["eclass_id"])

    op.create_table(
        "product_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price_type", sa.String(length=50), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("tax", sa.Numeric(5, 4), nullable=True),
    )
    op.create_index(
        "ix_product_prices_product_id", "product_prices", ["product_id"]
    )

    op.create_table(
        "product_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("purpose", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_product_media_product_id", "product_media", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_product_media_product_id", table_name="product_media")
    op.drop_table("product_media")

    op.drop_index("ix_product_prices_product_id", table_name="product_prices")
    op.drop_table("product_prices")

    op.drop_index("ix_products_eclass_id", table_name="products")
    op.drop_index("ix_products_manufacturer_name", table_name="products")
    op.drop_index("ix_products_ean", table_name="products")
    op.drop_index("ix_products_catalog_id", table_name="products")
    op.drop_table("products")

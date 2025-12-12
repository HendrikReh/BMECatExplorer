"""SQLAlchemy models for product data."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Multi-catalog support: supplier_aid is unique per catalog.
    catalog_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default"
    )
    supplier_aid: Mapped[str] = mapped_column(String(50), nullable=False)
    ean: Mapped[str | None] = mapped_column(String(20))
    manufacturer_aid: Mapped[str | None] = mapped_column(String(50))
    manufacturer_name: Mapped[str | None] = mapped_column(String(255))
    description_short: Mapped[str | None] = mapped_column(Text)
    description_long: Mapped[str | None] = mapped_column(Text)
    delivery_time: Mapped[int | None] = mapped_column(Integer)
    order_unit: Mapped[str | None] = mapped_column(String(10))
    price_quantity: Mapped[int | None] = mapped_column(Integer)
    quantity_min: Mapped[int | None] = mapped_column(Integer)
    quantity_interval: Mapped[int | None] = mapped_column(Integer)
    eclass_id: Mapped[str | None] = mapped_column(String(20))
    eclass_system: Mapped[str | None] = mapped_column(String(50))
    daily_price: Mapped[bool | None] = mapped_column(Boolean)
    mode: Mapped[str | None] = mapped_column(String(20))
    article_status_text: Mapped[str | None] = mapped_column(String(50))
    article_status_type: Mapped[str | None] = mapped_column(String(20))
    source_file: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    prices: Mapped[list["ProductPrice"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    media: Mapped[list["ProductMedia"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "catalog_id", "supplier_aid", name="uq_products_catalog_supplier_aid"
        ),
        Index("ix_products_catalog_id", "catalog_id"),
        Index("ix_products_ean", "ean"),
        Index("ix_products_manufacturer_name", "manufacturer_name"),
        Index("ix_products_eclass_id", "eclass_id"),
    )


class ProductPrice(Base):
    __tablename__ = "product_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    price_type: Mapped[str | None] = mapped_column(String(50))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    tax: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))

    product: Mapped["Product"] = relationship(back_populates="prices")

    __table_args__ = (Index("ix_product_prices_product_id", "product_id"),)


class ProductMedia(Base):
    __tablename__ = "product_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(String(50))

    product: Mapped["Product"] = relationship(back_populates="media")

    __table_args__ = (Index("ix_product_media_product_id", "product_id"),)

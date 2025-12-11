"""Integration tests for database operations.

These tests require a running PostgreSQL instance.
Run with: pytest tests/integration -m integration
"""

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.config import settings
from src.db.import_jsonl import parse_product
from src.db.models import Base, Product, ProductMedia, ProductPrice


@pytest.fixture(scope="module")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(settings.postgres_url_sync)
    # Create tables
    Base.metadata.create_all(engine)
    yield engine
    # Cleanup: drop all tables
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(test_engine):
    """Create a database session for each test."""
    with Session(test_engine) as session:
        yield session
        session.rollback()


@pytest.mark.integration
class TestDatabaseConnection:
    """Test database connectivity."""

    def test_connection(self, test_engine):
        """Test that we can connect to the database."""
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1


@pytest.mark.integration
class TestProductModel:
    """Test Product model operations."""

    def test_create_product(self, db_session: Session):
        """Test creating a product."""
        product = Product(
            supplier_aid="INT_TEST_001",
            ean="1234567890123",
            manufacturer_name="Test Manufacturer",
            description_short="Test Product",
        )
        db_session.add(product)
        db_session.commit()

        # Query back
        result = db_session.scalar(
            select(Product).where(Product.supplier_aid == "INT_TEST_001")
        )
        assert result is not None
        assert result.manufacturer_name == "Test Manufacturer"

        # Cleanup
        db_session.delete(result)
        db_session.commit()

    def test_create_product_with_prices(self, db_session: Session):
        """Test creating a product with associated prices."""
        product = Product(
            supplier_aid="INT_TEST_002",
            description_short="Product with prices",
        )
        product.prices = [
            ProductPrice(price_type="net_customer", amount=100.00, currency="EUR"),
            ProductPrice(price_type="net_list", amount=120.00, currency="EUR"),
        ]
        db_session.add(product)
        db_session.commit()

        # Query back with prices
        result = db_session.scalar(
            select(Product).where(Product.supplier_aid == "INT_TEST_002")
        )
        assert result is not None
        assert len(result.prices) == 2
        assert result.prices[0].amount == 100.00

        # Cleanup
        db_session.delete(result)
        db_session.commit()

    def test_create_product_with_media(self, db_session: Session):
        """Test creating a product with associated media."""
        product = Product(
            supplier_aid="INT_TEST_003",
            description_short="Product with media",
        )
        product.media = [
            ProductMedia(source="image1.jpg", type="image/jpeg", purpose="normal"),
            ProductMedia(source="image2.jpg", type="image/jpeg", purpose="thumbnail"),
        ]
        db_session.add(product)
        db_session.commit()

        result = db_session.scalar(
            select(Product).where(Product.supplier_aid == "INT_TEST_003")
        )
        assert len(result.media) == 2

        # Cleanup
        db_session.delete(result)
        db_session.commit()

    def test_unique_supplier_aid(self, db_session: Session):
        """Test that supplier_aid must be unique."""
        product1 = Product(supplier_aid="INT_TEST_UNIQUE")
        db_session.add(product1)
        db_session.commit()

        product2 = Product(supplier_aid="INT_TEST_UNIQUE")
        db_session.add(product2)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()
        # Cleanup
        db_session.delete(product1)
        db_session.commit()


@pytest.mark.integration
class TestImportParsing:
    """Test import parsing with database persistence."""

    def test_parse_and_persist(self, db_session: Session, sample_product_json: dict):
        """Test parsing JSON and persisting to database."""
        # Modify supplier_aid to avoid conflicts
        sample_product_json["supplier_aid"] = "INT_PARSE_TEST"

        product, prices, media = parse_product(sample_product_json)
        product.prices = prices
        product.media = media

        db_session.add(product)
        db_session.commit()

        # Query and verify
        result = db_session.scalar(
            select(Product).where(Product.supplier_aid == "INT_PARSE_TEST")
        )
        assert result is not None
        assert result.manufacturer_name == "Walraven GmbH"
        assert len(result.prices) == 1
        assert len(result.media) == 1
        assert float(result.prices[0].amount) == 360.48

        # Cleanup
        db_session.delete(result)
        db_session.commit()

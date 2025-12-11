"""Unit tests for JSONL import parsing."""

from decimal import Decimal

import pytest

from src.db.import_jsonl import parse_product
from src.db.models import Product, ProductMedia, ProductPrice


@pytest.mark.unit
class TestParseProduct:
    """Tests for parse_product function."""

    def test_parse_basic_fields(self, sample_product_json: dict):
        """Test parsing of basic product fields."""
        product, prices, media = parse_product(sample_product_json)

        assert isinstance(product, Product)
        assert product.supplier_aid == "1000864"
        assert product.ean == "8712993543250"
        assert product.manufacturer_aid == "50320009"
        assert product.manufacturer_name == "Walraven GmbH"
        assert (
            product.description_short
            == "Trägerklammer 5-9mm Britclips FC8 TB 4-8mm 50320009"
        )
        assert product.delivery_time == 5
        assert product.order_unit == "C62"
        assert product.price_quantity == 100
        assert product.quantity_min == 100
        assert product.quantity_interval == 100
        assert product.eclass_id == "23140307"
        assert product.eclass_system == "ECLASS-8.0"
        assert product.daily_price is False
        assert product.mode == "new"

    def test_parse_article_status(self, sample_product_json: dict):
        """Test parsing of article status nested object."""
        product, _, _ = parse_product(sample_product_json)

        assert product.article_status_text == "Neu"
        assert product.article_status_type == "new"

    def test_parse_prices(self, sample_product_json: dict):
        """Test parsing of price data."""
        _, prices, _ = parse_product(sample_product_json)

        assert len(prices) == 1
        price = prices[0]
        assert isinstance(price, ProductPrice)
        assert price.price_type == "net_customer"
        assert price.amount == Decimal("360.48")
        assert price.currency == "EUR"
        assert price.tax == Decimal("0.19")

    def test_parse_media(self, sample_product_json: dict):
        """Test parsing of media entries."""
        _, _, media = parse_product(sample_product_json)

        assert len(media) == 1
        m = media[0]
        assert isinstance(m, ProductMedia)
        assert m.source == "1000864.jpg"
        assert m.type == "image/jpeg"
        assert m.description == "Bild zur Produktgruppe"
        assert m.purpose == "normal"

    def test_parse_minimal_product(self):
        """Test parsing a product with only required fields."""
        minimal = {"supplier_aid": "TEST001"}
        product, prices, media = parse_product(minimal)

        assert product.supplier_aid == "TEST001"
        assert product.ean is None
        assert product.manufacturer_name is None
        assert len(prices) == 0
        assert len(media) == 0

    def test_parse_legacy_image_field(self):
        """Test parsing legacy 'image' field (string instead of media array)."""
        data = {
            "supplier_aid": "TEST002",
            "image": "test.jpg",
        }
        _, _, media = parse_product(data)

        assert len(media) == 1
        assert media[0].source == "test.jpg"

    def test_parse_multiple_prices(self):
        """Test parsing multiple price entries."""
        data = {
            "supplier_aid": "TEST003",
            "prices": [
                {
                    "price_type": "net_customer",
                    "amount": 100.0,
                    "currency": "EUR",
                    "tax": 0.19,
                },
                {
                    "price_type": "net_list",
                    "amount": 120.0,
                    "currency": "EUR",
                    "tax": 0.19,
                },
            ],
        }
        _, prices, _ = parse_product(data)

        assert len(prices) == 2
        assert prices[0].price_type == "net_customer"
        assert prices[1].price_type == "net_list"

    def test_parse_price_with_none_values(self):
        """Test parsing price with missing optional fields."""
        data = {
            "supplier_aid": "TEST004",
            "prices": [{"price_type": "net_customer"}],
        }
        _, prices, _ = parse_product(data)

        assert len(prices) == 1
        assert prices[0].amount is None
        assert prices[0].currency is None
        assert prices[0].tax is None

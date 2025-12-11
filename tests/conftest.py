"""Shared test fixtures."""

import json

import pytest


@pytest.fixture
def sample_product_json() -> dict:
    """Sample product data as parsed from JSONL."""
    return {
        "supplier_aid": "1000864",
        "ean": "8712993543250",
        "manufacturer_aid": "50320009",
        "manufacturer_name": "Walraven GmbH",
        "description_short": "Trägerklammer 5-9mm Britclips FC8 TB 4-8mm 50320009",
        "description_long": (
            "Ohne Schweißen oder Bohren befestigt die " "Federstahl-Trägerklammer"
        ),
        "delivery_time": 5,
        "order_unit": "C62",
        "price_quantity": 100,
        "quantity_min": 100,
        "quantity_interval": 100,
        "eclass_id": "23140307",
        "eclass_system": "ECLASS-8.0",
        "daily_price": False,
        "mode": "new",
        "article_status": {"text": "Neu", "type": "new"},
        "prices": [
            {
                "price_type": "net_customer",
                "amount": 360.48,
                "currency": "EUR",
                "tax": 0.19,
            }
        ],
        "media": [
            {
                "source": "1000864.jpg",
                "type": "image/jpeg",
                "description": "Bild zur Produktgruppe",
                "purpose": "normal",
            }
        ],
    }


@pytest.fixture
def sample_product_jsonl(sample_product_json: dict, tmp_path) -> str:
    """Create a temporary JSONL file with sample data."""
    file_path = tmp_path / "test_products.jsonl"
    with open(file_path, "w") as f:
        f.write(json.dumps(sample_product_json) + "\n")
        # Add a second product
        product2 = sample_product_json.copy()
        product2["supplier_aid"] = "1000865"
        product2["ean"] = "8712993543267"
        f.write(json.dumps(product2) + "\n")
    return str(file_path)

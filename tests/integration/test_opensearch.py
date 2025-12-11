"""Integration tests for OpenSearch operations.

These tests require a running OpenSearch instance.
Run with: pytest tests/integration -m integration
"""

import pytest
from opensearchpy import NotFoundError

from src.config import settings
from src.search.client import client
from src.search.mapping import INDEX_SETTINGS

TEST_INDEX = "test_products"


@pytest.fixture(scope="module", autouse=True)
def setup_test_index():
    """Create and cleanup test index."""
    original_index = settings.opensearch_index
    settings.opensearch_index = TEST_INDEX

    # Delete if exists and create fresh
    if client.indices.exists(index=TEST_INDEX):
        client.indices.delete(index=TEST_INDEX)
    client.indices.create(index=TEST_INDEX, body=INDEX_SETTINGS)

    yield

    # Cleanup
    if client.indices.exists(index=TEST_INDEX):
        client.indices.delete(index=TEST_INDEX)
    settings.opensearch_index = original_index


@pytest.fixture
def indexed_product():
    """Index a test product and clean up after."""
    doc = {
        "supplier_aid": "OS_TEST_001",
        "ean": "1234567890123",
        "manufacturer_name": "Test Manufacturer",
        "description_short": "Test Trägerklammer für Integration",
        "description_long": "A longer description for testing search functionality",
        "eclass_id": "23140307",
        "price_amount": 250.00,
        "price_currency": "EUR",
        "image": "test.jpg",
    }
    client.index(index=TEST_INDEX, id=doc["supplier_aid"], body=doc, refresh=True)

    yield doc

    # Cleanup
    try:
        client.delete(index=TEST_INDEX, id=doc["supplier_aid"], refresh=True)
    except Exception:
        pass


@pytest.mark.integration
class TestOpenSearchConnection:
    """Test OpenSearch connectivity."""

    def test_cluster_health(self):
        """Test that OpenSearch cluster is healthy."""
        health = client.cluster.health()
        assert health["status"] in ["green", "yellow"]

    def test_index_exists(self):
        """Test that our test index exists."""
        assert client.indices.exists(index=TEST_INDEX)


@pytest.mark.integration
class TestOpenSearchIndexing:
    """Test indexing operations."""

    def test_index_document(self):
        """Test indexing a single document."""
        doc = {
            "supplier_aid": "OS_INDEX_TEST",
            "description_short": "Index test product",
        }
        response = client.index(
            index=TEST_INDEX, id=doc["supplier_aid"], body=doc, refresh=True
        )
        assert response["result"] in ["created", "updated"]

        # Cleanup
        client.delete(index=TEST_INDEX, id=doc["supplier_aid"])

    def test_bulk_index(self):
        """Test bulk indexing multiple documents."""
        from opensearchpy.helpers import bulk

        docs = [
            {
                "_index": TEST_INDEX,
                "_id": f"BULK_TEST_{i}",
                "supplier_aid": f"BULK_TEST_{i}",
                "description_short": f"Bulk test product {i}",
            }
            for i in range(10)
        ]
        success, errors = bulk(client, docs, refresh=True)
        assert success == 10
        assert len(errors) == 0

        # Verify count
        count = client.count(index=TEST_INDEX)["count"]
        assert count >= 10

        # Cleanup
        for i in range(10):
            client.delete(index=TEST_INDEX, id=f"BULK_TEST_{i}")
        client.indices.refresh(index=TEST_INDEX)


@pytest.mark.integration
class TestOpenSearchSearch:
    """Test search operations."""

    def test_match_all(self, indexed_product):
        """Test match_all query."""
        response = client.search(
            index=TEST_INDEX, body={"query": {"match_all": {}}, "size": 100}
        )
        assert response["hits"]["total"]["value"] >= 1

    def test_text_search(self, indexed_product):
        """Test full-text search."""
        response = client.search(
            index=TEST_INDEX,
            body={
                "query": {
                    "multi_match": {
                        "query": "Trägerklammer",
                        "fields": ["description_short", "description_long"],
                    }
                }
            },
        )
        hits = response["hits"]["hits"]
        assert len(hits) >= 1
        assert hits[0]["_source"]["supplier_aid"] == "OS_TEST_001"

    def test_term_filter(self, indexed_product):
        """Test term filter on keyword field."""
        response = client.search(
            index=TEST_INDEX,
            body={"query": {"term": {"eclass_id": "23140307"}}},
        )
        assert response["hits"]["total"]["value"] >= 1

    def test_range_filter(self, indexed_product):
        """Test range filter on price."""
        response = client.search(
            index=TEST_INDEX,
            body={"query": {"range": {"price_amount": {"gte": 200, "lte": 300}}}},
        )
        assert response["hits"]["total"]["value"] >= 1

    def test_aggregations(self, indexed_product):
        """Test aggregations for facets."""
        response = client.search(
            index=TEST_INDEX,
            body={
                "size": 0,
                "aggs": {
                    "manufacturers": {
                        "terms": {"field": "manufacturer_name.keyword", "size": 10}
                    }
                },
            },
        )
        buckets = response["aggregations"]["manufacturers"]["buckets"]
        assert len(buckets) >= 1
        assert any(b["key"] == "Test Manufacturer" for b in buckets)

    def test_autocomplete(self, indexed_product):
        """Test autocomplete on description_short."""
        response = client.search(
            index=TEST_INDEX,
            body={
                "query": {
                    "match": {
                        "description_short.autocomplete": {
                            "query": "Träger",
                            "operator": "and",
                        }
                    }
                }
            },
        )
        assert response["hits"]["total"]["value"] >= 1


@pytest.mark.integration
class TestOpenSearchGetById:
    """Test get by ID operations."""

    def test_get_existing_document(self, indexed_product):
        """Test getting an existing document by ID."""
        response = client.get(index=TEST_INDEX, id="OS_TEST_001")
        assert response["found"] is True
        assert response["_source"]["supplier_aid"] == "OS_TEST_001"

    def test_get_nonexistent_document(self):
        """Test getting a non-existent document."""
        with pytest.raises(NotFoundError):
            client.get(index=TEST_INDEX, id="NONEXISTENT_ID")

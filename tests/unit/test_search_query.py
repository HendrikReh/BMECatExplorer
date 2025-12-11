"""Unit tests for search query building."""

import pytest

from src.api.routes.search import build_search_query


@pytest.mark.unit
class TestBuildSearchQuery:
    """Tests for build_search_query function."""

    def test_empty_query(self):
        """Test query with no parameters returns match_all."""
        query = build_search_query(
            q=None,
            manufacturers=None,
            eclass_ids=None,
            eclass_segments=None,
            order_units=None,
            price_min=None,
            price_max=None,
        )
        assert query == {"match_all": {}}

    def test_text_query(self):
        """Test full-text search query."""
        query = build_search_query(
            q="Kabel",
            manufacturers=None,
            eclass_ids=None,
            eclass_segments=None,
            order_units=None,
            price_min=None,
            price_max=None,
        )
        assert "bool" in query
        assert len(query["bool"]["must"]) == 1
        assert "multi_match" in query["bool"]["must"][0]
        assert query["bool"]["must"][0]["multi_match"]["query"] == "Kabel"

    def test_manufacturer_filter_single(self):
        """Test single manufacturer filter."""
        query = build_search_query(
            q=None,
            manufacturers=["Walraven GmbH"],
            eclass_ids=None,
            eclass_segments=None,
            order_units=None,
            price_min=None,
            price_max=None,
        )
        assert "bool" in query
        filters = query["bool"]["filter"]
        assert len(filters) == 1
        assert filters[0] == {"term": {"manufacturer_name.keyword": "Walraven GmbH"}}

    def test_manufacturer_filter_multiple(self):
        """Test multiple manufacturers filter (OR query)."""
        query = build_search_query(
            q=None,
            manufacturers=["Walraven GmbH", "Schneider Electric GmbH", "Siemens AG"],
            eclass_ids=None,
            eclass_segments=None,
            order_units=None,
            price_min=None,
            price_max=None,
        )
        assert "bool" in query
        filters = query["bool"]["filter"]
        assert len(filters) == 1
        assert filters[0] == {
            "terms": {
                "manufacturer_name.keyword": [
                    "Walraven GmbH",
                    "Schneider Electric GmbH",
                    "Siemens AG",
                ]
            }
        }

    def test_eclass_filter_single(self):
        """Test single ECLASS ID filter."""
        query = build_search_query(
            q=None,
            manufacturers=None,
            eclass_ids=["23140307"],
            eclass_segments=None,
            order_units=None,
            price_min=None,
            price_max=None,
        )
        filters = query["bool"]["filter"]
        assert {"term": {"eclass_id": "23140307"}} in filters

    def test_eclass_filter_multiple(self):
        """Test multiple ECLASS IDs filter (OR query)."""
        query = build_search_query(
            q=None,
            manufacturers=None,
            eclass_ids=["23140307", "27140501", "21030102"],
            eclass_segments=None,
            order_units=None,
            price_min=None,
            price_max=None,
        )
        assert "bool" in query
        filters = query["bool"]["filter"]
        assert len(filters) == 1
        assert filters[0] == {
            "terms": {
                "eclass_id": ["23140307", "27140501", "21030102"]
            }
        }

    def test_eclass_segment_filter_single(self):
        """Test ECLASS segment (2-digit prefix) filter with single segment."""
        query = build_search_query(
            q=None,
            manufacturers=None,
            eclass_ids=None,
            eclass_segments=["27"],
            order_units=None,
            price_min=None,
            price_max=None,
        )
        filters = query["bool"]["filter"]
        assert {"prefix": {"eclass_id": "27"}} in filters

    def test_eclass_segment_filter_multiple(self):
        """Test ECLASS segment filter with multiple segments (OR query)."""
        query = build_search_query(
            q=None,
            manufacturers=None,
            eclass_ids=None,
            eclass_segments=["27", "23", "21"],
            order_units=None,
            price_min=None,
            price_max=None,
        )
        filters = query["bool"]["filter"]
        assert len(filters) == 1
        # Should be a bool query with should clauses
        assert "bool" in filters[0]
        assert "should" in filters[0]["bool"]
        should_clauses = filters[0]["bool"]["should"]
        assert len(should_clauses) == 3
        assert {"prefix": {"eclass_id": "27"}} in should_clauses
        assert {"prefix": {"eclass_id": "23"}} in should_clauses
        assert {"prefix": {"eclass_id": "21"}} in should_clauses

    def test_order_unit_filter_single(self):
        """Test single order unit filter."""
        query = build_search_query(
            q=None,
            manufacturers=None,
            eclass_ids=None,
            eclass_segments=None,
            order_units=["MTR"],
            price_min=None,
            price_max=None,
        )
        filters = query["bool"]["filter"]
        assert {"term": {"order_unit": "MTR"}} in filters

    def test_order_unit_filter_multiple(self):
        """Test multiple order units filter (OR query)."""
        query = build_search_query(
            q=None,
            manufacturers=None,
            eclass_ids=None,
            eclass_segments=None,
            order_units=["MTR", "C62", "PK"],
            price_min=None,
            price_max=None,
        )
        assert "bool" in query
        filters = query["bool"]["filter"]
        assert len(filters) == 1
        assert filters[0] == {
            "terms": {
                "order_unit": ["MTR", "C62", "PK"]
            }
        }

    def test_price_range_filter(self):
        """Test price range filter."""
        query = build_search_query(
            q=None,
            manufacturers=None,
            eclass_ids=None,
            eclass_segments=None,
            order_units=None,
            price_min=100.0,
            price_max=500.0,
        )
        filters = query["bool"]["filter"]
        assert len(filters) == 1
        price_filter = filters[0]["range"]["price_amount"]
        assert price_filter["gte"] == 100.0
        assert price_filter["lte"] == 500.0

    def test_price_min_only(self):
        """Test price filter with only minimum."""
        query = build_search_query(
            q=None,
            manufacturers=None,
            eclass_ids=None,
            eclass_segments=None,
            order_units=None,
            price_min=50.0,
            price_max=None,
        )
        price_filter = query["bool"]["filter"][0]["range"]["price_amount"]
        assert price_filter == {"gte": 50.0}

    def test_price_max_only(self):
        """Test price filter with only maximum."""
        query = build_search_query(
            q=None,
            manufacturers=None,
            eclass_ids=None,
            eclass_segments=None,
            order_units=None,
            price_min=None,
            price_max=1000.0,
        )
        price_filter = query["bool"]["filter"][0]["range"]["price_amount"]
        assert price_filter == {"lte": 1000.0}

    def test_combined_query_and_filters(self):
        """Test combining text search with multiple filters."""
        query = build_search_query(
            q="Trägerklammer",
            manufacturers=["Walraven GmbH"],
            eclass_ids=["23140307"],
            eclass_segments=None,
            order_units=None,
            price_min=100.0,
            price_max=500.0,
        )
        assert "bool" in query
        # Should have text query in must
        assert len(query["bool"]["must"]) == 1
        assert "multi_match" in query["bool"]["must"][0]
        # Should have 3 filters (manufacturer, eclass, price)
        assert len(query["bool"]["filter"]) == 3

    def test_exact_match_query(self):
        """Test exact match search query (for EAN, supplier ID, etc.)."""
        query = build_search_query(
            q="4013288230058",
            manufacturers=None,
            eclass_ids=None,
            eclass_segments=None,
            order_units=None,
            price_min=None,
            price_max=None,
            exact_match=True,
        )
        assert "bool" in query
        must = query["bool"]["must"]
        assert len(must) == 1
        # Should use bool with should clauses for exact matching
        assert "bool" in must[0]
        assert "should" in must[0]["bool"]
        should_clauses = must[0]["bool"]["should"]
        # Should have term queries for exact fields
        assert {"term": {"ean": "4013288230058"}} in should_clauses
        assert {"term": {"supplier_aid": "4013288230058"}} in should_clauses
        assert {"term": {"manufacturer_aid": "4013288230058"}} in should_clauses

    def test_exact_match_with_filters(self):
        """Test exact match combined with filters."""
        query = build_search_query(
            q="12345678",
            manufacturers=["Wera Werkzeuge GmbH"],
            eclass_ids=None,
            eclass_segments=None,
            order_units=None,
            price_min=None,
            price_max=None,
            exact_match=True,
        )
        assert "bool" in query
        # Should have exact match query in must
        assert "bool" in query["bool"]["must"][0]
        assert "should" in query["bool"]["must"][0]["bool"]
        # Should have manufacturer filter
        assert len(query["bool"]["filter"]) == 1
        assert {"term": {"manufacturer_name.keyword": "Wera Werkzeuge GmbH"}} in query["bool"]["filter"]

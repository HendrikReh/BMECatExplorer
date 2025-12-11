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
            manufacturer=None,
            eclass_id=None,
            eclass_segment=None,
            order_unit=None,
            price_min=None,
            price_max=None,
        )
        assert query == {"match_all": {}}

    def test_text_query(self):
        """Test full-text search query."""
        query = build_search_query(
            q="Kabel",
            manufacturer=None,
            eclass_id=None,
            eclass_segment=None,
            order_unit=None,
            price_min=None,
            price_max=None,
        )
        assert "bool" in query
        assert len(query["bool"]["must"]) == 1
        assert "multi_match" in query["bool"]["must"][0]
        assert query["bool"]["must"][0]["multi_match"]["query"] == "Kabel"

    def test_manufacturer_filter(self):
        """Test manufacturer filter."""
        query = build_search_query(
            q=None,
            manufacturer="Walraven GmbH",
            eclass_id=None,
            eclass_segment=None,
            order_unit=None,
            price_min=None,
            price_max=None,
        )
        assert "bool" in query
        filters = query["bool"]["filter"]
        assert len(filters) == 1
        assert filters[0] == {"term": {"manufacturer_name.keyword": "Walraven GmbH"}}

    def test_eclass_filter(self):
        """Test ECLASS ID filter."""
        query = build_search_query(
            q=None,
            manufacturer=None,
            eclass_id="23140307",
            eclass_segment=None,
            order_unit=None,
            price_min=None,
            price_max=None,
        )
        filters = query["bool"]["filter"]
        assert {"term": {"eclass_id": "23140307"}} in filters

    def test_eclass_segment_filter(self):
        """Test ECLASS segment (2-digit prefix) filter."""
        query = build_search_query(
            q=None,
            manufacturer=None,
            eclass_id=None,
            eclass_segment="27",
            order_unit=None,
            price_min=None,
            price_max=None,
        )
        filters = query["bool"]["filter"]
        assert {"prefix": {"eclass_id": "27"}} in filters

    def test_order_unit_filter(self):
        """Test order unit filter."""
        query = build_search_query(
            q=None,
            manufacturer=None,
            eclass_id=None,
            eclass_segment=None,
            order_unit="MTR",
            price_min=None,
            price_max=None,
        )
        filters = query["bool"]["filter"]
        assert {"term": {"order_unit": "MTR"}} in filters

    def test_price_range_filter(self):
        """Test price range filter."""
        query = build_search_query(
            q=None,
            manufacturer=None,
            eclass_id=None,
            eclass_segment=None,
            order_unit=None,
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
            manufacturer=None,
            eclass_id=None,
            eclass_segment=None,
            order_unit=None,
            price_min=50.0,
            price_max=None,
        )
        price_filter = query["bool"]["filter"][0]["range"]["price_amount"]
        assert price_filter == {"gte": 50.0}

    def test_price_max_only(self):
        """Test price filter with only maximum."""
        query = build_search_query(
            q=None,
            manufacturer=None,
            eclass_id=None,
            eclass_segment=None,
            order_unit=None,
            price_min=None,
            price_max=1000.0,
        )
        price_filter = query["bool"]["filter"][0]["range"]["price_amount"]
        assert price_filter == {"lte": 1000.0}

    def test_combined_query_and_filters(self):
        """Test combining text search with multiple filters."""
        query = build_search_query(
            q="Trägerklammer",
            manufacturer="Walraven GmbH",
            eclass_id="23140307",
            eclass_segment=None,
            order_unit=None,
            price_min=100.0,
            price_max=500.0,
        )
        assert "bool" in query
        # Should have text query in must
        assert len(query["bool"]["must"]) == 1
        assert "multi_match" in query["bool"]["must"][0]
        # Should have 3 filters (manufacturer, eclass, price)
        assert len(query["bool"]["filter"]) == 3

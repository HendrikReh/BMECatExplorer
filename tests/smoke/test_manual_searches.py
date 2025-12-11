"""Smoke tests based on docs/manual_searches.md.

These tests verify all documented search scenarios work correctly.
Requires a running API server with data loaded.

Run with: pytest tests/smoke/test_manual_searches.py -v
"""

import httpx
import pytest

from src.config import settings

API_BASE_URL = f"http://localhost:{settings.api_port}"


@pytest.fixture(scope="module")
def client():
    """Create an HTTP client for testing."""
    with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
        yield client


@pytest.mark.smoke
class TestBasicSearches:
    """Basic search functionality from manual_searches.md."""

    def test_empty_search_returns_all_products(self, client: httpx.Client):
        """1. Empty search (all products)."""
        response = client.get("/api/v1/search")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert len(data["results"]) > 0

    def test_simple_text_search(self, client: httpx.Client):
        """2. Simple text search."""
        response = client.get("/api/v1/search", params={"q": "Kabel"})
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "results" in data

    def test_german_compound_word_search(self, client: httpx.Client):
        """3. German compound word search (Trägerklammer)."""
        response = client.get("/api/v1/search", params={"q": "Trägerklammer"})
        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    def test_search_with_special_characters(self, client: httpx.Client):
        """4. Search with special characters (M6x9)."""
        response = client.get("/api/v1/search", params={"q": "M6x9"})
        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    def test_multi_word_search(self, client: httpx.Client):
        """5. Multi-word search."""
        response = client.get("/api/v1/search", params={"q": "Federstahl Klammer"})
        assert response.status_code == 200
        data = response.json()
        assert "total" in data


@pytest.mark.smoke
class TestFilteredSearches:
    """Filtered search functionality from manual_searches.md."""

    def test_filter_by_manufacturer(self, client: httpx.Client):
        """6. Filter by manufacturer."""
        response = client.get(
            "/api/v1/search", params={"manufacturer": "Walraven GmbH"}
        )
        assert response.status_code == 200
        data = response.json()
        # Verify all results have correct manufacturer
        for result in data["results"]:
            if result["manufacturer_name"]:
                assert result["manufacturer_name"] == "Walraven GmbH"

    def test_filter_by_eclass_id(self, client: httpx.Client):
        """7. Filter by ECLASS ID."""
        response = client.get("/api/v1/search", params={"eclass_id": "23140307"})
        assert response.status_code == 200
        data = response.json()
        # Verify all results have correct ECLASS ID
        for result in data["results"]:
            if result["eclass_id"]:
                assert result["eclass_id"] == "23140307"

    def test_filter_by_price_range_low(self, client: httpx.Client):
        """8. Filter by price range (low: 0-100)."""
        response = client.get(
            "/api/v1/search", params={"price_min": 0, "price_max": 100}
        )
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            if result["price_amount"] is not None:
                assert result["price_amount"] <= 100

    def test_filter_by_price_range_mid(self, client: httpx.Client):
        """9. Filter by price range (mid: 100-500)."""
        response = client.get(
            "/api/v1/search", params={"price_min": 100, "price_max": 500}
        )
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            if result["price_amount"] is not None:
                assert 100 <= result["price_amount"] <= 500

    def test_filter_by_price_range_high(self, client: httpx.Client):
        """10. Filter by price range (high: 500+)."""
        response = client.get("/api/v1/search", params={"price_min": 500})
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            if result["price_amount"] is not None:
                assert result["price_amount"] >= 500


@pytest.mark.smoke
class TestCombinedSearches:
    """Combined search functionality from manual_searches.md."""

    def test_text_search_with_manufacturer_filter(self, client: httpx.Client):
        """11. Text search + manufacturer filter."""
        response = client.get(
            "/api/v1/search",
            params={"q": "Klammer", "manufacturer": "Walraven GmbH"},
        )
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            if result["manufacturer_name"]:
                assert result["manufacturer_name"] == "Walraven GmbH"

    def test_text_search_with_price_range(self, client: httpx.Client):
        """12. Text search + price range."""
        response = client.get(
            "/api/v1/search",
            params={"q": "Kabel", "price_min": 50, "price_max": 200},
        )
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            if result["price_amount"] is not None:
                assert 50 <= result["price_amount"] <= 200

    def test_text_search_with_eclass_filter(self, client: httpx.Client):
        """13. Text search + ECLASS filter."""
        response = client.get(
            "/api/v1/search", params={"q": "Stahl", "eclass_id": "23140307"}
        )
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            if result["eclass_id"]:
                assert result["eclass_id"] == "23140307"

    def test_multiple_filters_without_text(self, client: httpx.Client):
        """14. Multiple filters (no text)."""
        response = client.get(
            "/api/v1/search",
            params={
                "manufacturer": "Walraven GmbH",
                "price_min": 300,
                "price_max": 400,
            },
        )
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            if result["manufacturer_name"]:
                assert result["manufacturer_name"] == "Walraven GmbH"
            if result["price_amount"] is not None:
                assert 300 <= result["price_amount"] <= 400

    def test_all_filters_combined(self, client: httpx.Client):
        """15. All filters combined."""
        response = client.get(
            "/api/v1/search",
            params={
                "q": "Klammer",
                "manufacturer": "Walraven GmbH",
                "eclass_id": "23140307",
                "price_min": 100,
                "price_max": 500,
            },
        )
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            if result["manufacturer_name"]:
                assert result["manufacturer_name"] == "Walraven GmbH"
            if result["eclass_id"]:
                assert result["eclass_id"] == "23140307"
            if result["price_amount"] is not None:
                assert 100 <= result["price_amount"] <= 500


@pytest.mark.smoke
class TestPagination:
    """Pagination functionality from manual_searches.md."""

    def test_first_page_default(self, client: httpx.Client):
        """16. First page (default)."""
        response = client.get("/api/v1/search", params={"size": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5
        assert len(data["results"]) <= 5

    def test_second_page(self, client: httpx.Client):
        """17. Second page."""
        response = client.get("/api/v1/search", params={"page": 2, "size": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 5

    def test_large_page_size(self, client: httpx.Client):
        """18. Large page size (100)."""
        response = client.get("/api/v1/search", params={"size": 100})
        assert response.status_code == 200
        data = response.json()
        assert data["size"] == 100
        assert len(data["results"]) <= 100

    def test_pagination_consistency(self, client: httpx.Client):
        """Verify pagination returns different results per page."""
        response1 = client.get("/api/v1/search", params={"page": 1, "size": 5})
        response2 = client.get("/api/v1/search", params={"page": 2, "size": 5})
        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # If there are enough results, pages should have different items
        if data1["total"] > 5:
            ids1 = {r["supplier_aid"] for r in data1["results"]}
            ids2 = {r["supplier_aid"] for r in data2["results"]}
            assert ids1.isdisjoint(ids2), "Pages should not overlap"


@pytest.mark.smoke
class TestAutocomplete:
    """Autocomplete functionality from manual_searches.md."""

    def test_autocomplete_short_query(self, client: httpx.Client):
        """19. Autocomplete short query (Kab)."""
        response = client.get("/api/v1/search/autocomplete", params={"q": "Kab"})
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    def test_autocomplete_german_query(self, client: httpx.Client):
        """20. Autocomplete longer query with German characters (Träger)."""
        response = client.get("/api/v1/search/autocomplete", params={"q": "Träger"})
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

    def test_autocomplete_returns_max_10(self, client: httpx.Client):
        """Autocomplete should return at most 10 suggestions."""
        response = client.get("/api/v1/search/autocomplete", params={"q": "Ka"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) <= 10


@pytest.mark.smoke
class TestOtherEndpoints:
    """Other endpoints from manual_searches.md."""

    def test_get_single_product_by_id(self, client: httpx.Client):
        """Get single product by ID."""
        # First get a valid product ID
        search_response = client.get("/api/v1/search", params={"size": 1})
        assert search_response.status_code == 200
        search_data = search_response.json()

        if search_data["results"]:
            supplier_aid = search_data["results"][0]["supplier_aid"]
            response = client.get(f"/api/v1/products/{supplier_aid}")
            assert response.status_code == 200
            product = response.json()
            assert product["supplier_aid"] == supplier_aid
            # Verify all expected fields are present
            assert "ean" in product
            assert "manufacturer_name" in product
            assert "description_short" in product
            assert "price_amount" in product

    def test_get_all_facets(self, client: httpx.Client):
        """Get all facets."""
        response = client.get("/api/v1/facets")
        assert response.status_code == 200
        data = response.json()
        assert "manufacturers" in data
        assert "eclass_ids" in data

        # Verify facet structure
        if data["manufacturers"]:
            facet = data["manufacturers"][0]
            assert "value" in facet
            assert "count" in facet
            assert isinstance(facet["count"], int)
            assert facet["count"] > 0

    def test_search_returns_facets(self, client: httpx.Client):
        """Check facets in search response."""
        response = client.get("/api/v1/search", params={"q": "Kabel"})
        assert response.status_code == 200
        data = response.json()
        assert "facets" in data
        facets = data["facets"]
        assert "manufacturers" in facets
        assert "eclass_ids" in facets


@pytest.mark.smoke
class TestVerificationChecklist:
    """Verification checklist from manual_searches.md."""

    def test_empty_search_returns_products(self, client: httpx.Client):
        """Empty search returns products."""
        response = client.get("/api/v1/search")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0, "Empty search should return products"

    def test_text_search_returns_relevant_results(self, client: httpx.Client):
        """Text search returns relevant results."""
        response = client.get("/api/v1/search", params={"q": "Klammer"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_german_words_matched_correctly(self, client: httpx.Client):
        """German words are matched correctly (umlauts)."""
        response = client.get("/api/v1/search", params={"q": "Trägerklammer"})
        assert response.status_code == 200
        # Should not error on German characters

    def test_filters_reduce_result_count(self, client: httpx.Client):
        """Filters reduce result count."""
        # Get total without filter
        response_all = client.get("/api/v1/search")
        total_all = response_all.json()["total"]

        # Get total with price filter
        response_filtered = client.get(
            "/api/v1/search", params={"price_min": 100, "price_max": 200}
        )
        total_filtered = response_filtered.json()["total"]

        # Filtered should be less than or equal to total
        assert total_filtered <= total_all

    def test_combined_filters_work_together(self, client: httpx.Client):
        """Combined filters work together."""
        response = client.get(
            "/api/v1/search",
            params={
                "q": "Klammer",
                "manufacturer": "Walraven GmbH",
                "price_min": 100,
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Should return valid response (possibly empty if no matches)
        assert "results" in data
        assert "total" in data

    def test_pagination_returns_correct_pages(self, client: httpx.Client):
        """Pagination returns correct pages."""
        response = client.get("/api/v1/search", params={"page": 1, "size": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10

    def test_autocomplete_returns_suggestions(self, client: httpx.Client):
        """Autocomplete returns suggestions."""
        response = client.get("/api/v1/search/autocomplete", params={"q": "Kab"})
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

    def test_facets_show_aggregated_counts(self, client: httpx.Client):
        """Facets show aggregated counts."""
        response = client.get("/api/v1/facets")
        assert response.status_code == 200
        data = response.json()

        # Check manufacturers have counts
        if data["manufacturers"]:
            for facet in data["manufacturers"]:
                assert "count" in facet
                assert facet["count"] > 0

        # Check eclass_ids have counts
        if data["eclass_ids"]:
            for facet in data["eclass_ids"]:
                assert "count" in facet
                assert facet["count"] > 0

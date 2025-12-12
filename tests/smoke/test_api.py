"""Smoke tests for the API.

These tests require a running API server with data loaded.
Run with: pytest tests/smoke -m smoke

Start the server first:
    uv run uvicorn src.api.app:app --port 9019
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
class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_endpoint(self, client: httpx.Client):
        """Test that health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.smoke
class TestSearchEndpoint:
    """Test search endpoint."""

    def test_search_without_query(self, client: httpx.Client):
        """Test search endpoint without query returns results."""
        response = client.get("/api/v1/search")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "results" in data
        assert "facets" in data
        assert data["page"] == 1
        assert data["size"] == 20

    def test_search_with_query(self, client: httpx.Client):
        """Test search endpoint with text query."""
        response = client.get("/api/v1/search", params={"q": "Kabel"})
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert isinstance(data["results"], list)

    def test_search_with_pagination(self, client: httpx.Client):
        """Test search endpoint with pagination."""
        response = client.get("/api/v1/search", params={"page": 2, "size": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 10

    def test_search_with_manufacturer_filter(self, client: httpx.Client):
        """Test search endpoint with manufacturer filter."""
        response = client.get(
            "/api/v1/search", params={"manufacturer": "Walraven GmbH"}
        )
        assert response.status_code == 200
        data = response.json()
        # All results should have this manufacturer
        for result in data["results"]:
            if result["manufacturer_name"]:
                assert result["manufacturer_name"] == "Walraven GmbH"

    def test_search_with_price_range(self, client: httpx.Client):
        """Test search endpoint with price range filter."""
        response = client.get(
            "/api/v1/search", params={"price_min": 100, "price_max": 500}
        )
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            if result.get("price_unit_amount") is not None:
                assert 100 <= result["price_unit_amount"] <= 500

    def test_search_invalid_page(self, client: httpx.Client):
        """Test search endpoint with invalid page number."""
        response = client.get("/api/v1/search", params={"page": 0})
        assert response.status_code == 422  # Validation error

    def test_search_invalid_size(self, client: httpx.Client):
        """Test search endpoint with invalid size."""
        response = client.get("/api/v1/search", params={"size": 200})
        assert response.status_code == 422  # Validation error

    def test_search_returns_facets(self, client: httpx.Client):
        """Test that search returns facets for filtering."""
        response = client.get("/api/v1/search")
        assert response.status_code == 200
        data = response.json()
        facets = data["facets"]
        assert "manufacturers" in facets
        assert "eclass_ids" in facets
        assert isinstance(facets["manufacturers"], list)


@pytest.mark.smoke
class TestAutocompleteEndpoint:
    """Test autocomplete endpoint."""

    def test_autocomplete_valid_query(self, client: httpx.Client):
        """Test autocomplete with valid query."""
        response = client.get("/api/v1/search/autocomplete", params={"q": "Kab"})
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    def test_autocomplete_minimum_length(self, client: httpx.Client):
        """Test autocomplete requires minimum query length."""
        response = client.get("/api/v1/search/autocomplete", params={"q": "K"})
        assert response.status_code == 422  # Validation error - min_length=2

    def test_autocomplete_missing_query(self, client: httpx.Client):
        """Test autocomplete without query parameter."""
        response = client.get("/api/v1/search/autocomplete")
        assert response.status_code == 422  # Query is required


@pytest.mark.smoke
class TestProductEndpoint:
    """Test single product endpoint."""

    def test_get_product_not_found(self, client: httpx.Client):
        """Test getting a non-existent product."""
        response = client.get("/api/v1/products/NONEXISTENT_PRODUCT_ID")
        assert response.status_code == 404

    def test_get_product_valid(self, client: httpx.Client):
        """Test getting a valid product (requires data to be loaded)."""
        # First, get a valid product ID from search
        search_response = client.get("/api/v1/search", params={"size": 1})
        if search_response.status_code == 200:
            data = search_response.json()
            if data["results"]:
                supplier_aid = data["results"][0]["supplier_aid"]
                response = client.get(f"/api/v1/products/{supplier_aid}")
                assert response.status_code == 200
                product = response.json()
                assert product["supplier_aid"] == supplier_aid


@pytest.mark.smoke
class TestFacetsEndpoint:
    """Test facets endpoint."""

    def test_get_facets(self, client: httpx.Client):
        """Test getting all facets."""
        response = client.get("/api/v1/facets")
        assert response.status_code == 200
        data = response.json()
        assert "manufacturers" in data
        assert "eclass_ids" in data
        # Each facet should have value and count
        if data["manufacturers"]:
            assert "value" in data["manufacturers"][0]
            assert "count" in data["manufacturers"][0]


@pytest.mark.smoke
class TestOpenAPIDocs:
    """Test API documentation endpoints."""

    def test_openapi_json(self, client: httpx.Client):
        """Test OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_swagger_ui(self, client: httpx.Client):
        """Test Swagger UI is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()

    def test_redoc(self, client: httpx.Client):
        """Test ReDoc is available."""
        response = client.get("/redoc")
        assert response.status_code == 200

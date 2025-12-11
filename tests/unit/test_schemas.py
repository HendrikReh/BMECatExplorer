"""Unit tests for API schemas."""

import pytest
from pydantic import ValidationError

from src.api.schemas import (
    AutocompleteResponse,
    FacetBucket,
    Facets,
    ProductResult,
    SearchRequest,
    SearchResponse,
)


@pytest.mark.unit
class TestProductResult:
    """Tests for ProductResult schema."""

    def test_full_product(self):
        """Test creating a product with all fields."""
        product = ProductResult(
            supplier_aid="1000864",
            ean="8712993543250",
            manufacturer_aid="50320009",
            manufacturer_name="Walraven GmbH",
            description_short="Test product",
            description_long="Long description",
            eclass_id="23140307",
            price_amount=360.48,
            price_currency="EUR",
            image="test.jpg",
        )
        assert product.supplier_aid == "1000864"
        assert product.price_amount == 360.48

    def test_minimal_product(self):
        """Test creating a product with only required fields."""
        product = ProductResult(supplier_aid="TEST001")
        assert product.supplier_aid == "TEST001"
        assert product.ean is None
        assert product.price_amount is None

    def test_product_serialization(self):
        """Test product JSON serialization."""
        product = ProductResult(
            supplier_aid="TEST001",
            price_amount=100.50,
        )
        data = product.model_dump()
        assert data["supplier_aid"] == "TEST001"
        assert data["price_amount"] == 100.50


@pytest.mark.unit
class TestSearchRequest:
    """Tests for SearchRequest schema."""

    def test_default_values(self):
        """Test default pagination values."""
        request = SearchRequest()
        assert request.q is None
        assert request.page == 1
        assert request.size == 20

    def test_valid_request(self):
        """Test valid search request."""
        request = SearchRequest(
            q="Kabel",
            manufacturer="Walraven GmbH",
            price_min=10.0,
            price_max=500.0,
            page=2,
            size=50,
        )
        assert request.q == "Kabel"
        assert request.manufacturer == "Walraven GmbH"
        assert request.price_min == 10.0
        assert request.page == 2

    def test_invalid_page(self):
        """Test that page must be >= 1."""
        with pytest.raises(ValidationError):
            SearchRequest(page=0)

    def test_invalid_size(self):
        """Test that size must be between 1 and 100."""
        with pytest.raises(ValidationError):
            SearchRequest(size=0)
        with pytest.raises(ValidationError):
            SearchRequest(size=101)

    def test_invalid_price_min(self):
        """Test that price_min must be >= 0."""
        with pytest.raises(ValidationError):
            SearchRequest(price_min=-10)


@pytest.mark.unit
class TestSearchResponse:
    """Tests for SearchResponse schema."""

    def test_empty_response(self):
        """Test empty search response."""
        response = SearchResponse(
            total=0,
            page=1,
            size=20,
            results=[],
            facets=Facets(),
        )
        assert response.total == 0
        assert len(response.results) == 0

    def test_response_with_results(self):
        """Test search response with results and facets."""
        response = SearchResponse(
            total=100,
            page=1,
            size=20,
            results=[
                ProductResult(supplier_aid="TEST001"),
                ProductResult(supplier_aid="TEST002"),
            ],
            facets=Facets(
                manufacturers=[FacetBucket(value="Walraven GmbH", count=50)],
                eclass_ids=[FacetBucket(value="23140307", count=30)],
            ),
        )
        assert response.total == 100
        assert len(response.results) == 2
        assert len(response.facets.manufacturers) == 1
        assert response.facets.manufacturers[0].value == "Walraven GmbH"


@pytest.mark.unit
class TestAutocompleteResponse:
    """Tests for AutocompleteResponse schema."""

    def test_empty_suggestions(self):
        """Test empty autocomplete response."""
        response = AutocompleteResponse(suggestions=[])
        assert len(response.suggestions) == 0

    def test_with_suggestions(self):
        """Test autocomplete with suggestions."""
        response = AutocompleteResponse(
            suggestions=["Kabel 3x1.5", "Kabel 5x2.5", "Kabelbinder"]
        )
        assert len(response.suggestions) == 3
        assert "Kabel 3x1.5" in response.suggestions

"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field


class ProductResult(BaseModel):
    """Product in search results."""

    supplier_aid: str = Field(..., description="Unique supplier article ID", example="1000864")
    ean: str | None = Field(None, description="European Article Number (barcode)", example="8712993543250")
    manufacturer_aid: str | None = Field(None, description="Manufacturer's article ID", example="50320009")
    manufacturer_name: str | None = Field(None, description="Manufacturer name", example="Walraven GmbH")
    description_short: str | None = Field(None, description="Short product description", example="Trägerklammer 5-9mm")
    description_long: str | None = Field(None, description="Detailed product description")
    eclass_id: str | None = Field(None, description="ECLASS classification ID", example="23140307")
    price_amount: float | None = Field(None, description="Product price", example=360.48)
    price_currency: str | None = Field(None, description="Price currency (ISO 4217)", example="EUR")
    image: str | None = Field(None, description="Product image filename", example="1000864.jpg")


class FacetBucket(BaseModel):
    """A single facet value with count."""

    value: str = Field(..., description="Facet value (e.g., manufacturer name)", example="Walraven GmbH")
    count: int = Field(..., description="Number of products with this value", example=150)


class Facets(BaseModel):
    """Available facet values for filtering."""

    manufacturers: list[FacetBucket] = Field(default=[], description="Manufacturer names with product counts")
    eclass_ids: list[FacetBucket] = Field(default=[], description="ECLASS IDs with product counts")


class SearchResponse(BaseModel):
    """Paginated search results with facets."""

    total: int = Field(..., description="Total number of matching products", example=1250)
    page: int = Field(..., description="Current page number", example=1)
    size: int = Field(..., description="Number of results per page", example=20)
    results: list[ProductResult] = Field(..., description="List of matching products")
    facets: Facets = Field(..., description="Aggregated facet counts for filtering")


class AutocompleteResponse(BaseModel):
    """Autocomplete suggestions for search."""

    suggestions: list[str] = Field(..., description="List of matching product descriptions", example=["Kabel 3x1.5mm", "Kabelbinder"])


class SearchRequest(BaseModel):
    """Search query parameters."""

    q: str | None = Field(None, description="Search query text")
    manufacturer: str | None = Field(None, description="Filter by manufacturer name")
    eclass_id: str | None = Field(None, description="Filter by ECLASS ID")
    price_min: float | None = Field(None, ge=0, description="Minimum price filter")
    price_max: float | None = Field(None, ge=0, description="Maximum price filter")
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Results per page")

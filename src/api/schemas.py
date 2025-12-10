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


class ScoredProductResult(ProductResult):
    """Product result with relevance scores for hybrid search."""

    # Provenance fields
    catalog_id: str | None = Field(None, description="Catalog namespace identifier")
    source_uri: str | None = Field(None, description="Provenance URI for citation")

    # Relevance scores
    score: float | None = Field(None, description="Combined relevance score")
    bm25_score: float | None = Field(None, description="BM25 lexical match score")
    vector_score: float | None = Field(None, description="Vector similarity score (cosine)")

    # Optional embedding text for debugging
    embedding_text: str | None = Field(None, description="Text used to generate embedding")


class FacetBucket(BaseModel):
    """A single facet value with count."""

    value: str = Field(..., description="Facet value (e.g., manufacturer name)", example="Walraven GmbH")
    count: int = Field(..., description="Number of products with this value", example=150)


class Facets(BaseModel):
    """Available facet values for filtering."""

    manufacturers: list[FacetBucket] = Field(default=[], description="Manufacturer names with product counts")
    eclass_ids: list[FacetBucket] = Field(default=[], description="ECLASS IDs with product counts")
    catalogs: list[FacetBucket] = Field(default=[], description="Catalog IDs with product counts")


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


# === Hybrid Search Schemas (for projectAlpha integration) ===


class HybridSearchRequest(BaseModel):
    """Hybrid search request combining BM25 and vector search."""

    q: str = Field(..., min_length=1, description="Natural language search query")
    embedding: list[float] | None = Field(
        None,
        description="Pre-computed query embedding (1536 dimensions). If not provided, server generates it.",
    )

    # Search mode
    mode: str = Field(
        "hybrid",
        description="Search mode: 'bm25' (lexical only), 'vector' (semantic only), 'hybrid' (combined)",
    )

    # RRF fusion parameters
    rrf_k: int = Field(60, ge=1, le=100, description="RRF constant k (higher = smoother ranking)")
    bm25_weight: float = Field(0.5, ge=0, le=1, description="Weight for BM25 score in hybrid mode")
    vector_weight: float = Field(0.5, ge=0, le=1, description="Weight for vector score in hybrid mode")

    # Filters
    catalog_id: str | None = Field(None, description="Filter by catalog namespace")
    manufacturer: str | None = Field(None, description="Filter by manufacturer name")
    eclass_id: str | None = Field(None, description="Filter by exact ECLASS ID")
    eclass_prefix: str | None = Field(None, description="Filter by ECLASS prefix (hierarchy)")
    price_min: float | None = Field(None, ge=0, description="Minimum price filter")
    price_max: float | None = Field(None, ge=0, description="Maximum price filter")

    # Pagination
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    size: int = Field(20, ge=1, le=100, description="Results per page")

    # Response options
    include_scores: bool = Field(True, description="Include individual BM25 and vector scores")
    include_embedding_text: bool = Field(False, description="Include text used for embedding")
    include_facets: bool = Field(True, description="Include facet aggregations")


class HybridSearchResponse(BaseModel):
    """Hybrid search response with scores and provenance."""

    total: int = Field(..., description="Total matching products")
    page: int = Field(..., description="Current page")
    size: int = Field(..., description="Results per page")
    mode: str = Field(..., description="Search mode used")
    results: list[ScoredProductResult] = Field(..., description="Scored results")
    facets: Facets | None = Field(None, description="Facet aggregations (if requested)")

    # Timing for observability
    took_ms: int | None = Field(None, description="Query execution time in milliseconds")


class BatchSearchQuery(BaseModel):
    """Single query in a batch request."""

    q: str = Field(..., min_length=1, description="Search query")
    embedding: list[float] | None = Field(None, description="Pre-computed query embedding")
    catalog_id: str | None = Field(None, description="Filter by catalog")
    size: int = Field(10, ge=1, le=50, description="Results per query")


class BatchSearchRequest(BaseModel):
    """Batch multiple search queries in one request."""

    queries: list[BatchSearchQuery] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of queries (max 10)",
    )
    mode: str = Field("hybrid", description="Search mode for all queries")
    include_scores: bool = Field(True, description="Include relevance scores")


class BatchSearchResult(BaseModel):
    """Results for a single query in batch response."""

    query: str = Field(..., description="Original query text")
    total: int = Field(..., description="Total matches")
    results: list[ScoredProductResult] = Field(..., description="Top results")


class BatchSearchResponse(BaseModel):
    """Response for batch search."""

    results: list[BatchSearchResult] = Field(..., description="Results per query")
    took_ms: int | None = Field(None, description="Total execution time")


class CatalogInfo(BaseModel):
    """Information about a catalog namespace."""

    catalog_id: str = Field(..., description="Catalog identifier")
    product_count: int = Field(..., description="Number of products in catalog")
    source_file: str | None = Field(None, description="Original source file")
    has_embeddings: bool = Field(..., description="Whether products have embeddings")


class CatalogListResponse(BaseModel):
    """List of available catalogs."""

    catalogs: list[CatalogInfo] = Field(..., description="Available catalogs")
    total_products: int = Field(..., description="Total products across all catalogs")

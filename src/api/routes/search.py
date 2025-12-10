"""Search API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from opensearchpy import NotFoundError

from src.api.schemas import (
    AutocompleteResponse,
    Facets,
    FacetBucket,
    ProductResult,
    SearchResponse,
)
from src.config import settings
from src.search.client import client

router = APIRouter(prefix="/api/v1", tags=["search"])


def build_search_query(
    q: str | None,
    manufacturer: str | None,
    eclass_id: str | None,
    price_min: float | None,
    price_max: float | None,
) -> dict:
    """Build OpenSearch query from parameters."""
    must = []
    filter_clauses = []

    # Full-text search
    if q:
        must.append(
            {
                "multi_match": {
                    "query": q,
                    "fields": [
                        "description_short^3",
                        "description_long",
                        "manufacturer_name^2",
                        "supplier_aid",
                        "ean",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        )

    # Manufacturer filter
    if manufacturer:
        filter_clauses.append({"term": {"manufacturer_name.keyword": manufacturer}})

    # ECLASS filter
    if eclass_id:
        filter_clauses.append({"term": {"eclass_id": eclass_id}})

    # Price range filter
    if price_min is not None or price_max is not None:
        price_range = {}
        if price_min is not None:
            price_range["gte"] = price_min
        if price_max is not None:
            price_range["lte"] = price_max
        filter_clauses.append({"range": {"price_amount": price_range}})

    # Build final query
    if must or filter_clauses:
        query = {
            "bool": {
                "must": must if must else [{"match_all": {}}],
                "filter": filter_clauses,
            }
        }
    else:
        query = {"match_all": {}}

    return query


@router.get("/search", response_model=SearchResponse, summary="Search products")
async def search_products(
    q: str | None = Query(None, description="Full-text search query. Searches in description, manufacturer name, supplier ID, and EAN.", examples=["Kabel"]),
    manufacturer: str | None = Query(None, description="Filter by exact manufacturer name", examples=["Walraven GmbH"]),
    eclass_id: str | None = Query(None, description="Filter by ECLASS classification ID", examples=["23140307"]),
    price_min: float | None = Query(None, ge=0, description="Minimum price filter (inclusive)", examples=[100]),
    price_max: float | None = Query(None, ge=0, description="Maximum price filter (inclusive)", examples=[500]),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Number of results per page (max 100)"),
) -> SearchResponse:
    """
    Search products with full-text search and faceted filtering.

    - **Full-text search**: Uses German analyzer with fuzzy matching
    - **Filters**: Can be combined with text search
    - **Facets**: Returns aggregated counts for manufacturers and ECLASS IDs
    - **Pagination**: Use page and size parameters

    Returns matching products sorted by relevance score.
    """
    query = build_search_query(q, manufacturer, eclass_id, price_min, price_max)

    body = {
        "query": query,
        "from": (page - 1) * size,
        "size": size,
        "aggs": {
            "manufacturers": {
                "terms": {"field": "manufacturer_name.keyword", "size": 50}
            },
            "eclass_ids": {"terms": {"field": "eclass_id", "size": 50}},
        },
    }

    response = client.search(index=settings.opensearch_index, body=body)

    # Parse results
    hits = response["hits"]
    results = []
    for hit in hits["hits"]:
        source = hit["_source"]
        results.append(
            ProductResult(
                supplier_aid=source.get("supplier_aid"),
                ean=source.get("ean"),
                manufacturer_aid=source.get("manufacturer_aid"),
                manufacturer_name=source.get("manufacturer_name"),
                description_short=source.get("description_short"),
                description_long=source.get("description_long"),
                eclass_id=source.get("eclass_id"),
                price_amount=source.get("price_amount"),
                price_currency=source.get("price_currency"),
                image=source.get("image"),
            )
        )

    # Parse facets
    aggs = response.get("aggregations", {})
    facets = Facets(
        manufacturers=[
            FacetBucket(value=b["key"], count=b["doc_count"])
            for b in aggs.get("manufacturers", {}).get("buckets", [])
        ],
        eclass_ids=[
            FacetBucket(value=b["key"], count=b["doc_count"])
            for b in aggs.get("eclass_ids", {}).get("buckets", [])
        ],
    )

    return SearchResponse(
        total=hits["total"]["value"],
        page=page,
        size=size,
        results=results,
        facets=facets,
    )


@router.get("/search/autocomplete", response_model=AutocompleteResponse, summary="Autocomplete suggestions")
async def autocomplete(
    q: str = Query(..., min_length=2, description="Partial search term (minimum 2 characters)", examples=["Kab"]),
) -> AutocompleteResponse:
    """
    Get autocomplete suggestions for search terms.

    Returns up to 10 product descriptions matching the partial query.
    Uses edge n-gram tokenization for fast prefix matching.
    """
    body = {
        "query": {
            "match": {
                "description_short.autocomplete": {
                    "query": q,
                    "operator": "and",
                }
            }
        },
        "size": 10,
        "_source": ["description_short"],
    }

    response = client.search(index=settings.opensearch_index, body=body)

    # Extract unique suggestions
    suggestions = []
    seen = set()
    for hit in response["hits"]["hits"]:
        desc = hit["_source"].get("description_short", "")
        if desc and desc not in seen:
            suggestions.append(desc)
            seen.add(desc)

    return AutocompleteResponse(suggestions=suggestions[:10])


@router.get("/products/{supplier_aid}", response_model=ProductResult, summary="Get product by ID")
async def get_product(supplier_aid: str) -> ProductResult:
    """
    Get a single product by supplier article ID.

    Returns the full product details including price and image information.
    Returns 404 if the product is not found.
    """
    try:
        response = client.get(index=settings.opensearch_index, id=supplier_aid)
        source = response["_source"]
        return ProductResult(
            supplier_aid=source.get("supplier_aid"),
            ean=source.get("ean"),
            manufacturer_aid=source.get("manufacturer_aid"),
            manufacturer_name=source.get("manufacturer_name"),
            description_short=source.get("description_short"),
            description_long=source.get("description_long"),
            eclass_id=source.get("eclass_id"),
            price_amount=source.get("price_amount"),
            price_currency=source.get("price_currency"),
            image=source.get("image"),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail="Product not found") from e


@router.get("/facets", response_model=Facets, summary="Get filter options")
async def get_facets() -> Facets:
    """
    Get all available facet values for filtering.

    Returns aggregated counts for:
    - **manufacturers**: Top 100 manufacturer names with product counts
    - **eclass_ids**: Top 100 ECLASS classification IDs with product counts

    Use these values to populate filter dropdowns in the UI.
    """
    body = {
        "size": 0,
        "aggs": {
            "manufacturers": {
                "terms": {"field": "manufacturer_name.keyword", "size": 100}
            },
            "eclass_ids": {"terms": {"field": "eclass_id", "size": 100}},
        },
    }

    response = client.search(index=settings.opensearch_index, body=body)
    aggs = response.get("aggregations", {})

    return Facets(
        manufacturers=[
            FacetBucket(value=b["key"], count=b["doc_count"])
            for b in aggs.get("manufacturers", {}).get("buckets", [])
        ],
        eclass_ids=[
            FacetBucket(value=b["key"], count=b["doc_count"])
            for b in aggs.get("eclass_ids", {}).get("buckets", [])
        ],
    )

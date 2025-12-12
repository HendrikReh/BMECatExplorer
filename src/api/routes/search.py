"""Search API endpoints."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from src.api.schemas import (
    AutocompleteResponse,
    FacetBucket,
    Facets,
    PriceBandBucket,
    ProductResult,
    SearchResponse,
)
from src.config import settings
from src.eclass.names import get_eclass_name
from src.search.client import client
from src.search.constants import (
    ECLASS_SEGMENTS,
    ORDER_UNIT_LABELS,
    PRICE_BANDS,
    build_price_band_aggs,
)

router = APIRouter(prefix="/api/v1", tags=["search"])


def build_search_query(
    q: str | None,
    manufacturers: list[str] | None,
    eclass_ids: list[str] | None,
    eclass_segments: list[str] | None,
    order_units: list[str] | None,
    price_min: float | None,
    price_max: float | None,
    exact_match: bool = False,
    catalog_ids: list[str] | None = None,
) -> dict:
    """Build OpenSearch query from parameters."""
    must = []
    filter_clauses = []

    # Full-text search
    if q:
        if exact_match:
            # Exact match: search in keyword fields for exact value
            must.append(
                {
                    "bool": {
                        "should": [
                            {"term": {"ean": q}},
                            {"term": {"supplier_aid": q}},
                            {"term": {"manufacturer_aid": q}},
                            {"term": {"description_short.keyword": q}},
                            {"term": {"manufacturer_name.keyword": q}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        else:
            # Fuzzy full-text search
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

    # Manufacturer filter (supports multiple with OR)
    if manufacturers:
        if len(manufacturers) == 1:
            filter_clauses.append(
                {"term": {"manufacturer_name.keyword": manufacturers[0]}}
            )
        else:
            filter_clauses.append(
                {"terms": {"manufacturer_name.keyword": manufacturers}}
            )

    # ECLASS filter (supports multiple with OR)
    if eclass_ids:
        if len(eclass_ids) == 1:
            filter_clauses.append({"term": {"eclass_id": eclass_ids[0]}})
        else:
            filter_clauses.append({"terms": {"eclass_id": eclass_ids}})

    # ECLASS segment filter (prefix match on first 2 digits) - supports multiple
    if eclass_segments:
        if len(eclass_segments) == 1:
            filter_clauses.append({"prefix": {"eclass_id": eclass_segments[0]}})
        else:
            # OR query for multiple segments
            segment_should = [
                {"prefix": {"eclass_id": seg}} for seg in eclass_segments
            ]
            filter_clauses.append({"bool": {"should": segment_should}})

    # Order unit filter (supports multiple with OR)
    if order_units:
        if len(order_units) == 1:
            filter_clauses.append({"term": {"order_unit": order_units[0]}})
        else:
            filter_clauses.append({"terms": {"order_unit": order_units}})

    # Price range filter
    if price_min is not None or price_max is not None:
        price_range = {}
        if price_min is not None:
            price_range["gte"] = price_min
        if price_max is not None:
            price_range["lte"] = price_max
        filter_clauses.append({"range": {"price_unit_amount": price_range}})

    # Catalog filter (supports multiple with OR)
    if catalog_ids:
        if len(catalog_ids) == 1:
            filter_clauses.append({"term": {"catalog_id": catalog_ids[0]}})
        else:
            filter_clauses.append({"terms": {"catalog_id": catalog_ids}})

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
    q: str | None = Query(
        None,
        description=(
            "Full-text search query. Searches in description, manufacturer name, "
            "supplier ID, and EAN."
        ),
        examples=["Kabel"],
    ),
    manufacturer: list[str] | None = Query(
        None,
        description="Filter by manufacturer name(s). Can specify multiple.",
        examples=["Walraven GmbH"],
    ),
    eclass_id: list[str] | None = Query(
        None,
        description="Filter by ECLASS classification ID(s). Can specify multiple.",
        examples=["23140307"],
    ),
    eclass_segment: list[str] | None = Query(
        None,
        description="Filter by ECLASS segment(s) (2-digit prefix). Multiple allowed.",
        examples=["27"],
    ),
    order_unit: list[str] | None = Query(
        None,
        description="Filter by order unit(s) (C62=piece, MTR=meter, etc.). Multiple.",
        examples=["C62"],
    ),
    price_min: float | None = Query(
        None, ge=0, description="Minimum price filter (inclusive)", examples=[100]
    ),
    price_max: float | None = Query(
        None, ge=0, description="Maximum price filter (inclusive)", examples=[500]
    ),
    price_band: str | None = Query(
        None,
        description="Filter by price band (0-10, 10-50, 50-200, 200-1000, 1000+)",
        examples=["50-200"],
    ),
    catalog_id: list[str] | None = Query(
        None,
        description="Filter by catalog namespace(s). Multiple allowed.",
        examples=["default"],
    ),
    exact_match: bool = Query(
        False,
        description="If true, search for exact matches on EAN, supplier ID, etc.",
    ),
    sort_by: str | None = Query(
        None,
        description=(
            "Optional sort field. Supported: supplier_aid, manufacturer_name, "
            "eclass_id, price_unit_amount."
        ),
        examples=["price_unit_amount"],
    ),
    sort_order: Literal["asc", "desc"] | None = Query(
        None, description="Sort order for sort_by (asc or desc)."
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(
        20, ge=1, le=100, description="Number of results per page (max 100)"
    ),
) -> SearchResponse:
    """
    Search products with full-text search and faceted filtering.

    - **Full-text search**: Uses German analyzer with fuzzy matching
    - **Filters**: Can be combined with text search
    - **Facets**: Returns aggregated counts for manufacturers, ECLASS, order units,
      price bands
    - **Pagination**: Use page and size parameters

    Returns matching products sorted by relevance score.
    """
    # Handle price_band filter - convert to price_min/price_max
    if price_band:
        for band in PRICE_BANDS:
            if band["key"] == price_band:
                if price_min is None:
                    price_min = band["from"]
                if price_max is None and band["to"] is not None:
                    price_max = band["to"]
                break

    # Filter out empty strings from list parameters
    eclass_segments = [s for s in (eclass_segment or []) if s] or None
    manufacturers = [m for m in (manufacturer or []) if m] or None
    eclass_ids = [e for e in (eclass_id or []) if e] or None
    order_units = [u for u in (order_unit or []) if u] or None
    catalog_ids = [c for c in (catalog_id or []) if c] or None

    query = build_search_query(
        q,
        manufacturers,
        eclass_ids,
        eclass_segments,
        order_units,
        price_min,
        price_max,
        exact_match,
        catalog_ids=catalog_ids,
    )

    body = {
        "query": query,
        "from": (page - 1) * size,
        "size": size,
        "track_total_hits": True,
        "aggs": {
            "manufacturers": {
                "terms": {"field": "manufacturer_name.keyword", "size": 1500}
            },
            "eclass_ids": {"terms": {"field": "eclass_id", "size": 1500}},
            "eclass_segments": {
                "terms": {
                    "field": "eclass_id",
                    "size": 50,
                    "script": "_value.substring(0, 2)",
                }
            },
            "order_units": {"terms": {"field": "order_unit", "size": 50}},
            "price_bands": build_price_band_aggs(),
            "catalogs": {"terms": {"field": "catalog_id", "size": 100}},
        },
    }

    if sort_by:
        sort_fields = {
            "supplier_aid": "supplier_aid",
            "manufacturer_name": "manufacturer_name.keyword",
            "eclass_id": "eclass_id",
            "price_unit_amount": "price_unit_amount",
        }
        field = sort_fields.get(sort_by)
        if field is None:
            supported = ", ".join(sort_fields)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort_by '{sort_by}'. Supported: {supported}",
            )
        order = sort_order or "asc"
        sort_clause: dict = {field: {"order": order, "missing": "_last"}}
        body["sort"] = [sort_clause]

    response = await run_in_threadpool(
        client.search, index=settings.opensearch_index, body=body
    )

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
                eclass_name=get_eclass_name(source.get("eclass_id")),
                price_amount=source.get("price_amount"),
                price_unit_amount=source.get("price_unit_amount"),
                price_currency=source.get("price_currency"),
                price_quantity=source.get("price_quantity"),
                image=source.get("image"),
                catalog_id=source.get("catalog_id"),
                source_uri=source.get("source_uri"),
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
            FacetBucket(
                value=b["key"],
                name=get_eclass_name(b["key"]),
                count=b["doc_count"],
            )
            for b in aggs.get("eclass_ids", {}).get("buckets", [])
        ],
        eclass_segments=[
            FacetBucket(
                value=b["key"],
                name=ECLASS_SEGMENTS.get(b["key"], f"Segment {b['key']}"),
                count=b["doc_count"],
            )
            for b in aggs.get("eclass_segments", {}).get("buckets", [])
        ],
        order_units=[
            FacetBucket(
                value=b["key"],
                name=ORDER_UNIT_LABELS.get(b["key"], b["key"]),
                count=b["doc_count"],
            )
            for b in aggs.get("order_units", {}).get("buckets", [])
        ],
        price_bands=[
            PriceBandBucket(
                key=b["key"],
                label=next(
                    (pb["label"] for pb in PRICE_BANDS if pb["key"] == b["key"]),
                    b["key"],
                ),
                from_value=b.get("from"),
                to_value=b.get("to"),
                count=b["doc_count"],
            )
            for b in aggs.get("price_bands", {}).get("buckets", [])
        ],
        catalogs=[
            FacetBucket(value=b["key"], count=b["doc_count"])
            for b in aggs.get("catalogs", {}).get("buckets", [])
        ],
    )

    return SearchResponse(
        total=hits["total"]["value"],
        page=page,
        size=size,
        results=results,
        facets=facets,
    )


@router.get(
    "/search/autocomplete",
    response_model=AutocompleteResponse,
    summary="Autocomplete suggestions",
)
async def autocomplete(
    q: str = Query(
        ...,
        min_length=2,
        description="Partial search term (minimum 2 characters)",
        examples=["Kab"],
    ),
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

    response = await run_in_threadpool(
        client.search, index=settings.opensearch_index, body=body
    )

    # Extract unique suggestions
    suggestions = []
    seen = set()
    for hit in response["hits"]["hits"]:
        desc = hit["_source"].get("description_short", "")
        if desc and desc not in seen:
            suggestions.append(desc)
            seen.add(desc)

    return AutocompleteResponse(suggestions=suggestions[:10])


@router.get(
    "/products/{supplier_aid}",
    response_model=ProductResult,
    summary="Get product by ID",
)
async def get_product(
    supplier_aid: str,
    catalog_id: str | None = Query(
        None,
        description="Optional catalog namespace to disambiguate duplicate IDs",
    ),
) -> ProductResult:
    """Get a single product by supplier article ID.

    If multiple catalogs contain the same supplier_aid, pass catalog_id.
    Without catalog_id, the endpoint prefers the 'default' catalog.
    """

    async def do_search(body: dict) -> dict:
        return await run_in_threadpool(
            client.search, index=settings.opensearch_index, body=body
        )

    if catalog_id:
        body = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"supplier_aid": supplier_aid}},
                        {"term": {"catalog_id": catalog_id}},
                    ]
                }
            },
            "size": 1,
        }
        response = await do_search(body)
    else:
        # Prefer default catalog if present.
        body_default = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"supplier_aid": supplier_aid}},
                        {"term": {"catalog_id": "default"}},
                    ]
                }
            },
            "size": 1,
        }
        response = await do_search(body_default)
        if not response["hits"]["hits"]:
            body_any = {"query": {"term": {"supplier_aid": supplier_aid}}, "size": 1}
            response = await do_search(body_any)

    hits = response["hits"]["hits"]
    if not hits:
        raise HTTPException(status_code=404, detail="Product not found")

    source = hits[0]["_source"]
    return ProductResult(
        supplier_aid=source.get("supplier_aid"),
        ean=source.get("ean"),
        manufacturer_aid=source.get("manufacturer_aid"),
        manufacturer_name=source.get("manufacturer_name"),
        description_short=source.get("description_short"),
        description_long=source.get("description_long"),
        eclass_id=source.get("eclass_id"),
        eclass_name=get_eclass_name(source.get("eclass_id")),
        price_amount=source.get("price_amount"),
        price_unit_amount=source.get("price_unit_amount"),
        price_currency=source.get("price_currency"),
        price_quantity=source.get("price_quantity"),
        image=source.get("image"),
        catalog_id=source.get("catalog_id"),
        source_uri=source.get("source_uri"),
    )


@router.get("/facets", response_model=Facets, summary="Get filter options")
async def get_facets() -> Facets:
    """
    Get all available facet values for filtering.

    Returns aggregated counts for:
    - **manufacturers**: Top 100 manufacturer names with product counts
    - **eclass_ids**: Top 100 ECLASS classification IDs with product counts
    - **eclass_segments**: ECLASS segments (first 2 digits) with names
    - **order_units**: Order units (C62=piece, MTR=meter, etc.)
    - **price_bands**: Price range bands

    Use these values to populate filter dropdowns in the UI.
    """
    body = {
        "size": 0,
        "aggs": {
            "manufacturers": {
                "terms": {"field": "manufacturer_name.keyword", "size": 1500}
            },
            "eclass_ids": {"terms": {"field": "eclass_id", "size": 1500}},
            "eclass_segments": {
                "terms": {
                    "field": "eclass_id",
                    "size": 50,
                    "script": "_value.substring(0, 2)",
                }
            },
            "order_units": {"terms": {"field": "order_unit", "size": 50}},
            "price_bands": build_price_band_aggs(),
            "catalogs": {"terms": {"field": "catalog_id", "size": 100}},
        },
    }

    response = await run_in_threadpool(
        client.search, index=settings.opensearch_index, body=body
    )
    aggs = response.get("aggregations", {})

    return Facets(
        manufacturers=[
            FacetBucket(value=b["key"], count=b["doc_count"])
            for b in aggs.get("manufacturers", {}).get("buckets", [])
        ],
        eclass_ids=[
            FacetBucket(
                value=b["key"],
                name=get_eclass_name(b["key"]),
                count=b["doc_count"],
            )
            for b in aggs.get("eclass_ids", {}).get("buckets", [])
        ],
        eclass_segments=[
            FacetBucket(
                value=b["key"],
                name=ECLASS_SEGMENTS.get(b["key"], f"Segment {b['key']}"),
                count=b["doc_count"],
            )
            for b in aggs.get("eclass_segments", {}).get("buckets", [])
        ],
        order_units=[
            FacetBucket(
                value=b["key"],
                name=ORDER_UNIT_LABELS.get(b["key"], b["key"]),
                count=b["doc_count"],
            )
            for b in aggs.get("order_units", {}).get("buckets", [])
        ],
        price_bands=[
            PriceBandBucket(
                key=b["key"],
                label=next(
                    (pb["label"] for pb in PRICE_BANDS if pb["key"] == b["key"]),
                    b["key"],
                ),
                from_value=b.get("from"),
                to_value=b.get("to"),
                count=b["doc_count"],
            )
            for b in aggs.get("price_bands", {}).get("buckets", [])
        ],
        catalogs=[
            FacetBucket(value=b["key"], count=b["doc_count"])
            for b in aggs.get("catalogs", {}).get("buckets", [])
        ],
    )

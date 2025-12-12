"""Hybrid search endpoints optimized for RAG retrieval."""

import logging
import time

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from src.api.schemas import (
    BatchSearchRequest,
    BatchSearchResponse,
    BatchSearchResult,
    CatalogInfo,
    CatalogListResponse,
    FacetBucket,
    Facets,
    HybridSearchRequest,
    HybridSearchResponse,
    ScoredProductResult,
)
from src.config import settings
from src.eclass.names import get_eclass_name
from src.search.client import client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["hybrid"])


def build_filters(
    catalog_id: str | None,
    manufacturer: str | None,
    eclass_id: str | None,
    eclass_prefix: str | None,
    price_min: float | None,
    price_max: float | None,
) -> list[dict]:
    """Build OpenSearch filter clauses from search parameters.

    Args:
        catalog_id: Filter by catalog namespace.
        manufacturer: Filter by exact manufacturer name.
        eclass_id: Filter by exact ECLASS ID.
        eclass_prefix: Filter by ECLASS prefix (hierarchy).
        price_min: Minimum price filter.
        price_max: Maximum price filter.

    Returns:
        List of OpenSearch filter clause dictionaries.
    """
    filters = []

    if catalog_id:
        filters.append({"term": {"catalog_id": catalog_id}})

    if manufacturer:
        filters.append({"term": {"manufacturer_name.keyword": manufacturer}})

    if eclass_id:
        filters.append({"term": {"eclass_id": eclass_id}})
    elif eclass_prefix:
        filters.append({"prefix": {"eclass_id": eclass_prefix}})

    if price_min is not None or price_max is not None:
        price_range = {}
        if price_min is not None:
            price_range["gte"] = price_min
        if price_max is not None:
            price_range["lte"] = price_max
        filters.append({"range": {"price_unit_amount": price_range}})

    return filters


def build_bm25_query(q: str, filters: list[dict]) -> dict:
    """Build BM25 full-text search query.

    Args:
        q: Search query text.
        filters: List of filter clauses to apply.

    Returns:
        OpenSearch bool query with multi_match and filters.
    """
    must = [
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
    ]

    return {"bool": {"must": must, "filter": filters}}


def build_knn_query(embedding: list[float], k: int, filters: list[dict]) -> dict:
    """Build k-NN vector search query.

    Args:
        embedding: Query embedding vector (1536 dimensions).
        k: Number of nearest neighbors to retrieve.
        filters: List of filter clauses to apply.

    Returns:
        OpenSearch kNN query dictionary.
    """
    knn = {
        "embedding": {
            "vector": embedding,
            "k": k,
        }
    }

    # Add filter to kNN query if present
    if filters:
        knn["embedding"]["filter"] = {"bool": {"filter": filters}}

    return {"knn": knn}


def parse_hit_to_result(
    hit: dict,
    include_scores: bool,
    include_embedding_text: bool,
    bm25_score: float | None = None,
    vector_score: float | None = None,
    combined_score: float | None = None,
) -> ScoredProductResult:
    """Parse OpenSearch hit to ScoredProductResult.

    Args:
        hit: OpenSearch hit dictionary with _source field.
        include_scores: Whether to include relevance scores in result.
        include_embedding_text: Whether to include embedding source text.
        bm25_score: BM25 score from lexical search.
        vector_score: Cosine similarity score from vector search.
        combined_score: RRF combined score.

    Returns:
        ScoredProductResult with product data and optional scores.
    """
    source = hit["_source"]

    result = ScoredProductResult(
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

    if include_scores:
        result.score = combined_score or hit.get("_score")
        result.bm25_score = bm25_score
        result.vector_score = vector_score

    if include_embedding_text:
        result.embedding_text = source.get("embedding_text")

    return result


def build_facet_aggs() -> dict:
    """Build facet aggregations for search results.

    Returns:
        OpenSearch aggregations for manufacturers, eclass_ids, and catalogs.
    """
    return {
        "manufacturers": {"terms": {"field": "manufacturer_name.keyword", "size": 50}},
        "eclass_ids": {"terms": {"field": "eclass_id", "size": 50}},
        "catalogs": {"terms": {"field": "catalog_id", "size": 20}},
    }


def parse_facets(aggs: dict) -> Facets:
    """Parse aggregation results to Facets.

    Args:
        aggs: OpenSearch aggregations response dictionary.

    Returns:
        Facets object with manufacturers, eclass_ids, and catalogs.
    """
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
        catalogs=[
            FacetBucket(value=b["key"], count=b["doc_count"])
            for b in aggs.get("catalogs", {}).get("buckets", [])
        ],
    )


@router.post(
    "/search/hybrid", response_model=HybridSearchResponse, summary="Hybrid search"
)
async def hybrid_search(request: HybridSearchRequest) -> HybridSearchResponse:
    """
    Perform hybrid search combining BM25 lexical and vector semantic search.

    **Modes:**
    - `bm25`: Traditional full-text search with German analyzer
    - `vector`: Semantic similarity using embeddings
    - `hybrid`: Combined using Reciprocal Rank Fusion (RRF)

    **For projectAlpha integration:**
    - Pass pre-computed embeddings to avoid server-side embedding generation
    - Use `include_scores=true` to get individual BM25/vector scores for custom fusion
    - Use `catalog_id` to filter by data source

    Returns results sorted by relevance with provenance URIs for citation.
    """
    start_time = time.time()

    filters = build_filters(
        catalog_id=request.catalog_id,
        manufacturer=request.manufacturer,
        eclass_id=request.eclass_id,
        eclass_prefix=request.eclass_prefix,
        price_min=request.price_min,
        price_max=request.price_max,
    )

    # Use local variable to avoid mutating request object
    actual_mode = request.mode

    # Determine embedding
    embedding = request.embedding
    if actual_mode in ("vector", "hybrid") and embedding is None:
        # Generate embedding on server if not provided
        try:
            from src.embeddings.client import embed_single

            embedding = embed_single(request.q)
        except Exception as exc:
            logger.exception("Embedding generation failed", extra={"mode": actual_mode})
            if actual_mode == "vector":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Vector search requires embedding. "
                        f"Server embedding failed: {exc}"
                    ),
                ) from exc
            # Fall back to BM25 only for hybrid
            logger.warning(
                "Embedding generation failed; falling back to BM25-only search"
            )
            actual_mode = "bm25"

    results: list[ScoredProductResult] = []
    total = 0
    facets = None

    if actual_mode == "bm25":
        # BM25 only
        body = {
            "query": build_bm25_query(request.q, filters),
            "from": (request.page - 1) * request.size,
            "size": request.size,
            "track_total_hits": True,
        }
        if request.include_facets:
            body["aggs"] = build_facet_aggs()

        response = await run_in_threadpool(
            client.search, index=settings.opensearch_index, body=body
        )
        total = response["hits"]["total"]["value"]

        for hit in response["hits"]["hits"]:
            results.append(
                parse_hit_to_result(
                    hit,
                    include_scores=request.include_scores,
                    include_embedding_text=request.include_embedding_text,
                    bm25_score=hit.get("_score"),
                )
            )

        if request.include_facets:
            facets = parse_facets(response.get("aggregations", {}))

    elif actual_mode == "vector":
        # Vector-only mode: semantic similarity search using k-NN
        # Fetches k=size*2 neighbors to ensure enough results after filtering
        body = {
            "size": request.size,
            "query": build_knn_query(embedding, k=request.size * 2, filters=filters),
            "track_total_hits": True,
        }
        if request.include_facets:
            body["aggs"] = build_facet_aggs()

        response = await run_in_threadpool(
            client.search, index=settings.opensearch_index, body=body
        )
        total = response["hits"]["total"]["value"]

        for hit in response["hits"]["hits"]:
            results.append(
                parse_hit_to_result(
                    hit,
                    include_scores=request.include_scores,
                    include_embedding_text=request.include_embedding_text,
                    vector_score=hit.get("_score"),
                )
            )

        if request.include_facets:
            facets = parse_facets(response.get("aggregations", {}))

    else:
        # Hybrid mode: combine BM25 and vector results using Reciprocal Rank Fusion
        # Fetch enough results to cover requested page, with headroom for fusion.
        fetch_size = request.size * request.page * 3

        # Execute BM25 lexical search
        bm25_body = {
            "query": build_bm25_query(request.q, filters),
            "size": fetch_size,
            "track_total_hits": True,
        }
        bm25_response = await run_in_threadpool(
            client.search, index=settings.opensearch_index, body=bm25_body
        )

        # Execute vector semantic search
        vector_body = {
            "size": fetch_size,
            "query": build_knn_query(embedding, k=fetch_size, filters=filters),
        }
        vector_response = await run_in_threadpool(
            client.search, index=settings.opensearch_index, body=vector_body
        )

        # Build rank maps: doc_id -> (rank, score, hit)
        # Rank is 1-indexed for RRF formula
        bm25_ranks: dict[str, tuple[int, float, dict]] = {}
        for rank, hit in enumerate(bm25_response["hits"]["hits"]):
            doc_id = hit["_id"]
            bm25_ranks[doc_id] = (rank + 1, hit.get("_score", 0), hit)

        vector_ranks: dict[str, tuple[int, float, dict]] = {}
        for rank, hit in enumerate(vector_response["hits"]["hits"]):
            doc_id = hit["_id"]
            vector_ranks[doc_id] = (rank + 1, hit.get("_score", 0), hit)

        # Combine all unique document IDs from both result sets
        all_doc_ids = set(bm25_ranks.keys()) | set(vector_ranks.keys())

        # Calculate weighted RRF scores for each document
        # RRF formula: sum(weight / (k + rank)) for each retrieval method
        scored_docs = []
        for doc_id in all_doc_ids:
            bm25_rank = bm25_ranks.get(doc_id, (None, None, None))[0]
            vector_rank = vector_ranks.get(doc_id, (None, None, None))[0]

            # Weighted RRF
            rrf = 0.0
            if bm25_rank is not None:
                rrf += request.bm25_weight / (request.rrf_k + bm25_rank)
            if vector_rank is not None:
                rrf += request.vector_weight / (request.rrf_k + vector_rank)

            # Get hit from whichever query found it
            hit = bm25_ranks.get(doc_id, (None, None, None))[2]
            if hit is None:
                hit = vector_ranks.get(doc_id, (None, None, None))[2]

            bm25_score = bm25_ranks.get(doc_id, (None, None, None))[1]
            vector_score = vector_ranks.get(doc_id, (None, None, None))[1]

            scored_docs.append((rrf, bm25_score, vector_score, hit))

        # Sort by RRF score descending (highest relevance first)
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        # Apply pagination to fused results
        start_idx = (request.page - 1) * request.size
        end_idx = start_idx + request.size
        page_docs = scored_docs[start_idx:end_idx]

        # Total in hybrid mode is approximate: number of fused candidates fetched.
        total = len(scored_docs)

        for rrf_score_val, bm25_score, vector_score, hit in page_docs:
            results.append(
                parse_hit_to_result(
                    hit,
                    include_scores=request.include_scores,
                    include_embedding_text=request.include_embedding_text,
                    bm25_score=bm25_score,
                    vector_score=vector_score,
                    combined_score=rrf_score_val,
                )
            )

        # Get facets from a separate query
        if request.include_facets:
            facet_body = {
                "size": 0,
                "query": (
                    {"bool": {"filter": filters}} if filters else {"match_all": {}}
                ),
                "aggs": build_facet_aggs(),
            }
            facet_response = await run_in_threadpool(
                client.search, index=settings.opensearch_index, body=facet_body
            )
            facets = parse_facets(facet_response.get("aggregations", {}))

    took_ms = int((time.time() - start_time) * 1000)

    return HybridSearchResponse(
        total=total,
        page=request.page,
        size=request.size,
        mode=actual_mode,
        results=results,
        facets=facets,
        took_ms=took_ms,
    )


@router.post(
    "/search/batch", response_model=BatchSearchResponse, summary="Batch search"
)
async def batch_search(request: BatchSearchRequest) -> BatchSearchResponse:
    """
    Execute multiple search queries in a single request.

    Optimized for RAG retrieval where multiple queries need to be resolved efficiently.
    Each query can have its own catalog filter and result size.

    Maximum 10 queries per batch.
    """
    start_time = time.time()

    batch_results: list[BatchSearchResult] = []

    for query in request.queries:
        # Build single query
        hybrid_req = HybridSearchRequest(
            q=query.q,
            embedding=query.embedding,
            mode=request.mode,
            catalog_id=query.catalog_id,
            size=query.size,
            include_scores=request.include_scores,
            include_facets=False,  # Skip facets for batch
        )

        response = await hybrid_search(hybrid_req)

        batch_results.append(
            BatchSearchResult(
                query=query.q,
                total=response.total,
                results=response.results,
            )
        )

    took_ms = int((time.time() - start_time) * 1000)

    return BatchSearchResponse(
        results=batch_results,
        took_ms=took_ms,
    )


@router.get("/catalogs", response_model=CatalogListResponse, summary="List catalogs")
async def list_catalogs() -> CatalogListResponse:
    """
    List all available catalog namespaces.

    Each catalog represents a separate BMECat XML file import.
    Use catalog_id to filter searches to specific data sources.
    """
    # Get catalog aggregation
    body = {
        "size": 0,
        "aggs": {
            "catalogs": {
                "terms": {"field": "catalog_id", "size": 100},
                "aggs": {
                    "has_embedding": {"filter": {"exists": {"field": "embedding"}}},
                    "source_files": {"terms": {"field": "source_file", "size": 1}},
                },
            },
            "total": {"value_count": {"field": "supplier_aid"}},
        },
    }

    response = await run_in_threadpool(
        client.search, index=settings.opensearch_index, body=body
    )
    aggs = response.get("aggregations", {})

    catalogs = []
    for bucket in aggs.get("catalogs", {}).get("buckets", []):
        catalog_id = bucket["key"]
        product_count = bucket["doc_count"]
        has_embeddings = bucket.get("has_embedding", {}).get("doc_count", 0) > 0

        # Get source file if available
        source_files = bucket.get("source_files", {}).get("buckets", [])
        source_file = source_files[0]["key"] if source_files else None

        catalogs.append(
            CatalogInfo(
                catalog_id=catalog_id,
                product_count=product_count,
                source_file=source_file,
                has_embeddings=has_embeddings,
            )
        )

    # Handle products without catalog_id
    total_in_catalogs = sum(c.product_count for c in catalogs)
    total_products = aggs.get("total", {}).get("value", 0)

    if total_products > total_in_catalogs:
        # There are products without catalog_id
        catalogs.insert(
            0,
            CatalogInfo(
                catalog_id="default",
                product_count=total_products - total_in_catalogs,
                source_file=None,
                has_embeddings=False,
            ),
        )

    return CatalogListResponse(
        catalogs=catalogs,
        total_products=total_products,
    )

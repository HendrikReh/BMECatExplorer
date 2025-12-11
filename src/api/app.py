"""FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.hybrid import router as hybrid_router
from src.api.routes.search import router as search_router

DESCRIPTION = """
## Product Search API

Search and retrieve products from a BMECat catalog stored in OpenSearch.

### Features

* **Full-text search** - Search across product descriptions in German
* **Faceted filtering** - Filter by manufacturer, ECLASS category, price range
* **Autocomplete** - Type-ahead suggestions for search terms
* **Pagination** - Configurable page size up to 100 results

### Data Source

Products are imported from BMECat 1.2 XML catalogs and indexed in OpenSearch
with German language analysis for optimal search relevance.

### Hybrid Search (RAG Integration)

* **Hybrid search** - Combined BM25 lexical + vector semantic search with RRF fusion
* **Batch queries** - Execute multiple queries in a single request
* **Catalog namespaces** - Filter by data source for multi-catalog deployments
* **Provenance tracking** - Source URIs for citation in RAG responses
"""

app = FastAPI(
    title="Product Search API",
    description=DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "search",
            "description": "Product search and filtering operations",
        },
        {
            "name": "hybrid",
            "description": "Hybrid search optimized for RAG retrieval",
        },
    ],
    contact={
        "name": "BMECatDemo",
    },
    license_info={
        "name": "MIT",
    },
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(search_router)
app.include_router(hybrid_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

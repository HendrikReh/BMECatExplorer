# BMECatDemo

A complete solution for importing, storing, and searching BMECat XML product catalogs. Features a REST API powered by FastAPI and OpenSearch, plus a modern web interface for browsing and exporting products with faceted search, filtering, and batch export capabilities.

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) package manager

## Quick Start

```bash
# Install dependencies
uv sync

# Start PostgreSQL and OpenSearch
just up

# Convert BMECat XML to JSONL
just convert data/BME-cat_eClass_8.xml data/products.jsonl

# Import to PostgreSQL
just import data/products.jsonl

# Index to OpenSearch
just index

# Start API server
just serve

# Start web frontend (in another terminal)
just serve-frontend
```

Or use the pipeline command for a single step:

```bash
just up
just pipeline data/BME-cat_eClass_8.xml
just serve
just serve-frontend
```

- API docs: <http://localhost:9019/docs>
- Web frontend: <http://localhost:8080>

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/search` | Full-text search with filters and facets |
| `GET /api/v1/search/autocomplete?q=` | Type-ahead suggestions |
| `GET /api/v1/products/{supplier_aid}` | Get single product |
| `GET /api/v1/facets` | List available filter values |

### Search Parameters

- `q` - Search query (searches descriptions, manufacturer, IDs)
- `manufacturer` - Filter by manufacturer name (multiple allowed)
- `eclass_id` - Filter by ECLASS classification (multiple allowed)
- `eclass_segment` - Filter by ECLASS segment/2-digit prefix (multiple allowed)
- `order_unit` - Filter by order unit (multiple allowed)
- `price_min` / `price_max` - Price range filter
- `price_band` - Predefined price ranges (0-10, 10-50, 50-200, 200-1000, 1000+)
- `exact_match` - Use exact matching for EAN/ID searches (default: false)
- `page` / `size` - Pagination

### Example

```bash
curl "http://localhost:9019/api/v1/search?q=Kabel&manufacturer=Walraven%20GmbH&size=10"
```

## Web Frontend

The web frontend provides a user-friendly interface for exploring the product catalog:

- **Full-text search** with autocomplete suggestions
- **Faceted filtering** by category, price range, unit, manufacturer, and ECLASS ID
- **Collapsible filter panels** for a clean interface
- **Exact match toggle** for precise EAN/ID searches
- **Product selection** with multi-select across pages
- **Export** selected products to CSV or JSON with metadata
- **Responsive design** with Tailwind CSS

Start the frontend with:

```bash
just serve-frontend
```

Then open <http://localhost:8080> in your browser.

## Project Structure

```text
├── main.py                 # XML → JSONL converter
├── justfile                # Task runner commands
├── docker-compose.yml      # PostgreSQL + OpenSearch
├── src/
│   ├── config.py           # Settings
│   ├── db/
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── database.py     # DB connection
│   │   └── import_jsonl.py # Data importer
│   ├── search/
│   │   ├── mapping.py      # OpenSearch index config
│   │   ├── client.py       # OpenSearch client
│   │   └── indexer.py      # DB → OpenSearch sync
│   └── api/
│       ├── app.py          # FastAPI app
│       ├── schemas.py      # Pydantic models
│       └── routes/
│           ├── search.py   # Search endpoints
│           └── hybrid.py   # Hybrid search (BM25 + vector)
├── frontend/
│   ├── app.py              # Frontend FastAPI app
│   ├── config.py           # Frontend settings
│   ├── api_client.py       # Backend API client
│   ├── templates/          # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   └── partials/       # HTMX partial templates
│   └── static/
│       ├── css/
│       └── js/main.js      # Frontend JavaScript
└── tests/
    ├── unit/               # Unit tests
    ├── integration/        # Integration tests
    └── smoke/              # Smoke tests
```

## Configuration

Environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | localhost | PostgreSQL host |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `POSTGRES_DB` | products | Database name |
| `POSTGRES_USER` | postgres | Database user |
| `POSTGRES_PASSWORD` | postgres | Database password |
| `OPENSEARCH_HOST` | localhost | OpenSearch host |
| `OPENSEARCH_PORT` | 9200 | OpenSearch port |
| `OPENSEARCH_INDEX` | products | Index name |

> **Note:** The defaults in `src/config.py` match the credentials in `docker-compose.yml`, so no `.env` file is required for local development. For production, override these values via environment variables or a `.env` file.

## Just Commands

| Command | Description |
|---------|-------------|
| `just up` | Start PostgreSQL and OpenSearch |
| `just down` | Stop containers |
| `just convert <in> <out>` | Convert XML to JSONL |
| `just import <file>` | Import JSONL to PostgreSQL |
| `just index` | Index to OpenSearch |
| `just pipeline <xml>` | Convert, import, and index |
| `just serve` | Start API server (port 9019) |
| `just serve-frontend` | Start web frontend (port 8080) |
| `just test` | Run all tests |
| `just test-unit` | Run unit tests |
| `just test-integration` | Run integration tests |
| `just test-smoke` | Run smoke tests |
| `just lint` | Run Ruff lint checks |
| `just format` | Format code with Black |

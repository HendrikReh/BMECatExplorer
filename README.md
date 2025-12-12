# BMECat Catalog‑Explorer

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](https://github.com/HendrikReh/BMECatDemo)
[![GitHub issues](https://img.shields.io/github/issues/HendrikReh/BMECatDemo)](https://github.com/HendrikReh/BMECatDemo/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/HendrikReh/BMECatDemo)](https://github.com/HendrikReh/BMECatDemo/commits)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/ruff-linting-black?logo=ruff)](https://docs.astral.sh/ruff/)
[![Black](https://img.shields.io/badge/code%20style-black-000000?logo=python&logoColor=white)](https://black.readthedocs.io/)

BMECatExplorer is an end‑to‑end, memory‑light pipeline to ingest and explore large
BMECat 1.2 product catalogs. It stream‑converts XML to JSONL, imports into
PostgreSQL, indexes to OpenSearch (BM25 and optional ), and exposes
a FastAPI backend plus a small HTMX/Tailwind UI.

**Pipeline**
1. Stream‑convert large BMECat XML → JSONL (`main.py`)
2. Import JSONL into PostgreSQL (`src/db`)
3. Index products into OpenSearch with optional OpenAI embeddings (`src/search`)
4. Serve search + hybrid RAG‑friendly endpoints via FastAPI (`src/api`)
5. Browse/export results in the frontend (`frontend/`)

**Highlights**
- Streaming XML converter (`iterparse` + `clear()`) stays O(1) memory
- Faceted BM25 search + autocomplete
- Hybrid BM25 + vector search with RRF fusion (`POST /api/v1/search/hybrid`)
- Multi‑catalog namespaces via `catalog_id` (composite uniqueness in DB + index IDs)
- Normalized **unit price** (`price_unit_amount`) for correct price filters
- Optional embeddings (`OPENAI_API_KEY`) and provenance fields for RAG

## Prerequisites
- Python 3.12+
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/)

## Quick start (single catalog)

```bash
uv sync
just up

# Convert → import → index (safe to rerun; replaces the "default" catalog)
just pipeline data/BME-cat_eClass_8.xml

just serve
just serve-frontend
```

- API docs: http://localhost:9019/docs
- Frontend: http://localhost:9018

You can also run the steps manually:

```bash
just convert data/BME-cat_eClass_8.xml data/products.jsonl
just import data/products.jsonl --replace-catalog
just index
```

## Pricing model (BMECat bundles)

BMECat prices can refer to bundles. `PRICE_AMOUNT` applies to `PRICE_QUANTITY`
units (often 100). The backend computes a normalized unit price:

```text
price_unit_amount = price_amount / price_quantity
```

- UI and API show both **unit price** and **raw amount**.
- `price_min`, `price_max`, and `price_band` filters operate on unit price.

## Multi‑catalog import/index

To keep multiple XML sources in one DB/index without ID collisions:

```bash
just up
just pipeline-catalog data/catalog_a.xml catalog_a
just pipeline-catalog data/catalog_b.xml catalog_b
```

Search can be scoped with `catalog_id=catalog_a` (repeatable).

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/search` | BM25 search with filters and facets |
| `GET /api/v1/search/autocomplete?q=` | Prefix suggestions |
| `GET /api/v1/products/{supplier_aid}` | Fetch a single product (use `?catalog_id=` if needed) |
| `GET /api/v1/facets` | Facet counts for UI |
| `POST /api/v1/search/hybrid` | BM25 / vector / hybrid RRF search |
| `POST /api/v1/search/batch` | Batch hybrid queries |
| `GET /api/v1/catalogs` | List available catalogs |

### Common query params (`/api/v1/search`)

- `q` – Full‑text query (descriptions, manufacturer, IDs)
- `manufacturer` – Manufacturer name filter (repeatable)
- `eclass_id` – Exact ECLASS ID filter (repeatable)
- `eclass_segment` – ECLASS segment/2‑digit prefix filter (repeatable)
- `order_unit` – Order unit filter (repeatable)
- `price_min` / `price_max` – **Unit price** range filter
- `price_band` – Predefined **unit price** bands (0‑10, 10‑50, 50‑200, 200‑1000, 1000+)
- `catalog_id` – Catalog namespace filter (repeatable)
- `exact_match` – Exact matches for EAN/IDs
- `page` / `size` – Pagination

Example:

```bash
curl "http://localhost:9019/api/v1/search?q=Kabel&manufacturer=Walraven%20GmbH&catalog_id=default&size=10"
```

## Commands

Run `just --list` for all tasks. Common ones:

| Command | Description |
|---------|-------------|
| `just up` / `just down` | Start/stop PostgreSQL and OpenSearch |
| `just convert <in.xml> <out.jsonl>` | XML → JSONL |
| `just convert-with-header <in.xml> <out.jsonl> <header.json>` | Convert and save header |
| `just import <file.jsonl> [--catalog-id <id>] [--source-file <xml>] [--replace-catalog]` | Load JSONL into PostgreSQL |
| `just index` / `just index-embed` | Index DB rows to OpenSearch (embeddings optional) |
| `just index-catalog <catalog_id> <source.xml>` | Append a catalog to existing index |
| `just pipeline <xml>` | Convert → import → index (replaces default catalog) |
| `just pipeline-catalog <xml> <catalog_id>` | Pipeline under a catalog namespace |
| `just serve` / `just serve-frontend` | Run backend / frontend |
| `just test-unit|test-integration|test-smoke|test` | Pytest suites |
| `just lint` / `just format` | Ruff / Black |

## Configuration

Backend env vars (via `.env` or shell) follow `src/config.py`. Key ones:

| Variable | Default | Notes |
|----------|---------|------|
| `POSTGRES_*` | from `docker-compose.yml` | DB connection |
| `OPENSEARCH_*` | from `docker-compose.yml` | OpenSearch connection |
| `OPENAI_API_KEY` | unset | Required for `index-embed` and server‑side vector fallback |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | |
| `OPENAI_EMBEDDING_DIMENSIONS` | `1536` | Must match index mapping |

Frontend uses `FRONTEND_API_BASE_URL` and related settings (see `frontend/config.py`).

## Migrations (Alembic)

For production or long‑lived databases, prefer Alembic migrations over runtime
`create_all`:

```bash
uv run alembic upgrade head
```

## Project structure

```text
├── main.py                 # XML → JSONL converter
├── alembic/                # DB migrations
├── justfile                # Task runner commands
├── docker-compose.yml      # PostgreSQL + OpenSearch
├── src/
│   ├── config.py           # Settings
│   ├── db/                 # SQLAlchemy models + importer
│   ├── search/             # OpenSearch mapping/client/indexer
│   └── api/                # FastAPI app + routes
├── frontend/               # HTMX/Tailwind web UI
└── tests/                  # unit/, integration/, smoke/
```

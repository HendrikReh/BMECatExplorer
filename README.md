# BMECatDemo

Convert BMECat XML product catalogs to JSON Lines, store in PostgreSQL, and search via OpenSearch with a FastAPI REST API.

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
```

Or use the pipeline command for a single step:

```bash
just up
just pipeline data/BME-cat_eClass_8.xml
just serve
```

API docs available at <http://localhost:9019/docs>

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/search` | Full-text search with filters and facets |
| `GET /api/v1/search/autocomplete?q=` | Type-ahead suggestions |
| `GET /api/v1/products/{supplier_aid}` | Get single product |
| `GET /api/v1/facets` | List available filter values |

### Search Parameters

- `q` - Search query (searches descriptions, manufacturer, IDs)
- `manufacturer` - Filter by manufacturer name
- `eclass_id` - Filter by ECLASS classification
- `price_min` / `price_max` - Price range filter
- `page` / `size` - Pagination

### Example

```bash
curl "http://localhost:9019/api/v1/search?q=Kabel&manufacturer=Walraven%20GmbH&size=10"
```

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
│           └── search.py   # Search endpoints
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
| `just lint` | Run Ruff lint checks |
| `just format` | Format code with Black |
| `just serve` | Start API server |
| `just test-unit` | Run unit tests |
| `just test-integration` | Run integration tests |
| `just test-smoke` | Run smoke tests |
| `just pipeline <xml>` | Convert, import, and index |

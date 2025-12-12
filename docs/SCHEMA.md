# BMECat Explorer Data Schema Documentation

## Overview

BMECat Explorer converts BMECat XML product catalogs to JSON Lines, stores them in PostgreSQL, and indexes to OpenSearch for search. This document describes the data schema for integration with external RAG systems.

---

## Data Flow

```text
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ BMECat XML   │────▶│    JSONL     │────▶│  PostgreSQL  │────▶│  OpenSearch  │
│ (source)     │     │ (products)   │     │ (truth)      │     │ (search)     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                                                      ▼
                                                               ┌──────────────┐
                                                               │  FastAPI     │
                                                               │  REST API    │
                                                               └──────────────┘
                                                                      │
                                                                      ▼
                                                               ┌──────────────┐
                                                               │ External RAG │
                                                               │ (client)     │
                                                               └──────────────┘
```

---

## PostgreSQL Schema

### products (main table)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | PK | Auto-increment primary key |
| `catalog_id` | VARCHAR(100) | NOT NULL | Catalog namespace (default: `"default"`) |
| `supplier_aid` | VARCHAR(50) | NOT NULL | Supplier article ID (unique per catalog) |
| `ean` | VARCHAR(20) | NULL | European Article Number (barcode) |
| `manufacturer_aid` | VARCHAR(50) | NULL | Manufacturer's article ID |
| `manufacturer_name` | VARCHAR(255) | NULL | Manufacturer name |
| `description_short` | TEXT | NULL | Short product description (German) |
| `description_long` | TEXT | NULL | Detailed technical description (German) |
| `delivery_time` | INTEGER | NULL | Delivery time in days |
| `order_unit` | VARCHAR(10) | NULL | Unit of measure (e.g., "C62") |
| `price_quantity` | INTEGER | NULL | Quantity the price applies to |
| `quantity_min` | INTEGER | NULL | Minimum order quantity |
| `quantity_interval` | INTEGER | NULL | Order quantity increment |
| `eclass_id` | VARCHAR(20) | NULL | ECLASS classification ID |
| `eclass_system` | VARCHAR(50) | NULL | ECLASS version (e.g., "ECLASS-8.0") |
| `daily_price` | BOOLEAN | NULL | Whether price changes daily |
| `mode` | VARCHAR(20) | NULL | Product mode ("new", "update", "delete") |
| `article_status_text` | VARCHAR(50) | NULL | Status description |
| `article_status_type` | VARCHAR(20) | NULL | Status type code |
| `source_file` | VARCHAR(255) | NULL | Original BMECat XML filename |
| `created_at` | TIMESTAMP(TZ) | NOT NULL | Record creation time (UTC) |
| `updated_at` | TIMESTAMP(TZ) | NOT NULL | Last update time (UTC) |

**Indexes:**

- `uq_products_catalog_supplier_aid` unique on (`catalog_id`, `supplier_aid`)
- `ix_products_catalog_id` on `catalog_id`
- `ix_products_ean` on `ean`
- `ix_products_manufacturer_name` on `manufacturer_name`
- `ix_products_eclass_id` on `eclass_id`

### product_prices (1:N from products)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | PK | Auto-increment primary key |
| `product_id` | INTEGER | FK, NOT NULL | References products.id (CASCADE DELETE) |
| `price_type` | VARCHAR(50) | NULL | Price type (e.g., "net_customer") |
| `amount` | DECIMAL(12,2) | NULL | Price amount |
| `currency` | VARCHAR(3) | NULL | ISO 4217 currency code (e.g., "EUR") |
| `tax` | DECIMAL(5,4) | NULL | Tax rate (e.g., 0.19 for 19%) |

**Indexes:**

- `ix_product_prices_product_id` on `product_id`

### product_media (1:N from products)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | PK | Auto-increment primary key |
| `product_id` | INTEGER | FK, NOT NULL | References products.id (CASCADE DELETE) |
| `source` | VARCHAR(255) | NULL | Filename or URL |
| `type` | VARCHAR(50) | NULL | MIME type (e.g., "image/jpeg") |
| `description` | TEXT | NULL | Media description |
| `purpose` | VARCHAR(50) | NULL | Usage purpose (e.g., "normal", "thumbnail") |

**Indexes:**

- `ix_product_media_product_id` on `product_id`

---

## OpenSearch Index Mapping

**Index name:** `products` (configurable via `OPENSEARCH_INDEX`)

### Field Mappings

| Field | Type | Analyzer | Sub-fields | Description |
|-------|------|----------|------------|-------------|
| `supplier_aid` | keyword | — | — | Exact match only |
| `ean` | keyword | — | — | Exact match only |
| `manufacturer_aid` | keyword | — | — | Exact match only |
| `manufacturer_name` | text | german | `.keyword` (keyword) | Full-text + exact faceting |
| `description_short` | text | german | `.autocomplete` (edge_ngram), `.keyword` (keyword) | Full-text + type-ahead + exact match |
| `description_long` | text | german | — | Full-text search |
| `delivery_time` | integer | — | — | Numeric filtering |
| `order_unit` | keyword | — | — | Exact match |
| `price_quantity` | integer | — | — | Numeric filtering |
| `quantity_min` | integer | — | — | Numeric filtering |
| `eclass_id` | keyword | — | — | Exact match, faceting |
| `eclass_system` | keyword | — | — | Exact match |
| `price_amount` | float | — | — | Primary price for range queries |
| `price_currency` | keyword | — | — | Exact match |
| `price_type` | keyword | — | — | Exact match |
| `prices` | nested | — | — | Full price list (type/amount/currency/tax) |
| `image` | keyword | — | — | Filename reference |
| `media` | nested | — | — | Full media list (source/type/description/purpose) |
| `catalog_id` | keyword | — | — | Catalog namespace identifier |
| `source_uri` | keyword | — | — | Provenance URI for citation |
| `source_file` | keyword | — | — | Original source file |
| `embedding` | knn_vector | — | — | 1536-dim vector for semantic search |
| `embedding_text` | text | — | — | Text used for embedding (stored only) |

### Custom Analyzers

```json
{
  "autocomplete": {
    "type": "custom",
    "tokenizer": "autocomplete_tokenizer",
    "filter": ["lowercase"]
  },
  "autocomplete_search": {
    "type": "custom",
    "tokenizer": "standard",
    "filter": ["lowercase"]
  }
}
```

**Tokenizer:**

```json
{
  "autocomplete_tokenizer": {
    "type": "edge_ngram",
    "min_gram": 2,
    "max_gram": 20,
    "token_chars": ["letter", "digit"]
  }
}
```

---

## JSONL Record Format

Each line in `products.jsonl` is a JSON object:

```json
{
  "mode": "new",
  "catalog_id": "default",
  "source_file": "BME-cat_eClass_8.xml",
  "supplier_aid": "1000864",
  "ean": "8712993543250",
  "manufacturer_aid": "50320009",
  "manufacturer_name": "Walraven GmbH",
  "description_short": "Trägerklammer 5-9mm Britclips FC8 TB 4-8mm 50320009",
  "description_long": "Ohne Schweißen oder Bohren befestigt die Federstahl-Trägerklammer...",
  "delivery_time": 5,
  "order_unit": "C62",
  "price_quantity": 100,
  "quantity_min": 100,
  "quantity_interval": 100,
  "eclass_id": "23140307",
  "eclass_system": "ECLASS-8.0",
  "daily_price": false,
  "article_status_text": null,
  "article_status_type": null,
  "prices": [
    {
      "price_type": "net_customer",
      "amount": 360.48,
      "currency": "EUR",
      "tax": 0.19
    }
  ],
  "media": [
    {
      "source": "1000864.jpg",
      "type": "image/jpeg",
      "description": "Bild zur Produktgruppe",
      "purpose": "normal"
    }
  ]
}
```

---

## Text Fields for Semantic Embedding

For hybrid RAG (BM25 + vector search), these fields are candidates for embedding:

| Field | Priority | Rationale |
|-------|----------|-----------|
| `description_short` | High | Concise product identity, good for similarity |
| `description_long` | High | Rich technical details, best semantic content |
| `manufacturer_name` | Medium | Entity-based clustering, brand search |
| `eclass_id` + `eclass_system` | Low | Structured classification anchor |

**Recommended embedding text (combined):**

```text
{description_short}. {description_long}. Hersteller: {manufacturer_name}. ECLASS: {eclass_id}
```

---

## API Endpoints

### Standard Search

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/search` | GET | Full-text search with filters and facets |
| `/api/v1/search/autocomplete` | GET | Type-ahead suggestions |
| `/api/v1/products/{supplier_aid}` | GET | Single product by ID |
| `/api/v1/facets` | GET | Available filter values |
| `/health` | GET | Health check |

**Search Parameters:**

- `q` - Search query (multi-match with fuzziness)
- `manufacturer` - Exact manufacturer filter
- `eclass_id` - Exact ECLASS filter
- `price_min` / `price_max` - Price range
- `page` / `size` - Pagination (max 100 per page)

### Hybrid Search (RAG Integration)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/search/hybrid` | POST | Hybrid BM25 + vector search with RRF fusion |
| `/api/v1/search/batch` | POST | Execute multiple queries in a single request |
| `/api/v1/catalogs` | GET | List available catalog namespaces |

#### POST /api/v1/search/hybrid

**Request body:**

```json
{
  "q": "flexible Kabelklemme für Stahlträger",
  "embedding": null,
  "mode": "hybrid",
  "rrf_k": 60,
  "bm25_weight": 0.5,
  "vector_weight": 0.5,
  "catalog_id": "supplier-2024",
  "manufacturer": null,
  "eclass_id": null,
  "eclass_prefix": "27",
  "price_min": null,
  "price_max": 500,
  "page": 1,
  "size": 20,
  "include_scores": true,
  "include_embedding_text": false,
  "include_facets": true
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | required | Natural language search query |
| `embedding` | float[] | null | Pre-computed 1536-dim query embedding |
| `mode` | string | "hybrid" | Search mode: `bm25`, `vector`, or `hybrid` |
| `rrf_k` | int | 60 | RRF constant (higher = smoother ranking) |
| `bm25_weight` | float | 0.5 | Weight for BM25 score in fusion |
| `vector_weight` | float | 0.5 | Weight for vector score in fusion |
| `catalog_id` | string | null | Filter by catalog namespace |
| `eclass_prefix` | string | null | Filter by ECLASS hierarchy prefix |
| `include_scores` | bool | true | Include individual BM25/vector scores |
| `include_embedding_text` | bool | false | Include text used to generate embedding |
| `include_facets` | bool | true | Include facet aggregations |

**Response:**

```json
{
  "total": 150,
  "page": 1,
  "size": 20,
  "mode": "hybrid",
  "results": [
    {
      "supplier_aid": "1000864",
      "ean": "8712993543250",
      "manufacturer_name": "Walraven GmbH",
      "description_short": "Trägerklammer 5-9mm...",
      "description_long": "...",
      "eclass_id": "23140307",
      "price_amount": 360.48,
      "price_currency": "EUR",
      "catalog_id": "supplier-2024",
      "source_uri": "bmecat://supplier-2024/1000864",
      "score": 0.0312,
      "bm25_score": 12.45,
      "vector_score": 0.87
    }
  ],
  "facets": {
    "manufacturers": [{"value": "Walraven GmbH", "count": 45}],
    "eclass_ids": [{"value": "23140307", "count": 32}],
    "catalogs": [{"value": "supplier-2024", "count": 150}]
  },
  "took_ms": 45
}
```

#### POST /api/v1/search/batch

Execute multiple queries efficiently in a single request (max 10 queries).

**Request body:**

```json
{
  "queries": [
    {"q": "Kabelklemme", "embedding": null, "catalog_id": null, "size": 10},
    {"q": "Rohrschelle verzinkt", "embedding": null, "catalog_id": "supplier-2024", "size": 5}
  ],
  "mode": "hybrid",
  "include_scores": true
}
```

**Response:**

```json
{
  "results": [
    {
      "query": "Kabelklemme",
      "total": 85,
      "results": [...]
    },
    {
      "query": "Rohrschelle verzinkt",
      "total": 23,
      "results": [...]
    }
  ],
  "took_ms": 120
}
```

#### GET /api/v1/catalogs

List all available catalog namespaces.

**Response:**

```json
{
  "catalogs": [
    {
      "catalog_id": "supplier-2024",
      "product_count": 15000,
      "source_file": "supplier_catalog_2024.xml",
      "has_embeddings": true
    },
    {
      "catalog_id": "default",
      "product_count": 5000,
      "source_file": null,
      "has_embeddings": false
    }
  ],
  "total_products": 20000
}
```

---

## ECLASS Classification System

### About ECLASS

ECLASS is a hierarchical product classification standard widely used in B2B e-commerce, especially in German-speaking markets. The `eclass_id` field contains an 8-digit code representing the product category.

### ECLASS ID Structure

```text
ECLASS ID: 27062010
           ││││││││
           ││││││└┴── Commodity (basic category): 10
           ││││└┴──── Sub-group: 20
           ││└┴────── Main group: 06
           └┴──────── Segment: 27
```

**Hierarchy levels:**

| Level | Digits | Example | Description |
|-------|--------|---------|-------------|
| Segment | 1-2 | `27` | Elektrotechnik, Automation, Prozessleittechnik |
| Main group | 3-4 | `27-06` | Kabel, Leitungen, Installationsrohre |
| Sub-group | 5-6 | `27-06-20` | Kabelbefestigung, Kabeldurchführung |
| Commodity | 7-8 | `27-06-20-10` | Kabelschellen, Rohrschellen |

### Common ECLASS IDs in Dataset

| ECLASS ID | Category (German) | Translation |
|-----------|-------------------|-------------|
| `27062010` | Kabelschellen, Rohrschellen | Cable clamps, pipe clamps |
| `23140307` | Trägerklammer | Beam clamps |
| `27062001` | Kabelkanal | Cable trunking |
| `27400602` | Kabelverbinder | Cable connectors |

### ECLASS System Version

The `eclass_system` field indicates the ECLASS version used (e.g., `ECLASS-8.0`). Different versions may have different category structures.

### Using ECLASS for RAG

**Filtering:** Use ECLASS ID prefix matching for hierarchical filtering:

- Segment: `eclass_id LIKE '27%'` (all electrical products)
- Main group: `eclass_id LIKE '2706%'` (cables and installations)
- Sub-group: `eclass_id LIKE '270620%'` (cable fastening)

**Faceting:** Group products by ECLASS segment or main group for category navigation.

**Semantic hints:** Include ECLASS in embeddings to cluster similar product types.

---

## OpenSearch Query Examples

### 1. Full-Text Search (BM25)

**Simple search:**

```json
{
  "query": {
    "multi_match": {
      "query": "Kabel 3x1.5mm",
      "fields": ["description_short^3", "description_long", "manufacturer_name^2"],
      "type": "best_fields",
      "fuzziness": "AUTO"
    }
  }
}
```

### 2. Filtered Search

**Price range + manufacturer:**

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "description_short": "Trägerklammer" } }
      ],
      "filter": [
        { "term": { "manufacturer_name.keyword": "Walraven GmbH" } },
        { "range": { "price_amount": { "gte": 100, "lte": 500 } } }
      ]
    }
  }
}
```

### 3. ECLASS Hierarchy Filter

**All products in segment 27 (Elektrotechnik):**

```json
{
  "query": {
    "bool": {
      "filter": [
        { "prefix": { "eclass_id": "27" } }
      ]
    }
  }
}
```

### 4. Aggregations (Facets)

**Get manufacturer counts:**

```json
{
  "size": 0,
  "aggs": {
    "manufacturers": {
      "terms": { "field": "manufacturer_name.keyword", "size": 50 }
    },
    "eclass_segments": {
      "terms": { "field": "eclass_id", "size": 50 }
    },
    "price_ranges": {
      "range": {
        "field": "price_amount",
        "ranges": [
          { "to": 50 },
          { "from": 50, "to": 200 },
          { "from": 200, "to": 500 },
          { "from": 500 }
        ]
      }
    }
  }
}
```

### 5. Autocomplete Query

**Edge n-gram prefix matching:**

```json
{
  "query": {
    "match": {
      "description_short.autocomplete": {
        "query": "Kab",
        "operator": "and"
      }
    }
  },
  "size": 10,
  "_source": ["description_short", "supplier_aid"]
}
```

### 6. Hybrid Search (BM25 + kNN)

**Combined lexical and vector search:**

```json
{
  "query": {
    "hybrid": {
      "queries": [
        {
          "match": {
            "description_short": {
              "query": "flexible cable clamp"
            }
          }
        },
        {
          "knn": {
            "embedding": {
              "vector": [0.1, -0.2],
              "k": 10
            }
          }
        }
      ]
    }
  }
}
```

---

## Data Quality & Constraints

### Field Constraints

| Field | Constraints | Validation |
|-------|-------------|------------|
| `supplier_aid` | REQUIRED, UNIQUE | Max 50 chars, alphanumeric |
| `ean` | Optional | 8-14 digits (GTIN-8/13/14) |
| `manufacturer_name` | Optional | Max 255 chars |
| `description_short` | Optional | German text, variable length |
| `description_long` | Optional | German text, may contain HTML entities |
| `eclass_id` | Optional | 8 digits, must be valid ECLASS code |
| `price_amount` | Optional | Decimal >= 0, up to 12 digits |
| `currency` | Optional | ISO 4217 (usually "EUR") |

### Null Handling

| Field | Null Frequency | RAG Implications |
|-------|----------------|------------------|
| `description_long` | ~5% | Skip in embedding if null |
| `price_amount` | ~2% | Exclude from price filters |
| `ean` | ~10% | Cannot use for barcode lookup |
| `eclass_id` | <1% | Cannot use for category filtering |
| `manufacturer_name` | <1% | Falls back to manufacturer_aid |

### Data Cleaning Notes

1. **HTML entities:** `description_long` may contain `&amp;`, `&lt;`, etc.
2. **German characters:** Text includes umlauts (ä, ö, ü) and ß
3. **Unit codes:** `order_unit` uses UN/CEFACT codes (e.g., "C62" = piece)
4. **Price context:** `price_amount` is for `price_quantity` units (often 100)

### Duplicate Detection

**Primary key:** `supplier_aid` (unique per supplier)

**Near-duplicate detection for RAG:**

- Same `ean` but different `supplier_aid` → may be same product
- Same `manufacturer_aid` + `manufacturer_name` → likely same product
- High embedding similarity (>0.95) → semantic duplicates

---

## Hybrid RAG Integration

### Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                        External RAG                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │
│  │ Query Parser │──▶│ Retriever    │──▶│ Reranker     │         │
│  │ (LLM)        │   │ (Hybrid)     │   │ (Cross-enc.) │         │
│  └──────────────┘   └──────────────┘   └──────────────┘         │
│         │                  │                   │                │
└─────────┼──────────────────┼───────────────────┼────────────────┘
          │                  │                   │
          ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BMECat Explorer API                           │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │
│  │ /search      │   │ /search/     │   │ /products/   │         │
│  │ (BM25+kNN)   │   │ hybrid       │   │ {id}         │         │
│  └──────────────┘   └──────────────┘   └──────────────┘         │
│         │                  │                   │                │
└─────────┼──────────────────┼───────────────────┼────────────────┘
          │                  │                   │
          ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OpenSearch                                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ products index                                       │       │
│  │  - text fields (German analyzer)                     │       │
│  │  - embedding (knn_vector, 1536 dim)                  │       │
│  │  - keyword fields (faceting)                         │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### OpenSearch kNN Configuration

**Index mapping for vector search:**

```json
{
  "mappings": {
    "properties": {
      "embedding": {
        "type": "knn_vector",
        "dimension": 1536,
        "method": {
          "name": "hnsw",
          "space_type": "innerproduct",
          "engine": "faiss",
          "parameters": {
            "ef_construction": 128,
            "m": 16
          }
        }
      },
      "embedding_text": {
        "type": "text",
        "index": false
      }
    }
  },
  "settings": {
    "index": {
      "knn": true
    }
  }
}
```

> **Note:** Uses Faiss engine with `innerproduct` space type. OpenAI embeddings are pre-normalized, so `innerproduct` is equivalent to cosine similarity. Faiss supports dimensions >1024 (Lucene is limited to 1024).

### Embedding Generation

**Text preparation:**

```python
def prepare_embedding_text(product: dict) -> str:
    """Combine text fields for embedding."""
    parts = []

    if product.get("description_short"):
        parts.append(product["description_short"])

    if product.get("description_long"):
        # Clean HTML entities, limit length
        desc = clean_html(product["description_long"])[:2000]
        parts.append(desc)

    if product.get("manufacturer_name"):
        parts.append(f"Hersteller: {product['manufacturer_name']}")

    if product.get("eclass_id"):
        parts.append(f"ECLASS: {product['eclass_id']}")

    return ". ".join(parts)
```

**Batch embedding with OpenAI:**

```python
from openai import OpenAI

client = OpenAI()

def embed_batch(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    response = client.embeddings.create(
        input=texts,
        model=model
    )
    return [item.embedding for item in response.data]
```

### RRF Fusion Algorithm

The hybrid search uses Reciprocal Rank Fusion (RRF) to combine BM25 and vector results:

```python
def rrf_score(bm25_rank: int | None, vector_rank: int | None, k: int = 60) -> float:
    """Calculate weighted RRF score."""
    score = 0.0
    if bm25_rank is not None:
        score += bm25_weight / (k + bm25_rank)
    if vector_rank is not None:
        score += vector_weight / (k + vector_rank)
    return score
```

**RRF Parameters:**

- `rrf_k`: Smoothing constant (default 60). Higher values reduce the impact of top ranks.
- `bm25_weight` / `vector_weight`: Relative importance of each retrieval method.

### Provenance and Citation

Each result includes provenance fields for RAG citation:

| Field | Format | Example |
|-------|--------|---------|
| `catalog_id` | Namespace identifier | `"supplier-2024"` |
| `source_uri` | URI for citation | `"bmecat://supplier-2024/1000864"` |

Use `source_uri` in RAG responses to provide evidence attribution.

### Cost Estimation

**OpenAI text-embedding-3-small:**

- Price: $0.00002 per 1K tokens
- Avg product text: ~200 tokens
- 2M products: ~400M tokens = **$8**

**OpenSearch kNN:**

- Memory: 1536 dims × 4 bytes × 2M docs = ~12 GB
- Consider HNSW parameters based on available memory

"""OpenSearch index mapping for products with hybrid search support."""

from src.config import settings

INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index": {
            "knn": True,  # Enable k-NN for vector search
        },
        "analysis": {
            "analyzer": {
                "autocomplete": {
                    "type": "custom",
                    "tokenizer": "autocomplete_tokenizer",
                    "filter": ["lowercase"],
                },
                "autocomplete_search": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase"],
                },
            },
            "tokenizer": {
                "autocomplete_tokenizer": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20,
                    "token_chars": ["letter", "digit"],
                }
            },
        },
    },
    "mappings": {
        "properties": {
            # Identifiers
            "supplier_aid": {"type": "keyword"},
            "ean": {"type": "keyword"},
            "manufacturer_aid": {"type": "keyword"},
            # Catalog/provenance (for multi-catalog support)
            "catalog_id": {"type": "keyword"},
            "source_uri": {"type": "keyword"},
            "source_file": {"type": "keyword"},
            # Text fields with German analyzer
            "manufacturer_name": {
                "type": "text",
                "analyzer": "german",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "description_short": {
                "type": "text",
                "analyzer": "german",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search",
                    }
                },
            },
            "description_long": {"type": "text", "analyzer": "german"},
            # Numeric fields
            "delivery_time": {"type": "integer"},
            "order_unit": {"type": "keyword"},
            "price_quantity": {"type": "integer"},
            "quantity_min": {"type": "integer"},
            # Classification
            "eclass_id": {"type": "keyword"},
            "eclass_name": {"type": "keyword"},
            "eclass_system": {"type": "keyword"},
            # Pricing
            "price_amount": {"type": "float"},
            # Normalized unit price (price_amount / price_quantity when available)
            "price_unit_amount": {"type": "float"},
            "price_currency": {"type": "keyword"},
            "price_type": {"type": "keyword"},
            "prices": {
                "type": "nested",
                "properties": {
                    "price_type": {"type": "keyword"},
                    "amount": {"type": "float"},
                    "currency": {"type": "keyword"},
                    "tax": {"type": "float"},
                },
            },
            # Media
            "image": {"type": "keyword"},
            "media": {
                "type": "nested",
                "properties": {
                    "source": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "description": {"type": "text", "index": False},
                    "purpose": {"type": "keyword"},
                },
            },
            # Embedding for vector search (using Faiss engine)
            # Faiss supports dimensions >1024; Lucene is limited to 1024.
            # Using innerproduct with normalized OpenAI embeddings ~= cosine similarity.
            "embedding": {
                "type": "knn_vector",
                "dimension": settings.openai_embedding_dimensions,
                "method": {
                    "name": "hnsw",
                    "space_type": "innerproduct",
                    "engine": "faiss",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 16,
                    },
                },
            },
            # Text used to generate embedding (for debugging/provenance)
            "embedding_text": {
                "type": "text",
                "index": False,  # Not searchable, just stored
            },
        }
    },
}

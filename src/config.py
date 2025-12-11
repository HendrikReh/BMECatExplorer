"""Application configuration via environment variables.

Default values are intended for local development only.
Production deployments should override via .env file or environment variables.

Security considerations:
- postgres_password: Override with a strong password in production
- api_host: Consider restricting to specific IPs in production
- opensearch_use_ssl: Enable SSL/TLS in production
- openai_api_key: Store securely, never commit to version control
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "products"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # OpenSearch
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_index: str = "products"
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 9019

    # OpenAI Embeddings
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    embedding_batch_size: int = 100

    # ECLASS metadata
    eclass_names_path: str | None = "data/eclass_names.json"

    @property
    def postgres_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def postgres_url_sync(self) -> str:
        return f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def opensearch_url(self) -> str:
        return f"http://{self.opensearch_host}:{self.opensearch_port}"


settings = Settings()

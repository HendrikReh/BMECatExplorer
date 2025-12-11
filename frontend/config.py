"""Frontend configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class FrontendSettings(BaseSettings):
    """Configuration for the web frontend application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FRONTEND_",
        extra="ignore",
    )

    # Backend API connection
    api_base_url: str = "http://localhost:9019"

    # Frontend server
    host: str = "0.0.0.0"
    port: int = 9018

    # Display settings
    default_page_size: int = 25
    max_export_rows: int = 10000


settings = FrontendSettings()

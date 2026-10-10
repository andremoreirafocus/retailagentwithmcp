"""Validated configuration for the Order Management MCP server."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables or mcp/.env locally."""

    mcp_api_key: str = Field(validation_alias="MCP_API_KEY", min_length=1)
    database_url: str = Field(validation_alias="DATABASE_URL", min_length=1)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

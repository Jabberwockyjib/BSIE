"""Application configuration."""
import os
from pathlib import Path
from typing import Optional

import toml
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings."""

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://bsie:bsie@localhost:5432/bsie",
        description="PostgreSQL connection URL"
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # Storage
    storage_path: Path = Field(
        default=Path("./storage"),
        description="Path for PDF and artifact storage"
    )

    # API
    api_prefix: str = Field(
        default="/api/v1",
        description="API route prefix"
    )

    # Debug
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """Load settings from TOML file and environment."""
    config_data = {}

    if config_path and config_path.exists():
        raw = toml.load(config_path)
        # Flatten nested config
        if "database" in raw:
            config_data["database_url"] = raw["database"].get("url")
        if "redis" in raw:
            config_data["redis_url"] = raw["redis"].get("url")
        if "storage" in raw:
            config_data["storage_path"] = raw["storage"].get("path")
        if "api" in raw:
            config_data["api_prefix"] = raw["api"].get("prefix")
        if "debug" in raw:
            config_data["debug"] = raw.get("debug")

    # Filter None values
    config_data = {k: v for k, v in config_data.items() if v is not None}

    return Settings(**config_data)


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        config_path = Path(os.environ.get("BSIE_CONFIG", "config/app.toml"))
        _settings = load_settings(config_path)
    return _settings

"""Configuration tests."""
from pathlib import Path

from bsie.config import Settings, load_settings


def test_settings_has_required_fields():
    settings = Settings()
    assert hasattr(settings, "database_url")
    assert hasattr(settings, "redis_url")
    assert hasattr(settings, "storage_path")


def test_settings_loads_defaults():
    settings = Settings()
    assert settings.api_prefix == "/api/v1"
    assert settings.debug is False


def test_load_settings_from_toml(tmp_path):
    config_file = tmp_path / "app.toml"
    config_file.write_text('''
[database]
url = "postgresql+asyncpg://test:test@localhost/test"

[redis]
url = "redis://localhost:6379/1"

[storage]
path = "/tmp/bsie"
''')

    settings = load_settings(config_file)
    assert settings.database_url == "postgresql+asyncpg://test:test@localhost/test"
    assert settings.redis_url == "redis://localhost:6379/1"
    assert settings.storage_path == Path("/tmp/bsie")

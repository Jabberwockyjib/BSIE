"""Template registry tests."""
import pytest
from pathlib import Path

from sqlalchemy import select

from bsie.db.models import TemplateMetadata
from bsie.templates.registry import TemplateRegistry


def test_registry_instantiation(tmp_path):
    """Registry should instantiate with a templates directory."""
    registry = TemplateRegistry(templates_dir=tmp_path)
    assert registry.templates_dir == tmp_path


def test_registry_default_templates_dir():
    """Registry should have a default templates directory."""
    registry = TemplateRegistry()
    assert registry.templates_dir is not None
    assert "templates" in str(registry.templates_dir)


def test_registry_templates_dict_empty_initially(tmp_path):
    """Registry should have empty templates dict before loading."""
    registry = TemplateRegistry(templates_dir=tmp_path)
    assert len(registry.templates) == 0


@pytest.fixture
def sample_template_toml():
    """Sample TOML template content."""
    return '''
[metadata]
template_id = "test_bank_checking_v1"
version = "1.0.0"
bank_family = "test_bank"
statement_type = "checking"
segment = "personal"
description = "Test bank checking template"

[detect]
keywords = ["TEST BANK", "CHECKING"]
required_text = ["Account Activity"]
'''


def test_load_template_from_file(tmp_path, sample_template_toml):
    """Registry should load a single template from a file."""
    template_file = tmp_path / "test_bank" / "checking_v1.toml"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(sample_template_toml)

    registry = TemplateRegistry(templates_dir=tmp_path)
    template = registry.load_template(template_file)

    assert template.metadata.template_id == "test_bank_checking_v1"
    assert template.metadata.bank_family == "test_bank"


def test_load_all_templates(tmp_path, sample_template_toml):
    """Registry should load all templates from directory."""
    # Create multiple template files
    (tmp_path / "bank_a").mkdir()
    (tmp_path / "bank_b").mkdir()

    (tmp_path / "bank_a" / "checking_v1.toml").write_text(
        sample_template_toml.replace("test_bank_checking_v1", "bank_a_checking_v1")
        .replace("test_bank", "bank_a")
    )
    (tmp_path / "bank_b" / "savings_v1.toml").write_text(
        sample_template_toml.replace("test_bank_checking_v1", "bank_b_savings_v1")
        .replace("test_bank", "bank_b")
        .replace("checking", "savings")
    )

    registry = TemplateRegistry(templates_dir=tmp_path)
    loaded = registry.load_all()

    assert loaded == 2
    assert len(registry.templates) == 2
    assert "bank_a_checking_v1" in registry.templates
    assert "bank_b_savings_v1" in registry.templates


def test_load_all_skips_invalid_templates(tmp_path, sample_template_toml):
    """Registry should skip invalid templates and continue loading."""
    (tmp_path / "valid.toml").write_text(sample_template_toml)
    (tmp_path / "invalid.toml").write_text("[metadata]\n# Missing required fields")

    registry = TemplateRegistry(templates_dir=tmp_path)
    loaded = registry.load_all()

    assert loaded == 1
    assert "test_bank_checking_v1" in registry.templates


@pytest.mark.asyncio
async def test_sync_to_database(db_session, tmp_path, sample_template_toml):
    """Registry should sync template metadata to Postgres."""
    template_file = tmp_path / "test_bank" / "checking_v1.toml"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(sample_template_toml)

    registry = TemplateRegistry(templates_dir=tmp_path)
    registry.load_all()

    synced = await registry.sync_to_database(db_session, git_sha="abc123def")

    assert synced == 1

    # Verify in database
    result = await db_session.execute(
        select(TemplateMetadata).where(
            TemplateMetadata.template_id == "test_bank_checking_v1"
        )
    )
    meta = result.scalar_one()
    assert meta.bank_family == "test_bank"
    assert meta.git_sha == "abc123def"
    assert meta.status == "draft"


@pytest.mark.asyncio
async def test_sync_updates_existing_metadata(db_session, tmp_path, sample_template_toml):
    """Registry should update existing metadata on re-sync."""
    template_file = tmp_path / "test.toml"
    template_file.write_text(sample_template_toml)

    registry = TemplateRegistry(templates_dir=tmp_path)
    registry.load_all()

    # First sync
    await registry.sync_to_database(db_session, git_sha="sha_v1")

    # Second sync with new git_sha
    await registry.sync_to_database(db_session, git_sha="sha_v2")

    # Should have updated, not duplicated
    result = await db_session.execute(
        select(TemplateMetadata).where(
            TemplateMetadata.template_id == "test_bank_checking_v1"
        )
    )
    records = result.scalars().all()
    assert len(records) == 1
    assert records[0].git_sha == "sha_v2"

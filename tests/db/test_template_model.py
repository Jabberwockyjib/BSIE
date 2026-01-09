"""Template model tests."""
import pytest
from datetime import datetime, timezone

from bsie.db.models import TemplateMetadata


def test_template_metadata_model():
    meta = TemplateMetadata(
        template_id="chase_checking_v1",
        version="1.0.0",
        bank_family="chase",
        statement_type="checking",
        segment="personal",
        git_sha="abc123",
        file_path="templates/chase/checking_personal_v1.toml",
        status="stable",
    )
    assert meta.template_id == "chase_checking_v1"
    assert meta.status == "stable"


@pytest.mark.asyncio
async def test_template_metadata_persistence(db_session):
    meta = TemplateMetadata(
        template_id="chase_checking_v1",
        version="1.0.0",
        bank_family="chase",
        statement_type="checking",
        segment="personal",
        git_sha="abc123",
        file_path="templates/chase/checking_personal_v1.toml",
        status="stable",
    )
    db_session.add(meta)
    await db_session.commit()

    from sqlalchemy import select
    result = await db_session.execute(
        select(TemplateMetadata).where(TemplateMetadata.template_id == "chase_checking_v1")
    )
    loaded = result.scalar_one()
    assert loaded.bank_family == "chase"

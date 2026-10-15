import pytest

from app.core.config import Settings


@pytest.mark.parametrize("scheme", ["postgresql://", "postgres://", "postgresql+asyncpg://"])
def test_database_url_always_uses_asyncpg(scheme):
    settings = Settings(_env_file=None, database_url=f"{scheme}u:p@localhost:5432/db")
    assert settings.database_url == "postgresql+asyncpg://u:p@localhost:5432/db"

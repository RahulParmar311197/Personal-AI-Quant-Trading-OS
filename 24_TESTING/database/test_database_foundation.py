from app.core.config import Settings
from app.core.database import Base


def test_database_url_is_configurable() -> None:
    settings = Settings(database_url="postgresql+psycopg://user:pass@localhost/testdb")
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_database_metadata_starts_empty_before_domain_gates() -> None:
    assert len(Base.metadata.tables) == 0

from app.core.config import Settings
from app.core.database import Base
from app.models import Bar, ExecutionOrder, Instrument


def test_database_url_is_configurable() -> None:
    settings = Settings(database_url="postgresql+psycopg://user:pass@localhost/testdb")
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_domain_tables_are_registered() -> None:
    assert {"instruments", "bars", "execution_orders"} <= set(Base.metadata.tables)
    assert Base.metadata.tables["instruments"] is Instrument.__table__
    assert Base.metadata.tables["bars"] is Bar.__table__
    assert Base.metadata.tables["execution_orders"] is ExecutionOrder.__table__

"""Regression tests for the SQLAlchemy model import graph."""


def test_database_module_imports_all_persistence_models_without_cycle() -> None:
    from app.core.database import Base
    from app.models import Bar, ExecutionOrder, Instrument

    assert {"instruments", "bars", "execution_orders"} <= set(Base.metadata.tables)
    assert Base.metadata.tables["instruments"] is Instrument.__table__
    assert Base.metadata.tables["bars"] is Bar.__table__
    assert Base.metadata.tables["execution_orders"] is ExecutionOrder.__table__

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base for application SQLAlchemy models."""


settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield one database session and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Import concrete model modules after Base is declared. Do not import the
# aggregate app.models package here: it imports models that depend on Base,
# which creates a circular import during application/test initialization.
from app.models.execution import ExecutionOrder  # noqa: E402,F401
from app.models.market_data import Bar, Instrument  # noqa: E402,F401

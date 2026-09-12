"""SQLAlchemy declarative base isolated from database engine/session wiring."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class shared by all persistence models."""

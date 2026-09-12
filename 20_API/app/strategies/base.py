"""Provider-neutral strategy contracts.

A strategy observes point-in-time market context and emits research evidence.
It never creates broker orders, bypasses risk, or owns execution permission.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Literal, Mapping

from app.market_data.contracts import HistoricalBar

StrategySide = Literal["LONG", "SHORT", "FLAT"]


@dataclass(frozen=True)
class StrategyMetadata:
    """Stable identity used for registry lookup and experiment provenance."""

    name: str
    version: str
    description: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("strategy name cannot be empty")
        if not self.version.strip():
            raise ValueError("strategy version cannot be empty")
        if any(not tag.strip() for tag in self.tags):
            raise ValueError("strategy tags cannot be empty")


@dataclass(frozen=True)
class StrategyContext:
    """Point-in-time context visible to a strategy.

    ``bars`` is a chronological prefix ending at the observation bar. A
    strategy must never receive bars after ``as_of``. Feature values are also
    supplied as a point-in-time snapshot rather than a mutable global store.
    """

    as_of: datetime
    bars: tuple[HistoricalBar, ...]
    features: Mapping[str, Decimal] = MappingProxyType({})

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        as_of_utc = self.as_of.astimezone(timezone.utc)
        previous: datetime | None = None
        for bar in self.bars:
            timestamp = bar.event_time.astimezone(timezone.utc)
            if timestamp > as_of_utc:
                raise ValueError("strategy context cannot contain future bars")
            if previous is not None and timestamp <= previous:
                raise ValueError("strategy context bars must be strictly increasing")
            previous = timestamp
        object.__setattr__(self, "features", MappingProxyType(dict(self.features)))


@dataclass(frozen=True)
class StrategySignal:
    """Non-executable strategy output consumed by the decision layer."""

    event_time: datetime
    side: StrategySide
    confidence: Decimal
    evidence: tuple[str, ...] = ()
    suggested_stop_price: Decimal | None = None
    suggested_target_price: Decimal | None = None

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("signal event_time must be timezone-aware")
        if not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("confidence must be between 0 and 1")
        if any(not item.strip() for item in self.evidence):
            raise ValueError("signal evidence entries cannot be empty")


class Strategy(ABC):
    """Base strategy contract with explicit metadata and point-in-time input."""

    metadata: StrategyMetadata

    @abstractmethod
    def evaluate(self, context: StrategyContext) -> StrategySignal | None:
        """Evaluate the current context without causing side effects."""
        raise NotImplementedError

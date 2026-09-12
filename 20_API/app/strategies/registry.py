"""Explicit registry for versioned strategy implementations."""

from collections.abc import Iterable

from app.strategies.base import Strategy, StrategyMetadata


class StrategyRegistry:
    """In-memory strategy registry with immutable identity per key.

    The registry is intentionally small and process-local for V1. Persistence,
    remote discovery, and hot-reload are separate concerns and must not weaken
    strategy provenance.
    """

    def __init__(self, strategies: Iterable[Strategy] = ()) -> None:
        self._strategies: dict[tuple[str, str], Strategy] = {}
        for strategy in strategies:
            self.register(strategy)

    def register(self, strategy: Strategy) -> None:
        metadata = _validate_metadata(strategy.metadata)
        key = (metadata.name, metadata.version)
        if key in self._strategies:
            raise ValueError(f"strategy already registered: {metadata.name}@{metadata.version}")
        self._strategies[key] = strategy

    def get(self, name: str, version: str | None = None) -> Strategy:
        if not name.strip():
            raise ValueError("strategy name cannot be empty")
        if version is not None and not version.strip():
            raise ValueError("strategy version cannot be empty")

        if version is not None:
            key = (name, version)
            try:
                return self._strategies[key]
            except KeyError as exc:
                raise KeyError(f"unknown strategy: {name}@{version}") from exc

        matches = [strategy for (strategy_name, _), strategy in self._strategies.items() if strategy_name == name]
        if not matches:
            raise KeyError(f"unknown strategy: {name}")
        if len(matches) > 1:
            raise ValueError(f"strategy version is required: {name}")
        return matches[0]

    def list_metadata(self) -> tuple[StrategyMetadata, ...]:
        return tuple(strategy.metadata for strategy in self._strategies.values())

    def __len__(self) -> int:
        return len(self._strategies)


def _validate_metadata(metadata: StrategyMetadata) -> StrategyMetadata:
    if not isinstance(metadata, StrategyMetadata):
        raise TypeError("strategy.metadata must be a StrategyMetadata instance")
    return metadata

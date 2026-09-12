"""Ports separating providers from canonical market-data ingestion."""

from abc import ABC, abstractmethod

from app.market_data.contracts import HistoricalBarRequest, HistoricalBarResult


class HistoricalDataProvider(ABC):
    """Provider adapter interface; implementations must return canonical data."""

    name: str

    @abstractmethod
    def fetch(self, request: HistoricalBarRequest) -> HistoricalBarResult:
        """Fetch one bounded page of historical bars."""
        raise NotImplementedError

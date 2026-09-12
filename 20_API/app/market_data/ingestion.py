"""Historical ingestion orchestration with validation and idempotent persistence."""

from collections.abc import Callable
from datetime import datetime, timezone

from app.market_data.contracts import HistoricalBar, HistoricalBarRequest
from app.market_data.ports import HistoricalDataProvider


class HistoricalIngestionService:
    """Normalize provider pages and hand canonical bars to a persistence sink.

    The sink is deliberately injected so the ingestion layer does not depend on
    SQLAlchemy, a particular provider, or an API transport.
    """

    def __init__(
        self,
        provider: HistoricalDataProvider,
        persist: Callable[[list[HistoricalBar]], int],
    ) -> None:
        self.provider = provider
        self.persist = persist

    def ingest(self, request: HistoricalBarRequest) -> int:
        """Consume provider pages until the requested range is complete."""
        current_start = request.start_time
        total_persisted = 0
        seen_page_starts: set[datetime] = set()

        while current_start < request.end_time:
            page_request = request.model_copy(update={"start_time": current_start})
            if current_start in seen_page_starts:
                raise RuntimeError("historical provider returned a non-advancing cursor")
            seen_page_starts.add(current_start)

            result = self.provider.fetch(page_request)
            bars = [bar for bar in result.bars if request.start_time <= bar.event_time < request.end_time]
            self._validate_page(bars, page_request)
            total_persisted += self.persist(bars)

            if result.complete:
                break

            next_start = result.next_start_time
            if next_start is None and result.bars:
                next_start = max(bar.event_time for bar in result.bars)
            if next_start is None or next_start <= current_start:
                raise RuntimeError("historical provider page did not advance ingestion cursor")
            current_start = next_start.astimezone(timezone.utc)

        return total_persisted

    @staticmethod
    def _validate_page(bars: list[HistoricalBar], request: HistoricalBarRequest) -> None:
        previous: datetime | None = None
        for bar in sorted(bars, key=lambda item: item.event_time):
            if bar.instrument_id != request.instrument_id:
                raise ValueError("provider returned a different instrument")
            if bar.timeframe != request.timeframe:
                raise ValueError("provider returned a different timeframe")
            if previous is not None and bar.event_time == previous:
                raise ValueError("duplicate event_time in provider page")
            previous = bar.event_time

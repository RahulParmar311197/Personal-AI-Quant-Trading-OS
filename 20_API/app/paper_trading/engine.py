"""Deterministic bar-driven paper execution simulator.

Paper trading intentionally has no broker/network side effects. Orders are
filled against explicitly supplied market prices and every state transition
is deterministic and auditable.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.paper_trading.models import PaperAccount, PaperFill, PaperOrder, PaperPosition


@dataclass(frozen=True)
class PaperExecutionConfig:
    fee_bps: Decimal = Decimal("0")
    slippage_bps: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("costs cannot be negative")


class PaperTradingEngine:
    """Execute explicit paper orders and maintain netted positions."""

    def __init__(self, initial_cash: Decimal, config: PaperExecutionConfig | None = None) -> None:
        self.config = config or PaperExecutionConfig()
        self.account = PaperAccount.create(initial_cash)
        self._order_counter = 0
        self._fill_counter = 0
        self._last_event_time: datetime | None = None

    def submit_market_order(
        self,
        instrument_id: str,
        side: str,
        quantity: Decimal,
        event_time: datetime,
        market_price: Decimal,
        client_order_id: str | None = None,
    ) -> PaperFill:
        """Submit and immediately fill a simulated market order."""
        if side not in ("LONG", "SHORT"):
            raise ValueError("side must be LONG or SHORT")
        if quantity <= 0 or market_price <= 0:
            raise ValueError("quantity and market_price must be positive")
        if event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        event_time = event_time.astimezone(timezone.utc)
        if self._last_event_time is not None and event_time < self._last_event_time:
            raise ValueError("paper events must be chronological")

        self._order_counter += 1
        order_id = client_order_id or f"paper-order-{self._order_counter}"
        if any(order.order_id == order_id for order in self.account.orders):
            raise ValueError("duplicate order id")
        fill_price = self._execution_price(side, market_price)
        notional = quantity * fill_price
        fee = notional * self.config.fee_bps / Decimal("10000")
        self._fill_counter += 1
        fill = PaperFill(
            fill_id=f"paper-fill-{self._fill_counter}",
            order_id=order_id,
            instrument_id=instrument_id,
            side=side,
            quantity=quantity,
            price=fill_price,
            event_time=event_time,
            fee=fee,
        )
        filled_order = PaperOrder(order_id, instrument_id, side, quantity, event_time, "FILLED")
        self._apply_fill(filled_order, fill)
        self._last_event_time = event_time
        return fill

    def mark_to_market(self, instrument_id: str, market_price: Decimal) -> Decimal:
        """Return unrealized P&L for one currently open position."""
        if market_price <= 0:
            raise ValueError("market_price must be positive")
        position = self._find_position(instrument_id)
        if position is None or position.quantity == 0:
            return Decimal("0")
        return position.quantity * (market_price - position.average_price)

    def equity(self, prices: dict[str, Decimal]) -> Decimal:
        """Return mark-to-market account equity.

        Cash already reflects trade consideration. Therefore equity is cash
        plus the current market value of open positions, rather than cash plus
        unrealized P&L (which would double-count the position cost).
        """
        market_value = Decimal("0")
        for instrument_id, market_price in prices.items():
            if market_price <= 0:
                raise ValueError("market prices must be positive")
            position = self._find_position(instrument_id)
            if position is not None and position.quantity != 0:
                market_value += position.quantity * market_price
        return self.account.cash + market_value

    def _execution_price(self, side: str, market_price: Decimal) -> Decimal:
        slippage = self.config.slippage_bps / Decimal("10000")
        return market_price * (Decimal("1") + slippage if side == "LONG" else Decimal("1") - slippage)

    def _apply_fill(self, order: PaperOrder, fill: PaperFill) -> None:
        signed_quantity = fill.quantity if fill.side == "LONG" else -fill.quantity
        existing = self._find_position(fill.instrument_id)
        positions = [p for p in self.account.positions if p.instrument_id != fill.instrument_id]
        cash_change = -signed_quantity * fill.price - fill.fee
        realized = self.account.realized_pnl

        if existing is None or existing.quantity == 0:
            new_position = PaperPosition(fill.instrument_id, signed_quantity, fill.price, Decimal("0"))
            positions.append(new_position)
        elif existing.quantity * signed_quantity > 0:
            total_qty = existing.quantity + signed_quantity
            avg = (abs(existing.quantity) * existing.average_price + abs(signed_quantity) * fill.price) / abs(total_qty)
            positions.append(PaperPosition(fill.instrument_id, total_qty, avg, existing.realized_pnl))
        else:
            closing_qty = min(abs(existing.quantity), abs(signed_quantity))
            direction = Decimal("1") if existing.quantity > 0 else Decimal("-1")
            trade_pnl = closing_qty * (fill.price - existing.average_price) * direction
            realized += trade_pnl
            remaining = existing.quantity + signed_quantity
            if remaining != 0:
                positions.append(PaperPosition(fill.instrument_id, remaining, fill.price, existing.realized_pnl + trade_pnl))

        self.account = PaperAccount(
            initial_cash=self.account.initial_cash,
            cash=self.account.cash + cash_change,
            realized_pnl=realized,
            fees_paid=self.account.fees_paid + fill.fee,
            orders=self.account.orders + (order,),
            fills=self.account.fills + (fill,),
            positions=tuple(positions),
        )

    def _find_position(self, instrument_id: str) -> PaperPosition | None:
        return next((p for p in self.account.positions if p.instrument_id == instrument_id), None)

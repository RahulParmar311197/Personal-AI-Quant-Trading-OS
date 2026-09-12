"""Read-only dashboard state endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/state")
def dashboard_state() -> dict[str, object]:
    """Expose operator-safe runtime state without credentials or order controls."""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "environment": settings.environment,
        "mode": "RESEARCH" if not settings.live_trading_allowed else "LIVE",
        "live_trading_allowed": settings.live_trading_allowed,
        "execution_mode": "PAPER_FIRST" if not settings.live_trading_allowed else "LIVE_AUTHORIZED",
        "risk_gate": "REQUIRED",
        "high_volatility_policy": "BLOCKED_BY_DEFAULT",
        "read_only": True,
        "as_of": datetime.now(timezone.utc),
    }

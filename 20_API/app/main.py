from fastapi import FastAPI

from app import __version__
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str | bool]:
    """Return process health without exposing secrets or trading state."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "live_trading_allowed": settings.live_trading_allowed,
    }
